"""
BaseAnalyzer — 자산군 Analyzer 의 공통 추상화.

각 Analyzer 는 `run(state) -> partial_state_patch` 를 구현한다.
graph.py 의 analyzer_node 가 state.asset_class 에 맞춰 적절한 Analyzer 인스턴스를
선택해 호출한다.

Week-2 보강:
- input_data 에 OHLC 시계열이 섞여 오면(또는 state.context.ohlc 로 주입되면) 간단한
  정량 지표(최근 추세, MA20/MA60 교차, 변동성, 최대낙폭) 를 선계산해 프롬프트에 함께 전달.
- 프롬프트는 이 지표를 "evidence_snippets" 형태로 인용하도록 유도.
- 모델 선택: 행 수가 많으면 Opus 로 승급(`select_model`).
"""

from __future__ import annotations

import abc
import json
import math
from typing import Any

from app.agents.llm import call_llm, extract_json, select_model
from app.agents.state import AgentState


class BaseAnalyzer(abc.ABC):
    """자산군별 Analyzer 의 공통 인터페이스."""

    #: "stock" | "crypto" | "fx" | "macro"
    asset_class: str
    #: prompts/<name>.md 의 stem
    prompt_name: str

    async def run(self, state: AgentState) -> dict[str, Any]:
        """
        순수함수. state 를 받아 analyzer_output 에 들어갈 dict 를 반환한다.
        (state 병합은 상위 노드에서)
        """
        rows = state.get("input_data") or []
        query = state.get("query")
        portfolio_context = state.get("portfolio_context")
        indicators = compute_indicators(rows)
        raw = await self._call(
            rows=rows,
            query=query,
            indicators=indicators,
            portfolio_context=portfolio_context,
        )

        # JSON 파싱. 실패하면 schema gate 가 교정 재시도하도록 raw 를 그대로 담는다.
        try:
            parsed = extract_json(raw)
        except ValueError as exc:
            return {
                "asset_class": self.asset_class,
                "_parse_error": str(exc),
                "_raw": raw,
            }

        # asset_class 필드가 없으면 주입 (프롬프트가 빠뜨린 경우 대비)
        parsed.setdefault("asset_class", self.asset_class)
        # analyzer 가 indicator 를 무시하더라도 프런트/게이트 가 읽을 수 있게 첨부
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
        """LLM 호출. 서브클래스가 프롬프트 변수를 커스터마이즈할 때 override 가능.

        `portfolio_context` 가 None/누락이면 payload 에 해당 필드 자체를 포함하지 않는다.
        — 기존 골든 샘플과 byte-identical 재현을 위해 중요한 불변성.
        """
        payload: dict[str, Any] = {
            "rows": rows[:50],
            "row_count": len(rows),
            "query": query,
        }
        if indicators:
            payload["indicators"] = indicators
        if portfolio_context:
            payload["portfolio_context"] = portfolio_context
        user_content = json.dumps(payload, ensure_ascii=False)
        return await call_llm(
            system_prompt_name=self.prompt_name,
            user_content=user_content,
            model=select_model(len(rows)),
            max_tokens=4096,
            temperature=0.2,
        )


# ──────────────────── 정량 지표 계산 (순수함수) ────────────────────


_CLOSE_KEYS = ("close", "price", "rate", "trade_price", "latest_close", "latest_price")


def _row_close(row: dict[str, Any]) -> float | None:
    for k in _CLOSE_KEYS:
        if k in row:
            v = row[k]
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def compute_indicators(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    OHLC/시계열 rows 에서 간단한 정량 지표를 계산한다.
    행이 2개 미만이거나 종가 추출 실패 시 빈 dict 를 반환.
    """
    closes: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c = _row_close(row)
        if c is not None and c > 0:
            closes.append(c)
    if len(closes) < 2:
        return {}

    first = closes[0]
    last = closes[-1]
    period_return_pct = (last - first) / first * 100.0

    # 변동성: log-return 표준편차 (연환산 아님 — 기간 내 원시값)
    log_rets: list[float] = []
    for prev, curr in zip(closes[:-1], closes[1:]):
        if prev > 0 and curr > 0:
            log_rets.append(math.log(curr / prev))
    volatility_pct: float | None
    if log_rets:
        mean = sum(log_rets) / len(log_rets)
        var = sum((r - mean) ** 2 for r in log_rets) / len(log_rets)
        volatility_pct = math.sqrt(var) * 100.0
    else:
        volatility_pct = None

    # 최대낙폭 (Max Drawdown) — 누적 최대 대비 최저
    peak = closes[0]
    max_dd = 0.0
    for c in closes:
        if c > peak:
            peak = c
        if peak > 0:
            dd = (c - peak) / peak * 100.0
            if dd < max_dd:
                max_dd = dd

    # 이동평균 (짧은 시계열이어도 가능한 만큼)
    ma_20 = _sma(closes, 20)
    ma_60 = _sma(closes, 60)
    ma_cross: str | None = None
    if ma_20 is not None and ma_60 is not None:
        if ma_20 > ma_60:
            ma_cross = "golden"  # 단기 > 장기 (상승 추세)
        elif ma_20 < ma_60:
            ma_cross = "dead"
        else:
            ma_cross = "flat"

    # 최근 추세 — 마지막 5 포인트의 단순 기울기 부호
    tail = closes[-5:] if len(closes) >= 5 else closes
    trend = "up" if tail[-1] > tail[0] else ("down" if tail[-1] < tail[0] else "flat")

    return {
        "n": len(closes),
        "first_close": round(first, 6),
        "last_close": round(last, 6),
        "period_return_pct": round(period_return_pct, 4),
        "volatility_pct": round(volatility_pct, 4) if volatility_pct is not None else None,
        "max_drawdown_pct": round(max_dd, 4),
        "ma_20": round(ma_20, 6) if ma_20 is not None else None,
        "ma_60": round(ma_60, 6) if ma_60 is not None else None,
        "ma_cross": ma_cross,
        "trend": trend,
    }


def _sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    window_slice = closes[-window:]
    return sum(window_slice) / len(window_slice)
