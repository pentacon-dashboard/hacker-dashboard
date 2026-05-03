"""follow-up 컨텍스트 빌더 — sprint-05.

build_active_context(): 이전 세션 턴을 읽어 Planner 에게 전달할 ActiveContext 를 생성한다.

고정 규칙:
- 직전 3턴만 (더 많으면 최신 3개만)
- 총 max_chars=2000 (합산), 초과 시 오래된 턴부터 truncate
- XML 태그 직렬화 포맷 (인젝션 방지 fence)
- user_query 는 <user_query> 태그로 래핑
- prior turn 의 query(sanitized) + final.card 요약만 포함
"""

from __future__ import annotations

import html

from app.schemas.copilot import ActiveContext, PriorTurn, SessionTurn
from app.services.session.protocol import SessionStoreProtocol

# ── 상수 ─────────────────────────────────────────────────────────────────────

_MAX_PRIOR_TURNS = 8
_MAX_CHARS = 2000
_MAX_QUERY_LEN = 200  # 단일 query 최대 길이 (sanitize)
_MAX_SUMMARY_LEN = 400  # 단일 summary 최대 길이


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────


def _sanitize_query(query: str) -> str:
    """사용자 입력에서 잠재적 인젝션 패턴을 이스케이프하고 길이를 제한한다."""
    # HTML 엔티티 이스케이프 (XML fence 내부이므로 태그 무력화)
    sanitized = html.escape(query, quote=True)
    # 길이 제한
    if len(sanitized) > _MAX_QUERY_LEN:
        sanitized = sanitized[:_MAX_QUERY_LEN] + "…"
    return sanitized


def _extract_summary(turn: SessionTurn) -> str:
    """final_card 에서 요약 텍스트를 추출한다.

    raw LLM 출력 / full plan 포함 금지. card 의 content/summary 필드만 사용.
    """
    if turn.final_card is None:
        return "(결과 없음)"
    card = turn.final_card
    # text card: content 또는 body
    summary = card.get("content") or card.get("body") or card.get("summary") or ""
    if not isinstance(summary, str):
        summary = str(summary)
    # 길이 제한
    if len(summary) > _MAX_SUMMARY_LEN:
        summary = summary[:_MAX_SUMMARY_LEN] + "…"
    return html.escape(summary, quote=True)


def _build_xml_context(prior_turns: list[PriorTurn]) -> str:
    """prior_turns → XML fence 직렬화.

    포맷: <prior_turns><turn id="N">query: Q\nsummary: S</turn></prior_turns>
    """
    if not prior_turns:
        return ""
    parts = ["<prior_turns>"]
    for i, pt in enumerate(prior_turns, start=1):
        parts.append(f'<turn id="{i}">query: {pt.query}\nsummary: {pt.summary}</turn>')
    parts.append("</prior_turns>")
    return "\n".join(parts)


def _truncate_to_budget(
    turns: list[SessionTurn],
    max_chars: int,
) -> list[PriorTurn]:
    """max_chars 예산 내로 prior_turns 를 구성한다.

    초과 시 오래된 턴부터 제거.
    """
    candidates: list[PriorTurn] = []
    for t in turns:
        pt = PriorTurn(
            turn_id=t.turn_id,
            query=_sanitize_query(t.query),
            summary=_extract_summary(t),
        )
        candidates.append(pt)

    # 예산 체크: 오래된 것부터 제거
    while candidates:
        total = sum(len(pt.query) + len(pt.summary) for pt in candidates)
        if total <= max_chars:
            break
        candidates.pop(0)  # 가장 오래된 것 제거

    return candidates


# ── 공개 함수 ─────────────────────────────────────────────────────────────────


async def build_active_context(
    session_id: str | None,
    user_query: str,
    store: SessionStoreProtocol,
) -> ActiveContext:
    """이전 세션 턴을 읽어 ActiveContext 를 생성한다.

    - session_id=None 또는 세션 없음: prior_turns=[], user_query=<wrapped>
    - 직전 3턴, max_chars=2000, XML fence 직렬화
    """
    wrapped_query = f"<user_query>{html.escape(user_query, quote=True)}</user_query>"

    if session_id is None:
        return ActiveContext(prior_turns=[], user_query=wrapped_query)

    try:
        recent_turns = await store.get_turns(session_id, limit=_MAX_PRIOR_TURNS)
    except Exception:  # noqa: BLE001
        recent_turns = []

    if not recent_turns:
        return ActiveContext(prior_turns=[], user_query=wrapped_query)

    prior_turns = _truncate_to_budget(recent_turns, _MAX_CHARS)

    return ActiveContext(prior_turns=prior_turns, user_query=wrapped_query)


def format_context_for_planner(active_context: ActiveContext) -> str:
    """ActiveContext → planner user 메시지 문자열로 직렬화.

    포맷:
    <prior_turns>...</prior_turns>
    <user_query>...</user_query>
    """
    parts: list[str] = []

    if active_context.prior_turns:
        xml_ctx = _build_xml_context(active_context.prior_turns)
        parts.append(xml_ctx)

    parts.append(active_context.user_query)
    return "\n".join(parts)


def format_context_for_agent(active_context: ActiveContext) -> str:
    """Format bounded session memory for answer-generation prompts.

    The agent context is intentionally explanatory memory, not permission to
    calculate new facts. Analyzer prompts still receive deterministic metrics
    through their normal inputs.
    """
    if not active_context.prior_turns:
        return (
            "Conversation context: none.\nDo not introduce new calculations or facts from memory."
        )

    lines = [
        "Conversation context:",
        "Use only these verified prior-turn summaries when explaining follow-up questions.",
        "Do not introduce new calculations, fresh market facts, or investment actions from memory.",
    ]
    for idx, turn in enumerate(active_context.prior_turns, start=1):
        lines.append(f"{idx}. user: {turn.query}")
        lines.append(f"   verified_summary: {turn.summary}")
    return "\n".join(lines)
