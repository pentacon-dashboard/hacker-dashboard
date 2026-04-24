/**
 * Translation dictionary — ko / en 양방향.
 * 키는 dot-notation: sidebar.dashboard, kpi.totalAssets 등.
 * 누락된 키는 개발 중 경고 + fallback 으로 key 자체 표시.
 */

export type Locale = "ko" | "en";

type Dict = Record<string, { ko: string; en: string }>;

export const DICT: Dict = {
  // 공통
  "app.title": { ko: "Hacker Dashboard", en: "Hacker Dashboard" },
  "app.description": {
    ko: "임의 투자 데이터에서 자동으로 분석 뷰를 생성하는 금융 대시보드",
    en: "Auto-generated analytics dashboard for arbitrary investment data",
  },

  // Sidebar
  "sidebar.dashboard": { ko: "대시보드", en: "Dashboard" },
  "sidebar.portfolio": { ko: "포트폴리오", en: "Portfolio" },
  "sidebar.watchlist": { ko: "워치리스트", en: "Watchlist" },
  "sidebar.symbol": { ko: "종목 분석", en: "Symbol Analysis" },
  "sidebar.market": { ko: "시장 분석", en: "Market Analysis" },
  "sidebar.copilot": { ko: "코파일럿", en: "Copilot" },
  "sidebar.upload": { ko: "업로드 & 분석", en: "Upload & Analyze" },
  "sidebar.settings": { ko: "설정", en: "Settings" },
  "sidebar.collapse": { ko: "사이드바 접기", en: "Collapse sidebar" },
  "sidebar.expand": { ko: "사이드바 펼치기", en: "Expand sidebar" },
  "sidebar.marketStatus": { ko: "시장 상태", en: "Market Status" },
  "sidebar.marketOpen": { ko: "개장", en: "Open" },
  "sidebar.marketClosed": { ko: "휴장", en: "Closed" },
  "sidebar.volumeGood": { ko: "거래량 좋음", en: "Volume: Good" },

  // Header
  "header.apiOk": { ko: "API 정상", en: "API OK" },
  "header.env": { ko: "DEV", en: "DEV" },
  "header.darkMode": { ko: "다크 모드로 전환", en: "Switch to dark mode" },
  "header.lightMode": { ko: "라이트 모드로 전환", en: "Switch to light mode" },
  "header.csvUpload": { ko: "CSV 업로드", en: "CSV Upload" },
  "header.csvUploadLabel": { ko: "CSV 파일 업로드", en: "Upload CSV file" },
  "header.notifications": { ko: "알림", en: "Notifications" },
  "header.notificationsUnread": {
    ko: "{{n}}개 미확인",
    en: "{{n}} unread",
  },
  "header.markAllRead": { ko: "모두 읽음 처리", en: "Mark all as read" },
  "header.noNotifications": { ko: "알림 없음", en: "No notifications" },
  "header.dateRange": { ko: "날짜 범위", en: "Date range" },
  "header.copilotPlaceholder": {
    ko: "Copilot 질의 입력 (⌘K)",
    en: "Copilot query (⌘K)",
  },

  // Footer
  "footer.dataProviders": {
    ko: "데모용 • 가격 데이터: FinHub, IEX, Alpha Vantage, Bloomberg, Reuters",
    en: "Demo • Price data: FinHub, IEX, Alpha Vantage, Bloomberg, Reuters",
  },
  "footer.delay": {
    ko: "실시간 지연 약 20분 · 업데이트: {{time}}",
    en: "Real-time delay ~20min · Updated: {{time}}",
  },

  // Period tabs
  "period.1w": { ko: "1W", en: "1W" },
  "period.1m": { ko: "1M", en: "1M" },
  "period.3m": { ko: "3M", en: "3M" },
  "period.1y": { ko: "1Y", en: "1Y" },

  // Dashboard
  "dashboard.title": { ko: "대시보드", en: "Dashboard" },
  "dashboard.subtitle": {
    ko: "포트폴리오 전반을 한눈에 보세요.",
    en: "Portfolio overview at a glance.",
  },
  "dashboard.kpi.totalAssets": { ko: "총자산", en: "Total Assets" },
  "dashboard.kpi.dailyChange": { ko: "일간 변동", en: "Daily Change" },
  "dashboard.kpi.monthlyChange": { ko: "30일 변동", en: "30D Change" },
  "dashboard.kpi.holdings": { ko: "보유 종목", en: "Holdings" },
  "dashboard.kpi.holdingsUnit": { ko: "종목", en: "symbols" },
  "dashboard.kpi.todayPnl": { ko: "오늘 손익", en: "Today's P&L" },
  "dashboard.kpi.concentration": { ko: "집중도 리스크", en: "Concentration" },
  "dashboard.assetTrend": { ko: "자산 가치 추이", en: "Asset Value Trend" },
  "dashboard.last30Days": { ko: "최근 30일", en: "Last 30 days" },
  "dashboard.allocation": { ko: "자산 배분", en: "Allocation" },
  "dashboard.concentrationRisk": { ko: "집중도 리스크", en: "Concentration Risk" },
  "dashboard.top5Holdings": { ko: "보유 자산 TOP 5", en: "Top 5 Holdings" },
  "dashboard.dimensionAnalysis": {
    ko: "디멘션 분석 (섹터별 수익률)",
    en: "Dimension Analysis (Sector Return)",
  },
  "dashboard.marketLeaders": { ko: "시장 주도주", en: "Market Leaders" },
  "dashboard.latestNews": { ko: "최신 뉴스", en: "Latest News" },
  "dashboard.risk.low": { ko: "양호", en: "Low" },
  "dashboard.risk.medium": { ko: "보통", en: "Medium" },
  "dashboard.risk.high": { ko: "높음", en: "High" },
  "dashboard.alloc.crypto": { ko: "암호화폐", en: "Crypto" },
  "dashboard.alloc.stockUs": { ko: "해외 주식", en: "US Stocks" },
  "dashboard.alloc.stockKr": { ko: "국내 주식", en: "KR Stocks" },

  // Table headers
  "table.rank": { ko: "#", en: "#" },
  "table.symbol": { ko: "종목", en: "Symbol" },
  "table.market": { ko: "시장", en: "Market" },
  "table.avgCost": { ko: "평균가", en: "Avg Cost" },
  "table.currentPrice": { ko: "현재가", en: "Current" },
  "table.value": { ko: "평가액", en: "Value" },
  "table.return": { ko: "수익률", en: "Return" },
  "table.weight": { ko: "비중", en: "Weight" },
  "table.quantity": { ko: "수량", en: "Quantity" },

  // Portfolio
  "portfolio.title": { ko: "포트폴리오", en: "Portfolio" },
  "portfolio.subtitle": {
    ko: "자산군별 보유 현황 및 분석",
    en: "Holdings & analysis by asset class",
  },
  "portfolio.addHolding": { ko: "+ 보유자산 추가", en: "+ Add Holding" },
  "portfolio.kpi.totalValue": { ko: "총자산", en: "Total Value" },
  "portfolio.kpi.totalPnl": { ko: "총 평가손익", en: "Total P&L" },
  "portfolio.kpi.dailyChange": { ko: "일간 변동", en: "Daily Change" },
  "portfolio.kpi.holdings": { ko: "보유 종목", en: "Holdings" },
  "portfolio.kpi.winRate": { ko: "승률", en: "Win Rate" },
  "portfolio.allocation": { ko: "자산 구성", en: "Allocation" },
  "portfolio.holdingsOverview": { ko: "자산 한눈에", en: "Holdings Overview" },
  "portfolio.currencyFilter": { ko: "통화 필터", en: "Currency filter" },
  "portfolio.filterAll": { ko: "전체", en: "All" },
  "portfolio.sortBy": { ko: "정렬", en: "Sort" },
  "portfolio.sortByValue": { ko: "평가금액", en: "Value" },
  "portfolio.sortByReturn": { ko: "손익률", en: "Return" },
  "portfolio.sectorHeatmap": { ko: "섹터별 수익률 히트맵", en: "Sector Return Heatmap" },
  "portfolio.monthlyCalendar": { ko: "월간 수익률 달력", en: "Monthly Return Calendar" },
  "portfolio.aiInsight": { ko: "AI 인사이트", en: "AI Insight" },
  "portfolio.totalReturn": { ko: "총 손익률", en: "Total Return" },
  "portfolio.dialog.search": { ko: "종목 검색", en: "Search symbol" },
  "portfolio.dialog.currency": { ko: "통화", en: "Currency" },
  "portfolio.dialog.cancel": { ko: "취소", en: "Cancel" },
  "portfolio.dialog.add": { ko: "추가", en: "Add" },

  // Watchlist
  "watchlist.title": { ko: "워치리스트", en: "Watchlist" },
  "watchlist.subtitle": { ko: "관심 종목 및 알림 관리", en: "Watchlist & alerts" },
  "watchlist.alertSettings": { ko: "알림 설정", en: "Alert Settings" },
  "watchlist.popularTop5": { ko: "인기 TOP 5", en: "Popular TOP 5" },
  "watchlist.gainersLosers": { ko: "상승/하락 TOP", en: "Gainers/Losers" },
  "watchlist.customAlert": { ko: "맞춤 알림 설정", en: "Custom Alert" },
  "watchlist.recentTrades": { ko: "최근 체결", en: "Recent Trades" },
  "watchlist.noTrades": { ko: "최근 체결 내역 없음", en: "No recent trades" },
  "watchlist.addAlert": { ko: "+ 추가", en: "+ Add" },
  "watchlist.noAlerts": { ko: "알림 없음", en: "No alerts" },
  "watchlist.direction.above": { ko: "초과", en: "Above" },
  "watchlist.direction.below": { ko: "이하", en: "Below" },
  "watchlist.threshold": { ko: "임계값", en: "Threshold" },

  // Symbol
  "symbol.basicInfo": { ko: "기본 정보", en: "Basic Info" },
  "symbol.technicalIndicators": { ko: "기술 지표", en: "Technical Indicators" },
  "symbol.keyIssues": { ko: "주요 이슈", en: "Key Issues" },
  "symbol.relatedNews": { ko: "관련 뉴스", en: "Related News" },
  "symbol.aiAnalysis": { ko: "AI 분석", en: "AI Analysis" },
  "symbol.reflectPortfolio": {
    ko: "내 포트폴리오 반영",
    en: "Reflect my portfolio",
  },
  "symbol.routerEvidence": { ko: "Router 분석 근거", en: "Router Evidence" },
  "symbol.viewEvidence": { ko: "근거 보기", en: "View evidence" },
  "symbol.metric.changePct": { ko: "등락율", en: "Change %" },
  "symbol.metric.avgCost": { ko: "평단가", en: "Avg Cost" },
  "symbol.metric.volume": { ko: "거래량", en: "Volume" },
  "symbol.metric.signal": { ko: "시그널", en: "Signal" },
  "symbol.signal.buy": { ko: "매수", en: "Buy" },
  "symbol.signal.sell": { ko: "매도", en: "Sell" },
  "symbol.signal.hold": { ko: "보유", en: "Hold" },
  "symbol.tf.1m": { ko: "1분", en: "1m" },
  "symbol.tf.5m": { ko: "5분", en: "5m" },
  "symbol.tf.15m": { ko: "15분", en: "15m" },
  "symbol.tf.60m": { ko: "60분", en: "60m" },
  "symbol.tf.day": { ko: "일", en: "Day" },
  "symbol.tf.week": { ko: "주", en: "Week" },
  "symbol.tf.month": { ko: "월", en: "Month" },

  // Market
  "market.title": { ko: "시장 분석", en: "Market Analysis" },
  "market.subtitle": {
    ko: "글로벌 지수, 섹터, 원자재 및 세계 히트맵을 한눈에 확인합니다.",
    en: "Global indices, sectors, commodities and world heatmap at a glance.",
  },
  "market.globalTrend": { ko: "글로벌 시장 동향", en: "Global Trend" },
  "market.regionalReturn": { ko: "지역별 등락률", en: "Regional Return" },
  "market.sectorReturn": { ko: "섹터별 등락률", en: "Sector Return" },
  "market.commodities": { ko: "원자재", en: "Commodities" },
  "market.mainNews": { ko: "주요 뉴스", en: "Main News" },
  "market.legend.down": { ko: "하락", en: "Down" },
  "market.legend.up": { ko: "상승", en: "Up" },

  // Copilot
  "copilot.title": { ko: "코파일럿", en: "Copilot" },
  "copilot.subtitle": {
    ko: "포트폴리오 분석·질의응답을 AI 코파일럿에 맡기세요. 세션을 저장하고 이어서 대화할 수 있습니다.",
    en: "Delegate analysis & Q&A to the AI Copilot. Sessions persist and resume.",
  },
  "copilot.newChat": { ko: "새 대화 시작", en: "New Chat" },
  "copilot.noSessions": { ko: "대화 기록이 없습니다", en: "No conversation history" },
  "copilot.inputPlaceholder": {
    ko: "포트폴리오에 대해 질문하세요...",
    en: "Ask about your portfolio...",
  },
  "copilot.portfolioSummary": { ko: "포트폴리오 요약", en: "Portfolio Summary" },
  "copilot.aiInsightSummary": { ko: "AI 인사이트 요약", en: "AI Insight" },
  "copilot.quickQuestions": { ko: "추천 질문", en: "Suggested Questions" },
  "copilot.startGuide": { ko: "새 대화 시작 가이드", en: "How to Start" },

  // Upload
  "upload.title": { ko: "업로드 & 분석", en: "Upload & Analyze" },
  "upload.subtitle": {
    ko: "CSV 파일을 업로드하여 포트폴리오를 자동 분석합니다.",
    en: "Upload CSV to auto-analyze your portfolio.",
  },
  "upload.section.dropzone": { ko: "1. 파일 업로드", en: "1. File Upload" },
  "upload.section.validation": { ko: "2. 데이터 검증 상태", en: "2. Validation Status" },
  "upload.section.preview": {
    ko: "3. 데이터 미리보기 (상위 5행)",
    en: "3. Preview (top 5 rows)",
  },
  "upload.section.config": { ko: "4. 분석 설정", en: "4. Analysis Config" },
  "upload.section.progress": { ko: "5. 분석 진행 상태", en: "5. Analysis Progress" },
  "upload.templateDownload": {
    ko: "CSV 템플릿 다운로드",
    en: "Download CSV Template",
  },
  "upload.faq": { ko: "자주 묻는 질문", en: "FAQ" },

  // Settings
  "settings.title": { ko: "설정", en: "Settings" },
  "settings.subtitle": {
    ko: "개인 설정을 관리합니다. 테마, 알림, 데이터 옵션을 변경할 수 있습니다.",
    en: "Manage personal settings. Change theme, notifications, data options.",
  },
  "settings.general.title": { ko: "기본 설정", en: "General" },
  "settings.general.desc": {
    ko: "이름, 이메일, 언어, 시간대를 설정합니다",
    en: "Name, email, language, timezone",
  },
  "settings.general.name": { ko: "이름", en: "Name" },
  "settings.general.email": { ko: "이메일", en: "Email" },
  "settings.general.language": { ko: "언어", en: "Language" },
  "settings.general.timezone": { ko: "시간대", en: "Timezone" },
  "settings.lang.ko": { ko: "한국어", en: "Korean" },
  "settings.lang.en": { ko: "English", en: "English" },
  "settings.notifications.title": { ko: "알림 설정", en: "Notifications" },
  "settings.notifications.desc": {
    ko: "알림 채널 및 임계값을 설정합니다",
    en: "Notification channels & thresholds",
  },
  "settings.notifications.email": { ko: "이메일 알림", en: "Email Alerts" },
  "settings.notifications.emailDesc": {
    ko: "중요 포트폴리오 변동 시 이메일 발송",
    en: "Send email on significant changes",
  },
  "settings.notifications.push": { ko: "푸시 알림", en: "Push Alerts" },
  "settings.notifications.pushDesc": {
    ko: "브라우저 푸시 알림 활성화",
    en: "Enable browser push notifications",
  },
  "settings.notifications.daily": { ko: "일일 다이제스트", en: "Daily Digest" },
  "settings.notifications.dailyDesc": {
    ko: "매일 오전 8시 일간 요약 발송",
    en: "Send daily summary at 8am",
  },
  "settings.notifications.threshold": {
    ko: "가격 알림 임계값 (%)",
    en: "Price Alert Threshold (%)",
  },
  "settings.notifications.thresholdHint": {
    ko: "±{{n}}% 변동 시 알림",
    en: "Alert on ±{{n}}% change",
  },
  "settings.theme.title": { ko: "테마 설정", en: "Theme" },
  "settings.theme.desc": {
    ko: "다크/라이트 모드 및 색상 팔레트",
    en: "Dark/light mode & color palette",
  },
  "settings.theme.light": { ko: "라이트", en: "Light" },
  "settings.theme.dark": { ko: "다크", en: "Dark" },
  "settings.theme.system": { ko: "시스템", en: "System" },
  "settings.theme.colorTheme": { ko: "색상 테마", en: "Color Theme" },
  "settings.theme.violet": { ko: "보라", en: "Violet" },
  "settings.theme.cyan": { ko: "청록", en: "Cyan" },
  "settings.theme.blue": { ko: "파랑", en: "Blue" },
  "settings.theme.orange": { ko: "주황", en: "Orange" },
  "settings.theme.rose": { ko: "분홍", en: "Rose" },
  "settings.data.title": { ko: "데이터 설정", en: "Data" },
  "settings.data.desc": {
    ko: "새로고침 주기 및 캐시 설정",
    en: "Refresh interval & cache",
  },
  "settings.data.refreshInterval": {
    ko: "데이터 새로고침 주기",
    en: "Refresh Interval",
  },
  "settings.data.autoRefresh": { ko: "자동 새로고침", en: "Auto-refresh" },
  "settings.data.autoRefreshDesc": {
    ko: "백그라운드 데이터 업데이트",
    en: "Update data in background",
  },
  "settings.data.autoBackup": { ko: "자동 백업", en: "Auto-backup" },
  "settings.data.autoBackupDesc": {
    ko: "포트폴리오 데이터 주간 백업",
    en: "Weekly portfolio backup",
  },
  "settings.data.cacheSize": { ko: "캐시 크기", en: "Cache Size" },
  "settings.connected.title": { ko: "연결된 계정", en: "Connected Accounts" },
  "settings.connected.desc": {
    ko: "소셜 계정 연결 관리 (데모 모드 — 실 OAuth 없음)",
    en: "Social account connection (demo mode — no real OAuth)",
  },
  "settings.connected.connected": { ko: "연결됨", en: "Connected" },
  "settings.connected.disconnected": { ko: "미연결", en: "Disconnected" },
  "settings.connected.connect": { ko: "연결", en: "Connect" },
  "settings.connected.disconnect": { ko: "해제", en: "Disconnect" },
  "settings.system.title": { ko: "시스템 정보", en: "System Info" },
  "settings.system.version": { ko: "버전", en: "Version" },
  "settings.system.buildTime": { ko: "빌드 시간", en: "Build Time" },
  "settings.system.cacheSize": { ko: "캐시 크기", en: "Cache Size" },
  "settings.system.apiStatus": { ko: "API 상태", en: "API Status" },
  "settings.system.healthy": { ko: "정상", en: "Healthy" },
  "settings.system.degraded": { ko: "성능 저하", en: "Degraded" },
  "settings.system.error": { ko: "오류", en: "Error" },
  "settings.system.clearCache": { ko: "캐시 비우기", en: "Clear Cache" },
  "settings.system.cacheCleared": { ko: "캐시 삭제 완료", en: "Cache cleared" },

  // User card
  "user.name": { ko: "Demo User", en: "Demo User" },

  // Common
  "common.loading": { ko: "로딩 중...", en: "Loading..." },
  "common.error": { ko: "오류 발생", en: "Error" },
  "common.empty": { ko: "데이터 없음", en: "No data" },
  "common.retry": { ko: "다시 시도", en: "Retry" },
  "common.refresh": { ko: "새로고침", en: "Refresh" },
  "common.close": { ko: "닫기", en: "Close" },
  "common.demo": { ko: "DEMO", en: "DEMO" },
};

export function translate(key: string, locale: Locale, vars?: Record<string, string | number>): string {
  const entry = DICT[key];
  if (!entry) {
    if (typeof window !== "undefined" && process.env.NODE_ENV !== "production") {
      console.warn(`[i18n] missing translation key: ${key}`);
    }
    return key;
  }
  let text = entry[locale] ?? entry.ko;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(new RegExp(`\\{\\{${k}\\}\\}`, "g"), String(v));
    }
  }
  return text;
}
