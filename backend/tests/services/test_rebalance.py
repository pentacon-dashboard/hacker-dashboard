"""리밸런싱 순수함수 단위 테스트.

결정적 계산이므로 LLM/DB/외부 API 의존 없음.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from app.schemas.rebalance import RebalanceConstraints, RebalanceAction, TargetAllocation
from app.services.rebalance import (
    build_expected_allocation,
    build_summary,
    calculate_rebalance_actions,
    compute_current_allocation,
    compute_drift,
    infer_asset_class,
)


# ──────────── 테스트용 Holding 스텁 ────────────


@dataclass
class FakeHolding:
    id: int
    market: str
    code: str
    quantity: Decimal
    avg_cost: Decimal
    currency: str = "KRW"


def _h(
    id_: int,
    market: str,
    code: str,
    quantity: str = "1",
    avg_cost: str = "1000",
    currency: str = "KRW",
) -> FakeHolding:
    return FakeHolding(
        id=id_,
        market=market,
        code=code,
        quantity=Decimal(quantity),
        avg_cost=Decimal(avg_cost),
        currency=currency,
    )


def _default_constraints(**kwargs: object) -> RebalanceConstraints:
    defaults = {
        "max_single_weight": 0.5,
        "min_trade_krw": Decimal("100000"),
        "allow_fractional": True,
    }
    defaults.update(kwargs)
    return RebalanceConstraints(**defaults)  # type: ignore[arg-type]


def _target(**kwargs: float) -> TargetAllocation:
    base = {"stock_kr": 0.0, "stock_us": 0.0, "crypto": 0.0, "cash": 0.0, "fx": 0.0}
    base.update(kwargs)
    return TargetAllocation(**base)


# ──────────── infer_asset_class ────────────


def test_infer_asset_class_upbit():
    assert infer_asset_class("upbit", "KRW-BTC") == "crypto"


def test_infer_asset_class_binance():
    assert infer_asset_class("binance", "BTCUSDT") == "crypto"


def test_infer_asset_class_yahoo():
    assert infer_asset_class("yahoo", "AAPL") == "stock_us"


def test_infer_asset_class_naver_kr():
    assert infer_asset_class("naver_kr", "005930") == "stock_kr"


def test_infer_asset_class_fx():
    assert infer_asset_class("fx", "USD/KRW") == "fx"


def test_infer_asset_class_unknown():
    assert infer_asset_class("unknown_market", "XYZ") == "other"


# ──────────── compute_current_allocation ────────────


def test_compute_current_allocation_single_crypto():
    holdings = [_h(1, "upbit", "KRW-BTC")]
    values = {1: Decimal("10000000")}
    total = Decimal("10000000")
    alloc = compute_current_allocation(holdings, values, total)
    assert abs(alloc["crypto"] - 1.0) < 1e-5
    assert alloc["stock_us"] == 0.0
    assert alloc["stock_kr"] == 0.0


def test_compute_current_allocation_mixed():
    holdings = [
        _h(1, "upbit", "KRW-BTC"),
        _h(2, "yahoo", "AAPL"),
    ]
    values = {1: Decimal("6000000"), 2: Decimal("4000000")}
    total = Decimal("10000000")
    alloc = compute_current_allocation(holdings, values, total)
    assert abs(alloc["crypto"] - 0.6) < 1e-5
    assert abs(alloc["stock_us"] - 0.4) < 1e-5


def test_compute_current_allocation_zero_total():
    holdings = [_h(1, "upbit", "KRW-BTC")]
    values = {1: Decimal("0")}
    total = Decimal("0")
    alloc = compute_current_allocation(holdings, values, total)
    assert all(v == 0.0 for v in alloc.values())


# ──────────── compute_drift ────────────


def test_compute_drift_basic():
    current = {"crypto": 0.74, "stock_us": 0.19, "stock_kr": 0.07, "cash": 0.0, "fx": 0.0}
    target = {"stock_kr": 0.2, "stock_us": 0.4, "crypto": 0.3, "cash": 0.1, "fx": 0.0}
    drift = compute_drift(current, target)
    assert abs(drift["crypto"] - 0.44) < 1e-5   # 과도
    assert abs(drift["stock_us"] - (-0.21)) < 1e-5  # 부족
    assert abs(drift["cash"] - (-0.10)) < 1e-5   # 부족


def test_compute_drift_balanced():
    alloc = {"stock_kr": 0.25, "stock_us": 0.25, "crypto": 0.25, "cash": 0.25, "fx": 0.0}
    drift = compute_drift(alloc, alloc)
    for v in drift.values():
        assert abs(v) < 1e-6


# ──────────── calculate_rebalance_actions ────────────


def test_already_balanced_no_actions():
    """이미 균형 → actions = []."""
    holdings = [
        _h(1, "upbit", "KRW-BTC", quantity="1"),
        _h(2, "yahoo", "AAPL", quantity="1"),
    ]
    total = Decimal("2000000")
    values = {1: Decimal("1000000"), 2: Decimal("1000000")}
    prices = {1: Decimal("1000000"), 2: Decimal("1000000")}
    target = _target(crypto=0.5, stock_us=0.5)
    constraints = _default_constraints(min_trade_krw=Decimal("1000"))

    actions = calculate_rebalance_actions(
        holdings, values, prices, target, constraints, total
    )
    assert actions == []


def test_crypto_heavy_to_mixed():
    """crypto 100% 보유, 목표 stock_us 50% + crypto 50% → sell 1건 + buy 1건."""
    holdings = [
        _h(1, "upbit", "KRW-BTC"),
        _h(2, "yahoo", "AAPL"),
    ]
    total = Decimal("10000000")
    # crypto 100%, stock_us 0%
    values = {1: Decimal("10000000"), 2: Decimal("0")}
    prices = {1: Decimal("50000000"), 2: Decimal("150000")}
    target = _target(crypto=0.5, stock_us=0.5)
    constraints = _default_constraints(min_trade_krw=Decimal("100000"))

    actions = calculate_rebalance_actions(
        holdings, values, prices, target, constraints, total
    )

    sell_actions = [a for a in actions if a.action == "sell"]
    buy_actions = [a for a in actions if a.action == "buy"]
    assert len(sell_actions) >= 1, "코인 매도 액션이 1건 이상이어야 함"
    assert len(buy_actions) >= 1, "주식 매수 액션이 1건 이상이어야 함"
    assert sell_actions[0].code == "KRW-BTC"
    assert buy_actions[0].code == "AAPL"


def test_min_trade_krw_filters_small_actions():
    """매우 작은 drift → min_trade_krw 초과 필터링 → actions = []."""
    holdings = [
        _h(1, "upbit", "KRW-BTC"),
        _h(2, "yahoo", "AAPL"),
    ]
    # crypto 50.5%, stock_us 49.5% — 거의 균형
    total = Decimal("10000000")
    values = {1: Decimal("5050000"), 2: Decimal("4950000")}
    prices = {1: Decimal("50000000"), 2: Decimal("150000")}
    target = _target(crypto=0.50, stock_us=0.50)
    # min_trade_krw를 높게 설정 → 작은 drift는 필터링됨
    constraints = _default_constraints(min_trade_krw=Decimal("1000000"))

    actions = calculate_rebalance_actions(
        holdings, values, prices, target, constraints, total
    )
    assert actions == [], f"min_trade_krw 필터 후 빈 배열이어야 함. got: {actions}"


def test_max_single_weight_blocks_large_buy():
    """max_single_weight=0.3 → 단일 종목 매수 제한."""
    holdings = [
        _h(1, "upbit", "KRW-BTC"),
        _h(2, "yahoo", "AAPL"),
    ]
    total = Decimal("10000000")
    # AAPL 현재 0%, 목표 stock_us 80%
    values = {1: Decimal("10000000"), 2: Decimal("0")}
    prices = {1: Decimal("50000000"), 2: Decimal("200000")}
    target = _target(crypto=0.20, stock_us=0.80)
    constraints = _default_constraints(
        max_single_weight=0.3,  # AAPL 최대 30%
        min_trade_krw=Decimal("100000"),
    )

    actions = calculate_rebalance_actions(
        holdings, values, prices, target, constraints, total
    )

    buy_actions = [a for a in actions if a.action == "buy" and a.code == "AAPL"]
    if buy_actions:
        # 매수 후 가치가 total * 0.3 이하여야 함
        aapl_buy_value = sum(a.estimated_value_krw or Decimal("0") for a in buy_actions)
        assert aapl_buy_value <= total * Decimal("0.3") + Decimal("1"), (
            f"max_single_weight 위반: {aapl_buy_value} > {total * Decimal('0.3')}"
        )


def test_no_holdings_for_target_asset_class():
    """stock_kr holdings 없음 + stock_kr 목표 비중 있음 → drift 무시 (스코프 외)."""
    holdings = [
        _h(1, "upbit", "KRW-BTC"),
    ]
    total = Decimal("10000000")
    values = {1: Decimal("10000000")}
    prices = {1: Decimal("50000000")}
    # stock_kr 목표 50%이지만 holdings에 stock_kr 없음
    target = _target(crypto=0.5, stock_kr=0.5)
    constraints = _default_constraints()

    actions = calculate_rebalance_actions(
        holdings, values, prices, target, constraints, total
    )

    # stock_kr 매수 액션 없음 (신규 종목 추천 스코프 외)
    stock_kr_buys = [a for a in actions if a.asset_class == "stock_kr"]
    assert stock_kr_buys == [], "stock_kr holdings 없으면 해당 자산군 액션 없어야 함"


def test_no_negative_quantity():
    """입력이 깨져도 quantity가 0 이하인 액션은 생성되지 않아야 함."""
    holdings = [_h(1, "upbit", "KRW-BTC")]
    total = Decimal("10000000")
    values = {1: Decimal("10000000")}
    prices = {1: Decimal("0")}  # 가격 0 — 비정상 입력
    target = _target(crypto=0.5, cash=0.5)
    constraints = _default_constraints()

    actions = calculate_rebalance_actions(
        holdings, values, prices, target, constraints, total
    )
    for a in actions:
        assert a.quantity > Decimal("0"), "음수/0 수량 액션이 있으면 안 됨"


def test_allow_fractional_false_rounds_down():
    """allow_fractional=False → 수량이 정수로 내림."""
    holdings = [_h(1, "yahoo", "AAPL")]
    total = Decimal("10000000")
    # AAPL 없음, 목표 stock_us 100%
    values = {1: Decimal("0")}
    prices = {1: Decimal("300000")}  # 30만원/주
    target = _target(stock_us=1.0)
    constraints = _default_constraints(
        allow_fractional=False,
        min_trade_krw=Decimal("100000"),
    )

    actions = calculate_rebalance_actions(
        holdings, values, prices, target, constraints, total
    )

    for a in actions:
        if a.action == "buy" and a.code == "AAPL":
            assert a.quantity == a.quantity.to_integral_value(), (
                f"allow_fractional=False인데 소수점 수량: {a.quantity}"
            )


def test_empty_holdings_returns_empty_actions():
    """holdings 없으면 actions = []."""
    actions = calculate_rebalance_actions(
        holdings=[],
        current_values_krw={},
        current_prices_krw={},
        target=_target(crypto=1.0),
        constraints=_default_constraints(),
        total_value_krw=Decimal("0"),
    )
    assert actions == []


# ──────────── build_expected_allocation ────────────


def test_build_expected_allocation_after_sell():
    holdings = [_h(1, "upbit", "KRW-BTC")]
    total = Decimal("10000000")
    values = {1: Decimal("10000000")}
    prices = {1: Decimal("50000000")}
    action = RebalanceAction(
        action="sell",
        market="upbit",
        code="KRW-BTC",
        asset_class="crypto",
        quantity=Decimal("0.1"),
        estimated_value_krw=Decimal("5000000"),
        reason="테스트 매도",
    )
    expected = build_expected_allocation(values, holdings, [action], prices, total)
    assert expected["crypto"] < 1.0, "매도 후 crypto 비중이 줄어야 함"


def test_build_expected_allocation_no_actions():
    holdings = [_h(1, "upbit", "KRW-BTC")]
    total = Decimal("10000000")
    values = {1: Decimal("10000000")}
    prices = {1: Decimal("50000000")}
    expected = build_expected_allocation(values, holdings, [], prices, total)
    assert abs(expected["crypto"] - 1.0) < 1e-5


# ──────────── build_summary ────────────


def test_build_summary_basic():
    actions = [
        RebalanceAction(
            action="sell",
            market="upbit",
            code="KRW-BTC",
            asset_class="crypto",
            quantity=Decimal("0.1"),
            estimated_value_krw=Decimal("5000000"),
            reason="테스트 매도",
        ),
        RebalanceAction(
            action="buy",
            market="yahoo",
            code="AAPL",
            asset_class="stock_us",
            quantity=Decimal("3"),
            estimated_value_krw=Decimal("4500000"),
            reason="테스트 매수",
        ),
    ]
    summary = build_summary(actions)
    assert summary.total_trades == 2
    assert summary.total_sell_value_krw == Decimal("5000000")
    assert summary.total_buy_value_krw == Decimal("4500000")
    # 비용: (5000000 + 4500000) * 0.0025 = 23750
    expected_cost = (Decimal("5000000") + Decimal("4500000")) * Decimal("0.0025")
    assert summary.rebalance_cost_estimate_krw == expected_cost.quantize(Decimal("1"))


def test_build_summary_empty():
    summary = build_summary([])
    assert summary.total_trades == 0
    assert summary.total_sell_value_krw == Decimal("0")
    assert summary.total_buy_value_krw == Decimal("0")
    assert summary.rebalance_cost_estimate_krw == Decimal("0")


# ──────────── TargetAllocation validator ────────────


def test_target_allocation_valid():
    t = TargetAllocation(stock_kr=0.2, stock_us=0.4, crypto=0.3, cash=0.1, fx=0.0)
    assert abs(t.stock_kr + t.stock_us + t.crypto + t.cash + t.fx - 1.0) < 1e-5


def test_target_allocation_sum_tolerance():
    """±0.001 오차 허용."""
    t = TargetAllocation(stock_kr=0.2, stock_us=0.4, crypto=0.3, cash=0.1, fx=0.0005)
    assert t is not None


def test_target_allocation_invalid_sum():
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="합계는 1.0"):
        TargetAllocation(stock_kr=0.5, stock_us=0.5, crypto=0.5, cash=0.0, fx=0.0)
