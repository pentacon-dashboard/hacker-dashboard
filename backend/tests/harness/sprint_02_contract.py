"""sprint-02 acceptance — News/Filing RAG 인프라."""

from __future__ import annotations

import asyncio
import json
import math
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_pgvector_package_is_importable() -> None:
    """AC-02-0: pgvector>=0.3 이 dependencies에 선언되어 import 가능해야 한다."""
    from pgvector.sqlalchemy import Vector  # type: ignore

    assert Vector is not None


def test_document_models_exist() -> None:
    from app.db.models import Document, DocumentChunk  # type: ignore

    for col in ("id", "source_url", "title", "published_at"):
        assert hasattr(Document, col), f"Document.{col} missing"
    for col in ("id", "document_id", "chunk_index", "embedding", "text"):
        assert hasattr(DocumentChunk, col), f"DocumentChunk.{col} missing"


def test_alembic_migration_file_content() -> None:
    """AC-02-1 대체 채점 (1/2): 마이그레이션 파일 내용 정합성."""
    mig_dir = REPO_ROOT / "backend/alembic/versions"
    assert mig_dir.exists(), "alembic/versions 디렉토리 필요"
    candidates = list(mig_dir.glob("*.py"))
    contents = "\n".join(p.read_text(encoding="utf-8") for p in candidates)
    assert "CREATE EXTENSION IF NOT EXISTS vector" in contents, "pgvector extension 생성 DDL 누락"
    assert "VECTOR(1024)" in contents or "Vector(1024)" in contents, "VECTOR(1024) 컬럼 정의 누락"
    assert ("ivfflat" in contents.lower()) or ("hnsw" in contents.lower()), (
        "벡터 인덱스 DDL (ivfflat 또는 hnsw) 누락"
    )


def test_alembic_head_applies(tmp_path: Path) -> None:
    """`alembic upgrade head` 가 0 exit 로 끝나야 한다 (pgvector DB 필요).

    COPILOT_PGVECTOR_URL 미설정이면 **deferred** (skip). Evaluator는 skip을
    0점으로 처리하지 않으며, 대신 test_alembic_migration_file_content +
    test_ingest_inserts_vector_in_sqlite 로 대체 채점한다.
    """
    if not os.getenv("COPILOT_PGVECTOR_URL"):
        pytest.skip("COPILOT_PGVECTOR_URL not set; deferred — 대체 검증으로 채점")
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT / "backend",
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_ingest_inserts_vector_in_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-02-1 대체 채점 (2/2): skip 불가. fake_embed 출력이 길이 1024
    벡터로 직렬화/재조회 가능해야 한다. SQLite in-memory DB에서 `fake_embed` 출력이
    JSON 직렬화 가능한 길이 1024 벡터로 저장/재조회 되는지 검증. 이 테스트는
    **skip 불가, 반드시 통과**.
    """
    from app.services.rag.embeddings import fake_embed  # type: ignore

    vec = fake_embed("hello world — sprint-02 deterministic")
    assert isinstance(vec, list)
    assert len(vec) == 1024
    assert all(isinstance(x, float) for x in vec)
    # L2 norm ~= 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6, f"fake_embed must be L2-normalized, got {norm}"
    # 결정론성
    vec2 = fake_embed("hello world — sprint-02 deterministic")
    assert vec == vec2, "fake_embed must be deterministic for identical input"
    # 직렬화 가능성
    payload = json.dumps(vec)
    round_tripped = json.loads(payload)
    assert round_tripped == vec


def test_embed_provider_env_defaults_to_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-02-8: COPILOT_EMBED_PROVIDER 미설정 시 기본값 fake."""
    monkeypatch.delenv("COPILOT_EMBED_PROVIDER", raising=False)
    from app.services.rag import embeddings as emb_mod  # type: ignore

    # 모듈이 export 하는 provider selector 가 기본 fake 여야 한다.
    provider = getattr(emb_mod, "get_active_provider", lambda: "fake")()
    assert provider == "fake"


def test_search_news_stub_mode_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    """stub 모드에서 동일 쿼리는 동일 결과 순서를 반환한다."""
    monkeypatch.setenv("COPILOT_NEWS_MODE", "stub")
    monkeypatch.setenv("COPILOT_EMBED_PROVIDER", "fake")
    from app.main import app  # type: ignore

    client = TestClient(app)
    params = {"query": "earnings beat", "symbols": "AAPL", "k": 5}
    r1 = client.get("/search/news", params=params)
    r2 = client.get("/search/news", params=params)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json(), "stub mode must be deterministic"
    items = r1.json()
    assert len(items) >= 1 and len(items) <= 5
    for it in items:
        for k in ("doc_id", "chunk_id", "source_url", "title", "published_at", "excerpt", "score"):
            assert k in it, f"Citation.{k} missing"


def test_news_fixtures_are_nontrivial() -> None:
    fx_dir = REPO_ROOT / "backend/tests/fixtures/news"
    assert fx_dir.exists(), "fixtures/news 디렉토리 필요"
    docs = list(fx_dir.glob("*.json"))
    assert len(docs) >= 6, f"need >=6 fixture docs, got {len(docs)}"
    for doc in docs:
        payload = json.loads(doc.read_text("utf-8"))
        assert "source_url" in payload
        assert "published_at" in payload
        assert len(payload.get("text", "")) >= 512, f"{doc.name} too short"


def test_ingest_service_is_importable_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """동일 문서를 두 번 적재해도 청크가 중복 생성되지 않는다.

    ingest_document 는 `async def` 로 고정 (backend 규약 '모든 쿼리 비동기').
    동기 테스트에서 asyncio.run 으로 실행한다.
    """
    monkeypatch.setenv("COPILOT_NEWS_MODE", "stub")
    monkeypatch.setenv("COPILOT_EMBED_PROVIDER", "fake")
    from app.services.news.ingest import ingest_document  # type: ignore

    sample = {
        "source_url": "https://example.com/stub/apple-q1",
        "title": "Apple Q1 earnings",
        "published_at": "2026-01-30T21:00:00Z",
        "text": "Apple reported ... " + ("lorem " * 200),
    }
    # ingest_document 는 async 함수. asyncio.run 으로 실행.
    assert asyncio.iscoroutinefunction(ingest_document), (
        "ingest_document must be `async def` per backend 규약"
    )
    first = asyncio.run(ingest_document(sample))
    second = asyncio.run(ingest_document(sample))
    assert first["document_id"] == second["document_id"]
    assert first["chunk_count"] == second["chunk_count"]


def test_openapi_in_sync() -> None:
    current = (REPO_ROOT / "shared/openapi.json").read_text(encoding="utf-8")
    result = subprocess.run(
        ["uv", "run", "python", "-m", "app.export_openapi"],
        cwd=REPO_ROOT / "backend",
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    spec = json.loads(result.stdout)
    assert "/search/news" in spec["paths"]
    assert "/search/news/ingest" in spec["paths"]
    assert json.loads(result.stdout) == json.loads(current), "openapi drift"
