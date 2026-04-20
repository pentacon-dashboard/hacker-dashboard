"""
Mixed Analyzer 병렬 실행 + 머지 테스트.

검증:
- 버킷팅: stock / crypto / fx / macro 심볼이 각 버킷으로 분리되는가
- asyncio.gather 로 서브 analyzer 가 병렬 호출되는가 (fake client 가 여러 번 호출됨)
- 머지 결과: headline/highlights/signals 에 자산군 prefix 가 붙는가
- 일부 서브 실패해도 파이프라인은 통과
"""
from __future__ import annotations

from typing import Any

import pytest

from app.agents.analyzers.mixed import (
    MixedAnalyzer,
    _bucket_rows,
    _merge_sub_outputs,
)


def _mk_state(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "input_data": rows,
        "query": None,
        "asset_class_hint": None,
        "asset_class": "mixed",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }


# ───────── 버킷팅 ─────────


def test_bucket_rows_separates_stock_and_crypto() -> None:
    rows = [
        {"symbol": "AAPL", "close": 180},
        {"symbol": "KRW-BTC", "close": 60_000_000},
        {"symbol": "MSFT", "close": 420},
    ]
    buckets = _bucket_rows(rows)
    assert set(buckets.keys()) == {"stock", "crypto"}
    assert len(buckets["stock"]) == 2
    assert len(buckets["crypto"]) == 1


def test_bucket_rows_fx_and_macro() -> None:
    rows = [
        {"symbol": "USDKRW=X", "rate": 1350},
        {"date": "2024-01-01", "cpi": 3.1},
    ]
    buckets = _bucket_rows(rows)
    assert "fx" in buckets
    assert "macro" in buckets


# ───────── 머지 ─────────


def test_merge_sub_outputs_formats_highlights_with_prefix() -> None:
    subs = {
        "stock": {
            "asset_class": "stock",
            "summary": "AAPL 상승",
            "highlights": ["AAPL 171 → 174"],
            "signals": [{"kind": "trend", "strength": "medium", "rationale": "우상향"}],
            "evidence": [{"claim": "AAPL 171 → 174", "rows": [0, 2]}],
            "metrics": {"latest_close": 174.2},
            "confidence": 0.7,
        },
        "crypto": {
            "asset_class": "crypto",
            "summary": "BTC 상승",
            "highlights": ["KRW-BTC 59.5M → 62M"],
            "signals": [{"kind": "trend", "strength": "medium", "rationale": "3일 연속"}],
            "evidence": [],
            "metrics": {"latest_price": 62_000_000},
            "confidence": 0.8,
        },
    }
    merged = _merge_sub_outputs(subs)
    assert merged["asset_class"] == "mixed"
    assert "crypto" in merged["headline"] and "stock" in merged["headline"]
    # highlights 에 prefix
    assert any(h.startswith("[stock]") for h in merged["highlights"])
    assert any(h.startswith("[crypto]") for h in merged["highlights"])
    # metrics namespacing
    assert "stock__latest_close" in merged["metrics"]
    assert "crypto__latest_price" in merged["metrics"]
    # confidence 평균
    assert merged["confidence"] == pytest.approx(0.75, rel=1e-3)


def test_merge_sub_outputs_empty() -> None:
    merged = _merge_sub_outputs({})
    assert merged["asset_class"] == "mixed"
    assert merged["confidence"] == 0.0


# ───────── end-to-end with fake client ─────────


@pytest.mark.asyncio
async def test_mixed_analyzer_parallel_runs(fake_client) -> None:
    """stock + crypto 섞인 rows → 각 버킷으로 서브 analyzer 병렬 호출."""

    # 각 analyzer 요청에 대해 자산군별로 다른 응답을 주기 위해
    # 요청 payload 를 훑어 bucket rows 의 symbol 을 확인 → 적절 응답 반환
    def _answer(kwargs: dict[str, Any]) -> dict[str, Any]:
        import json as _j

        messages = kwargs.get("messages") or []
        content = ""
        if messages:
            c = messages[0].get("content", "")
            content = c if isinstance(c, str) else str(c)
        try:
            payload = _j.loads(content)
        except Exception:
            payload = {}
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        sym = ""
        if rows:
            first = rows[0]
            sym = first.get("symbol") or first.get("code") or first.get("pair") or ""

        if "KRW-BTC" in sym or "/USDT" in sym or "-USDT" in sym:
            return {
                "asset_class": "crypto",
                "summary": "KRW-BTC 상승",
                "highlights": ["KRW-BTC 59.5M → 62M"],
                "metrics": {"latest_price": 62_000_000},
                "signals": [{"kind": "trend", "strength": "medium", "rationale": "우상향"}],
                "evidence": [{"claim": "KRW-BTC 59500000 → 62000000", "rows": [0, 2]}],
                "confidence": 0.75,
            }
        return {
            "asset_class": "stock",
            "summary": "AAPL 상승",
            "highlights": ["AAPL 171 → 174.2"],
            "metrics": {"latest_close": 174.2},
            "signals": [{"kind": "trend", "strength": "medium", "rationale": "MA 상승"}],
            "evidence": [{"claim": "AAPL 171 → 174.2", "rows": [0, 2]}],
            "confidence": 0.7,
        }

    fake_client.responses["analyzer"] = _answer

    rows = [
        {"symbol": "AAPL", "date": "2024-04-01", "close": 171},
        {"symbol": "AAPL", "date": "2024-04-02", "close": 173.5},
        {"symbol": "AAPL", "date": "2024-04-03", "close": 174.2},
        {"symbol": "KRW-BTC", "date": "2024-04-01", "close": 59_500_000},
        {"symbol": "KRW-BTC", "date": "2024-04-02", "close": 60_800_000},
        {"symbol": "KRW-BTC", "date": "2024-04-03", "close": 62_000_000},
    ]
    analyzer = MixedAnalyzer()
    out = await analyzer.run(_mk_state(rows))  # type: ignore[arg-type]

    assert out["asset_class"] == "mixed"
    # 두 서브 analyzer 가 각각 1회씩 호출되었는가
    analyzer_calls = [c for c in fake_client.calls if c["route"] == "analyzer"]
    assert len(analyzer_calls) >= 2
    # sub_analyses 에 두 자산군 모두 있는가
    assert set(out["sub_analyses"].keys()) >= {"stock", "crypto"}


@pytest.mark.asyncio
async def test_mixed_analyzer_survives_partial_failure(fake_client) -> None:
    """서브 analyzer 하나가 터져도 나머지는 집계된다."""

    # stock 응답을 JSON 으로 반환하지만 crypto 쪽에 예외를 유도하려고 raise 설계는 못 하므로
    # 대신 parse_error 로 응답을 내게 만들어 본다. fake client 는 str 을 돌려주면
    # extract_json 이 실패 → analyzer.run 이 _parse_error 를 달아 돌려주는 경로.
    def _maybe_bad(kwargs: dict[str, Any]):
        import json as _j

        messages = kwargs.get("messages") or []
        content = messages[0].get("content", "") if messages else ""
        try:
            payload = _j.loads(content)
        except Exception:
            payload = {}
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        sym = rows[0].get("symbol", "") if rows else ""
        if "KRW-BTC" in sym:
            return "not json at all"
        return {
            "asset_class": "stock",
            "summary": "AAPL",
            "highlights": [],
            "metrics": {},
            "signals": [{"kind": "trend", "strength": "medium", "rationale": "x"}],
            "evidence": [],
            "confidence": 0.5,
        }

    fake_client.responses["analyzer"] = _maybe_bad

    rows = [
        {"symbol": "AAPL", "close": 180},
        {"symbol": "KRW-BTC", "close": 60_000_000},
    ]
    analyzer = MixedAnalyzer()
    out = await analyzer.run(_mk_state(rows))  # type: ignore[arg-type]
    assert out["asset_class"] == "mixed"
    # 최소 stock 서브 요약은 살아있다
    assert "stock" in out["sub_analyses"]


@pytest.mark.asyncio
async def test_mixed_analyzer_no_buckets_returns_minimal(fake_client) -> None:
    rows = [{"random": "data"}]
    analyzer = MixedAnalyzer()
    out = await analyzer.run(_mk_state(rows))  # type: ignore[arg-type]
    assert out["asset_class"] == "mixed"
    assert "분리하지 못" in out["summary"]
