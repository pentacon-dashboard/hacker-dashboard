"""Copilot SSE orchestrator.

The transport remains JSON-over-SSE, but user-facing final cards must be
conversation-ready text. Internal step ids, gate labels, and fallback markers
must never leak into final answers.
"""

from __future__ import annotations

import asyncio
import datetime
import html
import json
import os
import re
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import app.agents.llm as _llm_module
from app.agents.llm import extract_json
from app.agents.planner import build_copilot_plan
from app.schemas.copilot import (
    ActiveContext,
    ChartCard,
    CitationCard,
    ComparisonTableCard,
    CopilotPlan,
    CopilotStep,
    GatePolicy,
    ScorecardCard,
    SessionTurn,
    SimulatorResultCard,
    TextCard,
)
from app.services.copilot.context import (
    build_active_context,
    format_context_for_agent,
    format_context_for_planner,
)
from app.services.copilot.intent import classify_copilot_intent
from app.services.session import get_session_store
from app.services.session.memory_store import make_turn_id

_DEFAULT_COPILOT_CLIENT_ID = "client-001"
_PORTFOLIO_USER_IDS = ("pb-demo", "demo")
_CLIENT_ID_RE = re.compile(r"\bclient-(\d{3})\b", re.IGNORECASE)
_CLIENT_NUMERIC_RE = re.compile(r"\bclient\s*[-_ ]?\s*(\d{1,3})\b", re.IGNORECASE)
_CLIENT_LABEL_RE = re.compile(r"(?:고객|client|customer)\s*[-_:]?\s*([A-Za-z])\b", re.IGNORECASE)
_CLIENT_REVERSE_LABEL_RE = re.compile(
    r"\b([A-Za-z])\s*[-_:]?\s*(?:고객|client|customer)\b", re.IGNORECASE
)
_CLIENT_REFERENCE_PREFIX_RE = re.compile(
    r"^\s*(?P<reference>.+?)\s*(?:포트폴리오|portfolio|요약|분석|리밸런싱|rebalance|summary|report)\b",
    re.IGNORECASE,
)
_CLIENT_REFERENCE_MARKER_RE = re.compile(r"(?:고객|client|customer|client-\d{3})", re.IGNORECASE)
_CLIENT_PORTFOLIO_TERM_RE = re.compile(
    r"(?:포트폴리오|portfolio|요약|리밸런싱|rebalance|summary|report)",
    re.IGNORECASE,
)
_GENERIC_CLIENT_REFERENCES = {"", "현재", "지금", "내", "전체", "포트폴리오", "portfolio"}
_SAFETY_CLIENT_RESOLUTION_STATUSES = {
    "ambiguous",
    "mismatch",
    "not_found",
    "no_portfolio_data",
}


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


def _schema_gate(card: dict[str, Any], step: CopilotStep) -> tuple[str, str]:
    import pydantic

    card_type = card.get("type", "")
    model_map: dict[str, type[pydantic.BaseModel]] = {
        "text": TextCard,
        "chart": ChartCard,
        "scorecard": ScorecardCard,
        "citation": CitationCard,
        "comparison_table": ComparisonTableCard,
        "simulator_result": SimulatorResultCard,
    }
    model_cls = model_map.get(card_type)
    if model_cls is None:
        return "fail", f"unknown card type: {card_type!r}"

    try:
        model_cls.model_validate(card)
        return "pass", ""
    except Exception as exc:  # noqa: BLE001
        return "fail", str(exc)[:200]


def _domain_gate(card: dict[str, Any], step: CopilotStep) -> tuple[str, str]:
    card_type = card.get("type", "")
    if card_type == "chart" and not card.get("series"):
        return "fail", "chart card has no series data"
    if card_type == "scorecard" and not card.get("rows"):
        return "fail", "scorecard card has no rows"
    return "pass", ""


async def _critique_gate(
    card: dict[str, Any], step: CopilotStep, *, is_final: bool = False
) -> tuple[str, str]:
    instruction = "위 copilot card 가 사용자 질의에 적합하고 사실에 기반한 내용인지 평가하라. "
    instruction += (
        "Do not fail only because deterministic numeric metrics look unusual, high, low, "
        "or intuitively inconsistent. Fail only for unsupported claims, guaranteed returns, "
        "missing-data contradictions, or clear internal contradictions. "
    )
    if is_final:
        instruction += "최종 통합 응답이므로 인용이 있다면 excerpt 와 일치하는지 확인하라. "
    instruction += 'JSON 만 출력: {"verdict": "pass"|"fail", "reason": "..."}'

    prompt = json.dumps(
        {
            "step_id": step.step_id,
            "card": card,
            "instruction": instruction,
            "critique": True,
            "final": is_final,
        },
        ensure_ascii=False,
    )

    try:
        raw = await _llm_module.call_llm(
            system_prompt_name="critique_system",
            user_content=prompt,
            max_tokens=300,
        )
        parsed = extract_json(raw)
        verdict = parsed.get("verdict", "pass")
        reason = parsed.get("reason", "")
        if verdict == "fail":
            return "fail", reason or "critique failed"
        return "pass", reason
    except Exception:  # noqa: BLE001
        return "pass", "critique unavailable"


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        close = t.rfind("```")
        if close != -1:
            t = t[:close]
    return t.strip()


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, str):
        return value
    if value is None:
        return "-"
    return json.dumps(value, ensure_ascii=False, default=str)


def _to_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _format_krw(value: Any) -> str:
    number = _to_decimal(value)
    if number is None:
        return _format_value(value)
    return f"{number.quantize(Decimal('1')):,}원"


def _format_pct(value: Any) -> str:
    number = _to_decimal(value)
    if number is None:
        return f"{_format_value(value)}%"
    return f"{number.quantize(Decimal('0.01'))}%"


def _format_weight_pct(value: Any) -> str:
    number = _to_decimal(value)
    if number is None:
        return f"{_format_value(value)}%"
    if abs(number) <= Decimal("1"):
        number *= Decimal("100")
    return f"{number.quantize(Decimal('0.01'))}%"


def _asset_class_label(asset_class: str) -> str:
    labels = {
        "stock_us": "미국 주식",
        "stock_kr": "한국 주식",
        "crypto": "암호화폐",
        "cash": "현금",
    }
    return labels.get(asset_class, asset_class)


def _portfolio_context_to_text(ctx: dict[str, Any]) -> str | None:
    if ctx.get("portfolio_context_unavailable"):
        return None

    client_context = ctx.get("client_context") if isinstance(ctx.get("client_context"), dict) else {}
    indicators = ctx.get("indicators") if isinstance(ctx.get("indicators"), dict) else {}
    holdings = ctx.get("holdings") if isinstance(ctx.get("holdings"), list) else []
    client_name = str(client_context.get("client_name") or "선택 고객")

    total_value = indicators.get("total_value")
    pnl_pct = indicators.get("pnl_pct")
    n_holdings = indicators.get("n_holdings")
    if total_value is None or pnl_pct is None:
        return None

    lines = [
        (
            f"{client_name}의 포트폴리오는 총 평가금액 {_format_krw(total_value)}, "
            f"총 손익률 {_format_pct(pnl_pct)}, 보유 종목 {n_holdings}개입니다."
        )
    ]

    breakdown = indicators.get("asset_class_breakdown")
    if isinstance(breakdown, dict) and breakdown:
        allocation = ", ".join(
            f"{_asset_class_label(str(asset_class))} {_format_weight_pct(weight)}"
            for asset_class, weight in breakdown.items()
        )
        lines.append(f"자산군 비중은 {allocation}입니다.")

    holding_summaries: list[str] = []
    for holding in holdings[:3]:
        if not isinstance(holding, dict):
            continue
        code = str(holding.get("code") or "").strip()
        value_krw = holding.get("value_krw")
        holding_pnl_pct = holding.get("pnl_pct")
        if code and value_krw is not None and holding_pnl_pct is not None:
            holding_summaries.append(
                f"{code}({_format_krw(value_krw)}, {_format_pct(holding_pnl_pct)})"
            )
    if holding_summaries:
        lines.append(f"주요 보유 종목은 {', '.join(holding_summaries)}입니다.")

    return " ".join(lines)


def _coerce_llm_answer_to_text(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith(("{", "[")):
        return _sanitize_debug_text(stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return _sanitize_debug_text(stripped)

    if isinstance(parsed, dict):
        for key in (
            "answer",
            "response",
            "narrative",
            "summary",
            "headline",
            "message",
            "analysis",
            "content",
            "body",
        ):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        lines: list[str] = []
        highlights = parsed.get("highlights")
        if isinstance(highlights, list):
            lines.extend(f"- {_format_value(item)}" for item in highlights[:5])
        if lines:
            return "\n".join(lines)

        for key, value in parsed.items():
            if key in {"type", "metrics", "signals", "evidence"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                lines.append(f"{key.replace('_', ' ')}: {_format_value(value)}")
        return "\n".join(lines).strip() or "분석 결과를 정리했습니다."

    if isinstance(parsed, list):
        return (
            "\n".join(f"- {_format_value(item)}" for item in parsed[:6])
            or "분석 결과를 정리했습니다."
        )

    return _format_value(parsed)


def _sanitize_debug_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.replace("sync fallback:", "", 1).strip()
    cleaned = cleaned.replace("(sync fallback)", "").strip()
    cleaned = cleaned.replace(
        "LLM 미설정 — OPENAI_API_KEY 를 설정해 주세요.", "AI 분석 설정이 아직 완료되지 않았습니다."
    )
    cleaned = cleaned.replace(
        "LLM 미설정 - OPENAI_API_KEY 를 설정해 주세요.", "AI 분석 설정이 아직 완료되지 않았습니다."
    )
    for prefix in (
        "포트폴리오 분석 결과:",
        "portfolio 분석 결과:",
        "stock 분석 결과:",
        "crypto 분석 결과:",
        "fx 분석 결과:",
        "macro 분석 결과:",
        "rebalance 분석 결과:",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned or "분석 결과를 정리했습니다."


def _fallback_text(agent: str, user_query: str) -> str:
    if agent == "portfolio":
        return (
            "현재 포트폴리오 리스크는 수익률보다 집중도와 변동성 노출을 먼저 봐야 합니다. "
            "지금 응답은 실시간 AI 분석 경로가 제한되어 확정 지표 기반의 간단 요약으로 제공됩니다. "
            "보유 종목 수, 상위 종목 비중, 통화 노출, 최근 손익률을 함께 확인한 뒤 리밸런싱 여부를 판단하세요."
        )
    if agent == "rebalance":
        return (
            "리밸런싱은 단일 종목과 자산군 비중이 과도하게 높아졌는지부터 확인하는 것이 좋습니다."
        )
    return f"{user_query or '요청한 내용'}에 대한 분석을 정리했습니다."


def _client_id_from_label(label: str) -> str | None:
    normalized = label.strip().upper()
    if len(normalized) != 1 or not ("A" <= normalized <= "Z"):
        return None
    return f"client-{ord(normalized) - ord('A') + 1:03d}"


def _normalize_client_reference(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None

    id_match = _CLIENT_ID_RE.fullmatch(candidate)
    if id_match is not None:
        return f"client-{id_match.group(1)}"

    numeric_match = _CLIENT_NUMERIC_RE.fullmatch(candidate)
    if numeric_match is not None:
        return f"client-{int(numeric_match.group(1)):03d}"

    label_id = _client_id_from_label(candidate)
    if label_id is not None:
        return label_id

    for pattern in (_CLIENT_LABEL_RE, _CLIENT_REVERSE_LABEL_RE):
        label_match = pattern.fullmatch(candidate)
        if label_match is not None:
            label_id = _client_id_from_label(label_match.group(1))
            if label_id is not None:
                return label_id

    return None


def _client_display_name(client_id: str) -> str:
    match = _CLIENT_ID_RE.fullmatch(client_id.strip())
    if match is None:
        return client_id
    index = int(match.group(1)) - 1
    if 0 <= index < 26:
        return f"고객 {chr(ord('A') + index)}"
    return client_id


def _resolve_requested_client(step: CopilotStep, user_query: str) -> tuple[str, bool]:
    input_client_id = step.inputs.get("client_id")
    if isinstance(input_client_id, str) and input_client_id.strip():
        normalized = _normalize_client_reference(input_client_id)
        return normalized or input_client_id.strip(), True

    id_match = _CLIENT_ID_RE.search(user_query)
    if id_match is not None:
        return f"client-{id_match.group(1)}", True

    numeric_match = _CLIENT_NUMERIC_RE.search(user_query)
    if numeric_match is not None:
        return f"client-{int(numeric_match.group(1)):03d}", True

    for pattern in (_CLIENT_LABEL_RE, _CLIENT_REVERSE_LABEL_RE):
        label_match = pattern.search(user_query)
        if label_match is not None:
            resolved = _client_id_from_label(label_match.group(1))
            if resolved is not None:
                return resolved, True

    return _DEFAULT_COPILOT_CLIENT_ID, False


def _client_reference_fragment(user_query: str) -> str | None:
    match = _CLIENT_REFERENCE_PREFIX_RE.search(user_query)
    if match is None:
        return None
    reference = match.group("reference").strip()
    if not _CLIENT_REFERENCE_MARKER_RE.search(reference) and not _CLIENT_PORTFOLIO_TERM_RE.search(
        user_query
    ):
        return None
    if reference.casefold() in _GENERIC_CLIENT_REFERENCES:
        return None
    return reference or None


def _build_client_portfolio_plan(query: str, *, session_id: str) -> CopilotPlan | None:
    reference = _client_reference_fragment(query)
    if not reference:
        return None
    return CopilotPlan(
        plan_id=f"client-portfolio-{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        created_at=datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        steps=[
            CopilotStep(
                step_id="client-portfolio",
                agent="portfolio",
                inputs={"client_id": reference},
                depends_on=[],
                gate_policy=GatePolicy.model_validate(
                    {"schema": True, "domain": True, "critique": True}
                ),
            )
        ],
    )


async def _resolve_client_for_copilot(
    step: CopilotStep,
    user_query: str,
) -> tuple[str, bool, str | None, Any | None]:
    from app.db.session import AsyncSessionLocal
    from app.services.clients import resolve_client_reference

    input_client_id = step.inputs.get("client_id")
    raw_input = input_client_id.strip() if isinstance(input_client_id, str) else ""
    reference = raw_input or _client_reference_fragment(user_query)
    if not reference:
        client_id, client_was_explicit = _resolve_requested_client(step, user_query)
        return client_id, client_was_explicit, None, None

    async with AsyncSessionLocal() as db:
        resolution = await resolve_client_reference(
            db,
            reference,
            user_ids=_PORTFOLIO_USER_IDS,
        )

    if resolution.status == "resolved" and resolution.client_id:
        return resolution.client_id, True, resolution.display_label, resolution
    return _DEFAULT_COPILOT_CLIENT_ID, True, None, resolution


def _client_candidate_payload(candidate: Any) -> dict[str, Any]:
    last_activity_at = getattr(candidate, "last_activity_at", None)
    last_activity = (
        last_activity_at.isoformat() if hasattr(last_activity_at, "isoformat") else None
    )
    client_id = str(getattr(candidate, "client_id", "") or "")
    label = getattr(candidate, "label", None)
    display_name = getattr(candidate, "display_name", None)
    display_label = (
        str(getattr(candidate, "display_label", "") or "").strip()
        or str(display_name or "").strip()
        or str(label or "").strip()
        or client_id
    )
    return {
        "user_id": str(getattr(candidate, "user_id", "") or ""),
        "client_id": client_id,
        "label": label,
        "display_name": display_name,
        "display_label": display_label,
        "match_type": str(getattr(candidate, "match_type", "") or ""),
        "matched_value": str(getattr(candidate, "matched_value", "") or ""),
        "holdings_count": int(getattr(candidate, "holdings_count", 0) or 0),
        "last_activity_at": last_activity,
    }


def _client_resolution_result(resolution: Any) -> dict[str, Any]:
    status = getattr(resolution, "status", "not_found")
    candidates = list(getattr(resolution, "candidates", ()) or ())
    candidate_payloads = [_client_candidate_payload(candidate) for candidate in candidates[:10]]
    if status == "ambiguous":
        lines = ["일치하는 고객이 여러 명입니다. 고객을 선택해 주세요."]
        for idx, candidate in enumerate(candidates[:5], start=1):
            last_activity = (
                candidate.last_activity_at.date().isoformat()
                if getattr(candidate, "last_activity_at", None)
                else "최근 활동 없음"
            )
            lines.append(
                f"{idx}. {candidate.display_label} ({candidate.client_id}) · "
                f"보유 {candidate.holdings_count}개 · {last_activity}"
            )
        content = "\n".join(lines)
    elif status == "mismatch":
        lines = ["입력한 고객 라벨과 이름이 서로 다른 고객을 가리킵니다. 고객을 다시 선택해 주세요."]
        for candidate in candidates[:5]:
            lines.append(f"- {candidate.display_label} ({candidate.client_id})")
        content = "\n".join(lines)
    else:
        content = "입력한 고객을 찾을 수 없습니다. 고객 ID, 고객 라벨, 또는 등록된 고객명을 확인해 주세요."

    return {
        "card": {
            "type": "text",
            "content": content,
            "degraded": True,
            "degraded_reason": str(status),
            "client_resolution_status": str(status),
            "client_resolution_reason": str(getattr(resolution, "reason", "") or ""),
            "requires_client_selection": status in {"ambiguous", "mismatch"},
            "client_candidates": candidate_payloads,
        },
        "gate_results": {"schema": "pass", "domain": "fail", "critique": "skip"},
    }


def _missing_portfolio_context_result(ctx: dict[str, Any]) -> dict[str, Any]:
    client_context = ctx.get("client_context") if isinstance(ctx.get("client_context"), dict) else {}
    client_id = str(client_context.get("client_id") or _DEFAULT_COPILOT_CLIENT_ID)
    client_name = str(client_context.get("client_name") or _client_display_name(client_id))
    content = (
        f"{client_name}({client_id})의 포트폴리오 원장 데이터가 없습니다. "
        "존재하지 않거나 아직 업로드되지 않은 고객에 대해 총 평가금액, 수익률, 자산 비중을 "
        "산출하지 않겠습니다. 고객 목록 또는 업로드 원장을 확인해 주세요."
    )
    return {
        "card": {
            "type": "text",
            "content": content,
            "degraded": True,
            "degraded_reason": "client_portfolio_not_found",
            "client_resolution_status": "no_portfolio_data",
            "client_resolution_reason": "client_resolved_but_portfolio_missing",
            "requires_client_selection": False,
            "client_id": client_id,
            "client_name": client_name,
        },
        "gate_results": {"schema": "pass", "domain": "fail", "critique": "skip"},
    }


_AGENT_PROMPT_MAP: dict[str, str] = {
    "stock": "stock_system",
    "crypto": "crypto_system",
    "fx": "fx_system",
    "macro": "macro_system",
    "portfolio": "portfolio_system",
    "rebalance": "rebalance_system",
    "mixed": "mixed_system",
}

if os.environ.get("COPILOT_ALL_AGENTS_LLM", "").lower() in ("1", "true", "yes"):
    _AGENT_PROMPT_MAP.update(
        {
            "comparison": "comparison_system",
            "simulator": "simulator_system",
            "news-rag": "news_rag_system",
        }
    )


def _run_step_sync(step: CopilotStep, user_query: str = "") -> dict[str, Any]:
    force_fail = os.environ.get("COPILOT_FORCE_FAIL_STEP", "")
    if force_fail and step.step_id == force_fail:
        return {
            "card": {
                "type": "text",
                "content": "요청한 분석 일부를 완료하지 못했습니다.",
                "degraded": True,
            },
            "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
            "forced_fail": True,
        }

    if step.agent == "comparison":
        from app.agents.analyzers.comparison import run as run_comparison

        return run_comparison(step)
    if step.agent == "simulator":
        from app.agents.analyzers.simulator import run as run_simulator

        return run_simulator(step)
    if step.agent == "news-rag":
        from app.agents.analyzers.news_rag import run as run_news_rag

        return run_news_rag(step)

    return {
        "card": {
            "type": "text",
            "content": _fallback_text(step.agent, user_query),
            "degraded": True,
        },
        "gate_results": {"schema": "pass", "domain": "pass", "critique": "skip"},
    }


async def _fetch_portfolio_context(
    *, client_id: str = _DEFAULT_COPILOT_CLIENT_ID, client_name: str | None = None
) -> dict[str, Any]:
    from sqlalchemy import select

    from app.db.models import Holding
    from app.db.session import AsyncSessionLocal
    from app.services.portfolio import compute_summary, get_period_snapshot, get_prev_snapshot

    async with AsyncSessionLocal() as db:
        holdings_rows = []
        user_id = _PORTFOLIO_USER_IDS[0]
        for candidate_user_id in _PORTFOLIO_USER_IDS:
            result = await db.execute(
                select(Holding).where(
                    Holding.user_id == candidate_user_id,
                    Holding.client_id == client_id,
                )
            )
            holdings_rows = list(result.scalars().all())
            if holdings_rows:
                user_id = candidate_user_id
                break

        if not holdings_rows:
            return {
                "portfolio_context_unavailable": True,
                "reason": "client_portfolio_not_found",
                "client_context": {
                    "client_id": client_id,
                    "client_name": client_name or _client_display_name(client_id),
                },
                "indicators": {},
                "holdings": [],
            }

        prev_snap = await get_prev_snapshot(db, user_id=user_id, client_id=client_id)
        period_snap = await get_period_snapshot(
            db, user_id=user_id, period_days=30, client_id=client_id
        )
        summary = await compute_summary(
            holdings_rows,
            prev_snapshot=prev_snap,
            period_snapshot=period_snap,
            period_days=30,
            user_id=user_id,
            client_id=client_id,
            client_name=client_name or _client_display_name(client_id),
        )

    return {
        "client_context": {
            "client_id": client_id,
            "client_name": client_name or _client_display_name(client_id),
        },
        "indicators": {
            "total_value": str(summary.total_value_krw),
            "pnl_pct": str(summary.total_pnl_pct),
            "daily_change_pct": str(summary.daily_change_pct),
            "period_change_pct": str(summary.period_change_pct),
            "n_holdings": summary.holdings_count,
            "asset_class_breakdown": {k: str(v) for k, v in summary.asset_class_breakdown.items()},
        },
        "holdings": [
            {
                "market": h.market,
                "code": h.code,
                "quantity": str(h.quantity),
                "avg_cost": str(h.avg_cost),
                "value_krw": str(h.value_krw),
                "pnl_pct": str(h.pnl_pct),
            }
            for h in summary.holdings
        ],
    }


async def _run_agent_llm(
    step: CopilotStep,
    user_query: str,
    active_context: ActiveContext | None = None,
) -> dict[str, Any]:
    from app.agents.llm import LLMUnavailableError, call_llm

    agent = step.agent
    prompt_name = _AGENT_PROMPT_MAP.get(agent)
    if prompt_name is None:
        return _run_step_sync(step, user_query)

    portfolio_text: str | None = None
    try:
        memory_context = (
            format_context_for_agent(active_context)
            if active_context is not None
            else "Conversation context: none."
        )
        if agent in {"portfolio", "rebalance"}:
            (
                client_id,
                client_was_explicit,
                resolved_client_name,
                client_resolution,
            ) = await _resolve_client_for_copilot(step, user_query)
            if client_resolution is not None and client_resolution.status != "resolved":
                return _client_resolution_result(client_resolution)
            try:
                ctx = await _fetch_portfolio_context(
                    client_id=client_id,
                    client_name=resolved_client_name,
                )
            except Exception as exc:  # noqa: BLE001
                ctx = {
                    "portfolio_context_unavailable": True,
                    "reason": type(exc).__name__,
                    "client_context": {
                        "client_id": client_id,
                        "client_name": resolved_client_name or _client_display_name(client_id),
                    },
                    "indicators": {},
                    "holdings": [],
                }
            if client_was_explicit and ctx.get("portfolio_context_unavailable"):
                return _missing_portfolio_context_result(ctx)
            if agent == "portfolio":
                portfolio_text = _portfolio_context_to_text(ctx)
            user_content = (
                f"{memory_context}\n\n"
                f"User question: {user_query}\n\n"
                f"Deterministic portfolio data:\n{json.dumps(ctx, ensure_ascii=False, indent=2)}"
            )
        else:
            user_content = (
                f"{memory_context}\n\n"
                f"User question: {user_query}\n"
                f"Step inputs:\n{json.dumps(dict(step.inputs), ensure_ascii=False, indent=2)}"
            )

        raw = await call_llm(
            system_prompt_name=prompt_name,
            user_content=user_content,
            temperature=0.3,
            max_tokens=2048,
            expect_json=agent in {"portfolio", "rebalance"},
        )
        cleaned = _coerce_llm_answer_to_text(_strip_code_fence(raw)) or _fallback_text(
            agent, user_query
        )
        critique_gate = "pass"
        if portfolio_text:
            cleaned = portfolio_text
            critique_gate = "skip"
        return {
            "card": {"type": "text", "content": cleaned, "degraded": False},
            "gate_results": {"schema": "pass", "domain": "pass", "critique": critique_gate},
        }
    except LLMUnavailableError:
        if portfolio_text:
            return {
                "card": {
                    "type": "text",
                    "content": portfolio_text,
                    "degraded": True,
                },
                "gate_results": {"schema": "pass", "domain": "pass", "critique": "skip"},
            }
        return {
            "card": {
                "type": "text",
                "content": _fallback_text(agent, user_query),
                "degraded": True,
            },
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "skip"},
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "card": {
                "type": "text",
                "content": f"{_fallback_text(agent, user_query)}",
                "degraded": True,
                "degraded_reason": str(exc)[:160],
            },
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "skip"},
        }


async def _execute_step(
    step: CopilotStep,
    delay_ms: int,
    queue: asyncio.Queue[bytes],
    user_query: str = "",
    active_context: ActiveContext | None = None,
) -> dict[str, Any]:
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    start_events: list[bytes] = [
        _sse({"type": "step.start", "step_id": step.step_id}),
        _sse({"type": "step.token", "step_id": step.step_id, "text": f"{step.agent} 분석 중..."}),
    ]

    if step.agent in _AGENT_PROMPT_MAP:
        outcome = await _run_agent_llm(step, user_query, active_context)
    else:
        loop = asyncio.get_event_loop()
        outcome = await loop.run_in_executor(None, _run_step_sync, step, user_query)

    card = outcome["card"]
    gate_results = outcome.get("gate_results", {})
    forced_fail = outcome.get("forced_fail", False)
    gate_events: list[bytes] = []
    gate_policy = step.gate_policy
    degraded = bool(card.get("degraded"))

    if forced_fail or gate_results.get("schema") == "fail":
        gate_events.append(
            _sse(
                {
                    "type": "step.gate",
                    "step_id": step.step_id,
                    "gate": "schema",
                    "status": "fail",
                    "reason": gate_results.get("schema", ""),
                }
            )
        )
        if forced_fail:
            gate_events.append(
                _sse(
                    {
                        "type": "error",
                        "step_id": step.step_id,
                        "code": "STEP_FORCED_FAILURE",
                        "message": "step execution was forced to fail",
                    }
                )
            )
        degraded = True
    else:
        if gate_policy.schema_check:
            schema_status, schema_reason = _schema_gate(card, step)
            gate_events.append(
                _sse(
                    {
                        "type": "step.gate",
                        "step_id": step.step_id,
                        "gate": "schema",
                        "status": schema_status,
                        "reason": schema_reason if schema_status == "fail" else None,
                    }
                )
            )
            degraded = degraded or schema_status == "fail"

        if not degraded and gate_policy.domain:
            domain_status, domain_reason = _domain_gate(card, step)
            gate_events.append(
                _sse(
                    {
                        "type": "step.gate",
                        "step_id": step.step_id,
                        "gate": "domain",
                        "status": domain_status,
                        "reason": domain_reason if domain_status == "fail" else None,
                    }
                )
            )
            degraded = degraded or domain_status == "fail"

        if not degraded and gate_policy.critique and gate_results.get("critique") != "skip":
            critique_status, critique_reason = await _critique_gate(card, step)
            gate_events.append(
                _sse(
                    {
                        "type": "step.gate",
                        "step_id": step.step_id,
                        "gate": "critique",
                        "status": critique_status,
                        "reason": critique_reason if critique_status == "fail" else None,
                    }
                )
            )
            degraded = degraded or critique_status == "fail"

    if degraded:
        card = {**card, "degraded": True}
    gate_events.append(_sse({"type": "step.result", "step_id": step.step_id, "card": card}))

    return {
        "step_id": step.step_id,
        "card": card,
        "degraded": degraded,
        "_start_events": start_events,
        "_gate_events": gate_events,
    }


def _topological_levels(steps: list[CopilotStep]) -> list[list[CopilotStep]]:
    step_map = {s.step_id: s for s in steps}
    in_degree: dict[str, int] = {s.step_id: 0 for s in steps}
    dependents: dict[str, list[str]] = defaultdict(list)

    for step in steps:
        for dep in step.depends_on:
            in_degree[step.step_id] += 1
            dependents[dep].append(step.step_id)

    levels: list[list[CopilotStep]] = []
    ready = [s for s in steps if in_degree[s.step_id] == 0]
    while ready:
        levels.append(ready)
        next_ready: list[CopilotStep] = []
        for step in ready:
            for child_id in dependents[step.step_id]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    next_ready.append(step_map[child_id])
        ready = next_ready
    return levels


def _card_to_final_text(card: dict[str, Any]) -> str:
    card_type = card.get("type", "text")
    if card_type == "text":
        return _sanitize_debug_text(str(card.get("content") or card.get("body") or ""))

    if card_type == "comparison_table":
        lines: list[str] = []
        summary = str(card.get("summary") or "").strip()
        if summary:
            lines.append(summary)
        rows_value = card.get("rows")
        rows = rows_value if isinstance(rows_value, list) else []
        for row_value in rows[:4]:
            if not isinstance(row_value, dict):
                continue
            row = cast("dict[str, Any]", row_value)
            symbol = row.get("symbol", "종목")
            metrics_value = row.get("metrics")
            metrics = (
                cast("dict[str, Any]", metrics_value) if isinstance(metrics_value, dict) else {}
            )
            metric_text = ", ".join(
                f"{name}: {_format_value(value)}" for name, value in list(metrics.items())[:4]
            )
            lines.append(f"- {symbol}: {metric_text}" if metric_text else f"- {symbol}")
        return "\n".join(lines) or "비교 분석 결과를 정리했습니다."

    if card_type == "simulator_result":
        lines = [
            f"시뮬레이션 기준 포트폴리오 가치는 {_format_value(card.get('base_value'))}에서 {_format_value(card.get('shocked_value'))}로 변합니다.",
            f"예상 수익률 변화는 {_format_value(card.get('twr_change_pct'))}%입니다.",
        ]
        scenarios_value = card.get("scenarios")
        scenarios = scenarios_value if isinstance(scenarios_value, list) else []
        for scenario_value in scenarios[:3]:
            if isinstance(scenario_value, dict):
                scenario = cast("dict[str, Any]", scenario_value)
                lines.append(
                    f"- {scenario.get('symbol', '종목')}: 변화율 {_format_value(scenario.get('delta_pct'))}%"
                )
        return "\n".join(lines)

    if card_type == "scorecard":
        rows_value = card.get("rows")
        rows = rows_value if isinstance(rows_value, list) else []
        lines = [str(card.get("title") or "주요 지표")]
        for row_value in rows[:5]:
            if isinstance(row_value, dict):
                row = cast("dict[str, Any]", row_value)
                lines.append(
                    f"- {row.get('label', '지표')}: {_format_value(row.get('value'))}{row.get('unit') or ''}"
                )
        return "\n".join(lines)

    if card_type == "chart":
        return f"{card.get('title') or '차트'} 흐름을 기준으로 분석했습니다."

    if card_type == "citation":
        title = str(card.get("title") or "인용 자료")
        excerpt = str(card.get("excerpt") or "").strip()
        return f"{title}\n{excerpt}" if excerpt else f"{title} 자료를 참고했습니다."

    return "분석 결과를 정리했습니다."


def _compose_local_final_text(step_results: dict[str, dict[str, Any]]) -> tuple[str, bool]:
    bodies: list[str] = []
    any_step_degraded = False
    for _sid, result in step_results.items():
        card = result.get("card", {})
        degraded = bool(result.get("degraded", False) or card.get("degraded", False))
        if degraded:
            any_step_degraded = True
        content = _card_to_final_text(card)
        if len(step_results) == 1:
            bodies.append(content)
        else:
            suffix = " (일부 제한)" if degraded else ""
            bodies.append(f"분석 결과{suffix}\n{content}")
    return "\n\n".join(bodies) or "분석 결과를 정리했습니다.", any_step_degraded


def _client_safety_metadata(step_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for result in step_results.values():
        card = result.get("card", {})
        if not isinstance(card, dict):
            continue
        status = card.get("client_resolution_status")
        if status not in _SAFETY_CLIENT_RESOLUTION_STATUSES:
            continue
        metadata: dict[str, Any] = {
            "degraded_reason": card.get("degraded_reason") or status,
            "client_resolution_status": status,
            "client_resolution_reason": card.get("client_resolution_reason"),
            "requires_client_selection": bool(card.get("requires_client_selection", False)),
        }
        for key in ("client_id", "client_name", "client_candidates"):
            if key in card:
                metadata[key] = card[key]
        return metadata
    return {}


def _build_synthesizer_payload(
    step_results: dict[str, dict[str, Any]],
    query: str,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for step_id, result in step_results.items():
        card = result.get("card", {})
        steps.append(
            {
                "step_id": step_id,
                "agent": result.get("agent"),
                "degraded": bool(result.get("degraded", False) or card.get("degraded", False)),
                "card": card,
                "gate_results": result.get("gate_results", {}),
            }
        )
    return {
        "user_query": query,
        "steps": steps,
        "instructions": {
            "language": "ko",
            "audience": "PB",
            "no_new_numbers": True,
            "degraded_if_any_step_degraded": True,
        },
    }


async def _run_final_synthesizer_llm(
    step_results: dict[str, dict[str, Any]],
    query: str,
) -> str:
    from app.agents.llm import LLMUnavailableError, call_llm

    payload = _build_synthesizer_payload(step_results, query)
    raw = await call_llm(
        system_prompt_name="copilot_synthesizer_system",
        user_content=json.dumps(payload, ensure_ascii=False, default=str),
        temperature=0.2,
        max_tokens=1200,
    )
    content = _coerce_llm_answer_to_text(_strip_code_fence(raw))
    if not content or content in {"{}", "[]"}:
        raise LLMUnavailableError("empty synthesizer output")
    return content


async def _run_final_gate(
    step_results: dict[str, dict[str, Any]],
    query: str,
    queue: asyncio.Queue[bytes],
) -> dict[str, Any]:
    """모든 step 결과를 합성해 최종 통합 카드를 만들고 step_id='final' 게이트를 실행한다.

    sprint-05: 세션 컨텍스트를 썼더라도 매번 전부 재실행 (캐시 금지).
    """
    local_content, any_step_degraded = _compose_local_final_text(step_results)
    safety_metadata = _client_safety_metadata(step_results)
    synthesizer_degraded = False
    if safety_metadata:
        final_content = local_content
    else:
        try:
            final_content = await _run_final_synthesizer_llm(step_results, query)
        except Exception:  # noqa: BLE001
            final_content = local_content
            synthesizer_degraded = True

    final_card: dict[str, Any] = {
        "type": "text",
        "content": final_content,
        "degraded": any_step_degraded or synthesizer_degraded,
    }
    if safety_metadata:
        final_card.update(safety_metadata)

    final_step = CopilotStep.model_construct(
        step_id="final",
        agent="portfolio",
        gate_policy=GatePolicy(schema_check=True, domain=True, critique=True),
        inputs={},
        depends_on=[],
    )

    schema_status, schema_reason = _schema_gate(final_card, final_step)
    await queue.put(
        _sse(
            {
                "type": "step.gate",
                "step_id": "final",
                "gate": "schema",
                "status": schema_status,
                "reason": schema_reason if schema_status == "fail" else None,
            }
        )
    )

    domain_status, domain_reason = _domain_gate(final_card, final_step)
    await queue.put(
        _sse(
            {
                "type": "step.gate",
                "step_id": "final",
                "gate": "domain",
                "status": domain_status,
                "reason": domain_reason if domain_status == "fail" else None,
            }
        )
    )

    if safety_metadata:
        critique_status, critique_reason = "pass", "deterministic_client_resolution"
    else:
        critique_status, critique_reason = await _critique_gate(
            final_card, final_step, is_final=True
        )
    await queue.put(
        _sse(
            {
                "type": "step.gate",
                "step_id": "final",
                "gate": "critique",
                "status": critique_status,
                "reason": critique_reason if critique_status == "fail" else None,
            }
        )
    )

    if schema_status == "fail" or domain_status == "fail" or critique_status == "fail":
        final_card = {**final_card, "degraded": True}
    return final_card


def _conversation_fallback_text(active_context: ActiveContext, query: str) -> str:
    last = active_context.prior_turns[-1] if active_context.prior_turns else None
    if last is None:
        return "이전 대화가 없어 새 분석이 필요합니다."
    summary = html.unescape(last.summary).strip()
    user_query = html.unescape(query).strip()
    return (
        f"이전 답변을 기준으로 정리하면 다음과 같습니다.\n\n"
        f"{summary}\n\n"
        f"요청하신 표현('{user_query}')에 맞춰 새 계산 없이 설명만 바꿨습니다."
    )


async def _build_conversation_card(query: str, active_context: ActiveContext) -> dict[str, Any]:
    from app.agents.llm import LLMUnavailableError, call_llm

    prompt = (
        f"{format_context_for_agent(active_context)}\n\n"
        f"Current user request: {query}\n\n"
        "Answer conversationally in Korean unless the user used English. "
        "Only re-explain, summarize, or rephrase verified prior summaries. "
        "Do not calculate new numbers, compare new symbols, cite fresh news, "
        "or imply buy/sell/rebalance recommendations."
    )
    try:
        raw = await call_llm(
            system_prompt_name="copilot_conversation_system",
            user_content=prompt,
            temperature=0.2,
            max_tokens=900,
        )
        content = _sanitize_debug_text(_strip_code_fence(raw))
        if not content or content in {"{}", "[]"}:
            content = _conversation_fallback_text(active_context, query)
        return {"type": "text", "content": content, "degraded": False}
    except LLMUnavailableError:
        return {
            "type": "text",
            "content": _conversation_fallback_text(active_context, query),
            "degraded": True,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "type": "text",
            "content": _conversation_fallback_text(active_context, query),
            "degraded": True,
            "degraded_reason": str(exc)[:160],
        }


async def _stream_conversation_shortcut(
    *,
    query: str,
    resolved_session_id: str,
    turn_id: str,
    active_context: ActiveContext,
    store: Any,
    reason: str,
) -> AsyncGenerator[bytes, None]:
    plan = CopilotPlan(
        plan_id=f"conversation-{turn_id}",
        session_id=resolved_session_id,
        created_at=datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        steps=[
            CopilotStep(
                step_id="chat-1",
                agent="portfolio",
                inputs={"mode": "conversation", "intent_reason": reason},
                depends_on=[],
                gate_policy=GatePolicy.model_validate(
                    {"schema": True, "domain": True, "critique": False}
                ),
            )
        ],
    )

    yield _sse({"type": "plan.ready", "plan": plan.model_dump()})
    yield _sse({"type": "step.start", "step_id": "chat-1"})
    yield _sse({"type": "step.token", "step_id": "chat-1", "text": "답변을 정리하고 있습니다..."})

    final_card = await _build_conversation_card(query, active_context)
    yield _sse({"type": "step.result", "step_id": "chat-1", "card": final_card})
    yield _sse({"type": "final.card", "card": final_card})

    new_turn = SessionTurn(
        turn_id=turn_id,
        query=query,
        plan_id=plan.plan_id,
        final_card=final_card,
        citations=[],
        active_context=active_context.model_dump(),
    )
    try:
        await store.append_turn(resolved_session_id, new_turn)
    except Exception:  # noqa: BLE001
        pass

    yield _sse({"type": "done", "session_id": resolved_session_id, "turn_id": turn_id})


async def stream_copilot_query(
    query: str,
    session_id: str | None = None,
    context: dict[str, Any] | None = None,
    harness_step_delay_ms: int = 0,
) -> AsyncGenerator[bytes, None]:
    resolved_session_id = session_id or str(uuid.uuid4())
    turn_id = make_turn_id()
    store = get_session_store()

    active_context: ActiveContext = await build_active_context(
        session_id=session_id,
        user_query=query,
        store=store,
    )
    context_str = format_context_for_planner(active_context)

    intent = classify_copilot_intent(query, active_context=active_context)
    if intent.route == "conversation":
        async for chunk in _stream_conversation_shortcut(
            query=query,
            resolved_session_id=resolved_session_id,
            turn_id=turn_id,
            active_context=active_context,
            store=store,
            reason=intent.reason,
        ):
            yield chunk
        return

    plan = _build_client_portfolio_plan(query, session_id=resolved_session_id)
    if plan is None:
        try:
            plan = await build_copilot_plan(query=context_str, session_id=resolved_session_id)
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "code": "PLANNER_ERROR", "message": str(exc)})
            yield _sse({"type": "done", "session_id": resolved_session_id, "turn_id": turn_id})
            return

    yield _sse({"type": "plan.ready", "plan": plan.model_dump()})

    step_results: dict[str, dict[str, Any]] = {}
    dummy_queue: asyncio.Queue[bytes] = asyncio.Queue()

    for level in _topological_levels(plan.steps):
        results = await asyncio.gather(
            *[
                _execute_step(step, harness_step_delay_ms, dummy_queue, query, active_context)
                for step in level
            ],
            return_exceptions=True,
        )
        sorted_pairs = sorted(zip(level, results), key=lambda pair: pair[0].step_id)

        for _step, result in sorted_pairs:
            if not isinstance(result, Exception):
                result_dict: dict[str, Any] = result  # type: ignore[assignment]
                for event in result_dict.get("_start_events", []):
                    yield event

        for step, result in sorted_pairs:
            if isinstance(result, Exception):
                yield _sse(
                    {
                        "type": "error",
                        "step_id": step.step_id,
                        "code": "STEP_EXECUTION_ERROR",
                        "message": str(result)[:200],
                    }
                )
                step_results[step.step_id] = {
                    "card": {
                        "type": "text",
                        "content": "분석 중 일부 오류가 발생했습니다.",
                        "degraded": True,
                    },
                    "degraded": True,
                }
            else:
                result_dict = result  # type: ignore[assignment]
                for event in result_dict.get("_gate_events", []):
                    yield event
                step_results[step.step_id] = {
                    key: value
                    for key, value in result_dict.items()
                    if key not in ("_start_events", "_gate_events")
                }

    final_queue: asyncio.Queue[bytes] = asyncio.Queue()
    final_card = await _run_final_gate(step_results, query, final_queue)
    while not final_queue.empty():
        yield await final_queue.get()

    yield _sse({"type": "final.card", "card": final_card})

    new_turn = SessionTurn(
        turn_id=turn_id,
        query=query,
        plan_id=plan.plan_id,
        final_card=final_card,
        citations=[],
        active_context=active_context.model_dump(),
    )
    try:
        await store.append_turn(resolved_session_id, new_turn)
    except Exception:  # noqa: BLE001
        pass

    yield _sse({"type": "done", "session_id": resolved_session_id, "turn_id": turn_id})
