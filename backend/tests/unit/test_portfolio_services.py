"""포트폴리오 확장 서비스 단위 테스트 — sprint-08 Phase B-1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.portfolio import (
    HoldingDetail,
    PortfolioSummary,
)
from app.services.portfolio_service import (
    ai_insight_stub,
    build_market_leaders,
    calc_win_rate,
    monthly_returns,
    sector_heatmap,
)

# ──────────────────────────────────────────────────────────────────────────────
# 테스트 헬퍼
# ──────────────────────────────────────────────────────────────────────────────


def _make_holding(
    id_: int,
    code: str,
    pnl_pct: str,
    value_krw: str = "1000000.00",
    pnl_krw: str = "10000.00",
    market: str = "yahoo",
    currency: str = "USD",
    current_price: str = "100.0000",
) -> HoldingDetail:
    return HoldingDetail(
        id=id_,
        market=market,
        code=code,
        quantity="10.00000000",
        avg_cost="90.0000",
        currency=currency,
        current_price=current_price,
        current_price_krw="133000.00",
        value_krw=value_krw,
        cost_krw="900000.00",
        pnl_krw=pnl_krw,
        pnl_pct=pnl_pct,
    )


def _make_summary(holdings: list[HoldingDetail]) -> PortfolioSummary:
    from app.services.portfolio_service import build_market_leaders, calc_win_rate

    return PortfolioSummary(
        total_value_krw="10000000.00",
        total_cost_krw="9500000.00",
        total_pnl_krw="500000.00",
        total_pnl_pct="5.26",
        daily_change_krw="100000.00",
        daily_change_pct="1.00",
        asset_class_breakdown={"stock_us": "0.5000", "crypto": "0.5000"},
        holdings=holdings,
        holdings_count=len(holdings),
        worst_asset_pct="-2.00",
        risk_score_pct="50.00",
        period_change_pct="3.00",
        period_days=30,
        win_rate_pct=calc_win_rate(holdings),
        market_leaders=build_market_leaders(holdings),
    )


# ──────────────────────────────────────────────────────────────────────────────
# calc_win_rate 테스트
# ──────────────────────────────────────────────────────────────────────────────


class TestCalcWinRate:
    def test_empty_holdings(self):
        """빈 목록 → '0.00'."""
        assert calc_win_rate([]) == "0.00"

    def test_all_positive(self):
        """전체 플러스 → '100.00'."""
        holdings = [
            _make_holding(1, "AAPL", "3.75"),
            _make_holding(2, "MSFT", "1.20"),
            _make_holding(3, "NVDA", "8.50"),
        ]
        assert calc_win_rate(holdings) == "100.00"

    def test_all_negative(self):
        """전체 마이너스 → '0.00'."""
        holdings = [
            _make_holding(1, "AAPL", "-3.75"),
            _make_holding(2, "MSFT", "-1.20"),
        ]
        assert calc_win_rate(holdings) == "0.00"

    def test_mixed(self):
        """4개 중 3개 플러스 → '75.00'."""
        holdings = [
            _make_holding(1, "AAPL", "3.75"),
            _make_holding(2, "MSFT", "1.20"),
            _make_holding(3, "NVDA", "8.50"),
            _make_holding(4, "TSLA", "-5.00"),
        ]
        result = calc_win_rate(holdings)
        assert result == "75.00"

    def test_zero_pnl_not_counted_as_win(self):
        """pnl_pct == 0 는 win 아님."""
        holdings = [
            _make_holding(1, "AAPL", "0.00"),
            _make_holding(2, "MSFT", "1.00"),
        ]
        result = calc_win_rate(holdings)
        assert result == "50.00"

    def test_single_winner(self):
        """1개 보유 수익 → '100.00'."""
        holdings = [_make_holding(1, "AAPL", "10.00")]
        assert calc_win_rate(holdings) == "100.00"


# ──────────────────────────────────────────────────────────────────────────────
# build_market_leaders 테스트
# ──────────────────────────────────────────────────────────────────────────────


class TestBuildMarketLeaders:
    def test_empty_returns_fallback(self):
        """보유 없으면 S&P top3 fallback."""
        leaders = build_market_leaders([])
        assert len(leaders) == 3
        tickers = [item.ticker for item in leaders]
        assert "NVDA" in tickers
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_fallback_has_correct_ranks(self):
        """fallback rank 순서."""
        leaders = build_market_leaders([])
        ranks = [item.rank for item in leaders]
        assert ranks == [1, 2, 3]

    def test_returns_top3_by_value(self):
        """value_krw 기준 상위 3개 반환."""
        holdings = [
            _make_holding(1, "AAPL", "3.75", value_krw="5000000.00"),
            _make_holding(2, "MSFT", "1.20", value_krw="3000000.00"),
            _make_holding(3, "NVDA", "8.50", value_krw="8000000.00"),
            _make_holding(4, "TSLA", "-2.00", value_krw="1000000.00"),
        ]
        leaders = build_market_leaders(holdings)
        assert len(leaders) == 3
        assert leaders[0].ticker == "NVDA"  # 최대 value
        assert leaders[1].ticker == "AAPL"
        assert leaders[2].ticker == "MSFT"

    def test_returns_all_if_less_than_3(self):
        """보유 2개면 2개만 반환."""
        holdings = [
            _make_holding(1, "AAPL", "3.75", value_krw="5000000.00"),
            _make_holding(2, "MSFT", "1.20", value_krw="3000000.00"),
        ]
        leaders = build_market_leaders(holdings)
        assert len(leaders) == 2
        assert leaders[0].rank == 1
        assert leaders[1].rank == 2

    def test_change_pct_format(self):
        """pnl_pct 부호 포함 문자열."""
        holdings = [_make_holding(1, "AAPL", "3.75", value_krw="1000000.00")]
        leaders = build_market_leaders(holdings)
        assert leaders[0].change_pct.startswith("+")

    def test_negative_change_pct(self):
        """마이너스 pnl 은 - 부호."""
        holdings = [_make_holding(1, "AAPL", "-2.50", value_krw="1000000.00", pnl_krw="-25000.00")]
        leaders = build_market_leaders(holdings)
        assert leaders[0].change_pct.startswith("-")

    def test_krw_currency_price_display(self):
        """KRW 통화 종목은 ₩ 표기."""
        holdings = [
            _make_holding(
                1,
                "005930",
                "4.17",
                value_krw="7500000.00",
                market="naver_kr",
                currency="KRW",
                current_price="75000.0000",
            )
        ]
        leaders = build_market_leaders(holdings)
        assert leaders[0].price_display.startswith("₩")


# ──────────────────────────────────────────────────────────────────────────────
# sector_heatmap 테스트
# ──────────────────────────────────────────────────────────────────────────────


class TestSectorHeatmap:
    def test_empty_holdings(self):
        """빈 보유 → 빈 목록."""
        assert sector_heatmap([]) == []

    def test_basic_sectors(self):
        """기본 섹터 집계."""
        holdings = [
            _make_holding(1, "AAPL", "3.75", value_krw="5000000.00"),
            _make_holding(2, "NVDA", "8.50", value_krw="3000000.00"),
            _make_holding(
                3, "KRW-BTC", "10.00", value_krw="2000000.00", market="upbit", currency="KRW"
            ),
        ]
        tiles = sector_heatmap(holdings)
        assert len(tiles) >= 2  # 최소 Tech + Crypto

    def test_weight_sums_near_100(self):
        """weight_pct 합계 ≈ 100."""
        holdings = [
            _make_holding(1, "AAPL", "3.75", value_krw="5000000.00"),
            _make_holding(2, "NVDA", "8.50", value_krw="3000000.00"),
            _make_holding(
                3, "KRW-BTC", "10.00", value_krw="2000000.00", market="upbit", currency="KRW"
            ),
        ]
        tiles = sector_heatmap(holdings)
        total = sum(float(t.weight_pct) for t in tiles)
        assert abs(total - 100.0) < 0.1

    def test_intensity_range(self):
        """intensity 는 -1.0 ~ +1.0 범위."""
        holdings = [
            _make_holding(1, "AAPL", "50.00", value_krw="1000000.00"),  # 극단값
            _make_holding(2, "MSFT", "-50.00", value_krw="1000000.00", pnl_krw="-500000.00"),
        ]
        tiles = sector_heatmap(holdings)
        for t in tiles:
            intensity = float(t.intensity)
            assert -1.0 <= intensity <= 1.0

    def test_custom_sector_map(self):
        """커스텀 sector_map 적용."""
        holdings = [_make_holding(1, "AAPL", "3.75", value_krw="1000000.00")]
        custom_map = {"AAPL": "커스텀섹터"}
        tiles = sector_heatmap(holdings, sector_map=custom_map)
        assert tiles[0].sector == "커스텀섹터"

    def test_unknown_ticker_goes_to_gita(self):
        """미매핑 티커 → '기타' 섹터."""
        holdings = [_make_holding(1, "UNKNOWN_XYZ", "1.00", value_krw="1000000.00")]
        tiles = sector_heatmap(holdings)
        assert tiles[0].sector == "기타"


# ──────────────────────────────────────────────────────────────────────────────
# monthly_returns 테스트
# ──────────────────────────────────────────────────────────────────────────────


class TestMonthlyReturns:
    def test_365_cells_for_non_leap_year(self):
        """2023년(평년) → 365개 셀."""
        cells = monthly_returns([], year=2023)
        assert len(cells) == 365

    def test_366_cells_for_leap_year(self):
        """2024년(윤년) → 366개 셀."""
        cells = monthly_returns([], year=2024)
        assert len(cells) == 366

    def test_date_format(self):
        """date 필드는 YYYY-MM-DD."""
        cells = monthly_returns([], year=2023)
        for c in cells[:10]:
            parts = c.date.split("-")
            assert len(parts) == 3
            assert len(parts[0]) == 4

    def test_cell_level_range(self):
        """cell_level 은 0~4 범위."""
        cells = monthly_returns([], year=2024)
        for c in cells:
            assert 0 <= c.cell_level <= 4

    def test_deterministic(self):
        """같은 holdings 로 두 번 호출 → 동일 결과."""
        holdings = [_make_holding(1, "AAPL", "3.75")]
        cells1 = monthly_returns(holdings, year=2025)
        cells2 = monthly_returns(holdings, year=2025)
        for c1, c2 in zip(cells1, cells2):
            assert c1.date == c2.date
            assert c1.return_pct == c2.return_pct
            assert c1.cell_level == c2.cell_level

    def test_return_pct_has_sign(self):
        """return_pct 에 + 또는 - 부호 포함."""
        cells = monthly_returns([], year=2025)
        for c in cells[:20]:
            assert c.return_pct.startswith("+") or c.return_pct.startswith("-")

    def test_first_date_is_jan_1(self):
        """첫 번째 셀 날짜 = 해당 연도 1월 1일."""
        cells = monthly_returns([], year=2025)
        assert cells[0].date == "2025-01-01"

    def test_last_date_is_dec_31(self):
        """마지막 셀 날짜 = 해당 연도 12월 31일."""
        cells = monthly_returns([], year=2025)
        assert cells[-1].date == "2025-12-31"


# ──────────────────────────────────────────────────────────────────────────────
# ai_insight_stub 테스트
# ──────────────────────────────────────────────────────────────────────────────


class TestAiInsightStub:
    def _make_summary_with_holdings(self, holdings: list[HoldingDetail]) -> PortfolioSummary:
        return _make_summary(holdings)

    def test_stub_mode_true(self):
        """stub_mode 는 항상 True."""
        summary = _make_summary([])
        result = ai_insight_stub(summary)
        assert result.stub_mode is True

    def test_gates_all_pass(self):
        """gates 는 schema/domain/critique 모두 'pass'."""
        summary = _make_summary([])
        result = ai_insight_stub(summary)
        assert result.gates["schema"] == "pass"
        assert result.gates["domain"] == "pass"
        assert result.gates["critique"] == "pass"

    def test_summary_not_empty(self):
        """summary 문자열 비어 있지 않음."""
        summary = _make_summary([_make_holding(1, "AAPL", "3.75")])
        result = ai_insight_stub(summary)
        assert len(result.summary) > 0

    def test_bullets_count(self):
        """bullets 는 정확히 3개."""
        summary = _make_summary([_make_holding(1, "AAPL", "3.75")])
        result = ai_insight_stub(summary)
        assert len(result.bullets) == 3

    def test_generated_at_is_iso(self):
        """generated_at 은 ISO 형식."""
        from datetime import datetime

        summary = _make_summary([])
        result = ai_insight_stub(summary)
        # 파싱 가능해야 함
        dt = datetime.fromisoformat(result.generated_at)
        assert dt.year >= 2026

    def test_high_risk_message(self):
        """risk_score 높으면 요약에 리밸런싱 언급."""
        summary = _make_summary([])
        # risk_score_pct 를 직접 high로 세팅
        summary.risk_score_pct = "80.00"
        result = ai_insight_stub(summary)
        assert "리밸런싱" in result.summary or "분산" in result.summary


# ──────────────────────────────────────────────────────────────────────────────
# 골든 샘플 기반 테스트
# ──────────────────────────────────────────────────────────────────────────────

_GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "portfolio_insight_samples"


def test_golden_large_portfolio():
    """골든 샘플: 대형 포트폴리오 인사이트 검증."""
    golden_path = _GOLDEN_DIR / "large_portfolio.json"
    if not golden_path.exists():
        pytest.skip("골든 샘플 파일 없음")

    data = json.loads(golden_path.read_text(encoding="utf-8"))
    holdings = [HoldingDetail(**h) for h in data["holdings"]]

    win_rate = calc_win_rate(holdings)
    assert win_rate == data["expected_win_rate_pct"]

    leaders = build_market_leaders(holdings)
    assert len(leaders) == data["expected_market_leaders_count"]

    tiles = sector_heatmap(holdings)
    assert len(tiles) >= data["expected_sector_tiles_min"]
