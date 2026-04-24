"""리밸런싱 LLM 해석 Analyzer.

Track A의 계산 결과(actions, drift, allocations)를 입력받아 자연어 해석을 생성한다.
결정적 계산(수학)은 services/rebalance.py에서 수행됨 — 여기선 해석만.

3단 게이트 적용:
  - schema_gate: LLMAnalysis Pydantic 파싱
  - domain_gate: headline/narrative 길이·금지어·자명 무결성
  - critique_gate: narrative 가 actions 에 없는 종목을 언급하는지 자체 검증

이 Analyzer 는 일반 `BaseAnalyzer` 그래프 흐름이 아니라 /portfolio/rebalance 엔드포인트에서
직접 호출되므로, 게이트를 Analyzer 내부에서 같이 실행한다.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.llm import (
    LLMUnavailableError,
    call_llm,
    extract_json,
    select_model,
)
from app.schemas.rebalance import (
    LLMAnalysis,
    RebalanceAction,
    RebalanceConstraints,
    TargetAllocation,
)

logger = logging.getLogger(__name__)

# narrative 최소 길이 — 2문장 이상 서술을 강제하기 위한 휴리스틱
_NARRATIVE_MIN_CHARS = 20
_NARRATIVE_MAX_CHARS = 1000
_HEADLINE_MAX_CHARS = 120  # 60자 가이드 + 여유

# 금지어 (LLM 이 무단 투자권유 표현을 못 쓰도록)
_FORBIDDEN_TERMS: tuple[str, ...] = (
    "보장",
    "무조건",
    "확실히 오른다",
    "반드시 오른다",
    "투자 조언",
    "투자조언",
)

# critique 에서 unknown token 판정 시 제외할 일반 약어
_KNOWN_TOKENS: frozenset[str] = frozenset(
    {
        "LLM",
        "API",
        "KRW",
        "USD",
        "JPY",
        "EUR",
        "ETF",
        "HHI",
        "MDD",
        "AI",
        "US",
        "KR",
        "FX",
    }
)

# 대문자 토큰 추출 (예: AAPL, BTC, KRW-BTC, TSLA). 2~6글자 기본 + 하이픈 조합.
_TOKEN_RE = re.compile(r"\b[A-Z]{2,6}(?:-[A-Z]{2,6})?\b")


class RebalanceAnalyzer:
    """리밸런싱 자연어 해석 전용 Analyzer.

    일반 BaseAnalyzer 와 달리 graph node 가 아니라 REST 엔드포인트에서 직접 await 된다.
    """

    prompt_name = "rebalance_system"

    async def analyze(
        self,
        *,
        actions: list[RebalanceAction],
        drift: dict[str, float],
        current_allocation: dict[str, float],
        target_allocation: dict[str, float] | TargetAllocation,
        constraints: RebalanceConstraints,
    ) -> tuple[LLMAnalysis | None, dict[str, str]]:
        """LLM 해석 + 3단 게이트 실행.

        Returns:
            (analysis_or_None, gates_dict). analysis 가 None 이면 schema_gate fail.
            gates 의 각 값은 "pass" | "pending" | "fail: <reason>" | "warn: <reason>".
        """
        gates: dict[str, str] = {
            "schema_gate": "pending",
            "domain_gate": "pending",
            "critique_gate": "pending",
        }

        # ── 지름길: actions 가 비어있으면 LLM 호출 없이 결정적 응답 ─────────────
        if not actions:
            return self._empty_actions_shortcut(drift), {
                "schema_gate": "pass",
                "domain_gate": "pass",
                "critique_gate": "pass",
            }

        # ── LLM 호출 ──────────────────────────────────────────────────────────
        payload = self._build_payload(
            actions=actions,
            drift=drift,
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            constraints=constraints,
        )
        user_content = json.dumps(payload, ensure_ascii=False, default=str)

        try:
            raw = await call_llm(
                system_prompt_name=self.prompt_name,
                user_content=user_content,
                model=select_model(len(actions)),
                max_tokens=2048,
                temperature=0.2,
            )
        except LLMUnavailableError as exc:
            # 키 미설정/DI 미주입 — 엔드포인트가 llm_analysis=None 로 degraded 처리하도록.
            logger.warning("rebalance LLM unavailable: %s", exc)
            gates["schema_gate"] = f"fail: llm_unavailable: {exc}"
            return None, gates

        # ── Schema gate ───────────────────────────────────────────────────────
        try:
            parsed = extract_json(raw)
            analysis = LLMAnalysis.model_validate(parsed)
            gates["schema_gate"] = "pass"
        except Exception as exc:  # ValueError from extract_json OR pydantic ValidationError
            logger.warning("rebalance schema gate fail: %s; raw=%r", exc, raw[:200])
            gates["schema_gate"] = f"fail: {exc}"
            return None, gates

        # ── Domain gate ───────────────────────────────────────────────────────
        domain_result = _domain_check(analysis)
        gates["domain_gate"] = domain_result
        if domain_result.startswith("fail"):
            return analysis, gates

        # ── Critique gate (self-check, no extra LLM call) ─────────────────────
        critique_result = _critique_check(analysis, actions)
        gates["critique_gate"] = critique_result

        return analysis, gates

    # ──────────────────────── helpers ────────────────────────

    def _empty_actions_shortcut(self, drift: dict[str, float]) -> LLMAnalysis:
        """actions=[] 인 경우 LLM 호출 없이 결정적으로 응답 생성."""
        max_abs_drift = max((abs(d) for d in drift.values()), default=0.0)
        if max_abs_drift < 0.01:
            return LLMAnalysis(
                headline="포트폴리오가 이미 목표 비중에 도달했습니다",
                narrative=(
                    "현재 자산군 비중이 목표와 거의 일치합니다 "
                    f"(최대 drift {max_abs_drift*100:.2f}% < 1%). 리밸런싱이 불필요합니다."
                ),
                warnings=[],
                confidence=0.95,
            )
        return LLMAnalysis(
            headline="리밸런싱 제안 없음 — 제약 조건 검토 필요",
            narrative=(
                "자산군 drift 는 존재하지만 min_trade_krw 또는 max_single_weight 제약, "
                "혹은 해당 자산군 holdings 부재로 실행 가능한 액션이 없습니다. "
                "제약을 완화하거나 수동 조정을 고려하세요."
            ),
            warnings=["제약 조건 재검토 권장"],
            confidence=0.75,
        )

    def _build_payload(
        self,
        *,
        actions: list[RebalanceAction],
        drift: dict[str, float],
        current_allocation: dict[str, float],
        target_allocation: dict[str, float] | TargetAllocation,
        constraints: RebalanceConstraints,
    ) -> dict[str, Any]:
        """LLM 에 보낼 user_content payload 를 조립 (직렬화는 caller 가 담당)."""
        target_dict: dict[str, float]
        if isinstance(target_allocation, TargetAllocation):
            target_dict = target_allocation.model_dump()
        else:
            target_dict = dict(target_allocation)

        return {
            "actions": [a.model_dump(mode="json") for a in actions],
            "drift": drift,
            "current_allocation": current_allocation,
            "target_allocation": target_dict,
            "constraints": constraints.model_dump(mode="json"),
        }


# ──────────────────────── domain / critique helpers ────────────────────────


def _domain_check(analysis: LLMAnalysis) -> str:
    """narrative 길이·금지어·confidence 범위 sanity."""
    if not analysis.headline.strip():
        return "fail: headline empty"
    if len(analysis.headline) > _HEADLINE_MAX_CHARS:
        return f"fail: headline too long ({len(analysis.headline)} chars)"
    if len(analysis.narrative) < _NARRATIVE_MIN_CHARS:
        return f"fail: narrative too short ({len(analysis.narrative)} chars)"
    if len(analysis.narrative) > _NARRATIVE_MAX_CHARS:
        return f"fail: narrative too long ({len(analysis.narrative)} chars)"

    combined = f"{analysis.headline} {analysis.narrative} {' '.join(analysis.warnings)}"
    for term in _FORBIDDEN_TERMS:
        if term in combined:
            return f"fail: forbidden term '{term}'"

    if not (0.0 <= analysis.confidence <= 1.0):
        return f"fail: confidence out of range: {analysis.confidence}"

    return "pass"


def _critique_check(
    analysis: LLMAnalysis,
    actions: list[RebalanceAction],
) -> str:
    """narrative/warnings 에 actions 에 없는 종목 코드가 등장하는지 체크."""
    mentioned_codes = {a.code for a in actions}
    asset_classes = {a.asset_class for a in actions}

    text = f"{analysis.headline}\n{analysis.narrative}\n" + "\n".join(analysis.warnings)
    tokens = set(_TOKEN_RE.findall(text))

    unknown: set[str] = set()
    for tok in tokens:
        if tok in _KNOWN_TOKENS:
            continue
        if tok in mentioned_codes:
            continue
        # "KRW-BTC" 가 mention 되어 있고 "BTC" 가 narrative 에 쓰인 경우는 허용
        if any(tok in code or code in tok for code in mentioned_codes):
            continue
        # asset_class 매치 (대문자 전환) — "CRYPTO" 등
        if tok.lower() in {ac.lower() for ac in asset_classes}:
            continue
        unknown.add(tok)

    if unknown:
        # fail 로 격상하지 않고 warn — 운영상 허용 범위로 두되 관찰 가능하게 노출.
        return f"warn: unknown codes mentioned: {sorted(unknown)}"
    return "pass"
