"""
통합 테스트: /analyze 엔드포인트 + portfolio_context 주입 경로.

테스트 케이스:
  (a) include_portfolio_context=false (기본): 기존 경로와 동일, 캐시 키 패턴 확인
  (b) include_portfolio_context=true + holdings 없음: graceful degrade, status=ok
  (c) include_portfolio_context=true + AAPL holding pre-seed + symbol AAPL:
      evidence에 source="portfolio.matched_holding" 존재
  (d) 캐시 키 분리: 같은 symbol에 대해 on/off 두 번 호출 시 캐시 HIT가 구분됨

LLM 호출은 conftest.FakeAnthropicClient 를 통해 mock — 실 Anthropic API 불호출.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import analyze_cache

# ── 공통 Mock 응답 ────────────────────────────────────────────────────────────

_BASE_ANALYZER_OUTPUT: dict[str, Any] = {
    "asset_class": "stock",
    "headline": "AAPL 안정적 상승세 지속",
    "narrative": "애플은 견조한 실적을 바탕으로 완만한 상승 추세를 이어가고 있습니다.",
    "summary": "AAPL 안정적 상승세",
    "highlights": ["매출 성장 지속", "강한 현금흐름"],
    "metrics": {"latest_close": 192.5},
    "signals": [{"kind": "trend", "strength": "medium", "rationale": "MA20 > MA60"}],
    "evidence": [{"claim": "최근 90일 수익률 +8%", "rows": [0], "source": "ohlc"}],
    "confidence": 0.78,
}

_PORTFOLIO_ANALYZER_OUTPUT: dict[str, Any] = {
    **_BASE_ANALYZER_OUTPUT,
    "evidence": [
        {"claim": "최근 90일 수익률 +8%", "rows": [0], "source": "ohlc"},
        {
            "claim": "보유 5주, 평균단가 $185 대비 현재 +4.1% 수익",
            "source": "portfolio.matched_holding",
            "quantity": 5,
            "avg_cost": 185,
        },
    ],
    "metrics": {
        "latest_close": 192.5,
        "matched_holding": {
            "market": "yahoo",
            "code": "AAPL",
            "quantity": "5",
            "avg_cost": "185",
            "currency": "USD",
        },
    },
}

_CRITIQUE_OUTPUT: dict[str, Any] = {
    "verdict": "pass",
    "per_claim": [{"claim": "최근 90일 수익률 +8%", "status": "supported"}],
    "reason": "근거 인용 확인됨",
}

_ROUTER_OUTPUT: dict[str, Any] = {
    "asset_class": "stock",
    "reason": "AAPL 은 Yahoo Finance 미국 주식 심볼",
}


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_cache():
    """각 테스트 전 캐시 초기화."""
    analyze_cache.reset_for_testing()
    yield
    analyze_cache.reset_for_testing()


@pytest.fixture
async def client():
    """FastAPI AsyncClient — 실제 DB/Redis 없이 동작."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _make_fake_client(use_portfolio: bool = False):
    """FakeAnthropicClient 를 직접 생성 (conftest 의 fixture 버전과 독립)."""
    from tests.conftest import FakeAnthropicClient

    analyzer_output = _PORTFOLIO_ANALYZER_OUTPUT if use_portfolio else _BASE_ANALYZER_OUTPUT

    return FakeAnthropicClient(
        responses={
            "router": _ROUTER_OUTPUT,
            "analyzer": analyzer_output,
            "critique": _CRITIQUE_OUTPUT,
        }
    )


# ── (a) include_portfolio_context=false (기본 경로) ──────────────────────────


@pytest.mark.asyncio
async def test_analyze_without_portfolio_context(client: AsyncClient) -> None:
    """
    (a) include_portfolio_context=false (기본):
        - 응답 status=ok
        - portfolio_context 주입 없이 기존 경로와 동일하게 처리
        - build_portfolio_context 가 호출되지 않음
    """
    from app.agents import llm as llm_module

    fake = _make_fake_client(use_portfolio=False)
    llm_module.set_client(fake)  # type: ignore[arg-type]

    try:
        with patch("app.api.analyze.build_portfolio_context", new_callable=AsyncMock) as mock_build:
            response = await client.post(
                "/analyze",
                json={
                    "data": [{"symbol": "AAPL", "price": 192.5, "date": "2026-04-20"}],
                    "asset_class_hint": "stock",
                    "include_portfolio_context": False,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "meta" in body
        # build_portfolio_context 는 호출되지 않아야 함
        mock_build.assert_not_called()
        # X-Cache 헤더 존재
        assert response.headers.get("X-Cache") in ("HIT", "MISS")

    finally:
        llm_module.set_client(None)


# ── (b) include_portfolio_context=true + holdings 없음 ──────────────────────


@pytest.mark.asyncio
async def test_analyze_portfolio_context_empty_holdings(client: AsyncClient) -> None:
    """
    (b) include_portfolio_context=true + holdings 없음:
        - graceful degrade: build_portfolio_context 가 None 반환
        - 그래도 status=ok (분석 정상 진행)
        - portfolio_context 없이도 에러 없음
    """
    from app.agents import llm as llm_module

    fake = _make_fake_client(use_portfolio=False)
    llm_module.set_client(fake)  # type: ignore[arg-type]

    try:
        # build_portfolio_context 가 None 반환 (holdings 없음 시뮬레이션)
        with patch(
            "app.api.analyze.build_portfolio_context",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.post(
                "/analyze",
                json={
                    "data": [{"symbol": "AAPL", "price": 192.5, "date": "2026-04-20"}],
                    "asset_class_hint": "stock",
                    "include_portfolio_context": True,
                },
            )

        assert response.status_code == 200
        body = response.json()
        # holdings 없어도 분석 정상 완료
        assert body["status"] == "ok"
        assert body["meta"]["asset_class"] == "stock"

    finally:
        llm_module.set_client(None)


# ── (c) AAPL holding pre-seed + matched_holding evidence ────────────────────


@pytest.mark.asyncio
async def test_analyze_portfolio_context_with_matched_holding(client: AsyncClient) -> None:
    """
    (c) include_portfolio_context=true + AAPL holding pre-seed:
        - PortfolioContext.matched_holding 이 주입됨
        - LLM 이 portfolio.matched_holding source evidence 를 포함
        - 응답 result.evidence 에 source="portfolio.matched_holding" 항목 존재
    """
    from decimal import Decimal

    from app.agents import llm as llm_module
    from app.schemas.analyze import PortfolioContext, PortfolioHolding

    fake = _make_fake_client(use_portfolio=True)
    llm_module.set_client(fake)  # type: ignore[arg-type]

    try:
        # AAPL holding 이 DB에 있다고 가정 — PortfolioContext 직접 구성
        mock_holding = PortfolioHolding(
            market="yahoo",
            code="AAPL",
            quantity=Decimal("5"),
            avg_cost=Decimal("185"),
            currency="USD",
            current_value_krw=Decimal("1300000"),
            pnl_pct=4.1,
        )
        mock_context = PortfolioContext(
            holdings=[mock_holding],
            total_value_krw=Decimal("1300000"),
            asset_class_breakdown={"stock_us": 1.0},
            matched_holding=mock_holding,
        )

        with patch(
            "app.api.analyze.build_portfolio_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ):
            response = await client.post(
                "/analyze",
                json={
                    "symbol": {"market": "yahoo", "code": "AAPL"},
                    "include_portfolio_context": True,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"

        # evidence 에 portfolio.matched_holding source 존재
        result = body.get("result") or {}
        evidence_list = result.get("evidence") or []
        portfolio_evidence = [
            ev
            for ev in evidence_list
            if isinstance(ev, dict) and ev.get("source") == "portfolio.matched_holding"
        ]
        assert len(portfolio_evidence) >= 1, (
            f"portfolio.matched_holding source 가 evidence 에 없음. evidence={evidence_list}"
        )

    finally:
        llm_module.set_client(None)


# ── (d) 캐시 키 분리 — on/off 두 번 호출 시 서로 다른 캐시 키 사용 ──────────


@pytest.mark.asyncio
async def test_cache_key_separation_portfolio_on_off(client: AsyncClient) -> None:
    """
    (d) 캐시 키 분리:
        - 같은 symbol에 대해 include_portfolio_context=false 와 true 를 각각 호출
        - 두 호출이 서로 다른 캐시 버킷을 사용해야 함
        - 두 번째 같은 플래그 호출 시 캐시 HIT 발생해야 함 (키 충돌 없음)
    """
    from decimal import Decimal

    from app.agents import llm as llm_module
    from app.schemas.analyze import PortfolioContext, PortfolioHolding
    from app.services import analyze_cache

    # Redis 잔여 데이터 방지 — LRU 전용 모드로 격리
    analyze_cache.reset_for_testing()
    analyze_cache._redis_available = False

    fake_base = _make_fake_client(use_portfolio=False)
    fake_portfolio = _make_fake_client(use_portfolio=True)

    mock_holding = PortfolioHolding(
        market="yahoo",
        code="MSFT",
        quantity=Decimal("10"),
        avg_cost=Decimal("420"),
        currency="USD",
    )
    mock_context = PortfolioContext(
        holdings=[mock_holding],
        total_value_krw=Decimal("5000000"),
        asset_class_breakdown={"stock_us": 1.0},
        matched_holding=mock_holding,
    )

    base_payload = {
        "data": [{"symbol": "MSFT", "price": 430.0, "date": "2026-04-20"}],
        "asset_class_hint": "stock",
        "include_portfolio_context": False,
    }
    portfolio_payload = {
        **base_payload,
        "include_portfolio_context": True,
    }

    try:
        # 첫 번째: portfolio=false (MISS)
        llm_module.set_client(fake_base)  # type: ignore[arg-type]
        with patch(
            "app.api.analyze.build_portfolio_context",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp1 = await client.post("/analyze", json=base_payload)

        assert resp1.status_code == 200
        assert resp1.headers.get("X-Cache") == "MISS"

        # 두 번째: portfolio=true (MISS — 다른 캐시 키)
        llm_module.set_client(fake_portfolio)  # type: ignore[arg-type]
        with patch(
            "app.api.analyze.build_portfolio_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ):
            resp2 = await client.post("/analyze", json=portfolio_payload)

        assert resp2.status_code == 200
        # portfolio=true 첫 호출은 MISS (다른 캐시 키)
        assert resp2.headers.get("X-Cache") == "MISS"

        # 세 번째: portfolio=false 다시 호출 (HIT — 동일 키)
        with patch(
            "app.api.analyze.build_portfolio_context",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp3 = await client.post("/analyze", json=base_payload)

        assert resp3.status_code == 200
        assert resp3.headers.get("X-Cache") == "HIT"

        # 네 번째: portfolio=true 다시 호출 (HIT — 포트폴리오 캐시 키)
        with patch(
            "app.api.analyze.build_portfolio_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ):
            resp4 = await client.post("/analyze", json=portfolio_payload)

        assert resp4.status_code == 200
        assert resp4.headers.get("X-Cache") == "HIT"

        # 두 응답의 result 가 다름 (캐시 분리 확인)
        r1_result = resp1.json().get("result") or {}
        r2_result = resp2.json().get("result") or {}
        # portfolio 버전에는 matched_holding source evidence 가 있음
        r2_evidence = [
            ev
            for ev in (r2_result.get("evidence") or [])
            if isinstance(ev, dict) and ev.get("source") == "portfolio.matched_holding"
        ]
        r1_evidence = [
            ev
            for ev in (r1_result.get("evidence") or [])
            if isinstance(ev, dict) and ev.get("source") == "portfolio.matched_holding"
        ]
        assert len(r2_evidence) >= 1, "portfolio 버전에 matched_holding evidence 없음"
        assert len(r1_evidence) == 0, "기본 버전에 matched_holding evidence 가 있으면 안 됨"

    finally:
        llm_module.set_client(None)
