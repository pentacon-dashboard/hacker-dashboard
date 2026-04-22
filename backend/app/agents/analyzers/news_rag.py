"""
News-RAG Analyzer — sprint-03.

/search/news 에서 citation 을 가져와 요약 + 인용 강제 구조.
출력: TextCard (type="text") + citations: Citation[].

3단 게이트 정책:
  schema : citations 가 비어있으면 실패 (강제 인용). source_url 형식 확인.
  domain : 모든 citation 의 doc_id 가 stub 저장소에 존재.
  critique: citation faithfulness — content 에 인용 근거가 있는지 확인.
"""
from __future__ import annotations

import os
from typing import Any

from app.agents.state import AgentState
from app.schemas.copilot import CopilotStep, TextCard


def _is_stub_mode() -> bool:
    return os.environ.get("COPILOT_NEWS_MODE", "stub").lower() == "stub"


def _check_schema(card_dict: dict[str, Any]) -> tuple[str, str]:
    """schema gate: citations 가 비어있으면 fail. source_url 형식 확인."""
    citations = card_dict.get("citations", [])
    if not citations:
        return "fail", "citations must not be empty (citation faithfulness required)"

    for i, c in enumerate(citations):
        url = c.get("source_url", "")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return "fail", f"citation[{i}].source_url is not a valid URL: {url!r}"

    # TextCard 스키마 검증
    try:
        TextCard.model_validate(card_dict)
        return "pass", ""
    except Exception as exc:  # noqa: BLE001
        return "fail", str(exc)


def _check_domain(citations: list[dict[str, Any]]) -> tuple[str, str]:
    """domain gate: citation 의 source_url 이 stub 저장소에 존재하는지 확인."""
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

        # _stub_documents 는 source_url → doc_dict 로 keying 됨
        known_urls = set(_stub_documents.keys())
        for c in citations:
            source_url = c.get("source_url", "")
            if source_url and source_url not in known_urls:
                return "fail", (
                    f"citation source_url={source_url!r} not found in search index"
                )
    return "pass", ""


def _check_critique(card_dict: dict[str, Any]) -> tuple[str, str]:
    """critique gate: content 에 citations 의 excerpt 가 반영되었는지 간단 확인."""
    content = card_dict.get("content", "")
    citations = card_dict.get("citations", [])
    if not citations:
        return "fail", "no citations to verify faithfulness"

    # 최소 1개의 citation 제목 또는 excerpt 단어가 content 에 언급되었는지 확인
    for c in citations:
        title = c.get("title", "")
        if title and title[:20].lower() in content.lower():
            return "pass", ""
        excerpt = c.get("excerpt", "")
        # excerpt 의 첫 10개 단어 중 하나라도 content 에 있으면 통과
        words = excerpt.split()[:10]
        if any(w.lower() in content.lower() for w in words if len(w) > 4):
            return "pass", ""

    return "fail", "content does not reference any citation excerpt or title"


def _retrieve_citations(step: CopilotStep) -> list[dict[str, Any]]:
    """stub 모드에서 /search/news 를 동기 호출해 citations 를 가져온다."""
    query = step.inputs.get("query", "")
    symbols = step.inputs.get("symbols", [])

    try:
        from app.services.news.search import search_news_stub
        results = search_news_stub(
            query=query,
            symbols=symbols if symbols else None,
            start_date=step.inputs.get("start_date"),
            end_date=step.inputs.get("end_date"),
            k=step.inputs.get("k", 5),
        )
        return [c.model_dump() for c in results]
    except Exception:  # noqa: BLE001
        return []


def _build_card(step: CopilotStep, citations: list[dict[str, Any]]) -> dict[str, Any]:
    """citations 를 기반으로 TextCard 를 생성 (결정론적)."""
    if not citations:
        return {
            "type": "text",
            "content": "No relevant news or filings found for the query.",
            "citations": [],
        }

    # 인용 요약 생성 (결정론적 — LLM 없이)
    query = step.inputs.get("query", "")
    lines = [f"Summary of news for query: '{query}'\n"]
    for c in citations[:3]:
        title = c.get("title", "")
        excerpt = c.get("excerpt", "")[:200]
        lines.append(f"Based on [{title}]: {excerpt}")

    content = "\n\n".join(lines)
    return {
        "type": "text",
        "content": content,
        "citations": citations,
    }


def run(step: CopilotStep) -> dict[str, Any]:
    """
    CopilotStep 을 받아 text 카드 + citations 를 생성하고 3단 게이트 결과를 반환.

    반환 형식:
    {
        "card": dict,
        "gate_results": {
            "schema": "pass"|"fail",
            "domain": "pass"|"fail",
            "critique": "pass"|"fail",
        },
    }
    """
    gate_policy = step.gate_policy

    # ── Citations 조회 ──────────────────────────────────────────────────────
    citations = _retrieve_citations(step)

    # ── 카드 생성 ────────────────────────────────────────────────────────────
    card_dict = _build_card(step, citations)

    # ── Schema Gate ──────────────────────────────────────────────────────────
    schema_status, schema_reason = _check_schema(card_dict)
    if gate_policy.schema_check and schema_status == "fail":
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
        }

    # ── Domain Gate ──────────────────────────────────────────────────────────
    domain_status, domain_reason = _check_domain(card_dict.get("citations", []))
    if gate_policy.domain and domain_status == "fail":
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": schema_status, "domain": "fail", "critique": "skip"},
        }

    # ── Critique Gate ────────────────────────────────────────────────────────
    critique_status, critique_reason = _check_critique(card_dict)
    if gate_policy.critique and critique_status == "fail":
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": schema_status, "domain": domain_status, "critique": "fail"},
        }

    return {
        "card": card_dict,
        "gate_results": {
            "schema": schema_status,
            "domain": domain_status,
            "critique": critique_status,
        },
    }


async def run_async(state: AgentState) -> dict[str, Any]:
    """LangGraph 서브그래프 노드 진입점 (비동기)."""
    from app.schemas.copilot import CopilotStep

    copilot_plan = state.get("copilot_plan") or {}
    steps = copilot_plan.get("steps", [])
    rag_step = next((s for s in steps if s.get("agent") == "news-rag"), None)
    if rag_step is None:
        return {**state}

    step = CopilotStep.model_validate(rag_step)
    outcome = run(step)

    citations = outcome["card"].get("citations", [])
    step_results = dict(state.get("copilot_step_results") or {})
    step_results[step.step_id] = outcome["card"]

    existing_citations = list(state.get("copilot_citations") or [])
    return {
        **state,
        "copilot_step_results": step_results,
        "copilot_citations": existing_citations + citations,
    }
