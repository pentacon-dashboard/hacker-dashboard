"""
Week-2 OHLC 컨텍스트 주입 테스트.

- symbol 필드를 받아 market 어댑터가 OHLC 를 프리패치 → analyzer 가 indicators 와
  함께 해석 → 근거 인용을 meta.evidence_snippets 에 노출.
- respx 로 market 어댑터의 httpx 호출을 mocking.
- fake_llm_client 로 Anthropic 호출을 고정하고, usage 에 cache_read_input_tokens 를
  심어 meta.cache 가 올바르게 전파되는지 검증.
"""
from __future__ import annotations

import json
from typing import Any

import pytest
import respx
from httpx import AsyncClient, Response

from app.agents import llm as llm_module
from app.agents.analyzers.base import compute_indicators
from tests.golden.conftest import FakeAnthropicClient, _Usage


# ───────────────────────── 테스트용 OHLC 생성기 ────────────────────────


def _upbit_candles(n: int = 90, base: float = 50_000_000.0) -> list[dict[str, Any]]:
    """업비트 /candles/days 응답 형식 (최신순 정렬). 단조 증가 + 약간의 변동."""
    from datetime import datetime, timedelta

    start = datetime(2023, 1, 1)
    out: list[dict[str, Any]] = []
    for i in range(n):
        delta = i * 100_000
        close = base + delta
        day_dt = start + timedelta(days=i)
        day = day_dt.strftime("%Y-%m-%d")
        out.append(
            {
                "market": "KRW-BTC",
                "candle_date_time_utc": f"{day}T00:00:00",
                "opening_price": close - 50_000,
                "high_price": close + 200_000,
                "low_price": close - 100_000,
                "trade_price": close,
                "candle_acc_trade_volume": 1000 + i,
            }
        )
    # Upbit 는 최신순(역순) 반환
    return list(reversed(out))


def _yahoo_chart(n: int = 90, base: float = 170.0) -> dict[str, Any]:
    """Yahoo /v8/finance/chart 응답 형식. 오름차순 타임스탬프."""
    import time as _time

    now_ts = 1_700_000_000
    day = 86_400
    timestamps = [now_ts + i * day for i in range(n)]
    closes = [base + i * 0.25 for i in range(n)]
    opens = [c - 0.5 for c in closes]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.2 for c in closes]
    vols = [80_000_000 + i * 10_000 for i in range(n)]
    return {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "TSLA", "currency": "USD"},
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": opens,
                                "high": highs,
                                "low": lows,
                                "close": closes,
                                "volume": vols,
                            }
                        ]
                    },
                }
            ]
        }
    }


# ───────────────────────── LLM fixture (OHLC 응답 세트) ─────────────────


@pytest.fixture
def ohlc_llm_client():
    client = FakeAnthropicClient(
        responses={
            "analyzer": {
                "asset_class": "crypto",
                "headline": "KRW-BTC 90일 추세 기반 요약",
                "narrative": "indicators 기반 서술. 변동성 보통 수준.",
                "summary": "indicators 를 참조한 요약",
                "highlights": [
                    "첫 종가와 마지막 종가 차이 기반 상승",
                    "MA20/MA60 교차 확인",
                ],
                "metrics": {
                    "latest_price": 58_900_000,
                    "period_return_pct": 17.8,
                    "volatility_pct": 0.6,
                    "quote_currency": "KRW",
                },
                "signals": [
                    {"kind": "trend", "strength": "medium", "rationale": "MA20 > MA60"}
                ],
                "evidence": [
                    {"claim": "첫 종가와 마지막 종가 차이", "rows": [0, 89]}
                ],
                "confidence": 0.8,
            },
            "critique": {
                "verdict": "pass",
                "per_claim": [
                    {"claim": "첫 종가와 마지막 종가 차이", "status": "supported"}
                ],
                "reason": "all claims supported",
            },
        },
        usage_per_route={
            "analyzer": _Usage(
                cache_read_input_tokens=1234,
                cache_creation_input_tokens=256,
                input_tokens=800,
                output_tokens=250,
            ),
            "critique": _Usage(
                cache_read_input_tokens=300,
                cache_creation_input_tokens=0,
                input_tokens=200,
                output_tokens=80,
            ),
        },
    )
    llm_module.set_client(client)  # type: ignore[arg-type]
    yield client
    llm_module.set_client(None)


# ───────────────────────── 실제 테스트 ─────────────────────────


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_analyze_with_crypto_ohlc_symbol(
    client: AsyncClient, ohlc_llm_client
) -> None:
    """KRW-BTC 심볼만 주면 어댑터가 OHLC 90일 을 프리패치하여 analyzer 에 주입한다."""
    respx.get("https://api.upbit.com/v1/candles/days").mock(
        return_value=Response(200, json=_upbit_candles(90))
    )

    payload = {
        "data": [],
        "symbol": {"market": "upbit", "code": "KRW-BTC"},
        "asset_class_hint": "crypto",
    }
    resp = await client.post("/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # 기본 필드
    assert body["status"] == "ok"
    assert body["meta"]["asset_class"] == "crypto"
    assert body["meta"]["analyzer_name"] == "crypto"

    # 게이트 전부 pass
    gates = body["meta"]["gates"]
    assert gates["schema_gate"] == "pass"
    assert gates["domain_gate"] == "pass"
    assert gates["critique_gate"] == "pass"

    # evidence_snippets 가 critique pass 후에만 채워진다
    assert len(body["meta"]["evidence_snippets"]) >= 1
    assert isinstance(body["meta"]["evidence_snippets"][0], str)

    # cache 메트릭 전파 — analyzer + critique 두 호출의 합계
    cache = body["meta"]["cache"]
    assert cache["read_tokens"] == 1234 + 300
    assert cache["creation_tokens"] == 256
    assert cache["input_tokens"] == 800 + 200
    assert cache["output_tokens"] == 250 + 80


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_analyze_with_stock_ohlc_symbol(
    client: AsyncClient, ohlc_llm_client
) -> None:
    """TSLA 심볼 → yahoo 어댑터 → 주식 analyzer 파이프라인."""
    respx.get("https://query1.finance.yahoo.com/v8/finance/chart/TSLA").mock(
        return_value=Response(200, json=_yahoo_chart(90))
    )

    # analyzer 응답을 stock 용으로 재정의
    ohlc_llm_client.responses["analyzer"] = {
        "asset_class": "stock",
        "headline": "TSLA 90일 상승",
        "narrative": "MA20 > MA60 지속, 변동성 낮음",
        "summary": "TSLA 90일간 안정적 상승",
        "highlights": ["첫 종가 대비 마지막 종가 상승"],
        "metrics": {
            "latest_close": 192.25,
            "period_return_pct": 13.1,
            "volatility_pct": 0.4,
        },
        "signals": [
            {"kind": "trend", "strength": "medium", "rationale": "MA20 > MA60"}
        ],
        "evidence": [{"claim": "첫 종가 170.0 → 마지막 종가 192.25", "rows": [0, 89]}],
        "confidence": 0.75,
    }

    payload = {
        "data": [],
        "symbol": {"market": "yahoo", "code": "TSLA"},
        "asset_class_hint": "stock",
    }
    resp = await client.post("/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["meta"]["asset_class"] == "stock"
    assert body["meta"]["analyzer_name"] == "stock"
    assert body["meta"]["gates"]["schema_gate"] == "pass"
    assert body["meta"]["gates"]["domain_gate"] == "pass"
    assert body["meta"]["gates"]["critique_gate"] == "pass"
    assert body["meta"]["cache"]["read_tokens"] > 0


@pytest.mark.asyncio
async def test_analyze_with_inline_context_ohlc(
    client: AsyncClient, ohlc_llm_client
) -> None:
    """클라이언트가 context.ohlc 로 직접 넘기면 어댑터 호출 없이 분석."""
    bars = [
        {
            "ts": f"2024-01-{i+1:02d}T00:00:00Z",
            "open": 100.0 + i,
            "high": 102.0 + i,
            "low": 99.0 + i,
            "close": 101.0 + i,
            "volume": 1_000_000,
        }
        for i in range(30)
    ]
    payload = {
        "data": [],
        "context": {"ohlc": bars},
        "asset_class_hint": "stock",
    }
    # stock analyzer 응답으로 전환
    ohlc_llm_client.responses["analyzer"] = {
        "asset_class": "stock",
        "headline": "30일 데이터 상승",
        "narrative": "context 에서 들어온 OHLC 기반 분석",
        "summary": "30일 종가 101 → 130 (29% 상승)",
        "highlights": ["종가 101 → 130"],
        "metrics": {"latest_close": 130.0, "period_return_pct": 28.7},
        "signals": [],
        "evidence": [{"claim": "종가 101 → 130", "rows": [0, 29]}],
        "confidence": 0.7,
    }

    resp = await client.post("/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["asset_class"] == "stock"
    assert body["meta"]["gates"]["schema_gate"] == "pass"
    assert body["meta"]["evidence_snippets"], "evidence_snippets should be non-empty"


# ───────────────────── 순수함수 (indicators) 단위 테스트 ─────────────────


def test_compute_indicators_basic_trend_and_drawdown() -> None:
    rows = [{"close": 100.0}, {"close": 110.0}, {"close": 95.0}, {"close": 120.0}]
    ind = compute_indicators(rows)
    assert ind["n"] == 4
    assert ind["first_close"] == 100.0
    assert ind["last_close"] == 120.0
    assert ind["period_return_pct"] == 20.0
    assert ind["max_drawdown_pct"] < 0  # 110→95 구간 하락
    assert ind["trend"] == "up"


def test_compute_indicators_empty() -> None:
    assert compute_indicators([]) == {}
    assert compute_indicators([{"close": 100}]) == {}


def test_compute_indicators_ma_cross_golden() -> None:
    # 60개 이상 상승 시계열 → MA20 > MA60 (golden)
    rows = [{"close": 100.0 + i} for i in range(60)]
    ind = compute_indicators(rows)
    assert ind["ma_20"] is not None
    assert ind["ma_60"] is not None
    assert ind["ma_20"] > ind["ma_60"]
    assert ind["ma_cross"] == "golden"


def test_select_model_threshold() -> None:
    from app.agents.llm import COMPLEX_ROW_THRESHOLD, MODEL_OPUS, MODEL_SONNET, select_model

    assert select_model(100) == MODEL_SONNET
    assert select_model(COMPLEX_ROW_THRESHOLD + 1) == MODEL_OPUS
    assert select_model(COMPLEX_ROW_THRESHOLD) == MODEL_SONNET


def test_reset_and_get_cache_metrics() -> None:
    llm_module.reset_cache_metrics()
    m0 = llm_module.get_cache_metrics()
    assert all(v == 0 for v in m0.values())
