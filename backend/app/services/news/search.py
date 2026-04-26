"""뉴스/공시 RAG 검색 서비스.

sprint-02:
  - stub 모드: in-memory 벡터 저장소에서 cosine/L2 유사도로 top-k 반환
  - production 모드: pgvector DB에서 ANN 검색 (미구현, NotImplementedError)

stub 모드 결정론성:
  동일 query + symbols + k → 동일 순서/점수 (fake_embed 결정론성 보장).
"""

from __future__ import annotations

import math
import os
from typing import Any

from app.schemas.news import Citation
from app.services.rag.embeddings import embed


def _is_stub_mode() -> bool:
    return os.environ.get("COPILOT_NEWS_MODE", "stub").lower() == "stub"


def _l2_distance(a: list[float], b: list[float]) -> float:
    """L2 (Euclidean) 거리."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _ensure_fixture_loaded() -> None:
    """stub 저장소가 비어있으면 fixture corpus를 lazy 로드한다."""
    from app.services.news.ingest import _stub_documents, load_fixture_corpus

    if not _stub_documents:
        load_fixture_corpus()


def search_news_stub(
    query: str,
    symbols: list[str] | None,
    start_date: str | None,
    end_date: str | None,
    k: int,
) -> list[Citation]:
    """stub 저장소에서 top-k 청크를 검색해 Citation 목록으로 반환."""
    _ensure_fixture_loaded()
    from app.services.news.ingest import _stub_documents

    query_vec = embed(query)

    # 모든 청크 수집
    candidates: list[dict[str, Any]] = []
    for doc in _stub_documents.values():
        # symbols 필터 (제목/텍스트에 심볼이 포함된 문서만)
        if symbols:
            text_upper = (doc.get("title", "") + " " + doc.get("text", "")).upper()
            if not any(sym.upper() in text_upper for sym in symbols):
                continue

        # 날짜 필터 (published_at 비교)
        pub_at = doc.get("published_at", "")
        if start_date and pub_at and pub_at[:10] < start_date:
            continue
        if end_date and pub_at and pub_at[:10] > end_date:
            continue

        for chunk in doc.get("chunks", []):
            dist = _l2_distance(query_vec, chunk["embedding"])
            candidates.append(
                {
                    "doc_id": doc["id"],
                    "chunk_id": chunk["id"],
                    "source_url": doc["source_url"],
                    "title": doc["title"],
                    "published_at": doc.get("published_at"),
                    "excerpt": chunk["text"][:512],
                    "score": dist,
                }
            )

    # L2 거리 오름차순 정렬 (가까울수록 상위)
    candidates.sort(key=lambda x: (x["score"], x["chunk_id"]))

    return [Citation(**c) for c in candidates[:k]]


async def search_news(
    query: str,
    symbols: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    k: int = 5,
) -> list[Citation]:
    """뉴스/공시 RAG 검색.

    우선순위:
      1. 네이버 API 키가 설정돼 있으면 실시간 네이버 뉴스 검색 (한국·글로벌 모두 커버)
      2. 결과가 비어있거나 키 미설정이면 fixture stub 으로 폴백
    """
    from app.services.news.naver import is_naver_configured, search_naver_news

    if is_naver_configured():
        try:
            results = await search_naver_news(query, display=k, sort="date")
            if results:
                return results
        except Exception:  # noqa: BLE001 — 어떤 실패라도 fixture 로 폴백
            pass

    # fallback: fixture stub
    return search_news_stub(query, symbols, start_date, end_date, k)
