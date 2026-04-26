/**
 * copilot-sessions.ts — MSW handlers for /copilot/sessions
 *
 * C-5 코파일럿 풀페이지 세션 히스토리 픽스처.
 * BE γ-sprint 완료 후 실 엔드포인트로 swap.
 */
import { http, HttpResponse } from "msw";

export const COPILOT_SESSIONS = [
  {
    session_id: "sess-001",
    title: "포트폴리오 리밸런싱 분석",
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString(),
    turn_count: 5,
    last_query: "현재 포트폴리오 리밸런싱이 필요한가요?",
  },
  {
    session_id: "sess-002",
    title: "NVDA 매수 타이밍 질문",
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    turn_count: 3,
    last_query: "NVDA 지금 매수해도 될까요?",
  },
  {
    session_id: "sess-003",
    title: "비트코인 변동성 분석",
    created_at: new Date(Date.now() - 259200000).toISOString(),
    updated_at: new Date(Date.now() - 172800000).toISOString(),
    turn_count: 7,
    last_query: "비트코인 최근 변동성 분석 해주세요",
  },
  {
    session_id: "sess-004",
    title: "삼성전자 배당 전략",
    created_at: new Date(Date.now() - 345600000).toISOString(),
    updated_at: new Date(Date.now() - 259200000).toISOString(),
    turn_count: 2,
    last_query: "삼성전자 배당 전략 추천해주세요",
  },
  {
    session_id: "sess-005",
    title: "환율 리스크 헷지 방법",
    created_at: new Date(Date.now() - 432000000).toISOString(),
    updated_at: new Date(Date.now() - 345600000).toISOString(),
    turn_count: 4,
    last_query: "USD/KRW 환율 리스크 어떻게 관리하나요?",
  },
];

export const COPILOT_SESSION_DETAIL = {
  session_id: "sess-001",
  title: "포트폴리오 리밸런싱 분석",
  turns: [
    {
      turn_id: "turn-001-1",
      query: "현재 포트폴리오 리밸런싱이 필요한가요?",
      plan_id: "plan-001",
      analyzer: "portfolio_analyzer",
      analyzer_reason: "포트폴리오 비중·수익률 분석 요청 감지",
      final_card: {
        type: "text",
        content:
          "현재 포트폴리오 분석 결과, 기술주 비중이 61%로 과대 집중되어 있습니다. 목표 배분(기술 40%, 헬스케어 20%, 채권 20%, 기타 20%) 대비 리밸런싱이 권장됩니다.",
      },
      citations: [],
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
  ],
};

export const PORTFOLIO_SUMMARY_FOR_COPILOT = {
  total_value_krw: "18760000.00",
  total_pnl_pct: "4.77",
  daily_change_pct: "2.04",
  sharpe_ratio: 0.62,
  win_rate_pct: 68,
  beta: -8.35,
  alpha: 12.45,
};

export const AI_INSIGHTS = [
  { id: "ins1", icon: "TrendingUp", label: "기술주 집중 주의", severity: "warning" },
  { id: "ins2", icon: "Shield", label: "변동성 관리 양호", severity: "success" },
  { id: "ins3", icon: "Target", label: "목표 수익률 근접", severity: "info" },
];

export const QUICK_QUESTIONS = [
  "현재 포트폴리오 리스크 수준은?",
  "다음 달 수익률 예측은?",
  "리밸런싱 추천 종목은?",
  "환율 리스크 영향은?",
];

export const copilotSessionHandlers = [
  // GET /copilot/sessions
  http.get("http://localhost:8000/copilot/sessions", () =>
    HttpResponse.json(COPILOT_SESSIONS),
  ),

  // GET /copilot/sessions/:sessionId
  http.get("http://localhost:8000/copilot/sessions/:sessionId", () =>
    HttpResponse.json(COPILOT_SESSION_DETAIL),
  ),
];
