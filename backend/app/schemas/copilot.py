"""Copilot Planner 스키마.

sprint-01: NL Query Planner — CopilotPlan, CopilotStep, GatePolicy 정의.
sprint-03: CopilotCard discriminated union 확장 (6종 variant).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

# 9개 허용 에이전트 리터럴 (plan.md / contract.md 기준)
CopilotStepAgent = Literal[
    "stock",
    "crypto",
    "fx",
    "macro",
    "portfolio",
    "rebalance",
    "comparison",
    "simulator",
    "news-rag",
]


# ─────────────────────── CopilotCard discriminated union ─────────────────────
# plan.md 기준: text | chart | scorecard | citation | comparison_table | simulator_result


class TextCard(BaseModel):
    """일반 텍스트 분석 결과 카드."""

    type: Literal["text"] = "text"
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    degraded: bool = False


class ChartSeries(BaseModel):
    label: str
    data: list[float]
    timestamps: list[str] = Field(default_factory=list)


class ChartCard(BaseModel):
    """시계열 차트 카드 (TradingView Lightweight Charts 호환)."""

    type: Literal["chart"] = "chart"
    title: str
    series: list[ChartSeries]
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    degraded: bool = False


class ScorecardRow(BaseModel):
    label: str
    value: str | float
    unit: str = ""
    delta: float | None = None


class ScorecardCard(BaseModel):
    """주요 지표 스코어카드 카드."""

    type: Literal["scorecard"] = "scorecard"
    title: str
    rows: list[ScorecardRow]
    degraded: bool = False


class CitationCard(BaseModel):
    """뉴스/공시 단일 인용 카드."""

    type: Literal["citation"] = "citation"
    doc_id: int
    chunk_id: int
    source_url: str
    title: str
    published_at: str | None = None
    excerpt: str
    score: float
    degraded: bool = False


class ComparisonRow(BaseModel):
    symbol: str
    metrics: dict[str, Any]


class ComparisonTableCard(BaseModel):
    """N종목 비교 테이블 카드."""

    type: Literal["comparison_table"] = "comparison_table"
    symbols: list[str]
    metrics: list[str]
    rows: list[ComparisonRow]
    summary: str = ""
    degraded: bool = False


class ScenarioRow(BaseModel):
    symbol: str
    shock: float  # multiplier (0.8 = -20%)
    new_value: float
    delta_pct: float


class SimulatorResultCard(BaseModel):
    """what-if 시나리오 시뮬레이터 카드."""

    type: Literal["simulator_result"] = "simulator_result"
    base_value: float
    shocked_value: float
    twr_change_pct: float
    scenarios: list[ScenarioRow]
    sensitivity: dict[str, float] = Field(default_factory=dict)
    degraded: bool = False


# Pydantic v2 discriminated union — type 필드로 구분.
# RootModel + Annotated Union 으로 model_json_schema() 를 지원한다.
_CopilotCardUnion = Annotated[
    TextCard | ChartCard | ScorecardCard | CitationCard | ComparisonTableCard | SimulatorResultCard,
    Field(discriminator="type"),
]


class CopilotCard(RootModel[_CopilotCardUnion]):
    """Copilot 서브-에이전트 출력 카드 discriminated union.

    6종 variant: text | chart | scorecard | citation | comparison_table | simulator_result.
    Pydantic v2 RootModel 로 감싸 model_json_schema() / model_validate() 를 지원.
    """

    @classmethod
    def model_json_schema(cls, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        schema = super().model_json_schema(**kwargs)
        # RootModel 은 'anyOf' 를 root 에 두지 않고 '$defs' + '$ref' 구조를 씀.
        # contract test 가 anyOf/oneOf 를 기대하므로 flatten.
        if "anyOf" not in schema and "$defs" not in schema:
            return schema
        if "anyOf" in schema:
            return schema
        # $ref → anyOf 로 펼치기
        defs = schema.get("$defs", {})
        root_ref = schema.get("$ref")
        if root_ref and root_ref.startswith("#/$defs/"):
            def_key = root_ref.removeprefix("#/$defs/")
            inner = defs.get(def_key, schema)
            if "anyOf" in inner:
                schema = {**schema, "anyOf": inner["anyOf"]}
        return schema


class GatePolicy(BaseModel):
    """각 step 에 적용할 3단 게이트 정책.

    `schema` 는 Pydantic BaseModel 의 클래스메서드명과 충돌하므로
    내부 필드명은 `schema_check` 를 사용하고 JSON alias 를 "schema" 로 유지한다.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_check: bool = Field(True, alias="schema")
    domain: bool = True
    critique: bool = True


class CopilotStep(BaseModel):
    """플랜의 단일 실행 단계."""

    step_id: str
    agent: CopilotStepAgent
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    gate_policy: GatePolicy = Field(default_factory=lambda: GatePolicy.model_validate({"schema": True}))


class CopilotPlan(BaseModel):
    """자연어 질의로부터 생성된 멀티-스텝 에이전트 실행 계획.

    POST /copilot/plan 응답 스키마로도 사용됨.
    gate_results 는 3단 게이트 통과 여부 (옵션 필드).
    """

    plan_id: str
    session_id: str
    steps: list[CopilotStep]
    created_at: str  # ISO 8601 문자열
    gate_results: dict[str, str] = Field(
        default_factory=dict,
        description="schema/domain/critique gate 통과 여부",
    )


class CopilotPlanRequest(BaseModel):
    """POST /copilot/plan 요청 본문."""

    query: str = Field(..., description="자연어 질의", min_length=1)
    session_id: str | None = Field(default=None, description="기존 세션 ID (옵션)")


# 하위 호환 alias — 내부 모듈이 CopilotPlanResponse 를 참조하는 경우를 위해 유지
CopilotPlanResponse = CopilotPlan
