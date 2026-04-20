"""
Portfolio Analyzer 단위·통합 테스트.

검증 대상:
- compute_portfolio_metrics 순수함수: HHI/MDD/변동성/분산도/제안 신호
- PortfolioAnalyzer.run: fake LLM 응답으로 전체 흐름
- fallback 신호 3개 이상 보장
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.analyzers.portfolio import (
    PortfolioAnalyzer,
    compute_hhi,
    compute_mdd,
    compute_portfolio_metrics,
    compute_volatility,
    diversification_score,
)


_SAMPLES = Path(__file__).parent / "samples"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_SAMPLES / f"{name}.json").read_text(encoding="utf-8"))


# ───────────────── Pure function tests ─────────────────


def test_compute_hhi_single_dominant() -> None:
    # 단일 자산군이 1.0 → HHI 1.0
    assert compute_hhi({"crypto": 1.0}) == 1.0
    # 완전 균등(4개) → 0.25
    w = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
    assert compute_hhi(w) == pytest.approx(0.25, rel=1e-6)


def test_compute_hhi_empty() -> None:
    assert compute_hhi({}) == 0.0


def test_compute_mdd_strict() -> None:
    # 100 → 110 → 80 → 95 → peak 110 기준 (80-110)/110 = -27.27%
    vals = [100, 110, 80, 95]
    mdd = compute_mdd(vals)
    assert mdd == pytest.approx(-27.2727, rel=1e-4)


def test_compute_mdd_flat_or_rising() -> None:
    assert compute_mdd([100, 105, 110]) == 0.0
    assert compute_mdd([100]) == 0.0


def test_compute_volatility_basic() -> None:
    v = compute_volatility([100, 101, 100, 102, 101])
    assert v is not None
    assert v > 0


def test_compute_volatility_too_short() -> None:
    assert compute_volatility([100]) is None
    assert compute_volatility([]) is None


def test_diversification_score_balanced() -> None:
    # 10개 종목 · 4자산군 · HHI 0.26 → 40 + 30 + (1-0.26)*30 ≈ 92
    s = diversification_score(n_holdings=10, n_classes=4, hhi=0.26)
    assert s >= 85


def test_diversification_score_concentrated() -> None:
    # 3종목 · 3자산군 · HHI 0.82 → 12 + 30 + 5.4 ≈ 47
    s = diversification_score(n_holdings=3, n_classes=3, hhi=0.82)
    assert s <= 60


# ───────────────── compute_portfolio_metrics (golden) ─────────────────


def test_portfolio_metrics_balanced() -> None:
    sample = _load("portfolio_balanced")
    metrics = compute_portfolio_metrics(sample["input"]["data"])
    assert metrics["n_holdings"] == 6
    assert metrics["n_asset_classes"] >= 4
    # 기대: HHI < 0.4, 분산도 > 50
    assert metrics["hhi"] < 0.4
    assert metrics["diversification_score"] >= 50
    # suggested_signals: 최소 3개 보장
    assert len(metrics["suggested_signals"]) >= 3


def test_portfolio_metrics_concentrated() -> None:
    sample = _load("portfolio_concentrated")
    metrics = compute_portfolio_metrics(sample["input"]["data"])
    # crypto 단일 비중이 0.85 이상
    breakdown = metrics["asset_class_breakdown"]
    top_weight = max(breakdown.values())
    assert top_weight >= 0.85, breakdown
    assert metrics["hhi"] >= 0.6
    assert metrics["diversification_score"] <= 60
    # 강력한 리밸런싱 신호
    signals = metrics["suggested_signals"]
    assert any(s["kind"] == "rebalance" and s["strength"] == "high" for s in signals), signals


def test_portfolio_metrics_multi_currency() -> None:
    sample = _load("portfolio_multi_currency")
    metrics = compute_portfolio_metrics(sample["input"]["data"])
    ccy = metrics["currency_exposure"]
    assert len(ccy) >= 3, ccy
    non_krw = sum(w for c, w in ccy.items() if c != "KRW")
    assert non_krw >= 0.7
    # FX 헤지 신호가 medium 이상
    signals = metrics["suggested_signals"]
    assert any(
        s["kind"] == "fx_hedge" and s["strength"] in {"medium", "high"} for s in signals
    ), signals


def test_portfolio_metrics_with_snapshots() -> None:
    """snapshot 시계열이 섞여 있으면 MDD/volatility 가 채워진다."""
    rows = [
        {"market": "upbit", "code": "KRW-BTC", "quantity": 1, "avg_cost": 50_000_000, "currency": "KRW", "value_krw": 60_000_000, "cost_krw": 50_000_000, "asset_class": "crypto"},
    ]
    snaps = [
        {"snapshot_date": "2024-01-01", "total_value_krw": 60_000_000},
        {"snapshot_date": "2024-01-02", "total_value_krw": 66_000_000},
        {"snapshot_date": "2024-01-03", "total_value_krw": 50_000_000},  # -24% 낙폭
        {"snapshot_date": "2024-01-04", "total_value_krw": 55_000_000},
    ]
    metrics = compute_portfolio_metrics(rows, snapshots=snaps)
    assert metrics["n_snapshots"] == 4
    assert metrics["max_drawdown_pct"] < -20
    assert metrics["volatility_pct"] is not None


def test_portfolio_metrics_empty_returns_empty() -> None:
    assert compute_portfolio_metrics([]) == {}
    assert compute_portfolio_metrics([{"random": "blob"}]) == {}


# ───────────────── PortfolioAnalyzer.run (with fake LLM) ─────────────────


@pytest.mark.asyncio
async def test_portfolio_analyzer_run_full(fake_client) -> None:
    sample = _load("portfolio_concentrated")
    fake_client.responses["analyzer"] = sample["mock_analyzer_output"]
    analyzer = PortfolioAnalyzer()
    state = {
        "input_data": sample["input"]["data"],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "portfolio",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    out = await analyzer.run(state)  # type: ignore[arg-type]
    assert out["asset_class"] == "portfolio"
    assert "summary" in out or "headline" in out
    # _indicators 가 포함되어 critique 가 검증 가능
    assert "_indicators" in out
    ind = out["_indicators"]
    assert ind["hhi"] >= 0.6
    # signals 최소 3개
    assert len(out.get("signals", [])) >= 3


@pytest.mark.asyncio
async def test_portfolio_analyzer_injects_fallback_signals(fake_client) -> None:
    """LLM 이 signals 를 누락해도 analyzer 가 suggested_signals 로 채운다."""
    sample = _load("portfolio_balanced")
    # signals 없는 응답
    incomplete = {**sample["mock_analyzer_output"]}
    incomplete.pop("signals", None)
    fake_client.responses["analyzer"] = incomplete
    analyzer = PortfolioAnalyzer()
    state = {
        "input_data": sample["input"]["data"],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "portfolio",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    out = await analyzer.run(state)  # type: ignore[arg-type]
    assert len(out.get("signals", [])) >= 3


@pytest.mark.asyncio
async def test_portfolio_analyzer_handles_parse_error(fake_client) -> None:
    fake_client.responses["analyzer"] = "not json"
    analyzer = PortfolioAnalyzer()
    state = {
        "input_data": [
            {"market": "upbit", "code": "KRW-BTC", "quantity": 1, "avg_cost": 50_000_000, "currency": "KRW"},
        ],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "portfolio",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    out = await analyzer.run(state)  # type: ignore[arg-type]
    assert "_parse_error" in out
