"""News RAG analyzer for Copilot.

Live news retrieval must go through app.services.news.search.search_news so
configured Naver API credentials are used first. Fixture search remains only as
the service-level fallback when live credentials or upstream responses are not
available.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from app.agents.state import AgentState
from app.schemas.copilot import CopilotStep, TextCard


def _is_stub_mode() -> bool:
    return os.environ.get("COPILOT_NEWS_MODE", "stub").lower() == "stub"


def _coerce_symbols(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        values = [part.strip() for part in raw.split(",")]
        return [value for value in values if value] or None
    if isinstance(raw, list):
        values = [str(item).strip() for item in raw]
        return [value for value in values if value] or None
    return None


def _coerce_k(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 5
    return min(max(value, 1), 50)


def _step_query(step: CopilotStep) -> str:
    query = str(step.inputs.get("query") or "").strip()
    if query:
        return query
    symbols = _coerce_symbols(step.inputs.get("symbols")) or []
    if symbols:
        return " OR ".join(symbols)
    return "market news"


def _check_schema(card_dict: dict[str, Any]) -> tuple[str, str]:
    citations = card_dict.get("citations", [])
    if not citations:
        return "fail", "citations must not be empty (citation faithfulness required)"

    for i, citation in enumerate(citations):
        url = citation.get("source_url", "")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return "fail", f"citation[{i}].source_url is not a valid URL: {url!r}"

    try:
        TextCard.model_validate(card_dict)
        return "pass", ""
    except Exception as exc:  # noqa: BLE001
        return "fail", str(exc)


def _check_domain(citations: list[dict[str, Any]]) -> tuple[str, str]:
    from app.services.news.naver import is_naver_configured

    if is_naver_configured():
        return "pass", ""

    if _is_stub_mode():
        try:
            from app.services.news.ingest import _stub_documents, load_fixture_corpus
        except ImportError:
            return "pass", ""

        if not _stub_documents:
            try:
                load_fixture_corpus()
            except Exception:  # noqa: BLE001
                return "pass", ""

        known_urls = set(_stub_documents.keys())
        for citation in citations:
            source_url = citation.get("source_url", "")
            if source_url and source_url not in known_urls:
                return "fail", f"citation source_url={source_url!r} not found in search index"

    return "pass", ""


def _check_critique(card_dict: dict[str, Any]) -> tuple[str, str]:
    content = card_dict.get("content", "")
    citations = card_dict.get("citations", [])
    if not citations:
        return "fail", "no citations to verify faithfulness"

    for citation in citations:
        title = str(citation.get("title", ""))
        if title and title[:20].lower() in content.lower():
            return "pass", ""
        excerpt = str(citation.get("excerpt", ""))
        words = excerpt.split()[:10]
        if any(word.lower() in content.lower() for word in words if len(word) > 4):
            return "pass", ""

    return "fail", "content does not reference any citation excerpt or title"


async def _retrieve_citations_async(step: CopilotStep) -> list[dict[str, Any]]:
    from app.services.news.search import search_news

    results = await search_news(
        query=_step_query(step),
        symbols=_coerce_symbols(step.inputs.get("symbols")),
        start_date=step.inputs.get("start_date"),
        end_date=step.inputs.get("end_date"),
        k=_coerce_k(step.inputs.get("k", 5)),
    )
    return [citation.model_dump() for citation in results]


def _retrieve_citations(step: CopilotStep) -> list[dict[str, Any]]:
    try:
        return asyncio.run(_retrieve_citations_async(step))
    except RuntimeError:
        from app.services.news.search import search_news_stub

        results = search_news_stub(
            query=_step_query(step),
            symbols=_coerce_symbols(step.inputs.get("symbols")),
            start_date=step.inputs.get("start_date"),
            end_date=step.inputs.get("end_date"),
            k=_coerce_k(step.inputs.get("k", 5)),
        )
        return [citation.model_dump() for citation in results]
    except Exception:  # noqa: BLE001
        return []


def _build_card(step: CopilotStep, citations: list[dict[str, Any]]) -> dict[str, Any]:
    if not citations:
        return {
            "type": "text",
            "content": "관련 뉴스 또는 공시를 찾지 못했습니다.",
            "citations": [],
        }

    query = _step_query(step)
    lines = [f"'{query}' 관련 뉴스 요약입니다."]
    for citation in citations[:3]:
        title = str(citation.get("title", "")).strip()
        excerpt = str(citation.get("excerpt", "")).strip()[:220]
        lines.append(f"[{title}] 기준으로 보면 {excerpt}")

    return {
        "type": "text",
        "content": "\n\n".join(lines),
        "citations": citations,
    }


def _evaluate(step: CopilotStep, citations: list[dict[str, Any]]) -> dict[str, Any]:
    gate_policy = step.gate_policy
    card_dict = _build_card(step, citations)

    schema_status, schema_reason = _check_schema(card_dict)
    if gate_policy.schema_check and schema_status == "fail":
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
            "gate_reasons": {"schema": schema_reason},
        }

    domain_status, domain_reason = _check_domain(card_dict.get("citations", []))
    if gate_policy.domain and domain_status == "fail":
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": schema_status, "domain": "fail", "critique": "skip"},
            "gate_reasons": {"domain": domain_reason},
        }

    critique_status, critique_reason = _check_critique(card_dict)
    if gate_policy.critique and critique_status == "fail":
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {
                "schema": schema_status,
                "domain": domain_status,
                "critique": "fail",
            },
            "gate_reasons": {"critique": critique_reason},
        }

    return {
        "card": card_dict,
        "gate_results": {
            "schema": schema_status,
            "domain": domain_status,
            "critique": critique_status,
        },
    }


def run(step: CopilotStep) -> dict[str, Any]:
    return _evaluate(step, _retrieve_citations(step))


async def run_async(state: AgentState) -> dict[str, Any]:
    rag_step = next(
        (s for s in (state.get("copilot_plan") or {}).get("steps", []) if s.get("agent") == "news-rag"),
        None,
    )
    if rag_step is None:
        return {**state}

    step = CopilotStep.model_validate(rag_step)
    outcome = _evaluate(step, await _retrieve_citations_async(step))

    citations = outcome["card"].get("citations", [])
    step_results = dict(state.get("copilot_step_results") or {})
    step_results[step.step_id] = outcome["card"]

    existing_citations = list(state.get("copilot_citations") or [])
    return {
        **state,
        "copilot_step_results": step_results,
        "copilot_citations": existing_citations + citations,
    }
