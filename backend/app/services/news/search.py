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
    """뉴스/공시 RAG 검색. stub 모드와 production 모드를 분기한다."""
    if _is_stub_mode():
        return search_news_stub(query, symbols, start_date, end_date, k)
    else:
        raise NotImplementedError(
            "production 모드 pgvector 검색은 sprint-03 이후 구현 예정. "
            "COPILOT_NEWS_MODE=stub 사용."
        )
