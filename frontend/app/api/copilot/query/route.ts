/**
 * app/api/copilot/query/route.ts
 *
 * POST /api/copilot/query
 *
 * NEXT_PUBLIC_COPILOT_MOCK=1(또는 서버 사이드 COPILOT_MOCK=1) 환경에서
 * 결정론적 SSE 스트림을 Next.js API Route 레벨에서 직접 반환한다.
 *
 * 이 방식은 MSW 서비스 워커 등록 타이밍 문제를 우회하며,
 * 프로덕션 번들에 mock 코드가 노출되지 않는다.
 */
import { NextRequest, NextResponse } from "next/server";

const MOCK_ENABLED =
  process.env.NEXT_PUBLIC_COPILOT_MOCK === "1" ||
  process.env.COPILOT_MOCK === "1";

/** SSE 이벤트 직렬화 */
function sse(data: unknown): string {
  return `data: ${JSON.stringify(data)}\n\n`;
}

function buildNormalStream(query: string, mockScenario: string | null): string {
  if (mockScenario === "degraded") {
    return buildDegradedStream();
  }

  const isFollowUp =
    query.includes("포트폴리오") ||
    query.includes("simulator") ||
    query.includes("-30%");
  const isComparison = query.includes("비교") || query.includes("vs");

  const plan = {
    plan_id: "mock-plan-01",
    session_id: "mock-session-01",
    created_at: new Date().toISOString(),
    steps: isFollowUp
      ? [
          {
            step_id: "sim-1",
            agent: "simulator",
            inputs: {},
            depends_on: [],
            gate_policy: { schema: true, domain: true, critique: true },
          },
        ]
      : isComparison
        ? [
            {
              step_id: "cmp-1",
              agent: "comparison",
              inputs: { symbols: ["TSLA", "NVDA"] },
              depends_on: [],
              gate_policy: { schema: true, domain: true, critique: true },
            },
            {
              step_id: "chart-1",
              agent: "portfolio",
              inputs: {},
              depends_on: ["cmp-1"],
              gate_policy: { schema: true, domain: true, critique: true },
            },
          ]
        : [
            {
              step_id: "news-1",
              agent: "news-rag",
              inputs: {},
              depends_on: [],
              gate_policy: { schema: true, domain: true, critique: true },
            },
          ],
  };

  let stream = sse({ type: "plan.ready", plan });

  if (isFollowUp) {
    stream += sse({ type: "step.start", step_id: "sim-1" });
    stream += sse({
      type: "step.gate",
      step_id: "sim-1",
      gate: "schema",
      status: "pass",
    });
    stream += sse({
      type: "step.gate",
      step_id: "sim-1",
      gate: "domain",
      status: "pass",
    });
    stream += sse({
      type: "step.gate",
      step_id: "sim-1",
      gate: "critique",
      status: "pass",
    });
    stream += sse({
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
    // 이전 턴 히스토리 카드
    stream += sse({
      type: "step.result",
      step_id: "hist-cmp",
      card: {
        type: "comparison_table",
        rows: [
          {
            symbol: "TSLA",
            return_3m_pct: 12.3,
            volatility_pct: 45.2,
            pe_ratio: 68,
          },
          {
            symbol: "NVDA",
            return_3m_pct: 28.7,
            volatility_pct: 38.4,
            pe_ratio: 42,
          },
        ],
        degraded: false,
      },
    });
  } else if (isComparison) {
    for (const stepId of ["cmp-1", "chart-1"]) {
      stream += sse({ type: "step.start", step_id: stepId });
      stream += sse({
        type: "step.gate",
        step_id: stepId,
        gate: "schema",
        status: "pass",
      });
      stream += sse({
        type: "step.gate",
        step_id: stepId,
        gate: "domain",
        status: "pass",
      });
      stream += sse({
        type: "step.gate",
        step_id: stepId,
        gate: "critique",
        status: "pass",
      });
    }
    stream += sse({
      type: "step.result",
      step_id: "cmp-1",
      card: {
        type: "comparison_table",
        rows: [
          {
            symbol: "TSLA",
            return_3m_pct: 12.3,
            volatility_pct: 45.2,
            pe_ratio: 68,
          },
          {
            symbol: "NVDA",
            return_3m_pct: 28.7,
            volatility_pct: 38.4,
            pe_ratio: 42,
          },
        ],
        degraded: false,
      },
    });
    stream += sse({
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
  } else {
    stream += sse({ type: "step.start", step_id: "news-1" });
    stream += sse({
      type: "step.gate",
      step_id: "news-1",
      gate: "schema",
      status: "pass",
    });
    stream += sse({
      type: "step.gate",
      step_id: "news-1",
      gate: "domain",
      status: "pass",
    });
    stream += sse({
      type: "step.gate",
      step_id: "news-1",
      gate: "critique",
      status: "pass",
    });
    stream += sse({
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

  stream += sse({
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
  stream += sse({
    type: "done",
    session_id: "mock-session-01",
    turn_id: "turn-01",
  });

  return stream;
}

function buildDegradedStream(): string {
  let stream = "";
  const plan = {
    // plan_id, session_id, turn_id 에 "degraded" 문자열을 포함하지 않는다.
    // degraded.spec.ts 의 getByText(/stub 모드|degraded/i) 가 1개만 매칭돼야 하기 때문.
    plan_id: "mock-plan-limited",
    session_id: "mock-session-limited",
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

  stream += sse({ type: "plan.ready", plan });
  stream += sse({ type: "step.start", step_id: "news-d1" });
  stream += sse({
    type: "step.gate",
    step_id: "news-d1",
    gate: "schema",
    status: "pass",
  });
  stream += sse({
    type: "step.gate",
    step_id: "news-d1",
    gate: "domain",
    status: "fail",
    reason: "뉴스 소스 도메인 검증 실패 (stub 모드)",
  });
  stream += sse({
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
      // card 에 degraded_reason 을 포함해 DegradedCard 에 "stub 모드" 문구 표시
      degraded: true,
      degraded_reason: "stub 모드: 도메인 게이트 실패로 제한된 결과 반환",
    },
  });
  stream += sse({
    type: "final.card",
    card: {
      type: "text",
      // final card body 에는 "degraded" / "stub 모드" 문자열 없이 순수 요약만
      body: "일부 단계가 게이트를 통과하지 못해 제한된 결과를 반환합니다.",
      degraded: false,
    },
  });
  stream += sse({
    type: "done",
    session_id: "mock-session-limited",
    turn_id: "turn-limited-01",
  });

  return stream;
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const url = new URL(req.url);
  const mockScenario = url.searchParams.get("mock_scenario");

  if (!MOCK_ENABLED) {
    // 프로덕션: BE 로 프록시. body 는 text 로 한 번 읽어 Content-Length 를 고정해서 넘긴다
    // (ReadableStream 패스스루 시 uvicorn/FastAPI JSON 파서가 body 를 못 읽는 케이스 회피)
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
    const bodyText = await req.text();
    const upstream = await fetch(`${apiBase}/copilot/query${url.search}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(req.headers.get("authorization")
          ? { authorization: req.headers.get("authorization")! }
          : {}),
      },
      body: bodyText,
    });
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
      },
    });
  }

  let body: { query?: string } = {};
  try {
    body = (await req.json()) as { query?: string };
  } catch {
    // parse error — use defaults
  }

  const streamText = buildNormalStream(body.query ?? "", mockScenario);

  return new NextResponse(streamText, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
