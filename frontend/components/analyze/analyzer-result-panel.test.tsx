import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalyzerResultPanel } from "./analyzer-result-panel";
import type { AnalyzeResponse } from "@/lib/api/analyze";

function makeResponse(
  overrides: Partial<AnalyzeResponse> = {},
): AnalyzeResponse {
  return {
    request_id: "test-uuid-1234",
    status: "ok",
    result: null,
    meta: {
      asset_class: "stock",
      router_reason: "컬럼명과 데이터 패턴으로 주식 데이터로 판단",
      gates: {
        schema: "pass",
        domain: "pass",
        critique: "pass",
      },
      latency_ms: 320,
      analyzer_name: "stock",
      evidence_snippets: ["AAPL 수익률 +12.3%", "PER 28.5"],
      cache: null,
    },
    ...overrides,
  };
}

describe("AnalyzerResultPanel", () => {
  it("renders with data-testid=analyzer-result", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    expect(screen.getByTestId("analyzer-result")).toBeInTheDocument();
  });

  it("renders router-reason-content", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    expect(screen.getByTestId("router-reason-content")).toBeInTheDocument();
  });

  it("renders gate badges with correct data-testid", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    expect(screen.getByTestId("gate-badge-schema")).toBeInTheDocument();
    expect(screen.getByTestId("gate-badge-domain")).toBeInTheDocument();
    expect(screen.getByTestId("gate-badge-critique")).toBeInTheDocument();
  });

  it("applies green color class for pass gate status", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    const schemaBadge = screen.getByTestId("gate-badge-schema");
    expect(schemaBadge.className).toContain("green");
  });

  it("applies red color class for fail gate status", () => {
    const response = makeResponse({
      meta: {
        ...makeResponse().meta,
        gates: { schema: "fail", domain: "pass", critique: "pass" },
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    const schemaBadge = screen.getByTestId("gate-badge-schema");
    expect(schemaBadge.className).toContain("red");
  });

  it("applies yellow color class for warn gate status", () => {
    const response = makeResponse({
      meta: {
        ...makeResponse().meta,
        gates: { schema: "warn", domain: "pass", critique: "pass" },
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    const schemaBadge = screen.getByTestId("gate-badge-schema");
    expect(schemaBadge.className).toContain("yellow");
  });

  it("renders confidence bar when confidence is present in result", () => {
    const response = makeResponse({
      result: { confidence: 75, headline: "강세 신호 감지" },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    expect(screen.getByTestId("confidence-bar")).toBeInTheDocument();
  });

  it("does not render confidence bar when confidence is absent", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    expect(screen.queryByTestId("confidence-bar")).not.toBeInTheDocument();
  });

  it("renders evidence snippets list", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    expect(screen.getByText("AAPL 수익률 +12.3%")).toBeInTheDocument();
    expect(screen.getByText("PER 28.5")).toBeInTheDocument();
  });

  it("renders cache metrics when cache data is present", () => {
    const response = makeResponse({
      meta: {
        ...makeResponse().meta,
        cache: {
          read_tokens: 1500,
          creation_tokens: 200,
          input_tokens: 300,
          output_tokens: 400,
        },
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    expect(screen.getByText(/캐시/)).toBeInTheDocument();
    expect(screen.getByText(/1,500/)).toBeInTheDocument();
  });

  it("renders request ID in footer", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    expect(screen.getByText(/test-uuid-1234/)).toBeInTheDocument();
  });

  it("renders X-Cache header when cacheHeader provided and no cache metrics", () => {
    render(
      <AnalyzerResultPanel
        response={makeResponse()}
        cacheHeader="HIT"
      />,
    );
    expect(screen.getByText(/X-Cache: HIT/)).toBeInTheDocument();
  });

  it("renders holding badge when result.matched_holding is present", () => {
    const response = makeResponse({
      result: {
        matched_holding: {
          quantity: 5,
          currency: "주",
          pnl_pct: 12.3,
        },
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    const badge = screen.getByTestId("holding-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toContain("보유 중");
    expect(badge.textContent).toContain("5주");
    expect(badge.textContent).toContain("+12.3%");
  });

  it("renders holding badge when result.metrics.matched_holding is present", () => {
    const response = makeResponse({
      result: {
        metrics: {
          matched_holding: {
            quantity: 10,
            currency: "주",
            pnl_pct: -3.5,
          },
        },
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    const badge = screen.getByTestId("holding-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toContain("-3.5%");
  });

  it("renders holding badge from evidence when source is portfolio.matched_holding", () => {
    const response = makeResponse({
      result: {
        evidence: [
          {
            source: "portfolio.matched_holding",
            claim: "5주 보유, 평단 185 USD, 평가손익 +8.5%",
          },
        ],
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    const badge = screen.getByTestId("holding-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toContain("보유 중");
  });

  it("does not render holding badge when no matched_holding data", () => {
    render(
      <AnalyzerResultPanel response={makeResponse()} cacheHeader={null} />,
    );
    expect(screen.queryByTestId("holding-badge")).not.toBeInTheDocument();
  });

  it("renders concentration risk alert when signal with kind=risk and 집중도 in rationale", () => {
    const response = makeResponse({
      result: {
        signals: [
          {
            kind: "risk",
            label: "집중도 리스크",
            rationale: "포트폴리오 내 집중도가 35%로 과도합니다",
          },
        ],
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    const alert = screen.getByTestId("concentration-risk-alert");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveAttribute("role", "alert");
    expect(alert.textContent).toContain("집중도 리스크");
    expect(alert.textContent).toContain("집중도가 35%로 과도합니다");
  });

  it("does not render concentration risk alert when no risk signal", () => {
    const response = makeResponse({
      result: {
        signals: [
          {
            kind: "momentum",
            label: "강세 모멘텀",
            rationale: "RSI 70 초과",
          },
        ],
      },
    });
    render(<AnalyzerResultPanel response={response} cacheHeader={null} />);
    expect(screen.queryByTestId("concentration-risk-alert")).not.toBeInTheDocument();
  });
});
