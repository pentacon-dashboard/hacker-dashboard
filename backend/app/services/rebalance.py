"""리밸런싱 계산 서비스 — 결정적 순수함수. LLM 미개입.

알고리즘:
1. 자산군별 현재 비중 계산
2. drift = current - target (양수=과도, 음수=부족)
3. drift > 0 (과도): 해당 자산군 holdings를 비중 큰 순으로 매도
4. drift < 0 (부족): 해당 자산군 holdings를 비중 작은 순으로 매수
5. min_trade_krw 미만 skip, max_single_weight 위반 시 매수 중단
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_DOWN
from typing import Any

from app.schemas.rebalance import (
    RebalanceAction,
    RebalanceConstraints,
    RebalanceSummary,
    TargetAllocation,
)

logger = logging.getLogger(__name__)

# market → asset_class 매핑 (portfolio.py::_MARKET_TO_ASSET_CLASS 와 동기화)
_MARKET_TO_ASSET_CLASS: dict[str, str] = {
    "upbit": "crypto",
    "binance": "crypto",
    "yahoo": "stock_us",
    "naver_kr": "stock_kr",
    "krx": "stock_kr",
    "nasdaq": "stock_us",
    "nyse": "stock_us",
}

_ALL_ASSET_CLASSES = ["stock_kr", "stock_us", "crypto", "cash", "fx"]

_ZERO = Decimal("0")
_ONE = Decimal("1")
_TRADE_COST_RATE = Decimal("0.0025")  # 0.25%


def infer_asset_class(market: str, code: str) -> str:  # noqa: ARG001 (code reserved)
    """market/code로 자산군 추론.

    - naver_kr → stock_kr
    - yahoo → stock_us
    - upbit, binance → crypto
    - 환율 심볼 (USD/KRW 등, fx market) → fx
    - 매칭 실패 시 "other"
    """
    key = market.lower()
    if key == "fx":
        return "fx"
    return _MARKET_TO_ASSET_CLASS.get(key, "other")


def _d(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def compute_current_allocation(
    holdings: list[Any],
    current_values_krw: dict[int, Decimal],
    total_value_krw: Decimal,
) -> dict[str, float]:
    """현재 자산군별 비중 계산.

    cash는 holdings에 없으므로 0으로 고정 (v1 스코프).
    other는 합산하되 리밸런싱 대상에서 제외.
    """
    if total_value_krw == _ZERO:
        return {ac: 0.0 for ac in _ALL_ASSET_CLASSES}

    ac_values: dict[str, Decimal] = {ac: _ZERO for ac in _ALL_ASSET_CLASSES}

    for h in holdings:
        h_id = int(h.id)
        val = current_values_krw.get(h_id, _ZERO)
        ac = infer_asset_class(h.market, h.code)
        if ac in ac_values:
            ac_values[ac] += val
        # "other" 는 분모에는 포함되지만 breakdown에서 제외

    result: dict[str, float] = {}
    for ac in _ALL_ASSET_CLASSES:
        ratio = float(ac_values[ac] / total_value_krw)
        result[ac] = round(ratio, 6)

    return result


def compute_drift(
    current: dict[str, float],
    target: dict[str, float],
) -> dict[str, float]:
    """drift = current - target. 양수=과도, 음수=부족."""
    all_keys = set(current) | set(target)
    return {
        k: round(current.get(k, 0.0) - target.get(k, 0.0), 6)
        for k in all_keys
    }


def calculate_rebalance_actions(
    holdings: list[Any],
    current_values_krw: dict[int, Decimal],
    current_prices_krw: dict[int, Decimal],
    target: TargetAllocation,
    constraints: RebalanceConstraints,
    total_value_krw: Decimal,
) -> list[RebalanceAction]:
    """리밸런싱 액션 계산 — 순수함수.

    알고리즘 (v1):
    1. 자산군별 drift(KRW) = (current_weight - target_weight) * total_value_krw
    2. drift > 0 (과도): 비중 큰 holding 순으로 매도
    3. drift < 0 (부족): 비중 작은 holding 순으로 매수
    4. min_trade_krw 미만 → skip
    5. max_single_weight 위반 시 해당 종목 매수 중단
    6. 해당 자산군 holdings 없으면 drift 무시 (신규 추천 스코프 외)
    """
    if total_value_krw == _ZERO:
        return []

    current_alloc = compute_current_allocation(holdings, current_values_krw, total_value_krw)
    target_dict = target.model_dump()

    # 자산군별 holding 목록 구성
    ac_holdings: dict[str, list[Any]] = {ac: [] for ac in _ALL_ASSET_CLASSES}
    for h in holdings:
        ac = infer_asset_class(h.market, h.code)
        if ac in ac_holdings:
            ac_holdings[ac].append(h)

    actions: list[RebalanceAction] = []

    for ac in _ALL_ASSET_CLASSES:
        if ac == "cash":
            # cash는 현금 — 실제 매매 불가
            continue

        current_w = current_alloc.get(ac, 0.0)
        target_w = target_dict.get(ac, 0.0)
        drift_val = current_w - target_w

        if abs(drift_val) < 1e-6:
            continue

        drift_krw = _d(drift_val) * total_value_krw
        ac_hold = ac_holdings.get(ac, [])

        if not ac_hold:
            # 해당 자산군 holdings 없음 → 신규 종목 추천 스코프 외
            logger.debug("asset_class=%s drift 있지만 holdings 없어 skip", ac)
            continue

        if drift_krw > _ZERO:
            # 과도 → 매도. 비중 큰 순으로
            sorted_hold = sorted(
                ac_hold,
                key=lambda h: current_values_krw.get(int(h.id), _ZERO),
                reverse=True,
            )
            remaining = drift_krw
            for h in sorted_hold:
                if remaining < _d(constraints.min_trade_krw):
                    break
                h_id = int(h.id)
                h_value = current_values_krw.get(h_id, _ZERO)
                if h_value == _ZERO:
                    continue
                unit_price = current_prices_krw.get(h_id, _ZERO)
                if unit_price == _ZERO:
                    continue

                # 이 종목에서 매도할 금액 (remaining 전액 or 보유 전액 중 작은 것)
                sell_value = min(remaining, h_value)
                if sell_value < _d(constraints.min_trade_krw):
                    break

                quantity = sell_value / unit_price
                if not constraints.allow_fractional:
                    quantity = quantity.to_integral_value(rounding=ROUND_DOWN)

                if quantity <= _ZERO:
                    continue

                actual_value = quantity * unit_price

                actions.append(
                    RebalanceAction(
                        action="sell",
                        market=h.market,
                        code=h.code,
                        asset_class=ac,
                        quantity=quantity,
                        estimated_value_krw=actual_value,
                        reason=(
                            f"{ac} 비중 {current_w*100:.1f}% → 목표 {target_w*100:.1f}%. "
                            f"가장 비중이 큰 {h.code}부터 일부 매도"
                        ),
                    )
                )
                remaining -= actual_value

        else:
            # 부족 → 매수. 비중 작은 순으로
            sorted_hold = sorted(
                ac_hold,
                key=lambda h: current_values_krw.get(int(h.id), _ZERO),
            )
            buy_needed = abs(drift_krw)
            remaining = buy_needed

            for h in sorted_hold:
                if remaining < _d(constraints.min_trade_krw):
                    break
                h_id = int(h.id)
                unit_price = current_prices_krw.get(h_id, _ZERO)
                if unit_price == _ZERO:
                    continue

                # max_single_weight 검증: 매수 후 비중이 초과하는지 확인
                h_current_value = current_values_krw.get(h_id, _ZERO)
                max_allowed_value = _d(constraints.max_single_weight) * total_value_krw
                available_capacity = max_allowed_value - h_current_value
                if available_capacity <= _ZERO:
                    logger.debug(
                        "max_single_weight 초과 → %s/%s 매수 중단",
                        h.market, h.code,
                    )
                    continue

                buy_value = min(remaining, available_capacity)
                if buy_value < _d(constraints.min_trade_krw):
                    # 남은 매수 여력이 너무 작음
                    remaining -= buy_value
                    continue

                quantity = buy_value / unit_price
                if not constraints.allow_fractional:
                    quantity = quantity.to_integral_value(rounding=ROUND_DOWN)

                if quantity <= _ZERO:
                    continue

                actual_value = quantity * unit_price

                actions.append(
                    RebalanceAction(
                        action="buy",
                        market=h.market,
                        code=h.code,
                        asset_class=ac,
                        quantity=quantity,
                        estimated_value_krw=actual_value,
                        reason=(
                            f"{ac} 목표까지 +{abs(drift_val)*100:.1f}% 부족. "
                            f"기존 보유 종목 {h.code} 추가 매수로 다변화 유지"
                        ),
                    )
                )
                remaining -= actual_value

    return actions


def build_expected_allocation(
    current_values_krw: dict[int, Decimal],
    holdings: list[Any],
    actions: list[RebalanceAction],
    current_prices_krw: dict[int, Decimal],
    total_value_krw: Decimal,
) -> dict[str, float]:
    """actions 적용 후 예상 비중 계산."""
    if total_value_krw == _ZERO:
        return {ac: 0.0 for ac in _ALL_ASSET_CLASSES}

    # holdings별 조정된 값 계산
    adjusted_values = {h_id: val for h_id, val in current_values_krw.items()}

    # holding_id → (market, code) 매핑
    id_to_holding = {int(h.id): h for h in holdings}

    for action in actions:
        # code + market으로 holding 찾기
        matching = [
            h for h in holdings
            if h.code == action.code and h.market == action.market
        ]
        if not matching:
            continue
        h = matching[0]
        h_id = int(h.id)
        unit_price = current_prices_krw.get(h_id, _ZERO)
        if unit_price == _ZERO:
            continue

        delta = action.quantity * unit_price
        if action.action == "sell":
            adjusted_values[h_id] = max(_ZERO, adjusted_values.get(h_id, _ZERO) - delta)
        else:
            adjusted_values[h_id] = adjusted_values.get(h_id, _ZERO) + delta

    # 자산군별 합산
    ac_values: dict[str, Decimal] = {ac: _ZERO for ac in _ALL_ASSET_CLASSES}
    for h in holdings:
        h_id = int(h.id)
        ac = infer_asset_class(h.market, h.code)
        if ac in ac_values:
            ac_values[ac] += adjusted_values.get(h_id, _ZERO)

    # 총 조정 포트폴리오 가치 (매수/매도로 총합은 같다고 가정 — v1 단순화)
    result: dict[str, float] = {}
    for ac in _ALL_ASSET_CLASSES:
        ratio = float(ac_values[ac] / total_value_krw)
        result[ac] = round(max(0.0, ratio), 6)

    return result


def build_summary(actions: list[RebalanceAction]) -> RebalanceSummary:
    """총 매수/매도 금액 + 거래비용 추정 (총매매액 × 0.0025)."""
    total_sell = _ZERO
    total_buy = _ZERO

    for a in actions:
        val = a.estimated_value_krw or _ZERO
        if a.action == "sell":
            total_sell += val
        else:
            total_buy += val

    total_trade = total_sell + total_buy
    cost_estimate = (total_trade * _TRADE_COST_RATE).quantize(Decimal("1"))

    return RebalanceSummary(
        total_trades=len(actions),
        total_sell_value_krw=total_sell,
        total_buy_value_krw=total_buy,
        rebalance_cost_estimate_krw=cost_estimate,
    )
