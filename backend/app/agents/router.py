"""
Meta Router 노드.

설계:
1) 먼저 **결정적 패턴 매칭** 으로 자산군을 분류한다 (LLM 호출 없이).
   - 티커 정규식(`KRW-BTC`, `005930.KS`, `USDKRW=X` …), 컬럼 힌트
   - 이 단계에서 확정되면 latency · 비용 절감 + 데모 reproducibility 확보
2) 애매하거나 혼합이면 LLM Router 를 호출해 최종 결정
3) asset_class_hint 가 있고 `auto` 가 아니면 힌트 우선(+ reason 에 힌트임을 명시)

Week-4 확장:
- CSV 업로드 입력 형태 `[{"rows":[...], "columns":[...], "source":"csv_upload"}]` 를
  인식하고 자동으로 언래핑 → heuristic 커버리지 100% 목표.
- heuristic 결정 시 router_reason 끝에 "(heuristic)" 마커 부착하여 LLM 호출 여부를
  데모 UI 에서 식별 가능하게 한다.

router_reason 은 한국어 한 문장. 데모 UI 에 그대로 노출된다.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from app.agents.llm import call_llm, extract_json
from app.agents.state import AgentState

# 티커 패턴 — 가장 강한 신호부터
_CRYPTO_PATTERNS = [
    re.compile(r"^(KRW|BTC|ETH|USDT|USDC|BUSD)-[A-Z0-9]{2,10}$"),  # KRW-BTC
    re.compile(r"^[A-Z0-9]{2,10}-(KRW|USDT|USD|USDC|BUSD)$"),       # BTC-USD
    re.compile(r"^[A-Z0-9]{2,10}/(USDT|USD|BTC|ETH|KRW)$"),         # BTC/USDT
]
_STOCK_PATTERNS = [
    re.compile(r"^\d{6}\.(KS|KQ)$"),                                # 005930.KS
    re.compile(r"^[A-Z]{1,5}$"),                                    # AAPL, TSLA
]
_FX_PATTERNS = [
    re.compile(r"^[A-Z]{3}[A-Z]{3}=X$"),                            # USDKRW=X
    re.compile(r"^[A-Z]{3}=X$"),                                    # JPY=X
    re.compile(r"^[A-Z]{3}/[A-Z]{3}$"),                             # USD/KRW
]
_MACRO_COLUMNS = {"cpi", "gdp", "unemployment", "yield_10y", "fed_rate", "ppi"}
# Week-4: CSV 헤더 기반 macro 감지 확장 (대소문자 무관)
_MACRO_COLUMN_KEYWORDS = {
    "cpi",
    "gdp",
    "unemployment",
    "yield_10y",
    "fed_rate",
    "ppi",
    "rate_hike",
    "inflation",
}
# 포트폴리오 holdings 힌트 — 이 키 두개 이상이 동시에 존재하면 holdings 행으로 간주
_PORTFOLIO_HINT_KEYS = {"market", "code", "quantity", "avg_cost"}
# CSV 헤더 기반 portfolio 감지 — symbol 도 code 대신 허용
_PORTFOLIO_CSV_REQUIRED = {"quantity", "avg_cost"}
_PORTFOLIO_CSV_SYMBOL_KEYS = {"code", "symbol"}
# macro 질의 키워드 (query 에서 탐지)
_MACRO_QUERY_KEYWORDS = ("cpi", "소비자물가", "물가지수", "gdp", "금리", "실업률", "yield", "인플레이션")

# CSV 업로드 시 값 기반 crypto/stock/fx 패턴 (컬럼·셀값 스캔)
_CRYPTO_TOKEN_HINTS = (
    "KRW-",
    "USDT-",
    "USDC-",
    "BTC-",
    "ETH-",
    "/USDT",
    "/USD",
    "/BTC",
    "/ETH",
    "BINANCE",
    "UPBIT",
)
_CRYPTO_SYMBOL_WORDS = {"BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "XRP", "ADA", "DOGE"}
_STOCK_EXCHANGE_HINTS = ("NASDAQ", "NYSE", ".KS", ".KQ", ".T", ".HK", ".L")
_FX_CURRENCY_CODES = {"USD", "EUR", "JPY", "KRW", "GBP", "CNY", "AUD", "CAD", "CHF"}
_FX_COLUMN_HINTS = {"rate", "fx_rate", "exchange_rate", "pair"}

# 우선순위: crypto > fx > stock (KRW-BTC 같은 패턴이 주식으로 오인되지 않게)
_TYPE_ORDER = ("crypto", "fx", "stock")


def _classify_symbol(sym: str) -> str | None:
    """단일 심볼을 자산군 중 하나로 분류. 못 잡으면 None."""
    if not sym or not isinstance(sym, str):
        return None
    s = sym.strip().upper()
    for pat in _CRYPTO_PATTERNS:
        if pat.match(s):
            return "crypto"
    for pat in _FX_PATTERNS:
        if pat.match(s):
            return "fx"
    for pat in _STOCK_PATTERNS:
        if pat.match(s):
            return "stock"
    return None


def _collect_symbols(rows: list[dict[str, Any]]) -> list[str]:
    """rows 에서 symbol/ticker/pair 컬럼 값들을 모은다."""
    out: list[str] = []
    keys = ("symbol", "ticker", "pair", "code")
    for row in rows:
        if not isinstance(row, dict):
            continue
        for k in keys:
            if k in row and isinstance(row[k], str):
                out.append(row[k])
                break
    return out


def _detect_macro(rows: list[dict[str, Any]]) -> bool:
    """컬럼명이 매크로 지표를 가리키면 True."""
    for row in rows[:5]:  # 앞 5개만 샘플링
        if not isinstance(row, dict):
            continue
        if any(k.lower() in _MACRO_COLUMNS for k in row.keys()):
            return True
    return False


def _detect_macro_query(query: str | None) -> bool:
    if not query:
        return False
    low = query.lower()
    return any(kw.lower() in low for kw in _MACRO_QUERY_KEYWORDS)


def _detect_holdings(rows: list[dict[str, Any]]) -> bool:
    """
    rows 가 포트폴리오 holdings 인지 판별. `market`+`code`+`quantity`+`avg_cost` 중
    2개 이상이 첫 10개 행 모두에 있으면 True.
    """
    if not rows:
        return False
    sample = [r for r in rows[:10] if isinstance(r, dict)]
    if not sample:
        return False
    hits = 0
    for r in sample:
        common = _PORTFOLIO_HINT_KEYS & set(r.keys())
        if len(common) >= 2:
            hits += 1
    return hits == len(sample)


# ───────────────────── CSV 업로드 지원 ─────────────────────


def _is_csv_upload_wrapper(rows: list[dict[str, Any]]) -> bool:
    """
    CSV 업로드 라우트가 만든 래퍼 형태인지 판별.
    형태: `[{"rows": [...], "columns": [...], "source": "csv_upload"}]`
    """
    if not rows or not isinstance(rows, list) or len(rows) != 1:
        return False
    first = rows[0]
    if not isinstance(first, dict):
        return False
    return (
        first.get("source") == "csv_upload"
        and isinstance(first.get("rows"), list)
        and isinstance(first.get("columns"), list)
    )


def _unwrap_csv_upload(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    CSV 업로드 래퍼를 풀어 (실제 rows, columns) 를 돌려준다. 래퍼가 아니면
    원본 rows 와 컬럼 추론값을 돌려준다.
    """
    if _is_csv_upload_wrapper(rows):
        wrapper = rows[0]
        inner_rows = [r for r in wrapper.get("rows", []) if isinstance(r, dict)]
        columns = [str(c) for c in wrapper.get("columns", []) if isinstance(c, (str, int))]
        if not columns and inner_rows:
            columns = list(inner_rows[0].keys())
        return inner_rows, columns
    # 래퍼가 아니더라도 첫 행 키를 컬럼으로 간주
    cols: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            cols = list(row.keys())
            break
    return rows, cols


def _columns_match_portfolio(columns_lower: set[str]) -> bool:
    """CSV 헤더가 portfolio 시그니처를 가지는지."""
    if not _PORTFOLIO_CSV_REQUIRED.issubset(columns_lower):
        return False
    # code 또는 symbol 중 하나 존재
    if not (columns_lower & _PORTFOLIO_CSV_SYMBOL_KEYS):
        return False
    # market 또는 currency 중 하나 이상 — Week-4 요구사항 정렬
    if not (columns_lower & {"market", "currency"}):
        return False
    return True


def _cell_values(rows: list[dict[str, Any]], limit: int = 20) -> list[str]:
    """앞쪽 rows 의 모든 문자열 셀값을 플랫하게 모은다 (패턴 매칭용)."""
    out: list[str] = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        for v in row.values():
            if isinstance(v, str) and v:
                out.append(v)
    return out


def _detect_csv_asset_classes(
    rows: list[dict[str, Any]],
    columns: list[str],
) -> set[str]:
    """
    CSV 컬럼 + 셀값 기반으로 감지된 자산군 집합을 반환한다. 복수 매칭 가능.
    portfolio 는 별도로 처리되므로 여기서는 포함하지 않는다.
    """
    detected: set[str] = set()
    cols_lower = {c.lower() for c in columns if isinstance(c, str)}
    upper_tokens = {c.upper() for c in columns if isinstance(c, str)}

    # macro: 컬럼명에 매크로 키워드
    for kw in _MACRO_COLUMN_KEYWORDS:
        if any(kw in c for c in cols_lower):
            detected.add("macro")
            break

    # symbol 셀값 기반으로 자산군 분류 (가장 강한 신호)
    symbols = _collect_symbols(rows)
    for s in symbols:
        cls = _classify_symbol(s)
        if cls:
            detected.add(cls)

    # 컬럼/셀값에 crypto 힌트
    flat_values = " ".join(_cell_values(rows)).upper()
    flat_columns = " ".join(upper_tokens)
    haystack = flat_values + " " + flat_columns
    if any(hint in haystack for hint in _CRYPTO_TOKEN_HINTS):
        detected.add("crypto")
    # 단독 crypto 심볼 워드 (BTC, ETH 등) — 컬럼명이나 순수 셀값으로
    if upper_tokens & _CRYPTO_SYMBOL_WORDS:
        detected.add("crypto")

    # stock 거래소 hint
    if any(hint in haystack for hint in _STOCK_EXCHANGE_HINTS):
        detected.add("stock")

    # fx: rate 컬럼 + 통화코드 또는 =X 접미
    if cols_lower & _FX_COLUMN_HINTS:
        if any(code in haystack for code in _FX_CURRENCY_CODES) or "=X" in haystack:
            detected.add("fx")
    if "=X" in haystack:
        detected.add("fx")

    return detected


def heuristic_classify(
    rows: list[dict[str, Any]],
    query: str | None = None,
) -> tuple[str | None, str, list[str]]:
    """
    결정적 분류. 성공 시 (asset_class, reason, detected_symbols), 실패 시 (None, reason, symbols).

    Week-4: CSV 업로드 래퍼(`source=csv_upload`) 를 자동 언래핑하고 헤더 기반
    패턴 매칭을 수행한다. heuristic 결정 시 reason 끝에 "(heuristic)" 마커를 붙인다.
    """
    if not rows:
        return None, "입력이 비어있음", []

    # ── Week-4: CSV 업로드면 먼저 언래핑 후 CSV 전용 경로
    if _is_csv_upload_wrapper(rows):
        inner_rows, columns = _unwrap_csv_upload(rows)
        cols_lower = {c.lower() for c in columns if isinstance(c, str)}
        symbols = _collect_symbols(inner_rows)

        # 0) portfolio: market+code/symbol+quantity+avg_cost+currency 시그니처
        if _columns_match_portfolio(cols_lower):
            return (
                "portfolio",
                f"CSV 헤더에 portfolio 시그니처({sorted(cols_lower & (_PORTFOLIO_HINT_KEYS | {'symbol', 'currency'}))}) 감지 → portfolio (heuristic)",
                symbols,
            )

        # 1) 자산군 감지 (복수 가능)
        detected = _detect_csv_asset_classes(inner_rows, columns)
        # query 키워드로 macro 보강
        if _detect_macro_query(query):
            detected.add("macro")

        if len(detected) >= 2:
            pretty = ", ".join(sorted(detected))
            return (
                "mixed",
                f"CSV 헤더·셀값에서 복수 자산군({pretty}) 감지 → mixed (heuristic)",
                symbols,
            )
        if len(detected) == 1:
            only = next(iter(detected))
            return (
                only,
                f"CSV 헤더·셀값 분석 → {only} (heuristic)",
                symbols,
            )
        # CSV 래퍼지만 아무 패턴도 없음 → LLM 위임
        return (
            None,
            "CSV 헤더에서 자산군 패턴을 찾지 못함 — LLM Router 위임",
            symbols,
        )

    # 0) holdings 감지: portfolio 가 최우선
    if _detect_holdings(rows):
        symbols = _collect_symbols(rows)
        return (
            "portfolio",
            f"holdings 형태 감지(market/code/quantity/avg_cost, n={len(rows)}) → portfolio (heuristic)",
            symbols,
        )

    symbols = _collect_symbols(rows)
    classifications = [c for c in (_classify_symbol(s) for s in symbols) if c]

    # 1) 매크로: 컬럼 또는 쿼리 키워드
    if _detect_macro(rows) and not classifications:
        return "macro", "입력 컬럼에 매크로 지표(cpi/gdp 등) 감지 → macro (heuristic)", symbols
    if _detect_macro_query(query) and not classifications:
        return "macro", f"쿼리 키워드에 매크로 지표 감지('{query}') → macro (heuristic)", symbols

    if not classifications:
        # symbol 컬럼 자체가 없음 — LLM 에 위임
        return None, "심볼 패턴을 찾지 못함 — LLM Router 위임", symbols

    counts = Counter(classifications)
    # 2개 이상 자산군이 동시에 감지되면 mixed
    distinct = {c for c, n in counts.items() if n > 0}
    if len(distinct) >= 2:
        pretty = ", ".join(sorted(distinct))
        return (
            "mixed",
            f"복수 자산군({pretty}) 심볼 공존 감지 → mixed (heuristic)",
            symbols,
        )

    # 단일 자산군이면 그대로
    top = counts.most_common(1)[0][0]
    head = symbols[0] if symbols else ""
    return top, f"입력 심볼({head}...) 패턴 매칭 → {top} (heuristic)", symbols


async def _llm_router(rows: list[dict[str, Any]], query: str | None) -> dict[str, Any]:
    """LLM Router 호출. 결정적 분류가 애매할 때만 사용."""
    preview = rows[:10]  # 토큰 절약
    user_payload = {
        "data_sample": preview,
        "row_count": len(rows),
        "query": query,
    }
    raw = await call_llm(
        system_prompt_name="router_system",
        user_content=json.dumps(user_payload, ensure_ascii=False),
        max_tokens=400,
    )
    return extract_json(raw)


async def router_node(state: AgentState) -> AgentState:
    """
    Router 노드. 순수함수 서명 — state 를 받아 새 state 를 반환.
    오류 시 error 필드에 메시지를 남기고 계속 진행 (그래프가 결정).

    Week-4: CSV 업로드 래퍼를 인식하면 언래핑된 rows 를 downstream 에 넘겨
    analyzer 가 실제 데이터를 볼 수 있게 한다.
    """
    hint = state.get("asset_class_hint")
    rows = state.get("input_data") or []

    # CSV 업로드 래퍼면 언래핑 — heuristic/LLM/analyzer 모두 실제 rows 로 동작
    unwrapped_rows = rows
    if _is_csv_upload_wrapper(rows):
        unwrapped_rows, _cols = _unwrap_csv_upload(rows)

    # 1) hint 가 있고 auto 가 아니면 힌트 우선
    if hint and hint != "auto" and hint in {"stock", "crypto", "fx", "macro", "mixed", "portfolio"}:
        return {
            **state,
            "input_data": unwrapped_rows,
            "asset_class": hint,
            "router_reason": f"사용자 hint='{hint}' 수신 → 그대로 사용",
        }

    # 2) 결정적 분류 시도 (원본 rows 로 — CSV 래퍼 감지가 여기서 일어난다)
    asset_class, reason, _symbols = heuristic_classify(rows, state.get("query"))
    if asset_class is not None:
        return {
            **state,
            "input_data": unwrapped_rows,
            "asset_class": asset_class,
            "router_reason": reason,
        }

    # 3) LLM Router 위임 (언래핑된 rows 로 토큰 절약)
    try:
        parsed = await _llm_router(unwrapped_rows, state.get("query"))
    except Exception as exc:  # noqa: BLE001 — 외부 경계이므로 광역 처리
        # LLM 실패 시 안전한 기본값 (stock) + 이유 기록
        return {
            **state,
            "input_data": unwrapped_rows,
            "asset_class": "stock",
            "router_reason": f"LLM Router 실패({type(exc).__name__}), 기본값 stock 사용",
            "error": None,  # LLM 실패는 치명적이지 않음 — 게이트가 판단
        }

    ac = parsed.get("asset_class", "stock")
    if ac not in {"stock", "crypto", "fx", "macro", "mixed", "portfolio"}:
        ac = "stock"
    return {
        **state,
        "input_data": unwrapped_rows,
        "asset_class": ac,
        "router_reason": parsed.get("router_reason", "LLM Router 결정"),
    }
