"""뉴스·공시 문서 ingest 서비스.

sprint-02: URL 또는 텍스트를 받아 청킹 → 임베딩 → DB 업서트.
- stub 모드 (COPILOT_NEWS_MODE=stub): in-memory dict 저장소 사용 (pgvector DB 불필요)
- production 모드: SQLAlchemy 비동기 세션으로 pgvector DB에 저장

backend 규약: 모든 쿼리 비동기 → `async def ingest_document(...)` 고정.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from app.services.news.chunking import split_text
from app.services.rag.embeddings import embed

# ---------------------------------------------------------------------------
# stub 모드 in-memory 저장소
# ---------------------------------------------------------------------------

# stub_documents: {source_url -> {id, source_url, title, published_at, text, chunks}}
_stub_documents: dict[str, dict[str, Any]] = {}
_stub_doc_counter: int = 0
_stub_chunk_counter: int = 0


def _is_stub_mode() -> bool:
    return os.environ.get("COPILOT_NEWS_MODE", "stub").lower() == "stub"


def _next_doc_id() -> int:
    global _stub_doc_counter
    _stub_doc_counter += 1
    return _stub_doc_counter


def _next_chunk_id() -> int:
    global _stub_chunk_counter
    _stub_chunk_counter += 1
    return _stub_chunk_counter


async def ingest_document(doc: dict[str, Any]) -> dict[str, Any]:
    """문서를 적재한다.

    Parameters
    ----------
    doc:
        {
          "source_url": str,       # 유니크 키
          "title": str,
          "published_at": str,     # ISO-8601
          "text": str,
        }

    Returns
    -------
    {
      "document_id": int,
      "chunk_count": int,
      "is_new": bool,
    }

    멱등성: 동일 source_url 이면 기존 document_id 와 chunk_count 반환 (중복 없음).
    """
    source_url: str = doc["source_url"]
    title: str = doc.get("title", "")
    published_at: str = doc.get("published_at", datetime.now(UTC).isoformat())
    text: str = doc.get("text", "")

    if _is_stub_mode():
        return await _ingest_stub(source_url, title, published_at, text)
    else:
        return await _ingest_db(source_url, title, published_at, text)


# ---------------------------------------------------------------------------
# stub 모드 구현
# ---------------------------------------------------------------------------

async def _ingest_stub(
    source_url: str,
    title: str,
    published_at: str,
    text: str,
) -> dict[str, Any]:
    """in-memory 저장소에 적재 (멱등)."""
    if source_url in _stub_documents:
        existing = _stub_documents[source_url]
        return {
            "document_id": existing["id"],
            "chunk_count": len(existing["chunks"]),
            "is_new": False,
        }

    doc_id = _next_doc_id()
    chunks_text = split_text(text)
    chunks = []
    for idx, chunk_text in enumerate(chunks_text):
        vec = embed(chunk_text)
        chunks.append(
            {
                "id": _next_chunk_id(),
                "document_id": doc_id,
                "chunk_index": idx,
                "text": chunk_text,
                "embedding": vec,  # list[float] 1024차원
            }
        )

    _stub_documents[source_url] = {
        "id": doc_id,
        "source_url": source_url,
        "title": title,
        "published_at": published_at,
        "text": text,
        "chunks": chunks,
    }

    return {
        "document_id": doc_id,
        "chunk_count": len(chunks),
        "is_new": True,
    }


# ---------------------------------------------------------------------------
# production 모드 구현 (pgvector DB)
# ---------------------------------------------------------------------------

async def _ingest_db(
    source_url: str,
    title: str,
    published_at: str,
    text: str,
) -> dict[str, Any]:
    """SQLAlchemy 비동기 세션으로 pgvector DB에 적재 (멱등)."""
    from sqlalchemy import select

    from app.db.models import Document, DocumentChunk
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 기존 문서 확인
            result = await session.execute(
                select(Document).where(Document.source_url == source_url)
            )
            existing_doc = result.scalar_one_or_none()

            if existing_doc is not None:
                # 청크 수 조회
                chunk_result = await session.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.document_id == existing_doc.id
                    )
                )
                chunk_count = len(chunk_result.scalars().all())
                return {
                    "document_id": existing_doc.id,
                    "chunk_count": chunk_count,
                    "is_new": False,
                }

            # 신규 문서 생성
            try:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                pub_dt = None

            doc = Document(
                source_url=source_url,
                title=title,
                published_at=pub_dt,
            )
            session.add(doc)
            await session.flush()  # id 획득

            # 청킹 + 임베딩
            chunks_text = split_text(text)
            for idx, chunk_text in enumerate(chunks_text):
                vec = embed(chunk_text)
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    text=chunk_text,
                    embedding=vec,
                )
                session.add(chunk)

            return {
                "document_id": doc.id,
                "chunk_count": len(chunks_text),
                "is_new": True,
            }


# ---------------------------------------------------------------------------
# fixture 로드 유틸 (stub 모드에서 news/*.json 고정 코퍼스 사전 로드)
# ---------------------------------------------------------------------------

def _ingest_stub_sync(
    source_url: str,
    title: str,
    published_at: str,
    text: str,
) -> dict[str, Any]:
    """동기 버전 stub 적재 — fixture 사전 로드 전용 (asyncio 중첩 방지)."""
    global _stub_doc_counter, _stub_chunk_counter

    if source_url in _stub_documents:
        existing = _stub_documents[source_url]
        return {
            "document_id": existing["id"],
            "chunk_count": len(existing["chunks"]),
            "is_new": False,
        }

    doc_id = _next_doc_id()
    chunks_text = split_text(text)
    chunks = []
    for idx, chunk_text in enumerate(chunks_text):
        vec = embed(chunk_text)
        chunks.append(
            {
                "id": _next_chunk_id(),
                "document_id": doc_id,
                "chunk_index": idx,
                "text": chunk_text,
                "embedding": vec,
            }
        )

    _stub_documents[source_url] = {
        "id": doc_id,
        "source_url": source_url,
        "title": title,
        "published_at": published_at,
        "text": text,
        "chunks": chunks,
    }

    return {
        "document_id": doc_id,
        "chunk_count": len(chunks),
        "is_new": True,
    }


def load_fixture_corpus(fixture_dir: str | None = None) -> None:
    """tests/fixtures/news/*.json 를 stub 저장소에 사전 적재한다.

    동기 컨텍스트(lifespan 초기화, 테스트 setup 등)에서 안전하게 호출 가능.
    """
    from pathlib import Path

    if fixture_dir is None:
        # backend/app/services/news/ → backend/ → repo root 탐색
        base = Path(__file__).resolve().parents[4]  # → repo root
        fixture_dir_path = base / "backend" / "tests" / "fixtures" / "news"
    else:
        fixture_dir_path = Path(fixture_dir)

    if not fixture_dir_path.exists():
        return

    for json_file in sorted(fixture_dir_path.glob("*.json")):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            source_url = payload.get("source_url", "")
            title = payload.get("title", "")
            published_at = payload.get("published_at", "")
            text = payload.get("text", "")
            _ingest_stub_sync(source_url, title, published_at, text)
        except Exception:  # noqa: BLE001
            pass  # fixture 로드 실패는 조용히 무시
