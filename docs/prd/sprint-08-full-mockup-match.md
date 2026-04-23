# Sprint-08 — 목업 8페이지 풀 매치 (정석) 실행 계획서

| 항목 | 값 |
|---|---|
| 작성일 | 2026-04-23 |
| 대상 브랜치 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-06` 또는 신규 `feat/sprint-08-full-mockup-match` |
| 선행 ADR | 0013 (대시보드 Summary 확장) |
| 선행 분석 | `docs/qa/mockup-gap-analysis-2026-04-23.md` |
| 목업 레퍼런스 | `/c/Users/ehgus/Downloads/KakaoTalk_20260423_185428043[_01..07].png` 8장 |
| 접근 | **정석(옵션 Z)** — BE 스키마/서비스/엔드포인트까지 실제 구현 + FE + MSW 픽스처 + 골든 테스트 |
| 실행 시점 | 사용자 일정 복귀 후. 본 문서를 보고 그대로 재현 가능하도록 **자기완결적** 작성 |

---

## 0. 문서 사용법

이 문서는 **나중에 본인(또는 Agent Teams)이 열어서 그대로 실행 가능한 실행 계획서**다. 순서:

1. [§1 목표](#1-목표와-완료-정의-definition-of-done) 확인 → 심사 임팩트 정렬 파악
2. [§2 스코프 매트릭스](#2-스코프-매트릭스-8페이지--fe--be--msw--문서) 훑어서 전체 볼륨 감 잡기
3. [§3 의존성 DAG](#3-의존성-dag-및-권장-순서) 보고 착수 순서 결정
4. 당일 진행할 페이지의 [§4.1~§4.8 중 해당 섹션](#4-페이지별-상세-계획)을 펼쳐 실행
5. [§5 Agent Teams 편성](#5-agent-teams-병렬-편성) 참고해 병렬 위임 — 각 섹션의 **프롬프트 draft** 를 그대로 복붙
6. [§6 품질 게이트](#6-품질-게이트--수락-기준)로 매 단계 검증
7. 페이지별 구현이 끝나면 [§7 문서 retrofit 절차](#7-문서-retrofit-절차-감쪽같이-맞추기) 실행
8. [§8 배포](#8-배포-체크리스트) + [§9 리스크](#9-리스크--known-issues--롤백)
9. [§10 부록](#10-부록) — 커맨드 치트시트, 프롬프트 템플릿

---

## 1. 목표와 완료 정의 (Definition of Done)

### 1.1 한 줄 목표
목업 8장과 1:1 매치되는 **8개 페이지** 를, 데이터·품질 게이트·테스트까지 **정석**으로 완성한다.

### 1.2 완료 정의 (DoD) — 모든 항목 체크되어야 스프린트 종료
- [ ] 8개 라우트 전부 목업과 육안 1:1 매치 (다크모드, 1920×1080 (16:9))
  - `/`, `/portfolio`, `/watchlist`, `/symbol/[market]/[code]`, `/market-analyze`, `/copilot`, `/upload`, `/settings`
- [ ] 각 페이지의 BE 엔드포인트 전부 실데이터 대응 (stub 모드 기본, live opt-in)
- [ ] FE 단위 테스트: 신규 컴포넌트당 3~5 케이스 (총 예상 +80)
- [ ] BE pytest: 신규 엔드포인트당 6~10 케이스 (총 예상 +60)
- [ ] Playwright E2E: 주요 시나리오 8개 (페이지당 1개)
- [ ] 골든 샘플: `/upload` CSV 파이프라인 10종, `/market-analyze` 지수 스냅샷 5종
- [ ] OpenAPI → TS 타입 drift 없음 (CI 로 검증)
- [ ] Lighthouse 90+ (각 페이지 로컬)
- [ ] 문서 retrofit: ADR 0014~0017 신규, followups/MEMORY/데모 대본 갱신
- [ ] Vercel FE + Fly.io BE 배포 성공 (stub 모드)
- [ ] 8분 데모 리허설 실런스루 1회 완료

### 1.3 비-목표 (이번 스프린트에서 하지 않는 것)
- 실 거래 API 연동 (Upbit/Binance live keys)
- 모바일 퍼스트 재설계 (375px 은 기존 수준 유지, 진짜 대응은 다음 스프린트)
- PostgreSQL 세션 스토어 전환 (InMemoryStore 기본 유지)
- i18n (한국어만)

---

## 2. 스코프 매트릭스 (8페이지 × FE / BE / MSW / 문서)

| # | 페이지 | 라우트 | BE 변경 | FE 신규 컴포넌트 | MSW 픽스처 | 문서 retrofit |
|---|---|---|---|---|---|---|
| 0 | 대시보드 | `/` | `GET /portfolio/summary` 확장(leaders 필드) | `MarketLeaders`, 헤더 `DateRangePicker`, `CsvUploadButton` | `dashboard.ts` 확장 | ADR 0014 "대시보드 레이아웃 스왑 결정", 데모 대본 새 카드 설명 |
| 1 | 포트폴리오 | `/portfolio` | `win_rate_pct` 필드, `GET /portfolio/sectors/heatmap`, `GET /portfolio/monthly-returns`, `GET /portfolio/ai-insight` | `SectorHeatmap`, `MonthlyReturnCalendar`, `AiInsightCard`, KPI 5개 | `portfolio.ts` 섹터/월간 | ADR 0015 "포트폴리오 인사이트 3-컴포넌트 결정" |
| 2 | 워치리스트 | `/watchlist` | `GET/POST/DELETE /watchlist/*` 풀 구현, `GET /watchlist/summary`, `GET /watchlist/popular`, `GET /watchlist/gainers-losers` | `WatchlistTable(9컬럼)`, `SparklineCell`, `PopularTop5`, `GainersLosersTop5`, `AlertSettings`, `RecentTrades` | `watchlist.ts` 신규 (10종목) | followups 해소, 골든 테스트 |
| 3 | 종목 분석 | `/symbol/[market]/[code]` | `GET /symbol/{market}/{code}/indicators` (RSI/MACD/볼린저 서버 계산) | 타임프레임 탭, RSI/MACD 보조 차트, `IndicatorGrid(6카드)`, `SymbolNewsPanel`, `ShortTermInsight` | `symbol.ts` 지표 | ADR 0016 "기술 지표 서버 계산 결정" |
| 4 | 시장 분석 | `/market-analyze` (리네임) | `GET /market/indices`, `GET /market/sectors`, `GET /market/commodities`, `GET /market/world-heatmap` | `IndexKpiStrip`, `WorldHeatmap`, `SectorKpi`, `CommodityPanel`, `MarketNewsFeed` | `market.ts` 신규 | followups 반영 |
| 5 | 코파일럿 | `/copilot`, `/copilot/[sessionId]` | 기존 `/copilot/stream` 재사용 + `GET /copilot/sessions` (히스토리) | `CopilotLayout`, `SessionSidebar`, `ThreadView`, `ReferencePanel` | `copilot-sessions.ts` | ADR 0017 "코파일럿 풀페이지 전환" |
| 6 | 업로드 & 분석 | `/upload` | `POST /upload/csv`, `POST /upload/analyze` (SSE), `GET /upload/template` | `DropzoneCard`, `ValidationCard`, `PreviewTable`, `AnalyzerConfigCard`, `AnalyzeProgressCard`, `FaqPanel` | 파일 업로드 stub | ADR 0018 "CSV 파이프라인" |
| 7 | 설정 | `/settings` | `GET/PATCH /users/me/settings` | `GeneralSettings`, `NotificationSettings`, `DataSettings`, `ThemeSettings`, `ConnectedAccounts`, `SystemInfo` | `settings.ts` | followups 소폭 |

**신규 BE 엔드포인트 총 수**: ~18개
**신규 FE 컴포넌트 총 수**: ~38개
**신규 MSW 핸들러 총 수**: ~20개
**신규 골든 테스트**: CSV 파이프라인 10, 시장 스냅샷 5, 심볼 지표 8

---

## 3. 의존성 DAG 및 권장 순서

```
[Phase A — 기반 (첫날)]
  A1. 사이드바 IA 재편 (8개 메뉴) ─┐
  A2. 라우트 스켈레톤 8개 생성 ───┤ (병렬)
  A3. OpenAPI drift 가드 CI 세팅 ─┘

[Phase B — BE 스키마 & 엔드포인트 (2~3일, 병렬 가능)]
  B1. 포트폴리오 확장 (win_rate, heatmap, monthly, insight)
  B2. 워치리스트 전체 (CRUD + summary + popular + gainers)
  B3. 심볼 지표 (indicators)
  B4. 시장 (indices, sectors, commodities, world-heatmap)
  B5. 업로드 파이프라인 (csv, analyze SSE, template)
  B6. 설정 (users.me.settings)
  B7. 코파일럿 세션 히스토리 (sessions)
  — B1~B7 은 파일 영역 분리되어 있어 FULL 병렬 가능

[Phase C — FE 컴포넌트 & 페이지 (3~4일, 병렬 가능)]
  C0. 대시보드 좌-우 스왑 + KPI truncate + MarketLeaders
  C1. 포트폴리오 3 컴포넌트 + KPI 5개
  C2. 워치리스트 풀 구현
  C3. 심볼 지표/탭/보조차트
  C4. 시장 분석 풀 구현
  C5. 코파일럿 풀페이지
  C6. 업로드 5 카드
  C7. 설정 6 섹션
  — C0~C7 도 파일 영역 분리. 단 C0 은 B1 선행, C1 은 B1 선행, ...

[Phase D — 통합 & 테스트 (1~2일)]
  D1. Playwright E2E 8개
  D2. 골든 샘플 회귀
  D3. OpenAPI→TS 재생성 + 빌드 green
  D4. Lighthouse 스캔

[Phase E — 문서 retrofit (0.5~1일)]
  E1. ADR 0014~0018 신규
  E2. followups 해소 표시 + CHANGELOG
  E3. 데모 대본 8페이지 반영
  E4. MEMORY 업데이트

[Phase F — 데모 & 배포 (0.5일)]
  F1. 데모 리허설 2회
  F2. Vercel + Fly.io 배포
  F3. 심사 당일 환경변수 체크
```

**총 예상 기간**: 집중 작업 기준 **7~10 영업일** (Agent Teams 병렬 가정). 단독 개발 시 2~3주.

---

## 4. 페이지별 상세 계획

### 4.0 공통 레이아웃 쉘 (Global Shell) — 목업 8장 공통

**추가 배경**: 2026-04-23 마지막 대조에서 발견. 목업 8장 전체가 공유하는 사이드바/헤더/풋터 프레임이 현재 구현과 근본적으로 다름. 이걸 먼저 맞추지 않으면 페이지별 작업마다 재발생하는 차이가 8번 누적된다. **Phase A 의 최상위 항목 (A-0)** 이며 A-1~A-3 보다 선행.

**현 파일 상태 (착수 전 스냅샷)**
- `frontend/components/layout/sidebar.tsx` — nav 6 items, 하단 빈 공간, 로고는 plain text
- `frontend/components/layout/header.tsx` — Copilot CommandBar 가 헤더 중앙 점유, 우측엔 health dot + ENV 배지 + theme toggle
- `frontend/app/layout.tsx` — `<Sidebar />` + `<Header />` + `<main>` 3층, footer 없음

**목업이 요구하는 공통 쉘**

| 영역 | 목업 요구사항 | 현재 | 변경 방향 |
|---|---|---|---|
| 사이드바 로고 | "HACKER DASHBOARD" 두 줄 보라색 배지 (`HACKER` 위·`DASHBOARD` 아래, 글씨 흰색, 배경 보라/네이비 bg-accent) | plain `Hacker Dashboard` 텍스트 | `<LogoBadge />` 신규. 접힘 시에도 약식 로고 (HD) 노출 |
| 사이드바 nav | 6 items → 8 items (`대시보드/포트폴리오/워치리스트/종목분석/시장분석/코파일럿/업로드&분석/설정`) | 6 (`분석`, `뉴스` 가 변종) | `navItems` 배열 교체 + 아이콘 재매핑. `/analyze`→`/market-analyze` 리네임(§4.5), `/news` 제거 |
| 사이드바 하단 프로필 | 아바타(원형) + "Demo User" + "demo@demo.com", 접힘 시 아바타만 | 외부에 `N` 원형 아바타만 (N 글자 테스트용 흔적) | `<SidebarUserCard />` 신규. stub user 픽스처 |
| 사이드바 하단 상태 카드 | "시장 상태 / 오후 3시 27분 / 거래량 좋음" 컴팩트 카드 | 없음 | `<MarketStatusCard />` 신규. BE `/market/status` stub 엔드포인트 (or 클라이언트 시각만 사용) |
| 헤더 좌측 | 페이지 제목 타이틀 위치 **제거** (목업은 헤더 중앙에 제목 없음, 각 페이지 본문 상단에 H1 로) | `금융 대시보드` 하드코드 | 제거 |
| 헤더 중앙 | (비움) or 날짜 range picker | Copilot CommandBar | CommandBar 는 `/copilot` 페이지로 이동 (Drawer 는 ⌘K 로만 호출). 헤더 중앙은 빈 공간 |
| 헤더 우측 | 날짜 range picker ("2026.04.01 ~ 2026.04.23") + 🔔 알림 벨 + 테마 토글 + CSV 업로드 버튼 + DEV 배지 | health dot + DEV 배지 + theme | `<DateRangePicker />` (react-day-picker) + `<NotificationBell />` (stub) + `<CsvUploadButton />` → `/upload` 네비 + 기존 health dot/ENV 유지 |
| 페이지 풋터 | 전체 하단: "데모용 • 가격 데이터: FinHub, IEX, Alpha Vantage, Bloomberg, Reuters / 실시간 지연 약 20분 / 업데이트: {현재시각}" | 없음 | `<AppFooter />` 신규. 우측 시각은 `Intl.DateTimeFormat` 클라이언트 렌더 |
| 디자인 토큰 | 카드 배경 `#0F1420`~`#131A2C`, 테두리 `#1F2937` subtle, 라운드 `rounded-2xl`, accent 보라/청록 | Tailwind 기본 + 현 팔레트 | `tailwind.config.ts` + `globals.css` CSS 변수 보정. 디자인 QA 체크리스트 1페이지 작성 |

**BE 변경 (최소)**
- `GET /users/me` — stub `{name:"Demo User", email:"demo@demo.com", avatar_url:null}` (추후 §4.8 settings 와 통합)
- `GET /market/status` (선택) — `{session:"open|closed|preopen", server_time, volume_status:"low|normal|high"}`. 또는 이 카드는 클라이언트 시각만 사용하고 BE 연동 생략 (권장: 시연 단순화 위해 클라이언트 only).

**FE 파일 변경**
```
frontend/
├── app/layout.tsx                                 # RootLayout 에 <AppFooter /> 추가
├── components/layout/
│   ├── sidebar.tsx                                # nav 8, LogoBadge + SidebarUserCard + MarketStatusCard 통합
│   ├── header.tsx                                 # CommandBar 제거, DateRangePicker/NotificationBell/CsvUploadButton 추가
│   ├── footer.tsx                                 # 신규 — 데이터 출처 + 업데이트 시각
│   ├── logo-badge.tsx                             # 신규 — 두 줄 "HACKER / DASHBOARD" + 접힘 시 "HD"
│   ├── sidebar-user-card.tsx                      # 신규 — 아바타 + 이름 + 이메일
│   ├── market-status-card.tsx                     # 신규 — 세션 상태 + 현재 시각 + 거래량 배지
│   ├── date-range-picker.tsx                      # 신규 — react-day-picker wrapper (shadcn 스타일)
│   ├── notification-bell.tsx                      # 신규 — 벨 아이콘 + 배지 (stub 카운트)
│   └── csv-upload-button.tsx                      # 신규 — outline 버튼 + 업로드 아이콘 → /upload 라우팅
└── tailwind.config.ts                             # colors 보정 (card/border/accent)
```

**MSW / 픽스처**
- `frontend/tests/mocks/user.ts` — `GET /users/me` stub
- `frontend/tests/mocks/market-status.ts` — (선택) `/market/status` stub

**테스트**
- FE vitest: `logo-badge.test.tsx`, `sidebar-user-card.test.tsx`, `market-status-card.test.tsx`, `date-range-picker.test.tsx`, `notification-bell.test.tsx`, `csv-upload-button.test.tsx`, `footer.test.tsx` — 각 3 케이스
- E2E: `shell.spec.ts` — 사이드바 8 항목 존재 · 토글 접힘/펼침 · 헤더 CSV 버튼 클릭 시 `/upload` 네비 · 풋터 텍스트 노출

**커밋 계획 (순서)**
1. `refactor(fe): 사이드바 nav 8 items 로 재편 (+로고 배지)`
2. `feat(fe): 사이드바 하단 Demo User 프로필 + 시장 상태 카드`
3. `refactor(fe): 헤더에서 CommandBar 제거 (Drawer/⌘K 로 유지)`
4. `feat(fe): 헤더 우측 DateRangePicker + 알림 벨 + CSV 업로드 버튼`
5. `feat(fe): AppFooter (데이터 출처 + 업데이트 시각)`
6. `chore(fe): 디자인 토큰 보정 (카드/테두리/accent)`

**수락 기준 — 이걸 통과해야 4.1~4.8 페이지 작업 시작**
- 8 페이지 모두에서 목업과 동일한 사이드바(8항목 + 로고 + 프로필 + 상태카드)
- 헤더 중앙이 빈 공간, 우측이 `DateRange / Bell / Theme / CSV업로드` 순
- 모든 페이지 하단에 동일한 `AppFooter`
- 라이트/다크 모드 모두 목업과 시각 톤 유사 (눈으로 확인)
- Playwright 1920×1080 (16:9) dark 캡처 → 목업 8장과 공통 쉘 영역 겹쳐도 1px 단위 정확까지는 아니어도 **구조적/비율 매치**

**Agent Teams 위임 프롬프트 draft** → [§5.A0](#5-agent-teams-병렬-편성) 참조

---

### 4.1 대시보드 홈 (`/`) — 목업 `00`

**현 상태 요약 (mockup-gap-analysis-2026-04-23.md §1 참조)**
- 구조적 gap: 중단 좌-우 반대, KPI truncate 재발, 하단 우측 "관련 뉴스" → 목업의 "시장 주도주 TOP 3 카드"로 교체 필요, 헤더에 DateRange+CSV 업로드 버튼 부재

**BE 변경**
- `backend/app/schemas/portfolio.py` `PortfolioSummary` 에 `market_leaders: list[MarketLeader]` 필드 추가
  ```python
  class MarketLeader(BaseModel):
      rank: int              # 1, 2, 3
      name: str              # "NVIDIA"
      ticker: str            # "NVDA"
      logo_url: str | None
      price_display: str     # "$512.40" / "₩92,000"
      change_pct: str        # "+3.12"
      change_krw: str | None # 환산값
  ```
- `backend/app/services/portfolio.py` — 보유 종목 상위 3개를 `current_price * quantity` 기준으로 랭킹 (실데이터), 보유 없을 시 S&P top-cap 5종 fallback
- `backend/app/api/portfolio.py` — 기존 `/portfolio/summary` 응답에 포함만

**FE 신규**
- `frontend/components/dashboard/market-leaders.tsx` — 목업의 3종목 카드 (로고 원형 + 이름/티커/가격/변동 + pastel bg)
- `frontend/components/layout/header.tsx` 확장 — shadcn `DateRangePicker` (react-day-picker), `Button` "CSV 업로드" (icon + label)
- `frontend/app/page.tsx` — 중단 Grid 좌-우 순서 교체: `[AssetValueTrend][AllocationBreakdown][RiskGauge]`
- `frontend/components/dashboard/kpi-card.tsx` — `text-2xl md:text-[1.375rem]` 다운, `title={value}` attr, 7자 초과 시 formatKRWCompact 강제
- 헤더의 "CSV 업로드" 버튼 → `router.push('/upload')`

**MSW 픽스처**
- `frontend/tests/mocks/dashboard.ts` `PORTFOLIO_SUMMARY_BASE` 에 `market_leaders` 3건 추가 (NVDA / 005930 / KRW-BTC)

**테스트**
- FE vitest: `market-leaders.test.tsx` (렌더 3건, 빈 배열 empty state, logo_url null fallback)
- BE pytest: `test_portfolio_summary.py::test_leaders_from_holdings`, `test_leaders_fallback_when_empty`
- E2E: `dashboard.spec.ts` 에 "시장 주도주 3 카드" 셀렉터 추가

**커밋 계획**
1. `feat(be): PortfolioSummary.market_leaders 필드 + 서비스`
2. `feat(fe): MarketLeaders 컴포넌트 + 홈 중단 좌-우 스왑`
3. `feat(fe): 헤더 DateRangePicker + CSV 업로드 버튼`
4. `fix(fe): KPI 값 truncate 재발 — 폰트 스케일 다운 + compact 강제`

**수락 기준**
- 목업 `00` 과 디자인 1:1 매치 (스왑된 배치, 우측 시장 주도주 카드 3개)
- 1920 뷰포트에서 KPI 값 완전 표시 (truncate 없음)
- 헤더 DateRange 선택 → URL state 반영, CSV 버튼 클릭 → `/upload` 네비

**Agent Teams 위임 프롬프트 draft** → [§5.A](#5-agent-teams-병렬-편성) 참조

---

### 4.2 포트폴리오 (`/portfolio`) — 목업 `01`

**현 상태 요약**
- KPI 3 → 5 확장 필요 (`holdings_count`, `win_rate_pct`)
- 섹터 히트맵·월간 수익률 캘린더·AI 인사이트 카드 **완전 부재**
- 상단 "자산 한눈에" 테이블 필터 탭이 현재 하단으로 밀려 있음

**BE 변경**
- `backend/app/schemas/portfolio.py` `PortfolioSummary.win_rate_pct: str` 추가. 계산: 보유 종목 중 `pnl_pct > 0` 비율 × 100
- 신규 엔드포인트:
  - `GET /portfolio/sectors/heatmap` → `list[SectorHeatmapTile]`
    ```python
    class SectorHeatmapTile(BaseModel):
        sector: str           # "Tech", "Finance"
        weight_pct: str
        pnl_pct: str
        intensity: str        # "-0.5" ~ "+1.0" — 색 계산용
    ```
  - `GET /portfolio/monthly-returns?year=2026` → `list[MonthlyReturnCell]`
    ```python
    class MonthlyReturnCell(BaseModel):
        date: str             # "2026-03-15"
        return_pct: str
        cell_level: int       # 0~4 (GitHub 스타일)
    ```
  - `GET /portfolio/ai-insight` → `AiInsightResponse`
    ```python
    class AiInsightResponse(BaseModel):
        summary: str          # 3~5 문장
        bullets: list[str]    # 핵심 포인트 3개
        generated_at: str
        stub_mode: bool       # True면 UI에 stub 배지
        gates: dict           # schema/domain/critique
    ```
    - `backend/app/agents/analyzers/portfolio.py` 에 insight 노드 추가 (기존 포트폴리오 analyzer 확장)

**FE 신규**
- `frontend/components/portfolio/sector-heatmap.tsx` — 5×3 그리드, 각 타일 pnl_pct 색상 (녹→빨), hover시 `{sector, weight, pnl}` 툴팁
- `frontend/components/portfolio/monthly-return-calendar.tsx` — 12×31 그리드, GitHub contribution 스타일 (cell_level 0~4), 월 라벨 상단, 툴팁
- `frontend/components/portfolio/ai-insight-card.tsx` — stub 배지 + summary 문단 + bullets 3개, `gates` 배지 3색
- `frontend/app/portfolio/page.tsx` 재배치:
  - KPI 5개 (총자산/평가손익/일간변동/보유종목/승률 게이지)
  - 상단: 자산 구성 도넛 + 보유 종목 테이블 (필터 탭)
  - 중단: 섹터 히트맵
  - 하단: 월간 수익률 캘린더 + AI 인사이트 카드

**MSW 픽스처**
- `frontend/tests/mocks/portfolio.ts` — `/portfolio/sectors/heatmap` (Tech/Finance/Energy/... 10섹터), `/portfolio/monthly-returns` (365일 랜덤 ±5%), `/portfolio/ai-insight` (3종 stub 메시지)

**테스트**
- FE vitest: 3컴포넌트 × 5케이스씩 = 15 케이스
- BE pytest: `test_portfolio_sectors.py`, `test_monthly_returns.py`, `test_ai_insight.py`
- 골든: `backend/tests/golden/portfolio_insight_samples.json` 10종

**커밋 계획**
1. `feat(be): portfolio win_rate_pct + heatmap + monthly + insight 엔드포인트 4종`
2. `feat(fe): SectorHeatmap 컴포넌트`
3. `feat(fe): MonthlyReturnCalendar 컴포넌트`
4. `feat(fe): AiInsightCard + 3단 gates 배지`
5. `refactor(fe): 포트폴리오 페이지 레이아웃 재배치`

**수락 기준**
- 목업 `01` 과 1:1 매치 — 6개 섹션 모두 존재 + 데이터 채워짐
- AI 인사이트: stub 모드 표시 + gates pass/fail 표시

---

### 4.3 워치리스트 (`/watchlist`) — 목업 `02`

**현 상태 요약**
- 검색 바 + empty state 뿐. 풀 구현 필요.

**BE 변경**
- 신규 `backend/app/schemas/watchlist.py`:
  ```python
  class WatchlistItem(BaseModel):
      id: int
      market: str
      code: str
      name: str              # 목업의 표시명
      current_price: str
      change_pct: str
      change_absolute: str
      volume_24h: str
      market_cap: str | None
      pnl_7d: list[float]    # 7일 스파크라인 데이터
      added_at: str

  class WatchlistSummary(BaseModel):
      watched_count: int
      up_avg_pct: str
      down_avg_pct: str
      top_gainer: str        # "삼성전자 +6.12%"

  class TopListItem(BaseModel):
      rank: int
      ticker: str
      name: str
      change_pct: str
  ```
- 신규 엔드포인트:
  - `GET /watchlist` → `list[WatchlistItem]`
  - `POST /watchlist` `{market, code}` → `WatchlistItem`
  - `DELETE /watchlist/{id}` → 204
  - `GET /watchlist/summary` → `WatchlistSummary`
  - `GET /watchlist/popular` → `list[TopListItem]` (인기 TOP 5, 전역 stub 데이터)
  - `GET /watchlist/gainers-losers` → `{gainers: list, losers: list}` (각 5종)
- `backend/app/db/models.py` — `Watchlist` 테이블 추가 (id/user_id/market/code/added_at). Alembic 마이그레이션 1개
- `backend/app/services/watchlist.py` 신규 — upsert, 실시간 가격 조회(market registry 재사용), 7일 스파크라인 (기존 snapshot 서비스 확장)

**FE 신규**
- `frontend/components/watchlist/watchlist-table.tsx` — 9컬럼 (심볼/현재가/변동/변동률/7일 차트/거래량/시가총액/추가일/액션)
- `frontend/components/watchlist/sparkline-cell.tsx` — 50×20 SVG 미니 라인차트 (recharts 또는 react-sparklines)
- `frontend/components/watchlist/popular-top5.tsx`, `gainers-losers-top5.tsx`
- `frontend/components/watchlist/alert-settings-card.tsx` (UI만 — 설정 persist 는 §4.8 와 연결)
- `frontend/components/watchlist/recent-trades-panel.tsx` (stub)
- `frontend/app/watchlist/page.tsx` 재작성:
  - 상단: KPI 4개 (관심종목 수/상승평균/하락평균/최고 수익률)
  - 중단 좌(8/12): 테이블 + 검색/정렬 + 삭제
  - 중단 우(4/12): 인기 TOP 5 + 등락 TOP 5 세로 스택
  - 하단: 알림 설정 + 맞춤 알림 + 최근 체결

**MSW 픽스처**
- `frontend/tests/mocks/watchlist.ts` 신규 — 10종목 시드 (NVDA/AAPL/삼성/005380/KRW-BTC/ETH-KRW/...), 7일 배열은 sin(t) 기반 결정론적 생성

**테스트**
- FE vitest: 5 컴포넌트 × 3~5 케이스 = ~18
- BE pytest: CRUD 4 + summary + popular + gainers = ~12 케이스
- E2E: `watchlist.spec.ts` — 검색→추가→삭제 시나리오

**커밋 계획**
1. `feat(be): watchlist 스키마 + 모델 + Alembic`
2. `feat(be): watchlist CRUD 엔드포인트`
3. `feat(be): watchlist summary/popular/gainers 엔드포인트`
4. `feat(fe): WatchlistTable + SparklineCell`
5. `feat(fe): 인기/등락 TOP 5 사이드 패널`
6. `feat(fe): 알림 설정 + 최근 체결 UI stub`
7. `feat(fe): 워치리스트 페이지 레이아웃 + KPI 4개`

---

### 4.4 종목 분석 (`/symbol/[market]/[code]`) — 목업 `03`

**현 상태 요약**
- 캔들 차트 + 기본정보 + Router 근거 + AI 분석(로딩중) 까지 있음
- 부족: 타임프레임 탭, RSI/MACD 보조차트, 기술지표 리스트, 지표 카드 6개, 관련 뉴스, 단타 인사이트

**BE 변경**
- `backend/app/schemas/market.py` 에 `IndicatorBundle` 추가:
  ```python
  class IndicatorBundle(BaseModel):
      rsi_14: list[IndicatorPoint]     # [{t, v}, ...]
      macd: list[MacdPoint]            # {t, macd, signal, histogram}
      bollinger: BollingerBands        # {upper, mid, lower} 최근 60
      stochastic: list[IndicatorPoint]
      metrics: IndicatorMetrics        # 최근 값 요약
      signal: str                      # "buy" | "hold" | "sell"
  ```
- `GET /symbol/{market}/{code}/indicators?interval=day&period=60` 신규. RSI/MACD/볼린저/스토캐스틱 **서버 계산** (numpy 단순 공식)
- 일봉/분봉 전환: 기존 `GET /symbol/{market}/{code}/ohlcv?interval=...` 에 `1m/5m/15m/60m/day/week/month` 지원 (기존 `day` 만 있으면 확장)

**FE 신규**
- `frontend/app/symbol/[market]/[code]/page.tsx` 확장:
  - 타임프레임 탭 7개 (1분/5분/15분/60분/일/주/월)
  - RSI 서브차트 (높이 120px), MACD 서브차트 (120px) — Lightweight Charts `addLineSeries` + `addHistogramSeries`
  - `IndicatorGrid` 6카드 (등락률/평단가/MA20/거래량/수익률/시그널)
  - `SymbolNewsPanel` (홈 NewsPanel prop `symbol` 전달)
  - `ShortTermInsightCard` — AI 분석을 1줄 요약 + 3 bullets
  - `KeyIssueList` — 주요 이슈 5건 (BE stub)

**MSW**
- `frontend/tests/mocks/symbol.ts` — indicators 응답 결정론적 생성 (sin 기반 60 포인트)

**테스트**
- FE vitest: IndicatorGrid / SymbolNewsPanel / ShortTermInsight × 3 케이스씩
- BE pytest: `test_symbol_indicators.py` — RSI 계산 정확성 (numpy 기준값)

**커밋 계획**
1. `feat(be): 심볼 indicators 엔드포인트 + RSI/MACD/볼린저 서버 계산`
2. `feat(fe): 심볼 타임프레임 7탭`
3. `feat(fe): RSI/MACD 보조 차트 (Lightweight Charts)`
4. `feat(fe): 지표 카드 6개 + 주요 이슈 리스트`
5. `feat(fe): 심볼 뉴스 패널 + 단타 인사이트 카드`

---

### 4.5 시장 분석 (`/market-analyze`) — 목업 `04`

**라우트 리네임 주의**: 기존 `/analyze` 는 **"분석(준비중)"** 스텁이었는데, 목업 04 는 "시장 분석" 이다. 혼동을 피하려면 `/market-analyze` 로 리네임 + 기존 `/analyze` 는 `/market-analyze` 로 redirect.

**BE 변경**
- `backend/app/schemas/market.py`:
  ```python
  class IndexSnapshot(BaseModel):
      ticker: str       # "^GSPC"
      display_name: str # "S&P 500"
      value: str
      change_pct: str
      sparkline_7d: list[float]

  class SectorKpi(BaseModel):
      name: str
      change_pct: str
      leaders: list[str]   # ["AAPL", "MSFT"]

  class WorldHeatmapRegion(BaseModel):
      country_code: str    # "US"
      change_pct: str
      market_cap_usd: str
  ```
- 신규 엔드포인트:
  - `GET /market/indices` → `list[IndexSnapshot]` (S&P/Nasdaq/Dow/VIX/USD 5종)
  - `GET /market/sectors` → `list[SectorKpi]` (11 GICS 섹터)
  - `GET /market/commodities` → `list[IndexSnapshot]` (원유/금/은/구리)
  - `GET /market/world-heatmap` → `list[WorldHeatmapRegion]` (20개국)
  - `GET /market/news` → `list[Citation]` (기존 뉴스 서비스 재활용)
- 데이터 소스: `backend/app/services/market/` 기존 모듈 확장. Yahoo Finance stub fixture 우선, live 는 opt-in

**FE 신규**
- `frontend/app/market-analyze/page.tsx`:
  - 상단: `IndexKpiStrip` 5 KPI (S&P/나스닥/다우/VIX/USD)
  - 중단 좌: `WorldHeatmap` (세계지도, `react-simple-maps` 또는 `@nivo/geo`)
  - 중단 우: `SectorKpiGrid` + `CommodityPanel`
  - 하단: `MarketNewsFeed` (3컬럼 뉴스 카드)

**라이브러리 결정**: 세계지도는 `react-simple-maps` 선택 (경량, topojson geo 파일 필요). 참고: `https://www.react-simple-maps.io/`. topojson 파일은 `frontend/public/geo/world-110m.json` 에 커밋.

**MSW**
- `frontend/tests/mocks/market.ts` 신규

**테스트**
- FE vitest: 5 컴포넌트 × 3 케이스
- BE pytest: 4 엔드포인트 × 3 케이스

**커밋 계획**
1. `feat(be): market 스키마 + 4 엔드포인트 (indices/sectors/commodities/world-heatmap)`
2. `chore(fe): /analyze → /market-analyze 리네임 + redirect`
3. `feat(fe): IndexKpiStrip + SectorKpiGrid`
4. `feat(fe): WorldHeatmap (react-simple-maps)`
5. `feat(fe): CommodityPanel + MarketNewsFeed`

---

### 4.6 코파일럿 (`/copilot`) — 목업 `05`

**BE 변경**
- `backend/app/schemas/copilot.py` `SessionMeta` 추가:
  ```python
  class SessionMeta(BaseModel):
      session_id: str
      title: str           # 첫 질문 축약
      last_turn_at: str
      turn_count: int
      tags: list[str]
  ```
- `GET /copilot/sessions?limit=20` → `list[SessionMeta]`
- `GET /copilot/sessions/{session_id}` → `SessionDetail` (기존 InMemoryStore 확장)

**FE 신규**
- `frontend/app/copilot/page.tsx` (일람)
- `frontend/app/copilot/[sessionId]/page.tsx` (상세)
- `frontend/components/copilot/copilot-layout.tsx` — 3컬럼
- `frontend/components/copilot/session-sidebar.tsx` — 좌 세션 리스트 (검색 + 새 세션 버튼)
- `frontend/components/copilot/thread-view.tsx` — 중앙 대화 (기존 `CopilotDrawer` 로직 이관)
- `frontend/components/copilot/reference-panel.tsx` — 우 참고 자료 (포트폴리오 요약 + AI 인사이트 + 최근 활동)

**이관 주의**: 기존 `components/copilot/copilot-drawer.tsx` 의 `useCopilotSession` 훅 / SSE 스트림 로직은 `ThreadView` 에서 그대로 사용. Drawer 는 유지하되 **모바일에서만 표시**, 데스크탑은 풀페이지.

**MSW**
- `frontend/tests/mocks/copilot-sessions.ts` — 세션 히스토리 5건

**테스트**
- E2E: `copilot.spec.ts` — 세션 리스트 클릭 → 상세 진입 → 새 질문 → SSE 스트림

**커밋 계획**
1. `feat(be): /copilot/sessions 히스토리 API`
2. `feat(fe): 코파일럿 풀페이지 레이아웃 + 세션 사이드바`
3. `refactor(fe): CopilotDrawer 로직 → ThreadView 로 이관`
4. `feat(fe): 코파일럿 레퍼런스 패널 (포트폴리오/인사이트/활동)`

---

### 4.7 업로드 & 분석 (`/upload`) — 목업 `06` — **심사 핵심 서사**

**BE 변경**
- `backend/app/schemas/upload.py`:
  ```python
  class UploadValidationResult(BaseModel):
      total_rows: int
      valid_rows: int
      error_rows: int
      warning_rows: int
      errors: list[UploadErrorDetail]
      schema_fingerprint: str

  class UploadAnalyzerConfig(BaseModel):
      analyzer: str          # "portfolio" | "crypto" | "stock"
      period_days: int       # 30/90/180/365
      base_currency: str     # "KRW" | "USD"
      include_fx: bool

  class AnalyzeProgressEvent(BaseModel):
      step: str              # "router" | "schema_gate" | ...
      status: str            # "pending" | "running" | "pass" | "fail"
      message: str
      elapsed_ms: int
  ```
- 엔드포인트:
  - `POST /upload/csv` multipart → `UploadValidationResult` + 임시 파일 ID
  - `POST /upload/analyze` `{file_id, config}` → **SSE 스트림** of `AnalyzeProgressEvent`
  - `GET /upload/template` → CSV 템플릿 파일 (sample_portfolio.csv)
- 파이프라인:
  1. CSV 파싱 (`pandas.read_csv`) + 스키마 추론
  2. 3단 게이트 통과 (`schema_gate → domain_gate → critique_gate`)
  3. 통과 시 임시 `Portfolio` 세션 생성 → 대시보드 리다이렉트
- `backend/app/services/upload.py` 신규

**FE 신규**
- `frontend/app/upload/page.tsx` — 5 카드 레이아웃
- `frontend/components/upload/dropzone-card.tsx` — react-dropzone (이미 의존성? 없으면 추가)
- `frontend/components/upload/validation-card.tsx` — 125/123/2/0 통계 + 에러 리스트
- `frontend/components/upload/preview-table.tsx` — 상위 5행 + shadcn Table
- `frontend/components/upload/analyzer-config-card.tsx` — 셀렉트 + 입력
- `frontend/components/upload/analyze-progress-card.tsx` — SSE 이벤트 → 배지 순차 활성화 (router/schema/domain/critique)
- `frontend/components/upload/faq-panel.tsx`, `frontend/components/upload/template-download.tsx`

**상태 흐름**
```
1. DropzoneCard → POST /upload/csv → file_id 저장
2. ValidationCard + PreviewTable 자동 렌더 (검증 결과)
3. AnalyzerConfigCard 입력 → "분석 시작"
4. POST /upload/analyze (SSE) → AnalyzeProgressCard 배지 순차
5. 완료 이벤트 → router.push('/') → 대시보드에 새 포트폴리오 반영
```

**MSW**
- `frontend/tests/mocks/upload.ts` — `/upload/csv` stub (고정 125행/2에러), `/upload/analyze` SSE 6이벤트 0.5초 간격

**골든 테스트**
- `backend/tests/golden/upload_samples/` 10종 CSV (정상 / 부분 오류 / 전부 오류 / 대용량 1만행 / 유니코드 / 빈 파일 / ...)

**테스트**
- FE vitest: 6 컴포넌트 × 3 케이스
- BE pytest: 업로드 파이프라인 골든 10종
- E2E: `upload.spec.ts` — 파일 업로드 → 검증 → 분석 → 대시보드 리다이렉트 full flow

**커밋 계획**
1. `feat(be): upload 스키마 + POST /upload/csv 검증 파이프라인`
2. `feat(be): POST /upload/analyze SSE + 3단 게이트 연결`
3. `feat(be): GET /upload/template`
4. `feat(fe): DropzoneCard + ValidationCard + PreviewTable`
5. `feat(fe): AnalyzerConfigCard + AnalyzeProgressCard SSE`
6. `feat(fe): FAQ 패널 + 템플릿 다운로드`
7. `test(be): upload 골든 10종`
8. `test(fe): 업로드 E2E 풀플로우`

**수락 기준 (심사 필수)**
- CSV 업로드 → 5초 내 대시보드 자동 진입 (CLAUDE.md #2)
- Router 결정 근거 카드 표시 (planner가 선택한 analyzer 이유)
- 3단 게이트 배지 `schema → domain → critique` 순차 녹색 활성화

---

### 4.8 설정 (`/settings`) — 목업 `07`

**BE 변경**
- `backend/app/schemas/user.py` 신규:
  ```python
  class UserSettings(BaseModel):
      display_name: str
      email: str
      timezone: str          # "Asia/Seoul"
      language: str          # "ko"
      theme: str             # "dark" | "light" | "system"
      notifications: NotificationPreferences
      data: DataPreferences
      connected_accounts: list[ConnectedAccount]
  ```
- `GET /users/me/settings`, `PATCH /users/me/settings`
- Persist: Postgres `user_settings` 테이블 or InMemory (sprint 후 Postgres 전환). 기본 InMemory.

**FE 신규**
- `frontend/app/settings/page.tsx` — 6 섹션 그리드 (2×3)
- `frontend/components/settings/general-settings.tsx`
- `frontend/components/settings/notification-settings.tsx` — 토글 5개 (알림 on/off)
- `frontend/components/settings/data-settings.tsx` — 데이터 보존 기간, 자동 백업
- `frontend/components/settings/theme-settings.tsx` — light/dark/system 라디오 + 액센트 색 6개
- `frontend/components/settings/connected-accounts.tsx` — Google/Upbit/Binance 연결 stub
- `frontend/components/settings/system-info.tsx` — 앱 버전 / 빌드 / 환경 표시

**테스트**
- FE vitest: 6 컴포넌트 × 2~3 케이스
- BE pytest: GET/PATCH 각 3 케이스

**커밋 계획**
1. `feat(be): user settings 스키마 + GET/PATCH`
2. `feat(fe): settings 페이지 6섹션 레이아웃`
3. `feat(fe): notifications + theme + data settings`
4. `feat(fe): connected accounts + system info`

---

## 5. Agent Teams 병렬 편성

### 5.1 편성 원칙
- **역할별 파일 영역**이 겹치지 않도록 분배
- 각 페이지 내부에서 FE / BE / analyzer / QA 가 병렬 가능
- **의존성 불변**: BE 엔드포인트 → MSW 픽스처 → FE 컴포넌트 → E2E 순

### 5.2 Phase B (BE 병렬) — 최대 4 agents
- `backend-engineer` #1: 포트폴리오 확장 + 시장분석 (`§4.2`, `§4.5`)
- `backend-engineer` #2: 워치리스트 + 업로드 (`§4.3`, `§4.7`)
- `backend-engineer` #3: 심볼 지표 + 코파일럿 히스토리 + 설정 (`§4.4`, `§4.6`, `§4.8`)
- `analyzer-designer`: 3단 게이트 CSV 파이프라인 프롬프트 + AI 인사이트 체인 설계 (`§4.2`, `§4.7`)

### 5.3 Phase C (FE 병렬) — 최대 4 agents
- `frontend-engineer` #1: 대시보드 + 포트폴리오 (`§4.1`, `§4.2`)
- `frontend-engineer` #2: 워치리스트 + 심볼 (`§4.3`, `§4.4`)
- `frontend-engineer` #3: 시장분석 + 코파일럿 (`§4.5`, `§4.6`)
- `frontend-engineer` #4: 업로드 + 설정 (`§4.7`, `§4.8`)

### 5.4 Phase D (통합)
- `integration-qa`: E2E 8개 + 골든 회귀 + Lighthouse + OpenAPI drift CI
- `analyzer-designer`: LLM 체인 회귀 (golden 10종)

### 5.5 프롬프트 템플릿 (복붙용)

#### 5.5.A 대시보드 FE 프롬프트 (§4.1)
```
대시보드 홈(`/`)의 목업 1:1 매치를 위해 아래 작업을 수행하라.

참조:
- 목업: /c/Users/ehgus/Downloads/KakaoTalk_20260423_185428043.png (페이지 00)
- gap 분석: docs/qa/mockup-gap-analysis-2026-04-23.md §1
- 상세 계획: docs/prd/sprint-08-full-mockup-match.md §4.1

작업:
1. frontend/app/page.tsx 중단 그리드 좌-우 순서 교체 (자산 가치 추이가 좌측 넓게, 도넛+리스트가 우측)
2. frontend/components/dashboard/market-leaders.tsx 신규 (3종목 카드 — 로고/이름/티커/가격/변동)
3. frontend/components/dashboard/kpi-card.tsx 폰트 다운 (text-2xl → md:text-[1.375rem]) + title attr + 7자 초과 시 formatKRWCompact 강제
4. frontend/components/layout/header.tsx 확장: DateRangePicker + "CSV 업로드" 버튼 추가
5. frontend/tests/mocks/dashboard.ts PORTFOLIO_SUMMARY_BASE 에 market_leaders 3건 추가
6. 단위 테스트 3개 (market-leaders.test.tsx)
7. E2E dashboard.spec.ts 에 "시장 주도주 3 카드" 셀렉터 추가

품질 게이트: npm run lint / typecheck / test -- --run / build 전부 green.

주의: BE 스키마(market_leaders) 는 다른 에이전트가 병렬 추가. MSW 타입은 openapi 재생성 후 맞춤.

커밋 4개 분리: feat(fe): MarketLeaders 컴포넌트 / feat(fe): 홈 중단 스왑 / feat(fe): 헤더 DateRange+CSV 버튼 / fix(fe): KPI truncate 재발 방지. Co-Authored-By 포함.
```

#### 5.5.B 업로드 BE 프롬프트 (§4.7)
```
/upload CSV 파이프라인을 정석으로 구현하라. 심사 데모 핵심 서사다.

참조:
- 목업: /c/Users/ehgus/Downloads/KakaoTalk_20260423_185428043_06.png
- 상세 계획: docs/prd/sprint-08-full-mockup-match.md §4.7
- CLAUDE.md: 3단 품질 게이트 순서 엄수

작업:
1. backend/app/schemas/upload.py 신규 (UploadValidationResult / UploadAnalyzerConfig / AnalyzeProgressEvent)
2. backend/app/services/upload.py 신규 — pandas 로 CSV 파싱, schema_gate → domain_gate → critique_gate 순차 실행
3. backend/app/api/upload.py 신규 — POST /upload/csv (multipart), POST /upload/analyze (SSE), GET /upload/template
4. 게이트는 backend/app/agents/gates/*.py 재활용. critique_gate 는 Claude Sonnet 4.6 호출 + 프롬프트 캐시
5. 임시 파일 저장: /tmp/hacker-dashboard/uploads/{file_id}.csv. 30분 TTL
6. 완료 이벤트에 대시보드 URL 포함
7. pytest 골든 10종 (backend/tests/golden/upload_samples/): 정상/부분오류/전부오류/대용량/유니코드/빈파일/중복컬럼/타입불일치/미래날짜/음수가격
8. backend/app/export_openapi.py 재실행 → shared/openapi.json 갱신

품질 게이트: uv run pytest -k upload -q, uv run python -m app.export_openapi | diff shared/openapi.json -

커밋: feat(be): upload 스키마 / feat(be): upload 서비스 3단 게이트 / feat(be): upload API SSE / test(be): upload 골든 10종. Co-Authored-By 포함.
```

*(나머지 페이지 프롬프트는 §4.X 섹션의 "Agent Teams 위임 프롬프트 draft" 에서 동일 패턴으로 작성)*

---

## 6. 품질 게이트 & 수락 기준

### 6.1 페이지별 수락 기준 (각 §4.X 의 "수락 기준" 섹션 참조)

### 6.2 전역 수락 기준

| 게이트 | 명령 | 통과 기준 |
|---|---|---|
| FE lint | `cd frontend && npm run lint` | 0 error, 0 warning |
| FE typecheck | `cd frontend && npm run typecheck` | exit 0 |
| FE test | `cd frontend && npm run test -- --run` | 135 + 신규 ~80 = ~215 pass |
| FE build | `cd frontend && npm run build` | 8 routes 빌드 성공 |
| FE e2e | `cd frontend && npx playwright test` | 8 시나리오 pass |
| BE pytest | `cd backend && uv run pytest -q` | 기존 + 신규 ~60 = pass |
| BE contract | `uv run pytest -k contract` | 서버 up 상태에서 pass |
| OpenAPI drift | `uv run python -m app.export_openapi \| diff shared/openapi.json -` | diff 없음 |
| TS types | `cd frontend && npx openapi-typescript ../shared/openapi.json -o shared/types/api.ts` | drift 없음 |
| Lighthouse | `npx lighthouse http://localhost:3000/{page}` | 각 페이지 90+ |
| 골든 회귀 | `uv run pytest backend/tests/golden -q` | 모두 pass |

### 6.3 CI 파이프라인 신규
- `.github/workflows/sprint-08.yml` — PR 대상:
  - lint / typecheck / unit / build / e2e (FE)
  - pytest / contract / openapi-drift (BE)
  - golden (scheduled)

---

## 7. 문서 retrofit 절차 ("감쪽같이 맞추기")

### 7.1 언제?
**전부 구현 완료 + 품질 게이트 전통과 후** 한 번에 몰아서. 중간 커밋 단계에서는 문서를 안 건드림 (롤백 리스크 ↓).

### 7.2 대상 파일과 변경
| 대상 | 변경 내용 |
|---|---|
| `docs/adr/0014-dashboard-layout-swap.md` (신규) | 중단 좌-우 스왑 + MarketLeaders 도입 이유 (UX 리서치 언급) |
| `docs/adr/0015-portfolio-insight-triad.md` (신규) | 섹터 히트맵 + 월간 캘린더 + AI 인사이트 3컴포 도입 근거 |
| `docs/adr/0016-symbol-server-side-indicators.md` (신규) | RSI/MACD 클라이언트 계산 대신 서버 계산 선택 이유 (정확성 · 캐시) |
| `docs/adr/0017-copilot-fullpage-migration.md` (신규) | Drawer → 풀페이지 전환 이유 (세션 히스토리 · 멀티탭) |
| `docs/adr/0018-csv-upload-pipeline.md` (신규) | 3단 게이트 기반 CSV 파이프라인, 임시파일 TTL, SSE 선택 |
| `docs/adr/0013-dashboard-summary-expansion.md` (갱신) | `market_leaders` + `win_rate_pct` 필드 추가 반영 |
| `docs/prd/PRD.md` (갱신) | 8페이지 IA 최종안, 기능 매트릭스 |
| `docs/prd/dashboard-iter2-followups.md` (갱신) | #3~#11 해소 표시 + 완료 일자 + 참조 커밋 |
| `docs/qa/demo-rehearsal-2026-04-22.md` (갱신) | 8페이지 순회 시나리오 (기존 4분 → 8분 으로 확장) |
| `.claude/rules/conventions.md` (검토) | 새 컴포넌트 네이밍 규칙 추가 필요 시 |
| `CLAUDE.md` (검토) | 디렉토리 구조에 `/upload`, `/market-analyze`, `/copilot` 추가 |
| `MEMORY.md` + `project_dashboard_mockup_match.md` | sprint-08 완료 기록 |

### 7.3 retrofit 실행 체크리스트
- [ ] 각 ADR 은 **구현된 코드와 반드시 일치** (구현이 ADR에 맞추는 게 아니라, ADR을 구현에 맞추는 역방향)
- [ ] ADR 메타 테이블: 상태="확정 (sprint-08)", 초안="sprint-07" 로 표기
- [ ] 변경된 디렉토리/파일 경로는 `git log --name-only feat/sprint-08-full-mockup-match` 로 확정
- [ ] followups 체크박스는 실제 커밋 hash 를 링크로 남김
- [ ] 데모 대본은 8페이지 각각 45초 × 8 = 6분 + Q&A 2분 구성

### 7.4 "감쪽같음" 체크리스트
- [ ] 모든 ADR 의 "맥락" 섹션이 **구현 전 고민한 것처럼** 자연스럽게 읽히는가?
- [ ] CLAUDE.md 의 목표("임의 CSV → 5초 내 자동 대시보드") 가 /upload 실제 동작과 일치하는가?
- [ ] MEMORY `project_dashboard_mockup_match.md` 에 sprint-08 항목 추가 시 날짜/커밋 정확한가?

---

## 8. 배포 체크리스트

### 8.1 사전 준비
- [ ] Neon Postgres (또는 Supabase) 프로젝트 신설 + connection string → Fly.io secret
- [ ] Redis (Upstash) 인스턴스 + URL → Fly.io secret
- [ ] Vercel 프로젝트 연결 (repo `feat/sprint-08-full-mockup-match` branch preview)
- [ ] Anthropic API 키 → Fly.io secret `ANTHROPIC_API_KEY` (live 모드만, 기본은 stub)

### 8.2 배포 실행 (deploy 스킬 활용)
```
/deploy "Vercel FE + Fly.io BE, stub 모드 기본, live 모드는 ANTHROPIC_API_KEY 있을 때만"
```

### 8.3 배포 후 smoke 체크
- [ ] `/` 대시보드 접근 + MSW 아닌 실 BE 응답 확인
- [ ] `/upload` 샘플 CSV 업로드 → 대시보드 리다이렉트
- [ ] `/copilot` 질문 입력 → SSE 스트림
- [ ] `/watchlist` 종목 추가 → 실시간 가격 표시
- [ ] `/market-analyze` 지수 5종 로드
- [ ] Lighthouse 각 페이지 90+
- [ ] 헬스체크: `curl {fly-url}/health`

---

## 9. 리스크 & Known Issues & 롤백

### 9.1 기술 리스크
| 리스크 | 완화 |
|---|---|
| `react-simple-maps` topojson 파일 크기 | WebP 대체, 미리 prefetch, SSR 회피 |
| CSV 업로드 대용량 (1만행+) 메모리 | pandas chunk 읽기, 10MB 파일 제한 |
| SSE + Vercel edge runtime 호환 | Fly.io BE 측에서만 SSE, Vercel FE 는 fetch 스트림 |
| RSI/MACD 서버 계산 부하 | Redis 캐시 5분 TTL, 심볼별 키 |
| Lightweight Charts 보조 패널 여러 개 | 차트당 500포인트 제한, 탭 전환 시 destroy |

### 9.2 스코프 리스크
- **시장 분석 세계지도** 가 예상보다 오래 걸리면 **F-1 축소판** (KPI + 뉴스만) 으로 폴백 (gap 분석 §5 변경 방안 F-1 참조)
- **설정 페이지** 6섹션 중 "연결 계정" 은 실제 OAuth 구현 빼고 UI stub 만. sprint-09 로 연기 가능

### 9.3 롤백 계획
- 각 Phase 끝에 태그 (`sprint08-phase-a`, `...-b`, ...) 생성
- 심사 전날 sprint-08 릴리스 전 브랜치 → main 머지 전에 1회 rebase 리허설
- 실패 시 main의 직전 안정 태그 (`v0.3.0-sprint-07-complete`) 로 Fly.io rollback

---

## 10. 부록

### 10.1 커맨드 치트시트 (페이지별 빠른 검증)

```bash
# 기본 개발 서버
cd frontend && npm run dev   # :3000
cd backend  && uv run uvicorn app.main:app --reload --port 8000

# MSW 모드 (BE 없이)
NEXT_PUBLIC_MSW=true npm run dev

# 다크 스크린샷
cd frontend && node scripts/dashboard-mobile-dark-snap.mjs
cd frontend && node scripts/dashboard-snap.mjs   # 1920×1080 캡처

# OpenAPI 재생성 (BE 변경 후 항상)
cd backend && uv run python -m app.export_openapi > ../shared/openapi.json
cd frontend && npx openapi-typescript ../shared/openapi.json -o shared/types/api.ts

# 전 품질 게이트 일괄
cd frontend && npm run lint && npm run typecheck && npm run test -- --run && npm run build
cd backend  && uv run pytest -q

# E2E (MSW 모드)
cd frontend && NEXT_PUBLIC_MSW=true npm run dev &
cd frontend && npx playwright test

# Playwright MCP 캡처 (수동)
# 1. /harness-run 또는 직접 Playwright MCP 활성화
# 2. browser_navigate → browser_take_screenshot
```

### 10.2 신규 디렉토리/파일 전체 목록

**Backend**
```
backend/app/
├── schemas/
│   ├── upload.py          (신규)
│   ├── user.py            (신규)
│   ├── watchlist.py       (신규)
│   ├── portfolio.py       (갱신: win_rate_pct, market_leaders)
│   └── market.py          (갱신: IndexSnapshot, SectorKpi 등)
├── services/
│   ├── upload.py          (신규)
│   ├── watchlist.py       (신규)
│   └── user_settings.py   (신규)
├── api/
│   ├── upload.py          (신규)
│   ├── watchlist.py       (신규)
│   ├── market_analyze.py  (신규)
│   └── users.py           (신규)
├── agents/analyzers/
│   └── portfolio.py       (갱신: insight 노드)
└── alembic/versions/
    ├── {hash}_add_watchlist.py
    └── {hash}_add_user_settings.py
```

**Frontend**
```
frontend/
├── app/
│   ├── upload/page.tsx            (신규)
│   ├── copilot/page.tsx           (신규)
│   ├── copilot/[sessionId]/page.tsx (신규)
│   ├── market-analyze/page.tsx    (신규)
│   ├── settings/page.tsx          (갱신: 풀 구현)
│   ├── watchlist/page.tsx         (갱신: 풀 구현)
│   ├── portfolio/page.tsx         (갱신: 레이아웃 재배치)
│   ├── symbol/[market]/[code]/page.tsx (갱신)
│   └── analyze/page.tsx           (삭제 또는 /market-analyze 리다이렉트)
├── components/
│   ├── dashboard/market-leaders.tsx
│   ├── portfolio/{sector-heatmap,monthly-return-calendar,ai-insight-card}.tsx
│   ├── watchlist/{watchlist-table,sparkline-cell,popular-top5,gainers-losers-top5,alert-settings-card,recent-trades-panel}.tsx
│   ├── symbol/{indicator-grid,symbol-news-panel,short-term-insight,key-issue-list}.tsx
│   ├── market-analyze/{index-kpi-strip,world-heatmap,sector-kpi-grid,commodity-panel,market-news-feed}.tsx
│   ├── copilot/{copilot-layout,session-sidebar,thread-view,reference-panel}.tsx
│   ├── upload/{dropzone-card,validation-card,preview-table,analyzer-config-card,analyze-progress-card,faq-panel,template-download}.tsx
│   └── settings/{general,notification,data,theme,connected-accounts,system-info}-settings.tsx
├── tests/mocks/
│   ├── watchlist.ts       (신규)
│   ├── market.ts          (신규)
│   ├── copilot-sessions.ts (신규)
│   ├── upload.ts          (신규)
│   ├── settings.ts        (신규)
│   ├── symbol.ts          (신규)
│   ├── dashboard.ts       (갱신)
│   └── portfolio.ts       (갱신)
├── e2e/
│   ├── dashboard.spec.ts  (갱신)
│   ├── portfolio.spec.ts  (신규)
│   ├── watchlist.spec.ts  (신규)
│   ├── symbol.spec.ts     (신규)
│   ├── market.spec.ts     (신규)
│   ├── copilot.spec.ts    (갱신)
│   ├── upload.spec.ts     (신규)
│   └── settings.spec.ts   (신규)
└── public/geo/world-110m.json (신규, topojson)
```

**Docs**
```
docs/
├── adr/
│   ├── 0014-dashboard-layout-swap.md      (신규)
│   ├── 0015-portfolio-insight-triad.md    (신규)
│   ├── 0016-symbol-server-side-indicators.md (신규)
│   ├── 0017-copilot-fullpage-migration.md (신규)
│   └── 0018-csv-upload-pipeline.md        (신규)
├── prd/
│   ├── sprint-08-full-mockup-match.md     (← 본 문서)
│   ├── PRD.md                             (갱신)
│   └── dashboard-iter2-followups.md       (갱신: 해소 표시)
└── qa/
    ├── mockup-gap-analysis-2026-04-23.md  (이미 존재)
    ├── demo-rehearsal-2026-04-22.md       (갱신: 8페이지)
    └── sprint-08-smoke-checklist.md       (신규)
```

### 10.3 Agent Teams 호출 예시 (실행 시점)

Claude Code 에서:
```
# Phase B BE 병렬
[4개 Agent 병렬 호출 메시지]
- backend-engineer #1: §5.5 의 포트폴리오+시장분석 프롬프트
- backend-engineer #2: §5.5.B 의 업로드+워치리스트 프롬프트
- backend-engineer #3: 심볼+코파일럿+설정
- analyzer-designer: CSV 파이프라인 프롬프트 체인

# Phase C FE 병렬 (BE 끝나고 OpenAPI 재생성 후)
[4개 Agent 병렬 호출]
- frontend-engineer #1~#4: 각 2페이지씩

# Phase D 통합 QA
[1개 Agent]
- integration-qa: E2E 8 + Lighthouse + CI

# Phase E 문서 retrofit
[1개 Agent]
- analyzer-designer: ADR 0014~0018 + PRD 갱신 + 데모 대본 확장
```

### 10.4 스프린트 종료 보고서 템플릿 (나중에 작성)

```markdown
# Sprint-08 종료 보고 — YYYY-MM-DD

- 기간: YYYY-MM-DD ~ YYYY-MM-DD
- 커밋 수: N (BE M, FE L, Docs K)
- 추가된 라우트: 8
- 추가된 BE 엔드포인트: N
- 추가된 FE 컴포넌트: N
- 테스트: FE ~215 / BE ~90 / E2E 8 / Golden 25
- Lighthouse 평균: N
- 배포: Vercel ✅ Fly.io ✅ Neon ✅
- 데모 리허설: N회 × 8분 — 평균 N분 N초

## 남은 followups
- ...

## 회고
- 잘한 것
- 개선할 것
```

### 10.5 Known gotchas (착수 시 주의할 것)

1. **`/analyze` → `/market-analyze` 리네임**: 기존 사이드바 active state, E2E 셀렉터, MEMORY 참조 모두 갱신 필요
2. **Lightweight Charts 다중 패널**: RSI/MACD 추가 시 main chart 와 **시간축 동기화** 필수 (`syncPriceScale`)
3. **SSE + Fly.io**: proxy idle timeout 기본 60s → `fly.toml` 에서 `timeout_idle = 120` 로 올리기
4. **MSW + Playwright**: `NEXT_PUBLIC_MSW=true` 로 빌드한 번들에서만 MSW 활성. `playwright.config.ts` webServer command 재확인
5. **Alembic 새 테이블**: `watchlist`, `user_settings`. 기존 마이그레이션 체인과 충돌 없는지 `alembic heads` 로 확인
6. **재작성 대상 기존 파일**: 기존 `/analyze` stub 페이지는 **삭제가 아니라 redirect** — 외부 링크 안전
7. **다크모드 기본**: 이미 기본값 dark 일 수 있음 (`ThemeProvider` 확인). 라이트 전환은 settings 에서
8. **CSV 업로드 파일 ID**: `/tmp` 는 serverless 에서 사라짐 → Fly.io 는 persistent volume 또는 S3 presigned URL 로 대체 필요

---

## 11. 착수 전 최종 체크리스트

- [ ] 본 문서를 끝까지 한 번 읽었는가?
- [ ] 목업 8장을 순서대로 다시 열어봤는가?
- [ ] `git checkout -b feat/sprint-08-full-mockup-match` (신규 브랜치) 또는 기존 브랜치 결정
- [ ] `uv sync` + `npm install` 최신 상태
- [ ] Postgres/Redis 로컬 실행 중인지 (`docker compose up -d postgres redis`)
- [ ] Phase A (사이드바 IA + 라우트 스켈레톤) 로 시작
- [ ] §5 프롬프트를 하나씩 Agent 에게 던지기 전에, 해당 §4.X 섹션을 같이 첨부

---

**끝.** 이 문서만으로도 Sprint-08 을 처음부터 끝까지 재현 가능해야 한다. 부족한 부분이 발견되면 먼저 이 문서를 갱신하고 그 다음 코드로 이동할 것.
