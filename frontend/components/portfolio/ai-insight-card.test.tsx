import { describe, it, expect } from "vitest";
import { renderWithLocale as render, screen } from "@/lib/test-utils";
import { AiInsightCard, type AiInsightResponse } from "./ai-insight-card";

const MOCK_INSIGHT: AiInsightResponse = {
  summary: "포트폴리오는 기술주 중심으로 구성되어 있습니다.",
  bullets: ["기술주 비중 과다", "암호화폐 변동성 주의", "달러 환율 관리 필요"],
  generated_at: "2026-04-23T10:00:00Z",
  stub_mode: true,
  gates: { schema: "pass", domain: "pass", critique: "pass" },
};

describe("AiInsightCard", () => {
  it("insight 데이터를 렌더한다", () => {
    render(<AiInsightCard insight={MOCK_INSIGHT} />);
    expect(screen.getByTestId("ai-insight-card")).toBeInTheDocument();
    expect(screen.getByTestId("ai-insight-summary")).toBeInTheDocument();
    expect(screen.getByText("포트폴리오는 기술주 중심으로 구성되어 있습니다.")).toBeInTheDocument();
  });

  it("AI 인사이트 문장의 금액 숫자를 천 단위 콤마로 표시한다", () => {
    render(
      <AiInsightCard
        insight={{
          ...MOCK_INSIGHT,
          summary: "총 평가금액은 13715541원이고 예상 매수금액은 2500000원입니다.",
          bullets: ["현금성 자산 1200000원 확보", "리밸런싱 비용 15000원 예상"],
        }}
      />,
    );

    expect(
      screen.getByText("총 평가금액은 13,715,541원이고 예상 매수금액은 2,500,000원입니다."),
    ).toBeInTheDocument();
    expect(screen.getByText("현금성 자산 1,200,000원 확보")).toBeInTheDocument();
    expect(screen.getByText("리밸런싱 비용 15,000원 예상")).toBeInTheDocument();
  });

  it("3개 bullets를 렌더한다", () => {
    render(<AiInsightCard insight={MOCK_INSIGHT} />);
    const bullets = screen.getByTestId("ai-insight-bullets");
    expect(bullets.children.length).toBe(3);
  });

  it("stub_mode=true이면 목업 배지를 표시한다", () => {
    render(<AiInsightCard insight={MOCK_INSIGHT} />);
    expect(screen.getByText("목업")).toBeInTheDocument();
  });

  it("3개 gates 배지를 렌더한다", () => {
    render(<AiInsightCard insight={MOCK_INSIGHT} />);
    const gatesContainer = screen.getByTestId("ai-insight-gates");
    expect(gatesContainer).toBeInTheDocument();
    expect(screen.getByText("스키마")).toBeInTheDocument();
    expect(screen.getByText("도메인")).toBeInTheDocument();
    expect(screen.getByText("검토")).toBeInTheDocument();
  });

  it("insight=null이면 empty state를 렌더한다", () => {
    render(<AiInsightCard insight={null} />);
    expect(screen.getByTestId("ai-insight-empty")).toBeInTheDocument();
  });

  it("isLoading=true이면 loading state를 렌더한다", () => {
    render(<AiInsightCard insight={null} isLoading />);
    expect(screen.getByTestId("ai-insight-loading")).toBeInTheDocument();
  });
});
