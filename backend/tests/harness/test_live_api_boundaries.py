from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.asyncio
async def test_news_rag_uses_live_search_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_NEWS_MODE", "live")

    from app.agents.analyzers.news_rag import _retrieve_citations_async
    from app.schemas.copilot import CopilotStep, GatePolicy
    from app.schemas.news import Citation

    calls: list[dict[str, Any]] = []

    async def fake_search_news(
        query: str,
        symbols: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        k: int = 5,
    ) -> list[Citation]:
        calls.append(
            {
                "query": query,
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "k": k,
            }
        )
        return [
            Citation(
                doc_id=1,
                chunk_id=1,
                source_url="https://news.example.com/live-nvda",
                title="NVDA live news",
                published_at="2026-04-30T00:00:00+09:00",
                excerpt="NVDA live provider result",
                score=0.0,
            )
        ]

    monkeypatch.setattr("app.services.news.search.search_news", fake_search_news)

    step = CopilotStep(
        step_id="news-live-boundary",
        agent="news-rag",
        inputs={"query": "NVDA", "symbols": ["NVDA"], "k": 1},
        depends_on=[],
        gate_policy=GatePolicy.model_validate({"schema": True, "domain": True, "critique": True}),
    )

    citations = await _retrieve_citations_async(step)

    assert calls == [
        {
            "query": "NVDA",
            "symbols": ["NVDA"],
            "start_date": None,
            "end_date": None,
            "k": 1,
        }
    ]
    assert citations[0]["source_url"] == "https://news.example.com/live-nvda"


def test_compose_keeps_backend_env_wired_for_live_integrations() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "./.env" in compose
    assert "./backend/.env" in compose
    assert "COPILOT_NEWS_MODE: live" in compose
    assert "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-placeholder}" not in compose
    assert "NEXT_PUBLIC_COPILOT_MOCK" not in compose
