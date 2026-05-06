from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from app.services.news.naver import search_naver_news


@respx.mock
@pytest.mark.asyncio
async def test_search_naver_news_decodes_utf8_and_strips_html(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NAVER_CLIENT_ID", "client-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "client-secret")
    respx.get("https://openapi.naver.com/v1/search/news.json").mock(
        return_value=Response(
            200,
            content=json.dumps(
                {
                    "items": [
                        {
                            "originallink": "https://news.example.com/apple",
                            "link": "https://news.naver.com/apple",
                            "title": "<b>애플</b> 개발자 &amp; 뉴스",
                            "description": "포트폴리오 &quot;패스트 트랙&quot;",
                            "pubDate": "Wed, 06 May 2026 14:02:00 +0900",
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={"content-type": "application/json"},
        )
    )

    results = await search_naver_news("Apple", display=1)

    assert len(results) == 1
    assert results[0].source_url == "https://news.example.com/apple"
    assert results[0].title == "애플 개발자 & 뉴스"
    assert results[0].excerpt == '포트폴리오 "패스트 트랙"'
