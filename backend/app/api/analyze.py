"""
/analyze 라우터.

엔드포인트:
  POST /analyze        — JSON 요청 (기존)
  POST /analyze/csv    — multipart CSV 업로드 (Week-4 신규)

공통:
  - 분석 결과 캐시 (Redis > LRU, TTL 5분)
  - 응답 헤더 X-Cache: HIT|MISS
  - X-Request-ID 헤더 자동 전파
  - 구조화 분석 이벤트 로그
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import llm as llm_module
from app.agents.graph import build_graph
from app.agents.state import AgentState
from app.core.errors import AppError
from app.core.logging import log_analyze_event, logger
from app.db.session import get_db
from app.schemas.analyze import (
    AnalyzeMeta,
    AnalyzeRequest,
    AnalyzeResponse,
    CacheMetrics,
    PortfolioContext,
)
from app.services import analyze_cache
from app.services.market.registry import get_adapter
from app.services.portfolio import build_portfolio_context

router = APIRouter(prefix="/analyze", tags=["analyze"])

# 그래프는 앱 시작 시 한 번만 컴파일 — 재진입 안전
_graph = build_graph()

_MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB
_VALID_CSV_CONTENT_TYPES = {"text/csv", "application/vnd.ms-excel", "text/plain"}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────


async def _prefetch_ohlc_rows(req: AnalyzeRequest) -> list[dict[str, Any]]:
    """
    symbol 이 오면 market 어댑터로 OHLC 90일을 프리패치해 rows 형태로 돌려준다.
    외부 호출 실패 시 빈 리스트 (degraded).
    """
    if req.symbol is None:
        return []
    try:
        adapter = get_adapter(req.symbol.market)
        bars = await adapter.fetch_ohlc(req.symbol.code, interval="1d", limit=90)
    except Exception:  # noqa: BLE001 — 외부 경계
        return []
    rows: list[dict[str, Any]] = []
    for b in bars:
        rows.append(
            {
                "symbol": req.symbol.code,
                "date": b.ts,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
        )
    return rows


def _context_rows(req: AnalyzeRequest) -> list[dict[str, Any]]:
    """req.context.ohlc 를 rows 로 변환."""
    if req.context is None or not req.context.ohlc:
        return []
    code = req.symbol.code if req.symbol else "UNKNOWN"
    return [
        {
            "symbol": code,
            "date": b.ts,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in req.context.ohlc
    ]


def _collect_evidence_snippets(output: dict[str, Any] | None) -> list[str]:
    """
    analyzer_output 에서 근거 인용문을 3~5개 추린다.
    우선순위: evidence[].claim → highlights[] → narrative/summary 첫 줄.
    """
    if not isinstance(output, dict):
        return []
    snippets: list[str] = []
    for item in output.get("evidence") or []:
        if isinstance(item, dict):
            claim = item.get("claim")
            if isinstance(claim, str) and claim.strip():
                snippets.append(claim.strip())
    for hl in output.get("highlights") or []:
        if isinstance(hl, str) and hl.strip() and hl.strip() not in snippets:
            snippets.append(hl.strip())
        if len(snippets) >= 5:
            break
    return snippets[:5]


async def _run_graph(
    rows: list[dict[str, Any]],
    query: str | None,
    asset_class_hint: str | None,
    request_id: str,
    portfolio_context: PortfolioContext | None = None,
) -> AnalyzeResponse:
    """그래프 실행 공통 로직 — JSON /analyze 와 CSV /analyze/csv 에서 재사용."""
    llm_module.reset_cache_metrics()

    # 행 수에 따라 모델 선택은 llm.select_model 이 담당 (graph 내부에서 호출됨)
    initial_state: AgentState = {
        "input_data": rows,
        "query": query,
        "asset_class_hint": asset_class_hint,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {
            "schema_gate": "pending",
            "domain_gate": "pending",
            "critique_gate": "pending",
        },
        "error": None,
        "portfolio_context": portfolio_context.model_dump(mode="json") if portfolio_context is not None else None,
    }

    t0 = time.monotonic()
    final_state: AgentState = await _graph.ainvoke(initial_state)
    latency_ms = int((time.monotonic() - t0) * 1000)

    output = final_state.get("analyzer_output")
    analyzer_name = final_state.get("asset_class") or None
    evidence_snippets = (
        _collect_evidence_snippets(output)
        if final_state["gates"].get("critique_gate", "").startswith("pass")
        else []
    )

    raw = llm_module.get_cache_metrics()
    cache = CacheMetrics(
        read_tokens=raw.get("cache_read_input_tokens", 0),
        creation_tokens=raw.get("cache_creation_input_tokens", 0),
        input_tokens=raw.get("input_tokens", 0),
        output_tokens=raw.get("output_tokens", 0),
    )

    return AnalyzeResponse(
        request_id=request_id,
        status="ok" if final_state.get("error") is None else "error",
        result=output,
        meta=AnalyzeMeta(
            asset_class=final_state["asset_class"],
            router_reason=final_state["router_reason"],
            gates=final_state["gates"],
            latency_ms=latency_ms,
            analyzer_name=analyzer_name,
            evidence_snippets=evidence_snippets,
            cache=cache,
        ),
    )


def _parse_csv_bytes(raw_bytes: bytes) -> list[dict[str, Any]]:
    """
    CSV 바이트를 list[dict] 로 파싱.

    인코딩: utf-8 우선 → 실패 시 cp949 (국내 Excel 호환).
    검증:
      - 헤더(첫 행) 필수
      - 실제 데이터 행 1개 이상 필요
    에러: ValueError (코드: CSV_INVALID)
    """
    for encoding in ("utf-8", "cp949"):
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("CSV 인코딩을 감지할 수 없습니다 (utf-8, cp949 모두 실패)")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV 헤더가 없습니다")

    rows: list[dict[str, Any]] = []
    try:
        for row in reader:
            rows.append(dict(row))
    except csv.Error as exc:
        raise ValueError(f"CSV 파싱 오류: {exc}") from exc

    if len(rows) < 1:
        raise ValueError("CSV 데이터 행이 없습니다 (헤더만 존재)")

    return rows


# ── 엔드포인트 ────────────────────────────────────────────────────────────────


@router.post("", response_model=AnalyzeResponse)
async def analyze(
    req: AnalyzeRequest,
    http_request: Request,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    임의 투자 데이터를 받아 Router → Analyzer → 3단 게이트 파이프라인을 실행한다.

    - `data` 만 주어진 경우: 그대로 분석
    - `symbol` 이 주어진 경우: market 어댑터로 OHLC 프리패치 후 주입
    - `context.ohlc` 가 주어진 경우: 그대로 rows 로 변환해 주입
    - `include_portfolio_context=True` 인 경우: DB에서 holdings를 조회해 AgentState에 주입
    """
    request_id = http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    http_response.headers["X-Request-ID"] = request_id

    # 포트폴리오 컨텍스트 빌드 (include_portfolio_context=True 일 때만)
    pctx: PortfolioContext | None = None
    portfolio_hash = ""
    if req.include_portfolio_context:
        target_market = req.symbol.market if req.symbol else None
        target_code = req.symbol.code if req.symbol else None
        pctx = await build_portfolio_context(
            db,
            user_id="demo",
            target_market=target_market,
            target_code=target_code,
        )
        if pctx is not None:
            pctx_json = json.dumps(pctx.model_dump(mode="json"), sort_keys=True)
            portfolio_hash = hashlib.sha256(pctx_json.encode()).hexdigest()[:16]

    # 캐시 조회 (포트폴리오 해시 포함)
    cache_key = analyze_cache.make_request_key(req.model_dump_json(), portfolio_hash)
    cached = await analyze_cache.cache_get(cache_key)
    if cached is not None:
        http_response.headers["X-Cache"] = "HIT"
        logger.info(
            "analyze cache HIT",
            extra={"event": "analyze_cache_hit", "request_id": request_id},
        )
        return AnalyzeResponse.model_validate(cached)

    http_response.headers["X-Cache"] = "MISS"

    # 입력 데이터 병합 순서: context.ohlc > symbol prefetch > req.data
    rows: list[dict[str, Any]] = list(req.data or [])
    if not rows:
        ctx_rows = _context_rows(req)
        if ctx_rows:
            rows = ctx_rows
        else:
            rows = await _prefetch_ohlc_rows(req)
    elif req.symbol is not None and not any("close" in r for r in rows):
        # 사용자가 data 를 주긴 했는데 OHLC 가 없으면 보강
        extra = await _prefetch_ohlc_rows(req)
        rows = rows + extra

    result = await _run_graph(rows, req.query, req.asset_class_hint, request_id, portfolio_context=pctx)

    # 캐시 저장
    await analyze_cache.cache_set(cache_key, result.model_dump())

    log_analyze_event(
        request_id=request_id,
        asset_class=result.meta.asset_class,
        duration_ms=result.meta.latency_ms or 0,
        cache_tokens=result.meta.cache.model_dump() if result.meta.cache else {},
        cached=False,
    )

    return result


@router.post(
    "/csv",
    response_model=AnalyzeResponse,
    responses={
        400: {"description": "CSV 파싱 실패 또는 빈 파일"},
        413: {"description": "파일 크기 10MB 초과"},
        415: {"description": "지원하지 않는 Content-Type"},
    },
)
async def analyze_csv(
    http_request: Request,
    http_response: Response,
    file: UploadFile = File(...),
    user_note: str = Form(""),
    symbol_hint: str = Form(""),
    include_portfolio_context: bool = Form(False),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    CSV 파일 업로드 → 자동 분석.

    - content-type: text/csv 또는 application/vnd.ms-excel
    - 파일 크기: ≤ 10MB (초과 시 413)
    - 인코딩: utf-8 / cp949 자동 탐지
    - 행 수 > 300 이면 모델을 opus 로 자동 승급
    - 결과는 파일 해시 + user_note 기반 캐시 키로 5분 캐싱
    """
    request_id = http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    http_response.headers["X-Request-ID"] = request_id

    # content-type 검증 (느슨하게 — charset 파라미터 포함 가능)
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _VALID_CSV_CONTENT_TYPES:
        raise AppError(
            status_code=415,
            code="UNSUPPORTED_MEDIA_TYPE",
            detail=f"지원하지 않는 파일 형식: {file.content_type}. text/csv 또는 application/vnd.ms-excel 만 허용합니다.",
        )

    # 파일 읽기 + 크기 검증
    raw_bytes = await file.read()
    if len(raw_bytes) > _MAX_CSV_BYTES:
        raise AppError(
            status_code=413,
            code="FILE_TOO_LARGE",
            detail=f"파일 크기가 10MB 를 초과합니다 ({len(raw_bytes) // 1024 // 1024}MB).",
        )

    if len(raw_bytes) == 0:
        raise AppError(
            status_code=400,
            code="CSV_INVALID",
            detail="빈 파일입니다.",
        )

    # CSV 파싱
    try:
        rows = _parse_csv_bytes(raw_bytes)
    except ValueError as exc:
        raise AppError(
            status_code=400,
            code="CSV_INVALID",
            detail=str(exc),
        ) from exc

    # AgentState.input_data 에 CSV 구조로 래핑
    input_data: list[dict[str, Any]] = [
        {
            "rows": rows,
            "columns": list(rows[0].keys()) if rows else [],
            "source": "csv_upload",
        }
    ]

    # 행 수 > 300 이면 asset_class_hint 에 opus 승급 시그널 포함 (graph 내 select_model 재사용)
    # 실제 모델 선택은 analyzer 노드가 llm.select_model(len(rows)) 로 결정하므로
    # input_data 에 메타를 심어 힌트 전달
    if len(rows) > llm_module.COMPLEX_ROW_THRESHOLD:
        input_data[0]["_row_count"] = len(rows)

    query = user_note if user_note else None
    asset_class_hint = symbol_hint if symbol_hint else None

    # CSV 분석: include_portfolio_context=True 면 전체 맥락만 (target 없이)
    pctx_csv: PortfolioContext | None = None
    portfolio_hash_csv = ""
    if include_portfolio_context:
        pctx_csv = await build_portfolio_context(db, user_id="demo")
        if pctx_csv is not None:
            pctx_json = json.dumps(pctx_csv.model_dump(mode="json"), sort_keys=True)
            portfolio_hash_csv = hashlib.sha256(pctx_json.encode()).hexdigest()[:16]

    # 캐시 조회 (CSV 키에는 포트폴리오 해시를 user_note 뒤에 붙여 분리)
    cache_key = analyze_cache.make_csv_key(raw_bytes, user_note + portfolio_hash_csv)
    cached = await analyze_cache.cache_get(cache_key)
    if cached is not None:
        http_response.headers["X-Cache"] = "HIT"
        logger.info(
            "analyze/csv cache HIT",
            extra={"event": "analyze_csv_cache_hit", "request_id": request_id},
        )
        return AnalyzeResponse.model_validate(cached)

    http_response.headers["X-Cache"] = "MISS"

    result = await _run_graph(input_data, query, asset_class_hint, request_id, portfolio_context=pctx_csv)

    # 캐시 저장
    await analyze_cache.cache_set(cache_key, result.model_dump())

    log_analyze_event(
        request_id=request_id,
        asset_class=result.meta.asset_class,
        duration_ms=result.meta.latency_ms or 0,
        cache_tokens=result.meta.cache.model_dump() if result.meta.cache else {},
        cached=False,
    )

    return result
