/**
 * copilot-sse.ts — MSW handler for Copilot SSE mock
 *
 * NEXT_PUBLIC_COPILOT_MOCK=1 환경에서 /copilot/query POST 를 가로채
 * 결정론적 SSE 스트림을 반환한다.
 *
 * mock_scenario=degraded 쿼리파라미터 시 gate_fail 이벤트 포함.
 */
import { http, HttpResponse } from "msw";

/** SSE event 직렬화 */
function sseEvent(data: unknown): string {
  return `data: ${JSON.stringify(data)}\n\n`;
}

/** 일반 시나리오 SSE 이벤트 스트림 */
function buildNormalStream(query: string): string {
  const isFollowUp =
    query.includes("포트폴리오") || query.includes("simulator") || query.includes("-30%");
  const isComparison = query.includes("비교") || query.includes("vs");
  const isNews = query.includes("뉴스") || query.includes("공시");

  const plan = {
    plan_id: "mock-plan-01",
    session_id: "mock-session-01",
    created_at: new Date().toISOString(),
    steps: isFollowUp
      ? [{ step_id: "sim-1", agent: "simulator", inputs: {}, depends_on: [], gate_policy: { schema: true, domain: true, critique: true } }]
      : isComparison
      ? [
          { step_id: "cmp-1", agent: "comparison", inputs: { symbols: ["TSLA", "NVDA"] }, depends_on: [], gate_policy: { schema: true, domain: true, critique: true } },
          { step_id: "chart-1", agent: "portfolio", inputs: {}, depends_on: ["cmp-1"], gate_policy: { schema: true, domain: true, critique: true } },
        ]
      : [{ step_id: "news-1", agent: "news-rag", inputs: {}, depends_on: [], gate_policy: { schema: true, domain: true, critique: true } }],
  };

  let stream = "";
  stream += sseEvent({ type: "plan.ready", plan });

  if (isFollowUp) {
    stream += sseEvent({ type: "step.start", step_id: "sim-1" });
    stream += sseEvent({ type: "step.gate", step_id: "sim-1", gate: "schema", status: "pass" });
    stream += sseEvent({ type: "step.gate", step_id: "sim-1", gate: "domain", status: "pass" });
    stream += sseEvent({ type: "step.gate", step_id: "sim-1", gate: "critique", status: "pass" });
    stream += sseEvent({
      type: "step.result",
      step_id: "sim-1",
      card: {
        type: "simulator_result",
        scenario: "NVDA -30%",
        portfolio_impact_pct: -4.2,
        twr_impact_pct: -3.8,
        degraded: false,
      },
    });
    // 이전 턴 카드도 히스토리에 포함
    stream += sseEvent({
      type: "step.result",
      step_id: "hist-cmp",
      card: {
        type: "comparison_table",
        rows: [
          { symbol: "TSLA", return_3m_pct: 12.3, volatility_pct: 45.2, pe_ratio: 68 },
          { symbol: "NVDA", return_3m_pct: 28.7, volatility_pct: 38.4, pe_ratio: 42 },
        ],
        degraded: false,
      },
    });
  } else if (isComparison) {
    for (const stepId of ["cmp-1", "chart-1"]) {
      stream += sseEvent({ type: "step.start", step_id: stepId });
      stream += sseEvent({ type: "step.gate", step_id: stepId, gate: "schema", status: "pass" });
      stream += sseEvent({ type: "step.gate", step_id: stepId, gate: "domain", status: "pass" });
      stream += sseEvent({ type: "step.gate", step_id: stepId, gate: "critique", status: "pass" });
    }
    stream += sseEvent({
      type: "step.result",
      step_id: "cmp-1",
      card: {
        type: "comparison_table",
        rows: [
          { symbol: "TSLA", return_3m_pct: 12.3, volatility_pct: 45.2, pe_ratio: 68 },
          { symbol: "NVDA", return_3m_pct: 28.7, volatility_pct: 38.4, pe_ratio: 42 },
        ],
        degraded: false,
      },
    });
    stream += sseEvent({
      type: "step.result",
      step_id: "chart-1",
      card: {
        type: "chart",
        series: [
          { label: "TSLA", data: [100, 108, 112, 109, 115] },
          { label: "NVDA", data: [100, 118, 125, 122, 131] },
        ],
        degraded: false,
      },
    });
  } else if (isNews) {
    stream += sseEvent({ type: "step.start", step_id: "news-1" });
    stream += sseEvent({ type: "step.gate", step_id: "news-1", gate: "schema", status: "pass" });
    stream += sseEvent({ type: "step.gate", step_id: "news-1", gate: "domain", status: "pass" });
    stream += sseEvent({ type: "step.gate", step_id: "news-1", gate: "critique", status: "pass" });
    stream += sseEvent({
      type: "step.result",
      step_id: "news-1",
      card: {
        type: "news_rag_list",
        items: [
          {
            title: "AAPL Q1 2026 실적 발표",
            excerpt: "Apple Inc.가 Q1 2026 실적을 발표했습니다.",
            source_url: "https://example.com/news/aapl-q1-2026",
            published_at: "2026-02-01",
            score: 0.92,
          },
        ],
        degraded: false,
      },
    });
  }

  // final card
  stream += sseEvent({
    type: "final.card",
    card: {
      type: "text",
      body: isFollowUp
        ? "시뮬레이션 결과 종합: NVDA -30% 시 포트폴리오 영향은 -4.2%입니다."
        : isComparison
        ? "비교 분석 요약: NVDA가 3개월 수익률에서 TSLA를 상회합니다."
        : "뉴스 분석 요약: AAPL 관련 최신 뉴스를 확인했습니다.",
      degraded: false,
    },
  });
  stream += sseEvent({ type: "done", session_id: "mock-session-01", turn_id: "turn-01" });

  return stream;
}

/** degraded 시나리오 SSE 이벤트 스트림 */
function buildDegradedStream(): string {
  let stream = "";
  const plan = {
    plan_id: "mock-plan-degraded",
    session_id: "mock-session-degraded",
    created_at: new Date().toISOString(),
    steps: [
      {
        step_id: "news-d1",
        agent: "news-rag",
        inputs: {},
        depends_on: [],
        gate_policy: { schema: true, domain: true, critique: true },
      },
    ],
  };

  stream += sseEvent({ type: "plan.ready", plan });
  stream += sseEvent({ type: "step.start", step_id: "news-d1" });
  stream += sseEvent({ type: "step.gate", step_id: "news-d1", gate: "schema", status: "pass" });
  // domain gate fail
  stream += sseEvent({
    type: "step.gate",
    step_id: "news-d1",
    gate: "domain",
    status: "fail",
    reason: "뉴스 소스 도메인 검증 실패 (stub 모드)",
  });
  // degraded card — 여전히 렌더됨
  stream += sseEvent({
    type: "step.result",
    step_id: "news-d1",
    card: {
      type: "news_rag_list",
      items: [
        {
          title: "AAPL 최근 뉴스 (stub 모드)",
          excerpt: "stub 모드에서 반환된 픽스처 뉴스입니다.",
          source_url: "https://example.com/news/stub",
          published_at: "2026-04-22",
          score: 0.75,
        },
      ],
      degraded: true,
    },
  });
  stream += sseEvent({
    type: "final.card",
    card: {
      type: "text",
      body: "degraded: 일부 단계가 게이트를 통과하지 못했습니다. stub 모드로 제한된 결과를 반환합니다.",
      degraded: true,
    },
  });
  stream += sseEvent({
    type: "done",
    session_id: "mock-session-degraded",
    turn_id: "turn-degraded-01",
  });

  return stream;
}

/** MSW handler: POST /copilot/query */
export const copilotSseHandler = http.post(
  /\/copilot\/query/,
  async ({ request }) => {
    const url = new URL(request.url);
    const mockScenario = url.searchParams.get("mock_scenario");

    let body: { query?: string } = {};
    try {
      body = (await request.json()) as { query?: string };
    } catch {
      // ignore parse error
    }

    const isDegraded =
      mockScenario === "degraded" ||
      (typeof window !== "undefined" &&
        new URLSearchParams(window.location.search).get("mock_scenario") === "degraded");

    const streamText = isDegraded
      ? buildDegradedStream()
      : buildNormalStream(body.query ?? "");

    return new HttpResponse(streamText, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
      },
    });
  }
);

export const handlers = [copilotSseHandler];
