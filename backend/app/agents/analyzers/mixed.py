"""
Mixed Analyzer — 복수 자산군 감지 시 각 서브 analyzer 를 병렬 실행하고 결과를 머지.

설계:
- router 가 `asset_class = "mixed"` 로 판별한 상태에서 호출된다.
- rows 를 자산군별로 버킷팅 (stock/crypto/fx 우선. macro 키도 존재하면 추가).
- `asyncio.gather` 로 서브 analyzer 를 동시 실행. 각 서브 결과는 "sub_analyses" 에 담아두고,
  상위 요약은 LLM 없이 결정적 규칙으로 합성 (mixed_system 프롬프트 템플릿 사용).
- 실패한 서브 analyzer 는 _partial 플래그만 달아 통과. 전체 실패 시 빈 summary 로 폴백.

orchestration 변경이 필요 없도록 본체는 analyzer_node 내부(`.run(state)`)에서
직접 서브 analyzer 를 호출한다. LangGraph 그래프는 그대로 둔다.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from app.agents.analyzers.base import BaseAnalyzer
from app.agents.llm import call_llm, extract_json
from app.agents.router import _classify_symbol
from app.agents.state import AgentState

# 로컬 import 로 circular 회피 (mixed → stock/crypto/fx → base 는 OK)
_CLASS_TO_ANALYZER = {
    "stock": "app.agents.analyzers.stock:StockAnalyzer",
    "crypto": "app.agents.analyzers.crypto:CryptoAnalyzer",
    "fx": "app.agents.analyzers.fx:FxAnalyzer",
    "macro": "app.agents.analyzers.macro:MacroAnalyzer",
}


def _bucket_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """rows 를 심볼 기반으로 자산군별 버킷에 나눠 담는다."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = None
        for k in ("symbol", "ticker", "pair", "code"):
            if k in row and isinstance(row[k], str):
                sym = row[k]
                break
        cls = _classify_symbol(sym) if sym else None
        if cls is None:
            # macro 컬럼 키가 있으면 macro 로
            if any(
                k.lower() in {"cpi", "gdp", "unemployment", "yield_10y", "fed_rate", "ppi"}
                for k in row.keys()
            ):
                cls = "macro"
        if cls:
            buckets.setdefault(cls, []).append(row)
    return buckets


def _load_analyzer(path: str) -> BaseAnalyzer:
    import importlib

    mod_name, cls_name = path.split(":")
    mod = importlib.import_module(mod_name)
    return getattr(mod, cls_name)()


def _merge_sub_outputs(sub_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """서브 analyzer 결과를 하나의 AnalyzerOutput-호환 dict 로 합성."""
    classes = sorted(sub_outputs.keys())
    if not classes:
        return {
            "asset_class": "mixed",
            "summary": "분석 가능한 자산군이 감지되지 않음.",
            "headline": "복합 포트폴리오 요약 — 데이터 부족",
            "narrative": "자산군별 심볼/컬럼을 감지하지 못했습니다.",
            "highlights": [],
            "metrics": {},
            "signals": [],
            "evidence": [],
            "confidence": 0.0,
        }

    # headline / summary
    head = f"복합 자산군 요약 ({', '.join(classes)}) — 총 {len(classes)}개 서브분석 병합"

    # narrative: 각 서브의 summary 조각을 나열
    narrative_parts: list[str] = []
    highlights: list[str] = []
    signals: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    confs: list[float] = []

    for cls in classes:
        out = sub_outputs.get(cls) or {}
        s = out.get("summary") or out.get("headline") or ""
        if s:
            narrative_parts.append(f"[{cls}] {s}")
        for h in (out.get("highlights") or [])[:2]:
            if isinstance(h, str):
                highlights.append(f"[{cls}] {h}")
        for sig in (out.get("signals") or [])[:2]:
            if isinstance(sig, dict):
                sig = {**sig, "rationale": f"[{cls}] {sig.get('rationale', '')}".strip()}
                signals.append(sig)
        for ev in (out.get("evidence") or [])[:2]:
            if isinstance(ev, dict):
                evidence.append(ev)
        # metrics 는 prefix 로 네임스페이싱
        sub_metrics = out.get("metrics") or {}
        for k, v in sub_metrics.items():
            metrics[f"{cls}__{k}"] = v
        c = out.get("confidence")
        if isinstance(c, (int, float)):
            confs.append(float(c))

    avg_conf = round(sum(confs) / len(confs), 3) if confs else 0.0

    return {
        "asset_class": "mixed",
        "headline": head,
        "narrative": " ".join(narrative_parts) or "서브분석 결과 없음.",
        "summary": head,
        "highlights": highlights[:8],
        "metrics": metrics,
        "signals": signals[:6],
        "evidence": evidence[:6],
        "confidence": avg_conf,
        "sub_analyses": sub_outputs,
    }


class MixedAnalyzer(BaseAnalyzer):
    """
    BaseAnalyzer 인터페이스를 따르지만 LLM 을 한 번만 호출하거나 0번 호출한다.
    기본 동작:
      1) rows 를 버킷팅
      2) 서브 analyzer 를 asyncio.gather 로 병렬 실행
      3) 결정적 머지 (LLM 없이). merge_with_llm=True 면 최종 정돈만 LLM 호출.
    """

    asset_class = "mixed"
    prompt_name = "mixed_system"
    #: True 면 머지 후 LLM 으로 narrative 를 다듬는다. False 는 완전 결정적.
    merge_with_llm: bool = False

    async def run(self, state: AgentState) -> dict[str, Any]:
        rows = state.get("input_data") or []
        buckets = _bucket_rows(rows)

        if not buckets:
            # 감지 실패 — 스키마 통과를 위한 최소 출력
            return {
                "asset_class": "mixed",
                "summary": "mixed 라우팅되었으나 자산군을 분리하지 못했습니다.",
                "highlights": [],
                "metrics": {},
                "signals": [],
                "evidence": [],
                "confidence": 0.0,
            }

        # 각 버킷마다 서브 analyzer 실행을 위한 서브 state 구성
        tasks: list[tuple[str, Any]] = []
        for cls, bucket_rows in buckets.items():
            analyzer_path = _CLASS_TO_ANALYZER.get(cls)
            if not analyzer_path:
                continue
            analyzer = _load_analyzer(analyzer_path)
            sub_state: dict[str, Any] = {
                **state,
                "input_data": bucket_rows,
                "asset_class": cls,
            }
            tasks.append((cls, analyzer.run(sub_state)))  # type: ignore[arg-type]

        # 병렬 실행
        sub_outputs: dict[str, dict[str, Any]] = {}
        if tasks:
            results = await asyncio.gather(
                *(coro for _, coro in tasks), return_exceptions=True
            )
            for (cls, _), res in zip(tasks, results):
                if isinstance(res, Exception):
                    sub_outputs[cls] = {
                        "asset_class": cls,
                        "summary": f"{cls} 서브분석 실패: {type(res).__name__}",
                        "_error": f"{type(res).__name__}: {res}",
                    }
                elif isinstance(res, dict):
                    sub_outputs[cls] = res

        merged = _merge_sub_outputs(sub_outputs)

        if self.merge_with_llm:
            try:
                payload = {
                    "sub_summaries": {cls: o.get("summary") for cls, o in sub_outputs.items()},
                    "merged": merged,
                }
                raw = await call_llm(
                    system_prompt_name=self.prompt_name,
                    user_content=json.dumps(payload, ensure_ascii=False, default=str),
                    max_tokens=800,
                )
                refined = extract_json(raw)
                # LLM 은 narrative/headline 만 대체, 나머지는 결정적 머지 유지
                for k in ("headline", "narrative", "summary"):
                    if k in refined and isinstance(refined[k], str):
                        merged[k] = refined[k]
            except Exception:  # noqa: BLE001 — 머지 단계 LLM 은 실패해도 OK
                pass

        return merged
