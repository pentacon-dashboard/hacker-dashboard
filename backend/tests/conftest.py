from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """FastAPI AsyncClient fixture — 실제 DB/Redis 없이 동작한다."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ──────────────── in-memory SQLite 세션 (포트폴리오 서비스 테스트용) ─────────────────


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """SQLite in-memory AsyncSession — 포트폴리오 서비스 단위 테스트용."""
    from app.db.models import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    # SQLite 는 JSONB 미지원 → JSON 으로 폴백
    from sqlalchemy.dialects import postgresql
    from sqlalchemy import JSON

    # JSONB → JSON 교체 (SQLite 호환)
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB  # noqa: F401

    async with engine.begin() as conn:
        # JSONB 컬럼을 JSON 으로 교체하여 테이블 생성
        await conn.run_sync(_create_tables_sqlite)

    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


def _create_tables_sqlite(conn: Any) -> None:
    """SQLite 환경에서 JSONB → JSON 으로 교체해 테이블 생성."""
    from sqlalchemy import Column, Date, DateTime, Integer, JSON, Numeric, String, UniqueConstraint, text
    from sqlalchemy import MetaData, Table

    metadata = MetaData()

    Table(
        "holdings",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", String(50), nullable=False, default="demo"),
        Column("market", String(20), nullable=False),
        Column("code", String(50), nullable=False),
        Column("quantity", Numeric(24, 8), nullable=False),
        Column("avg_cost", Numeric(24, 8), nullable=False),
        Column("currency", String(3), nullable=False, default="USD"),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
    )

    Table(
        "portfolio_snapshots",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", String(50), nullable=False, default="demo"),
        Column("snapshot_date", Date, nullable=False),
        Column("total_value_krw", Numeric(24, 4), nullable=False),
        Column("total_pnl_krw", Numeric(24, 4), nullable=False),
        Column("asset_class_breakdown", JSON, nullable=False),
        Column("holdings_detail", JSON, nullable=False),
        Column("created_at", DateTime(timezone=True)),
        UniqueConstraint("user_id", "snapshot_date", name="uq_snapshot_user_date"),
    )

    metadata.create_all(conn)


# ──────────────── 공통 가짜 Anthropic 클라이언트 (LLM 없는 환경용) ─────────────────


@dataclass
class _TextBlock:
    text: str


@dataclass
class _FakeResponse:
    content: list[_TextBlock]


@dataclass
class _FakeMessages:
    parent: "FakeAnthropicClient"

    async def create(self, **kwargs: Any) -> _FakeResponse:
        system = kwargs.get("system") or []
        system_text = ""
        if isinstance(system, list) and system:
            block = system[0]
            system_text = block.get("text", "") if isinstance(block, dict) else str(block)
        elif isinstance(system, str):
            system_text = system

        route = _detect_route(system_text)
        self.parent.calls.append({"route": route, "kwargs": kwargs})

        payload = self.parent.responses.get(route)
        if callable(payload):
            payload = payload(kwargs)
        if payload is not None:
            text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
            return _FakeResponse(content=[_TextBlock(text=text)])
        # 기본 fallback: 빈 JSON 객체
        return _FakeResponse(content=[_TextBlock(text="{}")])


@dataclass
class FakeAnthropicClient:
    """anthropic.AsyncAnthropic 의 최소 surface 를 흉내낸다."""

    responses: dict[str, Any] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.messages = _FakeMessages(parent=self)


def _detect_route(system_text: str) -> str:
    head = system_text[:300]
    if "Meta Router" in head or ("asset_class" in head and "Router" in head):
        return "router"
    if "Critique Verifier" in head or ("verdict" in head and "per_claim" in head):
        return "critique"
    if (
        "Stock Analyzer" in head
        or "Crypto Analyzer" in head
        or "FX Analyzer" in head
        or "Portfolio Analyzer" in head
        or "Macro Analyzer" in head
        or "Mixed (Multi-Asset) Analyzer" in head
    ):
        return "analyzer"
    return "unknown"


_VALID_ANALYZER_OUTPUT = {
    "asset_class": "stock",
    "summary": "테스트용 분석 요약",
    "highlights": ["포인트 1"],
    "metrics": {"latest_close": 100.0},
    "evidence": [{"claim": "테스트 근거", "rows": [0]}],
}

_VALID_CRITIQUE_OUTPUT = {
    "verdict": "pass",
    "per_claim": [{"claim": "테스트 근거", "status": "supported"}],
    "reason": "모든 근거가 입력 데이터에서 확인됨",
}


@pytest.fixture
def fake_llm_client():
    """
    API 키 없이 all-gates-pass 를 보장하는 FakeAnthropicClient 주입 fixture.
    테스트 함수에 매개변수로 선언하면 자동으로 set_client → teardown 된다.
    """
    from app.agents import llm as llm_module

    client = FakeAnthropicClient(
        responses={
            "analyzer": _VALID_ANALYZER_OUTPUT,
            "critique": _VALID_CRITIQUE_OUTPUT,
        }
    )
    llm_module.set_client(client)  # type: ignore[arg-type]
    yield client
    llm_module.set_client(None)
