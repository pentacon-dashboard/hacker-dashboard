"""
Portfolio Analyzer — holdings + (선택) snapshots 기반 포트폴리오 해석.

Week-3 신규 analyzer. 입력 특징:

- `input_data` 는 holdings 배열 (market/code/quantity/avg_cost/currency + 선택 필드
  current_price_krw / value_krw / cost_krw / pnl_krw / asset_class 등). BE 의
  `/portfolio/summary` 응답 `holdings` 를 그대로 붙여 넣을 수 있도록 관대하게 받는다.
- `state["snapshots"]` 또는 rows 내 `{"_kind": "snapshot", "snapshot_date":..., "total_value_krw":...}`
  형태로 시계열이 섞여 올 수 있다. 이 경우 MDD/변동성 시계열 계산에 사용.

계산 지표 (pure function, 테스트 가능):

- `hhi`           : Herfindahl-Hirschman Index of asset class weights (0 < HHI ≤ 1)
- `asset_class_breakdown` : {class: weight}
- `currency_exposure`     : {currency: weight}  (FX 리스크용)
- `volatility_pct`        : 가중평균 일간 변동률 표준편차 (snapshot 있으면 가치 기반, 없으면 종목별 추정치 평균)
- `max_drawdown_pct`      : snapshot 시계열의 MDD. snapshot 없으면 None.
- `diversification_score` : 0~100. 종목수·자산군수·상관관계(근사) 종합.
- `signals`               : 리밸런싱 제안 리스트 (기본 3종 이상 보장)

모든 숫자는 **입력에 존재하는 값만** 인용하도록 프롬프트가 유도한다. critique gate 가
숫자 근거를 검증하며, highlights/evidence 의 수치는 compute_portfolio_metrics 가 미리 계산해서
사실 검증이 가능하도록 _indicators 에 노출된다.
"""

from __future__ import annotations

import json
import math
from typing import Any

from app.agents.analyzers.base import BaseAnalyzer
from app.agents.llm import call_llm, extract_json, select_model
from app.agents.state import AgentState
from app.services.sector_map import get_sector

# ──────────────────────── Pure metric helpers ────────────────────────


def _as_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _classify_holding_asset_class(h: dict[str, Any]) -> str:
    """
    holding 하나를 자산군 하나로 매핑. BE summary 의 asset_class_breakdown 키와 호환:
      crypto / stock_us / stock_kr / cash / other
    명시적으로 `asset_class` 필드가 있으면 존중한다.
    """
    explicit = h.get("asset_class")
    if isinstance(explicit, str) and explicit:
        return explicit

    market = (h.get("market") or "").lower()
    code = (h.get("code") or "").upper()
    currency = (h.get("currency") or "").upper()

    if market in {"upbit", "binance"}:
        return "crypto"
    if market == "yahoo":
        return "stock_us"
    if market in {"naver_kr", "krx", "kospi", "kosdaq"}:
        return "stock_kr"
    if market == "cash" or code in {"CASH", "KRW", "USD", "JPY", "EUR"}:
        return "cash"
    # 통화만으로 cash 추정: quantity 만 있고 avg_cost==1 인 경우는 현금성
    if currency and code == currency:
        return "cash"
    return "other"


def _classify_gics_sector(h: dict[str, Any]) -> str:
    """Map a holding to a GICS sector or explicit non-GICS bucket."""
    code = str(h.get("code") or h.get("symbol") or "").strip()
    if not code:
        return "Other"
    return get_sector(code)


def _holding_value(h: dict[str, Any]) -> float | None:
    """해당 holding 의 현재 평가액 (가능하면 KRW). 없으면 quantity*avg_cost 로 폴백."""
    for key in ("value_krw", "current_value_krw", "value"):
        v = _as_float(h.get(key))
        if v is not None and v > 0:
            return v
    q = _as_float(h.get("quantity"))
    p = (
        _as_float(h.get("current_price_krw"))
        or _as_float(h.get("current_price"))
        or _as_float(h.get("avg_cost"))
    )
    if q is not None and p is not None and q > 0 and p > 0:
        return q * p
    return None


def _holding_cost(h: dict[str, Any]) -> float | None:
    for key in ("cost_krw", "cost"):
        v = _as_float(h.get(key))
        if v is not None and v > 0:
            return v
    q = _as_float(h.get("quantity"))
    ac = _as_float(h.get("avg_cost"))
    if q is not None and ac is not None and q > 0 and ac > 0:
        return q * ac
    return None


def _weights_by_key(items: list[tuple[str, float]]) -> dict[str, float]:
    total = sum(v for _, v in items)
    if total <= 0:
        return {}
    agg: dict[str, float] = {}
    for k, v in items:
        agg[k] = agg.get(k, 0.0) + v
    return {k: round(v / total, 6) for k, v in agg.items()}


def compute_hhi(weights: dict[str, float]) -> float:
    """
    Herfindahl-Hirschman Index. 입력은 합이 1.0 에 가까운 가중치 dict.
    반환값은 [0, 1]. 단일 종목/단일 자산군이면 1.0, 완전 분산(무한 종목)이면 0.
    """
    if not weights:
        return 0.0
    return round(sum(w * w for w in weights.values()), 6)


def _is_snapshot_row(row: dict[str, Any]) -> bool:
    return (
        isinstance(row, dict)
        and (row.get("_kind") == "snapshot" or "snapshot_date" in row)
        and _as_float(row.get("total_value_krw")) is not None
    )


def compute_mdd(values: list[float]) -> float:
    """최대낙폭 (음수 %). 입력이 2개 미만이면 0."""
    if len(values) < 2:
        return 0.0
    peak = values[0]
    mdd = 0.0
    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak * 100.0
            if dd < mdd:
                mdd = dd
    return round(mdd, 4)


def compute_volatility(values: list[float]) -> float | None:
    """시계열 값에서 일간 로그수익률 표준편차 (%). 2개 미만이면 None."""
    if len(values) < 2:
        return None
    log_rets: list[float] = []
    for prev, curr in zip(values[:-1], values[1:]):
        if prev > 0 and curr > 0:
            log_rets.append(math.log(curr / prev))
    if not log_rets:
        return None
    mean = sum(log_rets) / len(log_rets)
    var = sum((r - mean) ** 2 for r in log_rets) / len(log_rets)
    return round(math.sqrt(var) * 100.0, 4)


def diversification_score(
    n_holdings: int,
    n_classes: int,
    hhi: float,
) -> int:
    """
    0~100 분산도. 휴리스틱:
      - 종목 수: min(40, n*4)          (10개면 만점 40)
      - 자산군 수: min(30, n_classes*10) (3개군이면 만점 30)
      - HHI 역수: (1 - hhi) * 30       (HHI=0.33 → 20점, HHI=0.9 → 3점)
    """
    p_holdings = min(40, n_holdings * 4)
    p_classes = min(30, n_classes * 10)
    p_hhi = max(0.0, (1.0 - hhi) * 30)
    return int(round(p_holdings + p_classes + p_hhi))


def _build_signals(
    *,
    class_weights: dict[str, float],
    currency_weights: dict[str, float],
    n_holdings: int,
    hhi: float,
    mdd_pct: float | None,
) -> list[dict[str, Any]]:
    """
    리밸런싱/리스크 신호. 프롬프트가 최종 rationale 을 풍부하게 다듬는다.
    여기서는 fallback·근거 검증용으로 최소 3개를 보장.
    """
    signals: list[dict[str, Any]] = []

    # 1) 자산군 집중도 신호
    if class_weights:
        top_cls, top_w = max(class_weights.items(), key=lambda x: x[1])
        if top_w >= 0.6:
            strength = "high" if top_w >= 0.75 else "medium"
            target_pct = 45
            signals.append(
                {
                    "kind": "rebalance",
                    "strength": strength,
                    "rationale": (
                        f"{top_cls} 비중 {round(top_w * 100, 1)}% → "
                        f"{target_pct}% 수준으로 축소해 집중 위험 완화"
                    ),
                }
            )
        elif hhi >= 0.5:
            signals.append(
                {
                    "kind": "rebalance",
                    "strength": "medium",
                    "rationale": (
                        f"HHI {hhi:.2f}로 상위 자산군 편중 — 저비중 자산군을 늘려 분산 제고"
                    ),
                }
            )
        else:
            signals.append(
                {
                    "kind": "diversified",
                    "strength": "low",
                    "rationale": f"자산군 분산 양호 (HHI {hhi:.2f}) — 현 구성 유지 검토",
                }
            )

    # 2) 통화 노출 신호 (FX 헤지)
    if currency_weights:
        non_krw = sum(w for c, w in currency_weights.items() if c != "KRW")
        if non_krw >= 0.5:
            strength = "high" if non_krw >= 0.7 else "medium"
            signals.append(
                {
                    "kind": "fx_hedge",
                    "strength": strength,
                    "rationale": (
                        f"비원화(비KRW) 노출 {round(non_krw * 100, 1)}% → "
                        "환헤지 또는 KRW 비중 확대 권장"
                    ),
                }
            )
        else:
            signals.append(
                {
                    "kind": "fx_hedge",
                    "strength": "low",
                    "rationale": f"비원화 노출 {round(non_krw * 100, 1)}% — 현수준 허용",
                }
            )

    # 3) 종목 수 / MDD 신호
    if n_holdings <= 3:
        signals.append(
            {
                "kind": "diversify",
                "strength": "medium",
                "rationale": f"보유 종목 {n_holdings}종 — 5종 이상으로 확대해 개별주 리스크 감소",
            }
        )
    elif mdd_pct is not None and mdd_pct <= -20.0:
        signals.append(
            {
                "kind": "risk",
                "strength": "high",
                "rationale": f"최대낙폭 {mdd_pct:.1f}% — 변동성 축소 자산(채권/현금) 비중 확대 검토",
            }
        )
    else:
        signals.append(
            {
                "kind": "monitor",
                "strength": "low",
                "rationale": f"보유 {n_holdings}종, MDD {mdd_pct if mdd_pct is not None else '—'}% — 분기 리뷰 권장",
            }
        )

    return signals


def compute_portfolio_metrics(
    rows: list[dict[str, Any]],
    snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    holdings rows + (선택) snapshots 에서 모든 집계 지표를 산출한다.
    rows 에 snapshot 레코드가 섞여있으면 자동 분리한다.
    """
    holdings: list[dict[str, Any]] = []
    inline_snaps: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if _is_snapshot_row(r):
            inline_snaps.append(r)
        elif "code" in r or "market" in r or "symbol" in r or "quantity" in r:
            holdings.append(r)

    all_snaps = list(inline_snaps)
    if snapshots:
        all_snaps.extend(s for s in snapshots if isinstance(s, dict))

    if not holdings:
        return {}

    # 자산군·통화 가중치
    class_items: list[tuple[str, float]] = []
    sector_items: list[tuple[str, float]] = []
    ccy_items: list[tuple[str, float]] = []
    total_value = 0.0
    total_cost = 0.0
    for h in holdings:
        v = _holding_value(h) or 0.0
        c = _holding_cost(h) or 0.0
        total_value += v
        total_cost += c
        if v > 0:
            class_items.append((_classify_holding_asset_class(h), v))
            sector_items.append((_classify_gics_sector(h), v))
            ccy = (h.get("currency") or "").upper() or "KRW"
            ccy_items.append((ccy, v))

    class_weights = _weights_by_key(class_items)
    sector_weights = _weights_by_key(sector_items)
    currency_weights = _weights_by_key(ccy_items)
    hhi = compute_hhi(class_weights)

    # snapshots → 시계열 가치
    snap_values: list[float] = []
    sorted_snaps = sorted(
        [s for s in all_snaps if _as_float(s.get("total_value_krw")) is not None],
        key=lambda s: str(s.get("snapshot_date") or ""),
    )
    for s in sorted_snaps:
        sv: float | None = _as_float(s.get("total_value_krw"))
        if sv is not None and sv > 0:
            snap_values.append(sv)

    mdd_pct = compute_mdd(snap_values) if snap_values else None
    volatility_pct = compute_volatility(snap_values) if snap_values else None

    # 손익
    pnl = total_value - total_cost if (total_value > 0 and total_cost > 0) else None
    pnl_pct = (pnl / total_cost * 100.0) if (pnl is not None and total_cost > 0) else None

    # 분산도
    score = diversification_score(
        n_holdings=len(holdings),
        n_classes=len(class_weights),
        hhi=hhi,
    )

    # 제안 신호
    signals = _build_signals(
        class_weights=class_weights,
        currency_weights=currency_weights,
        n_holdings=len(holdings),
        hhi=hhi,
        mdd_pct=mdd_pct,
    )

    return {
        "n_holdings": len(holdings),
        "n_asset_classes": len(class_weights),
        "hhi": hhi,
        "asset_class_breakdown": class_weights,
        "sector_breakdown": sector_weights,
        "currency_exposure": currency_weights,
        "total_value": round(total_value, 4) if total_value > 0 else None,
        "total_cost": round(total_cost, 4) if total_cost > 0 else None,
        "pnl": round(pnl, 4) if pnl is not None else None,
        "pnl_pct": round(pnl_pct, 4) if pnl_pct is not None else None,
        "max_drawdown_pct": mdd_pct,
        "volatility_pct": volatility_pct,
        "diversification_score": score,
        "n_snapshots": len(snap_values),
        "suggested_signals": signals,
    }


# ──────────────────────── Analyzer class ────────────────────────


class PortfolioAnalyzer(BaseAnalyzer):
    """holdings + snapshots 를 해석하는 Analyzer."""

    asset_class = "portfolio"
    prompt_name = "portfolio_system"

    async def run(self, state: AgentState) -> dict[str, Any]:
        rows = state.get("input_data") or []
        query = state.get("query")
        snapshots = state.get("snapshots") if isinstance(state, dict) else None
        portfolio_context = state.get("portfolio_context") if isinstance(state, dict) else None
        metrics = compute_portfolio_metrics(rows, snapshots=snapshots)

        raw = await self._call(
            rows=rows,
            query=query,
            indicators=metrics,
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

        # asset_class 일관성: 게이트의 consistency 체크가 state.asset_class 와 일치를 요구.
        # router 는 "portfolio" 를 내므로 analyzer 도 "portfolio" 로 마킹.
        parsed["asset_class"] = "portfolio"

        # 정량 근거 보존
        if metrics:
            parsed.setdefault("_indicators", metrics)
            # LLM 이 signals 를 누락한 경우 fallback 신호 주입 (최소 3개 보장)
            existing = parsed.get("signals") or []
            if not isinstance(existing, list) or len(existing) < 3:
                parsed["signals"] = metrics.get("suggested_signals", [])[:3]

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
        user_content = json.dumps(payload, ensure_ascii=False, default=str)
        return await call_llm(
            system_prompt_name=self.prompt_name,
            user_content=user_content,
            model=select_model(len(rows)),
            max_tokens=1400,
            temperature=0.2,
        )
