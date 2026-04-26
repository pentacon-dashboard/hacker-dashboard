"""포트폴리오 확장 서비스 — sprint-08 Phase B-1.

신규 순수 함수:
  - calc_win_rate: pnl_pct > 0 종목 비율
  - build_market_leaders: value_krw 상위 3개 (없으면 S&P top3 fallback)
  - sector_heatmap: 섹터별 가중 PnL 집계
  - monthly_returns: 결정론적 sin stub (년도 기준 365일)
  - ai_insight_stub: ADR-0012 stub 모드 인사이트

모든 함수는 외부 I/O 없는 순수 함수. (market_leaders 는 stub 가격 포함)
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.portfolio import (
    AiInsightResponse,
    HoldingDetail,
    MarketLeader,
    MonthlyReturnCell,
    PortfolioSummary,
    SectorHeatmapTile,
)
from app.services.sector_map import get_sector


def _fmt(v: Decimal, places: int = 2) -> str:
    quant = Decimal(10) ** -places
    return str(v.quantize(quant, rounding=ROUND_HALF_UP))


def _d(v: object) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# ──────────────────────────────────────────────────────────────────────────────
# calc_win_rate
# ──────────────────────────────────────────────────────────────────────────────


def calc_win_rate(holdings: list[HoldingDetail]) -> str:
    """보유 종목 중 pnl_pct > 0 비율 × 100 (문자열 소수점 2자리).

    빈 목록: "0.00"
    전체 플러스: "100.00"
    전체 마이너스: "0.00"
    """
    if not holdings:
        return "0.00"
    wins = sum(1 for h in holdings if _d(h.pnl_pct) > Decimal("0"))
    rate = Decimal(wins) / Decimal(len(holdings)) * Decimal("100")
    return _fmt(rate, 2)


# ──────────────────────────────────────────────────────────────────────────────
# build_market_leaders
# ──────────────────────────────────────────────────────────────────────────────

_SP500_FALLBACK: list[MarketLeader] = [
    MarketLeader(
        rank=1,
        name="NVIDIA",
        ticker="NVDA",
        market="yahoo",
        price="875.40",
        change_pct="+2.15",
        currency="USD",
        logo_url=None,
        price_display="$875.40",
        change_krw="+25,800",
    ),
    MarketLeader(
        rank=2,
        name="Apple",
        ticker="AAPL",
        market="yahoo",
        price="189.30",
        change_pct="+0.82",
        currency="USD",
        logo_url=None,
        price_display="$189.30",
        change_krw="+9,850",
    ),
    MarketLeader(
        rank=3,
        name="Microsoft",
        ticker="MSFT",
        market="yahoo",
        price="415.20",
        change_pct="+1.34",
        currency="USD",
        logo_url=None,
        price_display="$415.20",
        change_krw="+16,200",
    ),
]

_DISPLAY_NAMES: dict[str, str] = {
    "KRW-BTC": "Bitcoin",
    "KRW-ETH": "Ethereum",
    "KRW-SOL": "Solana",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "005930": "삼성전자",
    "000660": "SK하이닉스",
}


def build_market_leaders(holdings: list[HoldingDetail]) -> list[MarketLeader]:
    """value_krw 상위 3개 종목을 MarketLeader 로 변환.

    보유 종목 0건이면 S&P top3 하드코드 fallback 반환.
    """
    if not holdings:
        return list(_SP500_FALLBACK)

    sorted_holdings = sorted(holdings, key=lambda h: _d(h.value_krw), reverse=True)
    leaders: list[MarketLeader] = []
    for rank, h in enumerate(sorted_holdings[:3], start=1):
        pnl = _d(h.pnl_pct)
        sign = "+" if pnl >= 0 else ""
        pnl_str = f"{sign}{_fmt(pnl, 2)}"
        pnl_krw = _d(h.pnl_krw)
        krw_sign = "+" if pnl_krw >= 0 else ""
        # 간략 표기 (천 단위 쉼표)
        krw_display = f"{krw_sign}{int(pnl_krw):,}"

        # 현재가 display
        price_val = _d(h.current_price)
        currency = h.currency
        if currency == "KRW":
            price_display = f"₩{int(price_val):,}"
        elif currency in ("USD", "USDT"):
            price_display = f"${price_val:.2f}"
        else:
            price_display = f"{_fmt(price_val, 2)} {currency}"

        market_id = h.market
        leaders.append(
            MarketLeader(
                rank=rank,
                name=_DISPLAY_NAMES.get(h.code, h.code),
                ticker=h.code,
                market=market_id,
                price=str(price_val),
                change_pct=pnl_str,
                currency=currency,
                logo_url=None,
                price_display=price_display,
                change_krw=krw_display,
            )
        )
    return leaders


# ──────────────────────────────────────────────────────────────────────────────
# sector_heatmap
# ──────────────────────────────────────────────────────────────────────────────


def sector_heatmap(
    holdings: list[HoldingDetail],
    sector_map: dict[str, str] | None = None,
) -> list[SectorHeatmapTile]:
    """섹터별 가중 PnL 집계 → SectorHeatmapTile 목록.

    sector_map 이 None 이면 sector_map 서비스의 기본 맵 사용.
    """
    if sector_map is None:
        from app.services.sector_map import get_sector_map

        sector_map = get_sector_map()

    total_value = sum((_d(h.value_krw) for h in holdings), Decimal("0"))
    if total_value == 0:
        return []

    # 섹터 → (총 value, 총 pnl_krw)
    sector_value: dict[str, Decimal] = {}
    sector_pnl: dict[str, Decimal] = {}

    for h in holdings:
        sector = sector_map.get(h.code, get_sector(h.code))
        v = _d(h.value_krw)
        p = _d(h.pnl_krw)
        sector_value[sector] = sector_value.get(sector, Decimal("0")) + v
        sector_pnl[sector] = sector_pnl.get(sector, Decimal("0")) + p

    tiles: list[SectorHeatmapTile] = []
    for sector in sorted(sector_value.keys(), key=lambda s: sector_value[s], reverse=True):
        sv = sector_value[sector]
        sp = sector_pnl.get(sector, Decimal("0"))
        weight = sv / total_value * 100
        cost = sv - sp
        pnl_pct = (sp / cost * 100) if cost != 0 else Decimal("0")
        # intensity: pnl_pct 를 [-10%, +10%] 구간에 매핑 → [-1.0, +1.0] 클램프
        raw_intensity = float(pnl_pct) / 10.0
        clamped = max(-1.0, min(1.0, raw_intensity))
        sign = "+" if clamped >= 0 else ""
        pnl_sign = "+" if pnl_pct >= 0 else ""
        tiles.append(
            SectorHeatmapTile(
                sector=sector,
                weight_pct=_fmt(weight, 2),
                pnl_pct=f"{pnl_sign}{_fmt(pnl_pct, 2)}",
                intensity=f"{sign}{clamped:.2f}",
            )
        )
    return tiles


# ──────────────────────────────────────────────────────────────────────────────
# monthly_returns
# ──────────────────────────────────────────────────────────────────────────────


def monthly_returns(
    holdings: list[HoldingDetail],
    year: int | None = None,
) -> list[MonthlyReturnCell]:
    """year 연도의 일별 수익률 셀 목록 반환 (결정론적 sin stub).

    실제 스냅샷 서비스 연동 전까지 sin(day*0.1)*3 + offset 으로 결정론적 값 생성.
    cell_level: 0~4 (return_pct 구간 기반)
    """
    if year is None:
        year = date.today().year

    # 총 pnl 에서 오프셋 seed 추출 (결정론적, holdings 변경 시 달라짐)
    total_pnl = sum((_d(h.pnl_pct) for h in holdings), Decimal("0"))
    base_offset = float(total_pnl) * 0.01  # 작은 오프셋

    cells: list[MonthlyReturnCell] = []
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    current = start
    day_idx = 0
    while current <= end:
        # sin 기반 결정론적 수익률 (주말·공휴일 무관하게 매일 생성)
        raw = math.sin(day_idx * 0.1) * 3.0 + base_offset
        # 0.0 근처에서 약간의 노이즈 (day_idx 기반 결정론적)
        noise = math.cos(day_idx * 0.37) * 0.5
        ret = raw + noise

        sign = "+" if ret >= 0 else ""
        return_str = f"{sign}{ret:.2f}"

        # cell_level: 5구간
        abs_ret = abs(ret)
        if abs_ret < 0.5:
            level = 0
        elif abs_ret < 1.5:
            level = 1
        elif abs_ret < 2.5:
            level = 2
        elif abs_ret < 3.5:
            level = 3
        else:
            level = 4

        cells.append(
            MonthlyReturnCell(
                date=current.isoformat(),
                return_pct=return_str,
                cell_level=level,
            )
        )
        day_idx += 1
        current = date.fromordinal(current.toordinal() + 1)

    return cells


# ──────────────────────────────────────────────────────────────────────────────
# ai_insight_stub
# ──────────────────────────────────────────────────────────────────────────────


def ai_insight_stub(summary: PortfolioSummary) -> AiInsightResponse:
    """ADR-0012 stub 모드 AI 인사이트 생성.

    gates 전부 "pass", stub_mode=True.
    summary 기반 결정론적 문단 생성.
    """
    total = summary.total_value_krw
    pnl = summary.total_pnl_pct
    win = summary.win_rate_pct
    count = summary.holdings_count
    risk = summary.risk_score_pct

    summary_text = (
        f"현재 포트폴리오 총 평가금액은 ₩{total}이며, "
        f"총 손익률은 {pnl}%입니다. "
        f"보유 {count}개 종목 중 {win}%가 수익권에 있습니다. "
        f"집중도 리스크 점수는 {risk}점으로, "
        f"{'분산이 부족하여 리밸런싱을 검토할 필요가 있습니다.' if float(risk) > 50 else '적절한 분산 수준을 유지하고 있습니다.'}"
    )

    bullets = [
        f"총 평가 손익률 {pnl}% — 시장 대비 성과를 지속 모니터링하세요.",
        f"승률 {win}% — 수익 종목이 전체의 과반을 {'초과합니다.' if float(win) > 50 else '넘지 못합니다.'}",
        f"리스크 집중도 {risk}점 — {'다양한 자산군으로 분산 투자를 권장합니다.' if float(risk) > 50 else '현재 분산 수준은 양호합니다.'}",
    ]

    return AiInsightResponse(
        summary=summary_text,
        bullets=bullets,
        generated_at=datetime.now(UTC).isoformat(),
        stub_mode=True,
        gates={"schema": "pass", "domain": "pass", "critique": "pass"},
    )
