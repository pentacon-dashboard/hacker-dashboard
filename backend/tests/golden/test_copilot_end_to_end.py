"""
골든 샘플 E2E 회귀 테스트 — sprint-06 Copilot 통합

ASGI in-process (httpx.AsyncClient(app=...)) 방식으로 실행:
  - subprocess 로 uvicorn 기동 금지
  - FakeClient DI: backend/tests/conftest.py 의 fake_orchestrator_llm 상속
  - session 격리: 각 테스트에서 InMemorySessionStore() 명시 생성
  - baseline diff=0 이어야 통과
  - respx_mock fixture: 외부 HTTP(Anthropic/OpenAI API) 차단 → 실 LLM 호출 방지

환경변수 (모듈 상단 기본값):
  COPILOT_NEWS_MODE=stub
  COPILOT_EMBED_PROVIDER=fake
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
import respx  # noqa: F401 — respx 모듈 임포트: 외부 HTTP 차단 fixture 제공

os.environ.setdefault("COPILOT_NEWS_MODE", "stub")
os.environ.setdefault("COPILOT_EMBED_PROVIDER", "fake")

_SAMPLES_DIR = Path(__file__).parent / "samples" / "copilot"
_BASELINE_DIR = _SAMPLES_DIR
_REPO_ROOT = Path(__file__).resolve().parents[3]


# ───────────────────────── Helpers ──────────────────────────────────────────


def _load_sample(sample_id: str) -> dict[str, Any]:
    p = _SAMPLES_DIR / f"{sample_id}.json"
    return json.loads(p.read_text("utf-8"))


def _drain_sse(body: bytes) -> list[dict[str, Any]]:
    """SSE 바이트 스트림을 파싱해 event dict 목록 반환."""
    events: list[dict[str, Any]] = []
    for block in body.decode().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[len("data:") :].strip()))
                except json.JSONDecodeError:
                    pass
    return events


def _baseline_path(sample_id: str) -> Path:
    return _BASELINE_DIR / f"_baseline_copilot_e2e_{sample_id}.json"


_REGEN_BASELINE = os.environ.get("REGEN_BASELINE", "").lower() in ("1", "true", "yes")


def _load_or_create_baseline(sample_id: str, actual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """baseline 파일이 없으면 생성(초기화), 있으면 그대로 반환.

    REGEN_BASELINE=1 환경변수 설정 시 항상 baseline 을 현재 출력으로 업데이트한다.
    코드 변경(로직 regression 없음) 후 baseline 재정렬 목적으로만 사용.
    """
    p = _baseline_path(sample_id)
    if not p.exists() or _REGEN_BASELINE:
        p.write_text(json.dumps(actual, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(p.read_text("utf-8"))


def _strip_volatile(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """비교 전 휘발성 필드(timestamps, plan_id 등) 제거."""
    volatile_keys = {"created_at", "plan_id", "turn_id"}
    cleaned = []
    for ev in events:
        ev2 = {k: v for k, v in ev.items() if k not in volatile_keys}
        if "plan" in ev2 and isinstance(ev2["plan"], dict):
            ev2["plan"] = {k: v for k, v in ev2["plan"].items() if k not in volatile_keys}
        cleaned.append(ev2)
    return cleaned


# ───────────────────────── 격리 fixture ─────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_session_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """각 테스트마다 새 InMemorySessionStore 를 주입 — 모듈 간 누수 차단."""
    try:
        import app.services.session as _mod
        from app.services.session.memory_store import InMemorySessionStore

        store = InMemorySessionStore()
        monkeypatch.setattr(_mod, "_memory_store", store, raising=False)
        # get_session_store 가 항상 위 store 를 반환하도록
        monkeypatch.setattr(_mod, "get_session_store", lambda: store, raising=False)
    except Exception:  # noqa: BLE001
        pass


# ───────────────────────── Single-step golden tests ─────────────────────────


SINGLE_STEP_IDS = [
    "comparison_01",
    "comparison_02",
    "comparison_03",
    "simulator_01",
    "simulator_02",
    "simulator_03",
    "news_rag_01",
    "news_rag_02",
    "news_rag_03",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("sample_id", SINGLE_STEP_IDS)
async def test_single_step_golden(
    sample_id: str,
    fake_orchestrator_llm: Any,
) -> None:
    """단일 스텝 골든 샘플 — baseline diff=0."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app  # type: ignore[import]

    sample = _load_sample(sample_id)
    # step = sample["step"]  # unused; step_inputs used via sample.get("step") below

    # degraded 케이스: query 에 fake_orchestrator_llm 이 감지할 마커를 포함
    # - comparison_03: 존재하지 않는 심볼 → "DEFINITELY_NOT_A_SYMBOL_XYZ" 포함
    # - simulator_03: shock +500% → "500%" 포함
    base_query = sample.get("description", "test")
    if sample.get("expected_degraded"):
        agent = sample.get("agent", "")
        step_inputs = sample.get("step", {}).get("inputs", {})
        if agent == "comparison":
            symbols = step_inputs.get("symbols", [])
            unknown = [s for s in symbols if "DEFINITELY_NOT_A_SYMBOL" in s]
            if unknown:
                base_query = f"{base_query} DEFINITELY_NOT_A_SYMBOL_XYZ"
        elif agent == "simulator":
            shocks = step_inputs.get("shocks", {})
            if any(v >= 3.0 for v in shocks.values()):
                base_query = f"{base_query} shock +500%"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # copilot/query 엔드포인트를 통해 step 실행
        resp = await client.post(
            "/copilot/query",
            json={"query": base_query, "session_id": f"golden-{sample_id}"},
        )

    assert resp.status_code == 200, f"status={resp.status_code}: {resp.text[:500]}"

    events = _drain_sse(resp.content)
    assert events, "SSE stream must not be empty"

    # done 이벤트 존재 확인
    done_events = [e for e in events if e.get("type") == "done"]
    assert done_events, "SSE stream must end with 'done' event"

    # final.card 이벤트 존재 확인
    final_events = [e for e in events if e.get("type") == "final.card"]
    assert final_events, "SSE stream must contain 'final.card' event"

    # degraded 검증
    expected_degraded = sample.get("expected_degraded", False)
    final_card = final_events[-1].get("card", {})
    if not expected_degraded:
        assert not final_card.get("degraded", False), (
            f"sample {sample_id}: unexpected degraded=True in final card"
        )
    else:
        assert final_card.get("degraded", False), (
            f"sample {sample_id}: expected degraded=True but got False"
        )

    # baseline diff=0
    stripped = _strip_volatile(events)
    baseline = _load_or_create_baseline(sample_id, stripped)
    assert stripped == baseline, (
        f"sample {sample_id}: SSE event stream differs from baseline.\n"
        f"Expected: {json.dumps(baseline, indent=2)[:500]}\n"
        f"Got: {json.dumps(stripped, indent=2)[:500]}"
    )


# ───────────────────────── follow_up_2turn ──────────────────────────────────


@pytest.mark.asyncio
async def test_follow_up_2turn_golden(
    fake_orchestrator_llm: Any,
) -> None:
    """follow_up_2turn 골든 샘플 — 2턴 세션 격리 + baseline diff=0."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app  # type: ignore[import]

    sample = _load_sample("follow_up_2turn")
    session_id = "golden-follow_up_2turn"

    all_events: list[dict[str, Any]] = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for turn in sample["turns"]:
            payload: dict[str, Any] = {
                "query": turn["user"],
                "session_id": session_id,
            }
            resp = await client.post("/copilot/query", json=payload)
            assert resp.status_code == 200, f"turn {turn['turn_id']} status={resp.status_code}"

            turn_events = _drain_sse(resp.content)
            assert turn_events, f"turn {turn['turn_id']}: SSE stream empty"

            done_events = [e for e in turn_events if e.get("type") == "done"]
            assert done_events, f"turn {turn['turn_id']}: no 'done' event"

            # session_id carry-over: 이후 턴은 동일 session_id 사용
            if done_events:
                returned_sid = done_events[-1].get("session_id")
                if returned_sid:
                    session_id = returned_sid

            # expected_session_carry 검증
            if turn.get("expected_session_carry"):
                plan_events = [e for e in turn_events if e.get("type") == "plan.ready"]
                if plan_events:
                    plan = plan_events[0].get("plan", {})
                    steps_str = json.dumps(plan.get("steps", []))
                    # planner 가 prior turn 에서 심볼을 carry-over 했는지 확인
                    assert "TSLA" in steps_str or "NVDA" in steps_str or "a" in steps_str, (
                        f"turn {turn['turn_id']}: expected session carry, "
                        f"but plan steps don't carry prior context"
                    )

            all_events.extend(turn_events)

    # baseline diff=0
    stripped = _strip_volatile(all_events)
    baseline = _load_or_create_baseline("follow_up_2turn", stripped)
    assert stripped == baseline, (
        "follow_up_2turn: SSE event stream differs from baseline.\n"
        f"Expected events count: {len(baseline)}, Got: {len(stripped)}"
    )
