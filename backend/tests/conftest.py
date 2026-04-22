from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app


# ──────────────── fake_orchestrator_llm — sprint-04/05 공통 fixture ──────────────


@dataclass
class _FakeOrchestratorLLM:
    """planner + sub-agent + critique LLM 호출을 결정론적 fake 로 대체하는 스파이.

    captured_prompts: list[dict] — 매 LLM 호출마다 아래 형태로 append.
      { "role_tag": "planner"|"critique"|"unknown", "system": str, "user": str }

    sprint-05 에서 role_tag="planner" 호출 캡처 + prompt injection 검증에 사용.
    """

    captured_prompts: list[dict[str, Any]] = field(default_factory=list)


@pytest.fixture(autouse=False, scope="function")
def fake_orchestrator_llm(monkeypatch: pytest.MonkeyPatch) -> _FakeOrchestratorLLM:
    """planner + sub-agent + 최종 통합 LLM 호출을 결정론적 fake 로 대체.

    대체 대상: app.agents.llm.call_llm (planner/critique/final 공용 진입).
    반환값은 테스트 호출 경로를 구분해 고정 plan/card 를 돌려준다.

    sprint-05 추가:
    - captured_prompts: list[dict] 에 매 호출 (role_tag, system, user) 기록
    - role_tag="planner": plan JSON 을 반환하는 경로
    - role_tag="critique": pass verdict 반환
    """
    spy = _FakeOrchestratorLLM()

    # planner system prompt 텍스트 (role_tag 감지용)
    _PLANNER_MARKERS = {"plan_id", "session_id", "steps", "agent", "gate_policy"}
    _CRITIQUE_MARKERS = {"critique", "verdict", "final"}

    async def _fake(
        *,
        system_prompt_name: str,
        user_content: str,
        model: str | None = None,
        max_tokens: int = 4096,
        **_: Any,
    ) -> str:
        lower = user_content.lower()

        # role_tag 판별
        if any(m in lower for m in ("plan_id", "session_id")) and "steps" in lower:
            role_tag = "planner"
        elif any(m in lower for m in ("critique", "verdict", "final")):
            role_tag = "critique"
        else:
            role_tag = "unknown"

        # system prompt 텍스트 로드 (실제 파일)
        try:
            from app.agents.llm import load_prompt
            system_text = load_prompt(system_prompt_name)
        except Exception:  # noqa: BLE001
            system_text = system_prompt_name

        spy.captured_prompts.append({
            "role_tag": role_tag,
            "system": system_text,
            "user": user_content,
            "system_prompt_name": system_prompt_name,
        })

        # 반환값
        if role_tag == "planner":
            # follow-up 질의에서 prior_turns 에 AAPL 이 있으면 steps 에 AAPL 주입
            symbol = "AAPL"
            if "aapl" in lower or "AAPL" in user_content:
                symbol = "AAPL"
            elif "msft" in lower:
                symbol = "MSFT"

            # <prior_turns> 에서 symbol 추출 시도
            import re as _re
            prior_match = _re.search(
                r"<prior_turns>.*?query:.*?([A-Z]{2,5}).*?</prior_turns>",
                user_content,
                _re.DOTALL,
            )
            if prior_match:
                symbol = prior_match.group(1)

            # follow-up 단축 조건: prior_turns 있고 "계속"/"조금" 등 단축 키워드이면 1개 step
            is_followup_short = (
                "<prior_turns>" in user_content and
                any(kw in user_content for kw in ("계속", "조금", "더", "만"))
            )
            if is_followup_short:
                steps = [
                    {
                        "step_id": "a",
                        "agent": "news-rag",
                        "inputs": {"symbol": symbol},
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    }
                ]
            else:
                steps = [
                    {
                        "step_id": "a",
                        "agent": "portfolio",
                        "inputs": {"symbol": symbol},
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    },
                    {
                        "step_id": "b",
                        "agent": "comparison",
                        "inputs": {"symbol": symbol},
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    },
                ]

            return json.dumps({
                "plan_id": "p-fake",
                "session_id": "s-fake",
                "steps": steps,
                "created_at": "2026-04-22T00:00:00Z",
            })

        if role_tag == "critique":
            return json.dumps({"verdict": "pass", "ok": True, "text": "fake critique pass"})

        # step token/result 경로
        return json.dumps({"type": "text", "body": "fake card"})

    monkeypatch.setattr("app.agents.llm.call_llm", _fake, raising=False)

    # 세션 저장소 초기화 (테스트 격리)
    try:
        from app.services.session import get_session_store
        store = get_session_store()
        if hasattr(store, "reset_all"):
            store.reset_all()
    except Exception:  # noqa: BLE001
        pass

    return spy


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
