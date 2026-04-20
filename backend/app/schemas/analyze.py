from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.market import OhlcBar


class PortfolioHolding(BaseModel):
    """포트폴리오 컨텍스트 주입용 보유 종목 단위."""

    market: str
    code: str
    quantity: Decimal
    avg_cost: Decimal
    currency: str
    current_value_krw: Decimal | None = None
    pnl_pct: float | None = None


class PortfolioContext(BaseModel):
    """분석 요청에 주입되는 개인화 포트폴리오 컨텍스트."""

    holdings: list[PortfolioHolding]
    total_value_krw: Decimal
    asset_class_breakdown: dict[str, float]  # {"stock": 0.6, "crypto": 0.4}
    matched_holding: PortfolioHolding | None = None  # 분석 대상 심볼과 일치하는 보유


class GateStatus(BaseModel):
    schema_gate: str = Field("pending", description="ok | fail | pending")
    domain_gate: str = Field("pending", description="ok | fail | pending")
    critique_gate: str = Field("pending", description="ok | fail | pending")


class SymbolRef(BaseModel):
    """업로드 없이 심볼만으로 분석할 때 사용하는 참조."""

    market: str = Field(..., description="upbit | binance | yahoo | naver_kr")
    code: str = Field(..., description="티커/코드. 예: KRW-BTC, AAPL")


class AnalyzeContext(BaseModel):
    """선택적 부가 컨텍스트. 현재는 OHLC 프리패치 결과만."""

    ohlc: list[OhlcBar] | None = Field(
        default=None, description="서버 또는 클라이언트가 제공한 OHLC 시계열"
    )


class AnalyzeRequest(BaseModel):
    """임의 투자 데이터를 받아 자동 분석을 요청한다."""

    # 사용자가 업로드한 원시 데이터 (CSV rows, JSON 등 자유 형식)
    data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="분석할 원시 데이터 rows. symbol 만으로도 분석할 경우 빈 리스트 허용.",
    )
    query: str | None = Field(None, description="자연어 분석 지시 (선택)")
    asset_class_hint: str | None = Field(
        None, description="Router 힌트: stock | crypto | fx | macro | auto"
    )
    symbol: SymbolRef | None = Field(
        None,
        description="심볼 분석 요청. 존재 시 서버가 market 어댑터로 OHLC 를 프리패치한다.",
    )
    context: AnalyzeContext | None = Field(
        None, description="클라이언트가 선계산해 넘기는 OHLC 등 부가 컨텍스트"
    )
    include_portfolio_context: bool = Field(
        False,
        description="True면 서버가 DB에서 holdings를 조회해 AgentState에 주입. LLM이 개인화된 분석 수행.",
    )


class AnalyzerSignal(BaseModel):
    """Analyzer 가 추출한 정량·정성 신호 하나."""

    kind: str = Field(..., description="trend | volatility | ma_cross | breakout | risk | other")
    strength: Literal["low", "medium", "high"] = Field(
        ..., description="신호 강도 버킷"
    )
    rationale: str = Field(..., description="왜 이 신호라고 판단했는지 한 문장")


class AnalyzerOutput(BaseModel):
    """Analyzer 최종 출력 — 응답의 `result` 필드에 직렬화된다."""

    asset_class: str
    headline: str = Field(..., description="한 문장 요약 헤드라인")
    narrative: str = Field(..., description="2~4문장 서술형 분석")
    summary: str | None = Field(
        None, description="(legacy) 첫 버전 호환용. headline 과 동일하거나 더 긴 요약"
    )
    highlights: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    signals: list[AnalyzerSignal] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class CacheMetrics(BaseModel):
    read_tokens: int = Field(0, description="프롬프트 캐시 히트 토큰")
    creation_tokens: int = Field(0, description="캐시 생성(기록) 토큰")
    input_tokens: int = Field(0)
    output_tokens: int = Field(0)


class AnalyzeMeta(BaseModel):
    asset_class: str = Field(..., description="Router 가 결정한 자산군")
    router_reason: str = Field(..., description="Router 가 선택한 이유 (한 문장)")
    gates: dict[str, str] = Field(..., description="각 게이트의 최종 상태")
    latency_ms: int | None = Field(None, description="그래프 실행 소요 시간(ms)")
    analyzer_name: str | None = Field(
        None, description="어떤 analyzer 가 실행되었는지 (stock | crypto | fx | ...)"
    )
    evidence_snippets: list[str] = Field(
        default_factory=list,
        description="critique 통과 후 확정된 근거 인용 3~5개",
    )
    cache: CacheMetrics | None = Field(
        None, description="직전 요청의 프롬프트 캐시/토큰 사용량"
    )


class AnalyzeResponse(BaseModel):
    request_id: str = Field(..., description="추적용 UUID")
    status: str = Field(..., description="ok | error | degraded")
    result: dict[str, Any] | None = Field(None, description="Analyzer 출력 (자산군별 상이)")
    meta: AnalyzeMeta
