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
from decimal import Decimal
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
_ENGLISH_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z_-]*\b")
_KOREAN_RE = re.compile(r"[가-힣]")

_ASSET_CLASS_LABELS: dict[str, str] = {
    "stock_kr": "한국 주식",
    "stock_us": "미국 주식",
    "crypto": "암호화폐",
    "cash": "현금",
    "fx": "외화",
    "other": "기타 자산",
}

_ACTION_LABELS: dict[str, str] = {
    "buy": "매수",
    "sell": "매도",
}

_TEXT_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmax_single_weight\b", re.IGNORECASE), "단일 종목 최대 비중"),
    (re.compile(r"\bmin_trade_krw\b", re.IGNORECASE), "최소 거래액"),
    (re.compile(r"\ballow_fractional\b", re.IGNORECASE), "소수점 수량 허용"),
    (re.compile(r"\btarget[_ ]allocation\b", re.IGNORECASE), "목표 비중"),
    (re.compile(r"\bcurrent[_ ]allocation\b", re.IGNORECASE), "현재 비중"),
    (re.compile(r"\bstock_kr\b", re.IGNORECASE), "한국 주식"),
    (re.compile(r"\bstock_us\b", re.IGNORECASE), "미국 주식"),
    (re.compile(r"\bcrypto\b", re.IGNORECASE), "암호화폐"),
    (re.compile(r"\bcash\b", re.IGNORECASE), "현금"),
    (re.compile(r"\bfx\b", re.IGNORECASE), "외화"),
    (re.compile(r"\bdrift\b", re.IGNORECASE), "괴리"),
    (re.compile(r"\bholdings?\b", re.IGNORECASE), "보유 종목"),
    (re.compile(r"\brebalanc(?:e|ing)\b", re.IGNORECASE), "리밸런싱"),
    (re.compile(r"\ballocation\b", re.IGNORECASE), "비중"),
    (re.compile(r"\bportfolio\b", re.IGNORECASE), "포트폴리오"),
    (re.compile(r"\bconstraints?\b", re.IGNORECASE), "제약"),
    (re.compile(r"\btarget\b", re.IGNORECASE), "목표"),
    (re.compile(r"\bcurrent\b", re.IGNORECASE), "현재"),
    (re.compile(r"\btrades?\b", re.IGNORECASE), "거래"),
    (re.compile(r"\bbuy\b", re.IGNORECASE), "매수"),
    (re.compile(r"\bsell\b", re.IGNORECASE), "매도"),
    (re.compile(r"\brisk\b", re.IGNORECASE), "위험"),
    (re.compile(r"\bupbit\b", re.IGNORECASE), "업비트"),
    (re.compile(r"\byahoo\b", re.IGNORECASE), "야후"),
    (re.compile(r"\bnaver_kr\b", re.IGNORECASE), "네이버 국내"),
    (re.compile(r"\bbinance\b", re.IGNORECASE), "바이낸스"),
    (re.compile(r"\bkrx\b", re.IGNORECASE), "한국거래소"),
    (re.compile(r"\bnasdaq\b", re.IGNORECASE), "나스닥"),
    (re.compile(r"\bnyse\b", re.IGNORECASE), "뉴욕거래소"),
)


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
            analysis = _localize_analysis_language(analysis)
            gates["schema_gate"] = "pass"
        except Exception as exc:  # ValueError from extract_json OR pydantic ValidationError
            logger.warning("rebalance schema gate fail: %s; raw=%r", exc, raw[:200])
            gates["schema_gate"] = f"fail: {exc}"
            return None, gates

        # ── Korean language guard ─────────────────────────────────────────────
        # 프롬프트가 한국어를 요구해도 모델이 일부 영어 도메인 용어를 남길 수 있으므로,
        # UI 로 보내기 전 한국어화하고 그래도 영어 산문이 남으면 결정적 한국어 해석으로 대체한다.
        language_result = _language_check(analysis, actions)
        if language_result.startswith("fail"):
            logger.info("rebalance language guard fallback: %s", language_result)
            fallback = self._korean_fallback_analysis(
                actions=actions,
                drift=drift,
                current_allocation=current_allocation,
                target_allocation=target_allocation,
                constraints=constraints,
                source_confidence=analysis.confidence,
            )
            gates["domain_gate"] = f"warn: korean_fallback: {language_result}"
            gates["critique_gate"] = "pass"
            return fallback, gates

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
                    f"(최대 괴리 {max_abs_drift * 100:.2f}% < 1%). 리밸런싱이 불필요합니다."
                ),
                warnings=[],
                confidence=0.95,
            )
        return LLMAnalysis(
            headline="리밸런싱 제안 없음: 제약 조건 검토 필요",
            narrative=(
                "자산군 괴리는 존재하지만 최소 거래액 또는 단일 종목 최대 비중 제약, "
                "혹은 해당 자산군 보유 종목 부재로 실행 가능한 항목이 없습니다. "
                "제약 완화 또는 수동 조정 검토가 필요합니다."
            ),
            warnings=["제약 조건 재검토가 필요합니다"],
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

    def _korean_fallback_analysis(
        self,
        *,
        actions: list[RebalanceAction],
        drift: dict[str, float],
        current_allocation: dict[str, float],
        target_allocation: dict[str, float] | TargetAllocation,
        constraints: RebalanceConstraints,
        source_confidence: float,
    ) -> LLMAnalysis:
        """LLM 산문에 영어가 남은 경우 UI 에 노출할 결정적 한국어 해석."""
        target_dict = _target_allocation_dict(target_allocation)
        top_asset, top_drift = max(
            drift.items(),
            key=lambda item: abs(item[1]),
            default=("other", 0.0),
        )
        asset_label = _asset_label(top_asset)
        current_pct = current_allocation.get(top_asset, 0.0) * 100
        target_pct = target_dict.get(top_asset, 0.0) * 100
        drift_pct = abs(top_drift) * 100

        if top_drift > 0:
            direction = "과대"
        elif top_drift < 0:
            direction = "부족"
        else:
            direction = "목표와 유사"

        headline = (
            f"{asset_label} 비중 {current_pct:.1f}%에서 목표 {target_pct:.1f}%로 조정 필요"
        )
        buy_count = sum(1 for action in actions if action.action == "buy")
        sell_count = sum(1 for action in actions if action.action == "sell")
        action_text = ", ".join(_format_action_summary(action) for action in actions[:3])

        narrative_parts = [
            (
                f"현재 {asset_label} 비중은 {current_pct:.1f}%이고 목표는 "
                f"{target_pct:.1f}%로, 괴리는 {drift_pct:.1f}퍼센트포인트 {direction}입니다."
            ),
            (
                f"결정적 계산은 매도 {sell_count}건과 매수 {buy_count}건을 "
                "제안했습니다."
            ),
        ]
        if action_text:
            narrative_parts.append(f"주요 실행 항목은 {action_text}입니다.")
        narrative_parts.append(
            "단일 종목 최대 비중과 최소 거래액 제약을 반영한 결과입니다."
        )

        warnings: list[str] = []
        if any(action.estimated_value_krw is None for action in actions):
            warnings.append("가격이 없는 항목은 실행 전에 기준가 재확인이 필요합니다.")
        if not constraints.allow_fractional:
            warnings.append("정수 수량 조건이 적용되어 실제 주문 수량이 달라질 수 있습니다.")
        if drift_pct >= 10:
            warnings.append("괴리가 큰 자산군은 거래 비용과 분할 실행 여부 확인이 필요합니다.")

        return LLMAnalysis(
            headline=headline,
            narrative=" ".join(narrative_parts),
            warnings=warnings[:3],
            confidence=min(max(source_confidence, 0.5), 0.75),
        )


# ──────────────────────── domain / critique helpers ────────────────────────


def _target_allocation_dict(target_allocation: dict[str, float] | TargetAllocation) -> dict[str, float]:
    if isinstance(target_allocation, TargetAllocation):
        return target_allocation.model_dump()
    return dict(target_allocation)


def _asset_label(asset_class: str) -> str:
    return _ASSET_CLASS_LABELS.get(asset_class, "해당 자산군")


def _format_krw(value: Decimal | None) -> str:
    if value is None:
        return "금액 미확인"
    amount = int(value)
    if amount >= 10_000:
        return f"{amount / 10_000:,.0f}만원"
    return f"{amount:,.0f}원"


def _format_action_summary(action: RebalanceAction) -> str:
    action_label = _ACTION_LABELS.get(action.action, action.action)
    if action.estimated_value_krw is None:
        return f"{action.code} {action_label} 수량 {action.quantity}"
    return f"{action.code} {action_label} 약 {_format_krw(action.estimated_value_krw)}"


def _localize_text(text: str) -> str:
    localized = re.sub(
        r"(\d+(?:\.\d+)?)\s*%p\b",
        r"\1퍼센트포인트",
        text,
        flags=re.IGNORECASE,
    )
    for pattern, replacement in _TEXT_REPLACEMENTS:
        localized = pattern.sub(replacement, localized)
    return re.sub(r"\s+", " ", localized).strip()


def _localize_analysis_language(analysis: LLMAnalysis) -> LLMAnalysis:
    """LLM 이 남긴 영어 도메인 용어를 UI 노출 전 한국어로 치환."""
    return analysis.model_copy(
        update={
            "headline": _localize_text(analysis.headline),
            "narrative": _localize_text(analysis.narrative),
            "warnings": [_localize_text(warning) for warning in analysis.warnings],
        }
    )


def _allowed_english_tokens(actions: list[RebalanceAction]) -> set[str]:
    allowed = {token.upper() for token in _KNOWN_TOKENS}
    allowed.update({"PB", "WM"})
    for action in actions:
        code = action.code.upper()
        allowed.add(code)
        allowed.update(part for part in re.split(r"[-/._:]", code) if part)
    return allowed


def _language_check(analysis: LLMAnalysis, actions: list[RebalanceAction]) -> str:
    """종목/통화 표준 코드를 제외한 영어 산문이 남았는지 검증."""
    combined = f"{analysis.headline} {analysis.narrative} {' '.join(analysis.warnings)}"
    if not _KOREAN_RE.search(combined):
        return "fail: missing korean text"

    allowed = _allowed_english_tokens(actions)
    unknown_terms: set[str] = set()
    for match in _ENGLISH_WORD_RE.finditer(combined):
        term = match.group(0)
        upper = term.upper()
        if upper in allowed:
            continue
        # 알려지지 않은 대문자 티커는 언어 문제가 아니라 critique gate 에서 다룬다.
        if term.isupper() and 2 <= len(term) <= 6:
            continue
        unknown_terms.add(term)

    if unknown_terms:
        return f"fail: non_korean_terms: {sorted(unknown_terms)[:5]}"
    return "pass"


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
