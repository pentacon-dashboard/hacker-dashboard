"""
Macro Analyzer — 경제지표(CPI, GDP, 금리, 실업률 등) 시계열 해석.

단순 템플릿 분석기. compute_indicators 기반 보편 지표는 재사용하지 못하므로
자체 helper 로 **지표별 추세 요약**을 미리 뽑는다. 결과는 `_indicators` 로 첨부되고
프롬프트는 이를 인용하도록 유도.
"""
from __future__ import annotations

import json
from typing import Any

from app.agents.analyzers.base import BaseAnalyzer
from app.agents.llm import call_llm, extract_json, select_model
from app.agents.state import AgentState

_MACRO_KEYS = ("cpi", "gdp", "unemployment", "yield_10y", "fed_rate", "ppi", "rate", "index", "value")


def _as_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _series_for(rows: list[dict[str, Any]], key: str) -> list[float]:
    out: list[float] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        v = _as_float(r.get(key))
        if v is not None:
            out.append(v)
    return out


def compute_macro_indicators(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    rows 에서 거시 지표 컬럼을 감지해 최근 추세 요약을 돌려준다.
    - series 의 첫/마지막 값, 변화율, 방향(up/down/flat)
    """
    if not rows:
        return {}

    candidate_keys: set[str] = set()
    for r in rows[:10]:
        if isinstance(r, dict):
            for k in r.keys():
                if k.lower() in _MACRO_KEYS:
                    candidate_keys.add(k)

    if not candidate_keys:
        return {}

    indicators: dict[str, Any] = {"row_count": len(rows), "series": {}}
    for k in sorted(candidate_keys):
        series = _series_for(rows, k)
        if len(series) < 1:
            continue
        first = series[0]
        last = series[-1]
        change_abs = round(last - first, 6)
        change_pct = round((last - first) / first * 100.0, 4) if first not in (0, 0.0) else None
        direction = "up" if last > first else ("down" if last < first else "flat")
        indicators["series"][k] = {
            "n": len(series),
            "first": round(first, 6),
            "last": round(last, 6),
            "change_abs": change_abs,
            "change_pct": change_pct,
            "direction": direction,
        }
    return indicators


class MacroAnalyzer(BaseAnalyzer):
    asset_class = "macro"
    prompt_name = "macro_system"

    async def run(self, state: AgentState) -> dict[str, Any]:
        rows = state.get("input_data") or []
        query = state.get("query")
        portfolio_context = state.get("portfolio_context")
        indicators = compute_macro_indicators(rows)
        raw = await self._call(
            rows=rows,
            query=query,
            indicators=indicators,
            portfolio_context=portfolio_context,
        )

        try:
            parsed = extract_json(raw)
        except ValueError as exc:
            return {
                "asset_class": self.asset_class,
                "_parse_error": str(exc),
                "_raw": raw,
            }
        parsed["asset_class"] = "macro"
        if indicators:
            parsed.setdefault("_indicators", indicators)
        return parsed

    async def _call(
        self,
        *,
        rows: list[dict[str, Any]],
        query: str | None,
        indicators: dict[str, Any] | None = None,
        portfolio_context: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "rows": rows[:50],
            "row_count": len(rows),
            "query": query,
        }
        if indicators:
            payload["indicators"] = indicators
        if portfolio_context:
            payload["portfolio_context"] = portfolio_context
        return await call_llm(
            system_prompt_name=self.prompt_name,
            user_content=json.dumps(payload, ensure_ascii=False, default=str),
            model=select_model(len(rows)),
            max_tokens=4096,
            temperature=0.2,
        )
