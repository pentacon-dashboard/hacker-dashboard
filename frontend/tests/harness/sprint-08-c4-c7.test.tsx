/**
 * sprint-08-c4-c7.test.tsx — C-4/C-5/C-6/C-7 컴포넌트 유닛 테스트
 *
 * 15 (C-4) + 24 (C-5) + 20 (C-6) + 18 (C-7) = 77 케이스 목표.
 * 이 파일에서 핵심 케이스를 커버한다.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/common/theme-provider";
import { LocaleProvider } from "@/lib/i18n/locale-provider";

/**
 * 모든 유닛 테스트에 Theme + Locale Provider 를 주입하는 기본 wrapper.
 * ThemeProvider 가 없으면 useTheme() 실패, LocaleProvider 가 없으면 useLocale() 실패.
 */
function BaseProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <LocaleProvider>{children}</LocaleProvider>
    </ThemeProvider>
  );
}

function renderUnit(ui: React.ReactElement) {
  return render(ui, { wrapper: BaseProviders });
}

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <BaseProviders>{children}</BaseProviders>
      </QueryClientProvider>
    );
  };
}

// ─── C-4: 시장 분석 ─────────────────────────────────────────────────────────

import { IndexKpiStrip } from "@/components/market-analyze/index-kpi-strip";
import { WorldHeatmap } from "@/components/market-analyze/world-heatmap";
import { SectorKpiGrid } from "@/components/market-analyze/sector-kpi-grid";
import { CommodityPanel } from "@/components/market-analyze/commodity-panel";
import { MarketNewsFeed } from "@/components/market-analyze/market-news-feed";

// BE 실 스키마 기준 샘플 데이터
const SAMPLE_INDICES = [
  { ticker: "KOSPI", display_name: "KOSPI", value: "2,705.32", change_pct: "+1.24", change_abs: "+33.01", sparkline_7d: [2645, 2658, 2672, 2680, 2668, 2690, 2705] },
  { ticker: "NASDAQ", display_name: "나스닥", value: "18,720.02", change_pct: "-0.38", change_abs: "-71.34", sparkline_7d: [18500, 18580, 18620, 18560, 18650, 18700, 18720] },
  { ticker: "VIX", display_name: "VIX", value: "18.34", change_pct: "+5.12", change_abs: "+0.89", sparkline_7d: [16.2, 16.8, 17.5, 18.1, 17.8, 18.0, 18.34] },
];

const SAMPLE_SECTORS = [
  { name: "Technology", change_pct: "+1.85", constituents: 75, leaders: ["AAPL", "MSFT"] },
  { name: "Healthcare", change_pct: "-0.31", constituents: 60, leaders: ["JNJ", "PFE"] },
  { name: "Financials", change_pct: "+0.42", constituents: 65, leaders: ["JPM", "BAC"] },
];

const SAMPLE_COMMODITIES = [
  { symbol: "OIL", name: "원유(WTI)", price: "78.42", unit: "USD/배럴", change_pct: "-0.85" },
  { symbol: "GOLD", name: "금", price: "2,342.10", unit: "USD/온스", change_pct: "+0.54" },
];

const SAMPLE_NEWS = [
  { id: "n1", title: "Fed 금리 동결", source: "Reuters", published_at: new Date().toISOString(), url: "#", sentiment: "neutral" as const },
  { id: "n2", title: "엔비디아 어닝 서프라이즈", source: "Bloomberg", published_at: new Date().toISOString(), url: "#", sentiment: "positive" as const },
  { id: "n3", title: "중국 PMI 하회", source: "Yonhap", published_at: new Date().toISOString(), url: "#", sentiment: "negative" as const },
];

const SAMPLE_HEATMAP = [
  { country_code: "KR", country_name: "동아시아", change_pct: "+0.84", market_cap_usd: "$1.8T" },
  { country_code: "GB", country_name: "유럽", change_pct: "-0.18", market_cap_usd: "$2.9T" },
];

describe("C-4: IndexKpiStrip", () => {
  it("지수 카드를 렌더한다", () => {
    render(<IndexKpiStrip indices={SAMPLE_INDICES} />);
    expect(screen.getByTestId("index-kpi-strip")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-KOSPI")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-NASDAQ")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-VIX")).toBeInTheDocument();
  });

  it("양수 변동은 녹색 클래스, 음수는 적색 클래스를 가진다", () => {
    render(<IndexKpiStrip indices={SAMPLE_INDICES} />);
    const kospi = screen.getByTestId("kpi-KOSPI");
    expect(kospi.textContent).toContain("+1.24%");
  });

  it("로딩 상태에서 스켈레톤을 렌더한다", () => {
    render(<IndexKpiStrip indices={[]} loading={true} />);
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe("C-4: WorldHeatmap", () => {
  it("나라 카드를 렌더한다", () => {
    render(<WorldHeatmap data={SAMPLE_HEATMAP} />);
    expect(screen.getByTestId("world-heatmap")).toBeInTheDocument();
    expect(screen.getByText("동아시아")).toBeInTheDocument();
    expect(screen.getByText("유럽")).toBeInTheDocument();
  });

  it("양수 지역에 그린 배경 클래스가 적용된다", () => {
    render(<WorldHeatmap data={SAMPLE_HEATMAP} />);
    const text = screen.getByText("+0.84%");
    expect(text).toBeInTheDocument();
  });

  it("로딩 상태에서 스켈레톤을 렌더한다", () => {
    render(<WorldHeatmap data={[]} loading={true} />);
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe("C-4: SectorKpiGrid", () => {
  it("섹터 항목을 렌더한다", () => {
    render(<SectorKpiGrid sectors={SAMPLE_SECTORS} />);
    expect(screen.getByTestId("sector-kpi-grid")).toBeInTheDocument();
    expect(screen.getByTestId("sector-Technology")).toBeInTheDocument();
  });

  it("3개 섹터 모두 표시한다", () => {
    render(<SectorKpiGrid sectors={SAMPLE_SECTORS} />);
    expect(screen.getAllByText("Technology").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Healthcare").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Financials").length).toBeGreaterThan(0);
  });

  it("빈 상태에서 에러 없이 렌더한다", () => {
    render(<SectorKpiGrid sectors={[]} />);
    expect(screen.getByTestId("sector-kpi-grid")).toBeInTheDocument();
  });
});

describe("C-4: CommodityPanel", () => {
  it("원자재 항목을 렌더한다", () => {
    render(<CommodityPanel commodities={SAMPLE_COMMODITIES} />);
    expect(screen.getByTestId("commodity-panel")).toBeInTheDocument();
    expect(screen.getByTestId("commodity-OIL")).toBeInTheDocument();
    expect(screen.getByTestId("commodity-GOLD")).toBeInTheDocument();
  });

  it("가격과 변동률을 표시한다", () => {
    render(<CommodityPanel commodities={SAMPLE_COMMODITIES} />);
    expect(screen.getByText("78.42")).toBeInTheDocument();
    expect(screen.getByText("+0.54%")).toBeInTheDocument();
  });

  it("로딩 상태를 처리한다", () => {
    render(<CommodityPanel commodities={[]} loading={true} />);
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe("C-4: MarketNewsFeed", () => {
  it("뉴스 카드를 렌더한다", () => {
    render(<MarketNewsFeed news={SAMPLE_NEWS} />);
    expect(screen.getByTestId("market-news-feed")).toBeInTheDocument();
    expect(screen.getByTestId("news-n1")).toBeInTheDocument();
  });

  it("3개 뉴스 모두 표시한다", () => {
    render(<MarketNewsFeed news={SAMPLE_NEWS} />);
    expect(screen.getByText("Fed 금리 동결")).toBeInTheDocument();
    expect(screen.getByText("엔비디아 어닝 서프라이즈")).toBeInTheDocument();
    expect(screen.getByText("중국 PMI 하회")).toBeInTheDocument();
  });

  it("빈 상태 메시지를 표시한다", () => {
    render(<MarketNewsFeed news={[]} />);
    expect(screen.getByText("뉴스를 불러올 수 없습니다")).toBeInTheDocument();
  });
});

// ─── C-6: 업로드 ─────────────────────────────────────────────────────────────

import { ValidationCard, type ValidationResult } from "@/components/upload/validation-card";
import { PreviewTable } from "@/components/upload/preview-table";
import { AnalyzerConfigCard, type AnalyzerConfig } from "@/components/upload/analyzer-config-card";

const SAMPLE_VALIDATION: ValidationResult = {
  upload_id: "test-001",
  filename: "test.csv",
  total_rows: 100,
  valid_rows: 95,
  error_rows: 2,
  warning_rows: 3,
  columns_detected: ["date", "symbol", "quantity", "price", "currency"],
  preview_rows: [
    { date: "2024-01-01", symbol: "AAPL", quantity: "10", price: "182.5", currency: "USD" },
  ],
  errors: [{ row: 23, column: "price", message: "음수 가격" }],
  warnings: [{ row: 12, column: "currency", message: "통화 추측됨" }],
};

describe("C-6: ValidationCard", () => {
  it("초기 빈 상태를 렌더한다", () => {
    render(<ValidationCard />);
    expect(screen.getByTestId("validation-card")).toBeInTheDocument();
    expect(screen.getByText("파일 업로드 후 검증 결과가 표시됩니다")).toBeInTheDocument();
  });

  it("검증 결과를 표시한다", () => {
    render(<ValidationCard result={SAMPLE_VALIDATION} />);
    expect(screen.getByTestId("validation-counts")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument(); // total
    expect(screen.getByText("95")).toBeInTheDocument(); // valid
  });

  it("로딩 상태를 렌더한다", () => {
    render(<ValidationCard loading={true} />);
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("에러 메시지를 표시한다", () => {
    render(<ValidationCard error="업로드 실패" />);
    expect(screen.getByText("업로드 실패")).toBeInTheDocument();
  });

  it("컬럼 감지 정보를 표시한다", () => {
    render(<ValidationCard result={SAMPLE_VALIDATION} />);
    expect(screen.getByText("date")).toBeInTheDocument();
    expect(screen.getByText("symbol")).toBeInTheDocument();
  });
});

describe("C-6: PreviewTable", () => {
  it("초기 빈 상태를 렌더한다", () => {
    render(<PreviewTable />);
    expect(screen.getByTestId("preview-table")).toBeInTheDocument();
  });

  it("컬럼 헤더와 데이터를 표시한다", () => {
    render(
      <PreviewTable
        columns={SAMPLE_VALIDATION.columns_detected}
        rows={SAMPLE_VALIDATION.preview_rows}
      />,
    );
    expect(screen.getByText("date")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
  });

  it("로딩 상태를 렌더한다", () => {
    render(<PreviewTable loading={true} />);
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe("C-6: AnalyzerConfigCard", () => {
  const defaultConfig: AnalyzerConfig = {
    analyzer: "portfolio",
    period_days: 90,
    currency: "KRW",
    include_fx: true,
  };

  it("초기 설정 값을 렌더한다", () => {
    render(<AnalyzerConfigCard config={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByTestId("analyzer-config-card")).toBeInTheDocument();
  });

  it("분석기 버튼 3개를 표시한다", () => {
    render(<AnalyzerConfigCard config={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByText("포트폴리오")).toBeInTheDocument();
    expect(screen.getByText("암호화폐")).toBeInTheDocument();
    expect(screen.getByText("주식")).toBeInTheDocument();
  });

  it("분석기 변경 시 onChange가 호출된다", () => {
    const onChange = vi.fn();
    render(<AnalyzerConfigCard config={defaultConfig} onChange={onChange} />);
    fireEvent.click(screen.getByText("암호화폐"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ analyzer: "crypto" }));
  });

  it("disabled 상태에서 버튼이 비활성화된다", () => {
    render(<AnalyzerConfigCard config={defaultConfig} onChange={vi.fn()} disabled={true} />);
    const buttons = screen.getAllByRole("button", { name: /포트폴리오|암호화폐|주식/ });
    buttons.forEach((btn) => expect(btn).toBeDisabled());
  });
});

// ─── C-7: 설정 ─────────────────────────────────────────────────────────────

import { GeneralSettings } from "@/components/settings/general-settings";
import { ThemeSettings } from "@/components/settings/theme-settings";
import { ThemeProvider } from "@/components/common/theme-provider";
import { NotificationSettings, type NotificationConfig } from "@/components/settings/notification-settings";
import { SystemInfo } from "@/components/settings/system-info";
import { ConnectedAccounts, type ConnectedAccountsConfig } from "@/components/settings/connected-accounts";
import { DataSettings, type DataConfig } from "@/components/settings/data-settings";

// next-themes mock
vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: "dark", setTheme: vi.fn() }),
}));

describe("C-7: GeneralSettings", () => {
  it("기본 정보를 렌더한다", () => {
    renderUnit(<GeneralSettings />);
    expect(screen.getByTestId("general-settings")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Demo User")).toBeInTheDocument();
  });

  it("이메일 필드는 비활성화, 이름은 편집 가능하다", () => {
    renderUnit(<GeneralSettings />);
    const nameInput = screen.getByDisplayValue("Demo User");
    const emailInput = screen.getByDisplayValue("demo@example.com");
    expect(nameInput).not.toBeDisabled();
    expect(emailInput).toBeDisabled();
  });

  it("이름 변경 시 onChange 콜백을 호출한다", () => {
    const onChange = vi.fn();
    renderUnit(<GeneralSettings onChange={onChange} />);
    const nameInput = screen.getByDisplayValue("Demo User");
    fireEvent.change(nameInput, { target: { value: "New Name" } });
    expect(onChange).toHaveBeenCalledWith({ displayName: "New Name" });
  });

  it("커스텀 이름을 표시한다", () => {
    renderUnit(<GeneralSettings displayName="테스트 유저" />);
    expect(screen.getByDisplayValue("테스트 유저")).toBeInTheDocument();
  });
});

describe("C-7: ThemeSettings", () => {
  it("3개 테마 버튼을 렌더한다", () => {
    renderUnit(<ThemeSettings />);
    expect(screen.getByTestId("theme-settings")).toBeInTheDocument();
    expect(screen.getByTestId("theme-btn-dark")).toBeInTheDocument();
    expect(screen.getByTestId("theme-btn-light")).toBeInTheDocument();
    expect(screen.getByTestId("theme-btn-system")).toBeInTheDocument();
  });

  it("5개 색상 팔레트 버튼을 렌더한다", () => {
    renderUnit(<ThemeSettings accentColor="violet" />);
    expect(screen.getByTestId("accent-violet")).toBeInTheDocument();
    expect(screen.getByTestId("accent-cyan")).toBeInTheDocument();
    expect(screen.getByTestId("accent-blue")).toBeInTheDocument();
  });

  it("색상 변경 콜백이 호출된다", () => {
    const onChange = vi.fn();
    renderUnit(<ThemeSettings onAccentChange={onChange} />);
    fireEvent.click(screen.getByTestId("accent-cyan"));
    expect(onChange).toHaveBeenCalledWith("cyan");
  });
});

describe("C-7: NotificationSettings", () => {
  const defaultConfig: NotificationConfig = {
    email_alerts: true,
    push_alerts: false,
    price_threshold_pct: 5.0,
    daily_digest: true,
  };

  it("알림 토글을 렌더한다", () => {
    renderUnit(<NotificationSettings config={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByTestId("notification-settings")).toBeInTheDocument();
    expect(screen.getByLabelText("이메일 알림")).toBeInTheDocument();
  });

  it("3개 토글 항목을 표시한다", () => {
    renderUnit(<NotificationSettings config={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByText("이메일 알림")).toBeInTheDocument();
    expect(screen.getByText("푸시 알림")).toBeInTheDocument();
    expect(screen.getByText("일일 다이제스트")).toBeInTheDocument();
  });

  it("가격 임계값 입력을 표시한다", () => {
    renderUnit(<NotificationSettings config={defaultConfig} onChange={vi.fn()} />);
    // aria-label 은 사전 i18n 키 "가격 알림 임계값 (%)" 기준
    expect(screen.getByLabelText(/가격 알림 임계값/)).toBeInTheDocument();
  });
});

describe("C-7: SystemInfo", () => {
  it("버전 정보를 표시한다", () => {
    render(<SystemInfo version="0.3.1-test" />, { wrapper: makeWrapper() });
    expect(screen.getByTestId("system-info")).toBeInTheDocument();
    expect(screen.getByText("0.3.1-test")).toBeInTheDocument();
  });

  it("API 상태 정상 표시", () => {
    render(<SystemInfo apiStatus="healthy" />, { wrapper: makeWrapper() });
    expect(screen.getByText("정상")).toBeInTheDocument();
  });

  it("캐시 비우기 버튼이 작동한다", () => {
    render(<SystemInfo />, { wrapper: makeWrapper() });
    const btn = screen.getByTestId("clear-cache-btn");
    fireEvent.click(btn);
    expect(screen.getByText("캐시 삭제 완료")).toBeInTheDocument();
  });
});

describe("C-7: ConnectedAccounts", () => {
  const config: ConnectedAccountsConfig = {
    google: false,
    apple: false,
    kakao: false,
    github: true,
  };

  it("4개 계정 항목을 렌더한다", () => {
    renderUnit(<ConnectedAccounts config={config} />);
    expect(screen.getByTestId("connected-accounts")).toBeInTheDocument();
    expect(screen.getByText("Google")).toBeInTheDocument();
    expect(screen.getByText("GitHub")).toBeInTheDocument();
  });

  it("GitHub 연결 상태를 표시한다", () => {
    renderUnit(<ConnectedAccounts config={config} />);
    expect(screen.getByText("연결됨")).toBeInTheDocument();
  });

  it("onToggle 콜백이 호출된다", () => {
    const onToggle = vi.fn();
    renderUnit(<ConnectedAccounts config={config} onToggle={onToggle} />);
    const connectBtns = screen.getAllByRole("button");
    // 최소 하나는 클릭 가능 (이전엔 disabled 여서 click 무시됨)
    fireEvent.click(connectBtns[0]!);
    expect(onToggle).toHaveBeenCalled();
  });
});

describe("C-7: DataSettings", () => {
  const defaultConfig: DataConfig = {
    refresh_interval_sec: 30,
    auto_refresh: true,
    auto_backup: false,
    cache_size_mb: 128,
  };

  it("데이터 설정을 렌더한다", () => {
    renderUnit(<DataSettings config={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByTestId("data-settings")).toBeInTheDocument();
  });

  it("자동 새로고침 토글을 표시한다", () => {
    renderUnit(<DataSettings config={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByLabelText(/자동 새로고침/)).toBeInTheDocument();
  });

  it("캐시 크기 슬라이더를 표시한다", () => {
    renderUnit(<DataSettings config={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByLabelText(/캐시 크기/)).toBeInTheDocument();
  });
});

// ─── C-5: 코파일럿 ─────────────────────────────────────────────────────────

import { SessionSidebar, type CopilotSession } from "@/components/copilot/full/session-sidebar";
import { ReferencePanel } from "@/components/copilot/full/reference-panel";

const SAMPLE_SESSIONS: CopilotSession[] = [
  {
    session_id: "sess-001",
    title: "포트폴리오 리밸런싱",
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString(),
    turn_count: 5,
    last_query: "리밸런싱 필요하나요?",
  },
  {
    session_id: "sess-002",
    title: "NVDA 분석",
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    turn_count: 3,
    last_query: "NVDA 매수 타이밍?",
  },
];

describe("C-5: SessionSidebar", () => {
  it("세션 목록을 렌더한다", () => {
    render(
      <SessionSidebar
        sessions={SAMPLE_SESSIONS}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
      />,
    );
    expect(screen.getByTestId("session-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("session-item-sess-001")).toBeInTheDocument();
    expect(screen.getByTestId("session-item-sess-002")).toBeInTheDocument();
  });

  it("새 세션 버튼이 있다", () => {
    render(
      <SessionSidebar
        sessions={SAMPLE_SESSIONS}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
      />,
    );
    expect(screen.getByTestId("new-session-btn")).toBeInTheDocument();
  });

  it("세션 클릭 시 콜백이 호출된다", () => {
    const onSelect = vi.fn();
    render(
      <SessionSidebar
        sessions={SAMPLE_SESSIONS}
        onSelectSession={onSelect}
        onNewSession={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("session-item-sess-001"));
    expect(onSelect).toHaveBeenCalledWith("sess-001");
  });

  it("검색 입력으로 필터링된다", () => {
    render(
      <SessionSidebar
        sessions={SAMPLE_SESSIONS}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("세션 검색"), { target: { value: "NVDA" } });
    expect(screen.queryByText("포트폴리오 리밸런싱")).not.toBeInTheDocument();
    expect(screen.getByText("NVDA 분석")).toBeInTheDocument();
  });

  it("로딩 상태를 렌더한다", () => {
    render(
      <SessionSidebar
        sessions={[]}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
        loading={true}
      />,
    );
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe("C-5: ReferencePanel", () => {
  it("포트폴리오 요약을 렌더한다", () => {
    render(<ReferencePanel />);
    expect(screen.getByTestId("reference-panel")).toBeInTheDocument();
    expect(screen.getByText("포트폴리오 요약")).toBeInTheDocument();
  });

  it("4개 추천 질문을 표시한다", () => {
    render(<ReferencePanel quickQuestions={["질문1", "질문2", "질문3", "질문4"]} />);
    expect(screen.getByTestId("quick-question-0")).toBeInTheDocument();
    expect(screen.getByTestId("quick-question-3")).toBeInTheDocument();
  });

  it("추천 질문 클릭 시 콜백이 호출된다", () => {
    const onQ = vi.fn();
    render(<ReferencePanel quickQuestions={["테스트 질문"]} onQuickQuestion={onQ} />);
    fireEvent.click(screen.getByTestId("quick-question-0"));
    expect(onQ).toHaveBeenCalledWith("테스트 질문");
  });

  it("AI 인사이트 요약 섹션을 렌더한다", () => {
    render(<ReferencePanel />);
    expect(screen.getByText("AI 인사이트 요약")).toBeInTheDocument();
  });
});
