from __future__ import annotations

import json

from app.services.news.ingest import _stub_documents, load_fixture_corpus
from app.services.news.search import search_news_stub


def test_stub_news_search_filters_malformed_fixture_rows(tmp_path) -> None:
    _stub_documents.clear()
    try:
        (tmp_path / "bad.json").write_text(
            json.dumps(
                {
                    "source_url": "not-a-url",
                    "title": "",
                    "published_at": None,
                    "text": "broken row",
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "good.json").write_text(
            json.dumps(
                {
                    "source_url": "https://example.com/news/market-note",
                    "title": "Market note",
                    "published_at": "2026-04-01T00:00:00Z",
                    "text": "Market update covering NVDA, Apple, Bitcoin, and Korean equities.",
                }
            ),
            encoding="utf-8",
        )

        load_fixture_corpus(str(tmp_path))
        results = search_news_stub("market", None, None, None, 5)

        assert results
        assert {item.source_url for item in results} == {
            "https://example.com/news/market-note"
        }
        assert all(item.title for item in results)
    finally:
        _stub_documents.clear()
