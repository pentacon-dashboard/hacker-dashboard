"""Client briefing report service tests."""

from __future__ import annotations

from app.schemas.portfolio import HoldingDetail, PortfolioSummary
from app.services.report import build_client_briefing_report


def test_client_briefing_report_degrades_when_cost_basis_pnl_missing() -> None:
    summary = PortfolioSummary(
        user_id="demo",
        client_id="client-001",
        client_name="Client One",
        total_value_krw="30000000.00",
        total_cost_krw=None,
        total_pnl_krw=None,
        total_pnl_pct=None,
        daily_change_krw="0.00",
        daily_change_pct="0.00",
        asset_class_breakdown={"crypto": "1.0000"},
        sector_breakdown={"Digital Assets": "1.0000"},
        holdings=[
            HoldingDetail(
                id=1,
                market="upbit",
                code="KRW-BTC",
                quantity="0.50000000",
                avg_cost=None,
                currency="KRW",
                current_price="60000000.0000",
                current_price_krw="60000000.00",
                value_krw="30000000.00",
                cost_krw=None,
                pnl_krw=None,
                pnl_pct=None,
            )
        ],
        holdings_count=1,
        worst_asset_pct=None,
        risk_score_pct="100.00",
        period_change_pct="0.00",
        dimension_breakdown=[],
        win_rate_pct=None,
        market_leaders=[],
    )

    report = build_client_briefing_report(summary)
    report_text = "\n".join(section.body for section in report.sections)

    assert report.status == "degraded"
    assert report.export_ready is False
    assert report.gate_results["evidence_gate"] == "degraded: missing cost basis"
    assert "None%" not in report_text
    assert "손익률은 0.00%" not in report_text
    assert "원가 정보 부족" in report_text
