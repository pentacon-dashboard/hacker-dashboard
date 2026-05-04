"""Deterministic Copilot intent routing for conversation shortcuts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas.copilot import ActiveContext

CopilotIntentRoute = Literal["conversation", "analysis"]


@dataclass(frozen=True)
class CopilotIntentDecision:
    route: CopilotIntentRoute
    reason: str


_EXPLANATION_KEYWORDS = (
    "방금",
    "아까",
    "위 내용",
    "이전",
    "그 말",
    "그 내용",
    "쉽게",
    "요약",
    "정리",
    "고객용",
    "한 문장",
    "다시 설명",
    "무슨 뜻",
    "explain",
    "summarize",
    "rephrase",
)

_NEW_ANALYSIS_KEYWORDS = (
    "계산",
    "다시 계산",
    "비교",
    "뉴스",
    "근거",
    "현재",
    "오늘",
    "최근",
    "공시",
    "방금 시세",
    "최신",
    "조회",
    "시뮬레이션",
    "what if",
    "compare",
    "news",
    "citation",
    "current",
    "today",
    "latest",
)

_INVESTMENT_JUDGEMENT_KEYWORDS = (
    "리밸런싱",
    "리밸런스",
    "매수",
    "매도",
    "사야",
    "팔아",
    "해야",
    "필요",
    "괜찮아",
    "추천",
    "target",
    "buy",
    "sell",
    "should",
    "recommend",
)

_CORRECTION_OR_EXISTENCE_KEYWORDS = (
    "없는데",
    "없어",
    "없습니다",
    "없는 고객",
    "존재하지",
    "아닌데",
    "틀렸",
    "잘못",
    "오류",
    "not exist",
    "doesn't exist",
    "does not exist",
    "wrong",
    "incorrect",
)

_TICKER_OR_NUMERIC_RE = re.compile(
    r"(\b[A-Z]{2,5}\b|\b\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?\s?(?:주|원|달러|krw|usd)\b)",
    re.IGNORECASE,
)
_CLIENT_OR_PORTFOLIO_ANALYSIS_RE = re.compile(
    r"("
    r"\bclient-\d{3}\b|"
    r"\bclient\s*[-_ ]?\s*[a-z0-9]+\b|"
    r"\bcustomer\s*[-_ ]?\s*[a-z0-9]+\b|"
    r"\uace0\uac1d\s*[-_:]?\s*[a-z0-9]+|"
    r"\ud3ec\ud2b8\ud3f4\ub9ac\uc624|"
    r"portfolio|"
    r"\ub9ac\ubc38\ub7f0\uc2f1|"
    r"rebalance"
    r")",
    re.IGNORECASE,
)


def classify_copilot_intent(
    query: str,
    *,
    active_context: ActiveContext,
) -> CopilotIntentDecision:
    """Choose whether a query can use the chat shortcut.

    The shortcut is conservative: it only opens for explanatory follow-ups with
    prior context. Anything involving fresh data, numbers, tickers, or
    investment judgement is sent through the full analyzer path.
    """
    normalized = " ".join(query.strip().split())
    lowered = normalized.lower()

    if not active_context.prior_turns:
        return CopilotIntentDecision(route="analysis", reason="no_prior_context")

    if any(keyword in lowered for keyword in _CORRECTION_OR_EXISTENCE_KEYWORDS):
        return CopilotIntentDecision(route="analysis", reason="correction_or_missing_context")

    if _CLIENT_OR_PORTFOLIO_ANALYSIS_RE.search(normalized):
        return CopilotIntentDecision(route="analysis", reason="client_or_portfolio_reference")

    if any(keyword in lowered for keyword in _INVESTMENT_JUDGEMENT_KEYWORDS):
        return CopilotIntentDecision(route="analysis", reason="investment_judgement_keyword")

    if any(keyword in lowered for keyword in _NEW_ANALYSIS_KEYWORDS):
        return CopilotIntentDecision(route="analysis", reason="new_analysis_keyword")

    if _TICKER_OR_NUMERIC_RE.search(normalized):
        return CopilotIntentDecision(route="analysis", reason="ticker_or_numeric_input")

    if any(keyword in lowered for keyword in _EXPLANATION_KEYWORDS):
        return CopilotIntentDecision(route="conversation", reason="explanatory_follow_up")

    return CopilotIntentDecision(route="analysis", reason="default_analysis")
