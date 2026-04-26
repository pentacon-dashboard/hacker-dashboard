# Next Actions — 2026-04-23 복귀 기준 (자기완결적)

| 항목 | 값 |
|---|---|
| 작성일 | 2026-04-23 저녁 |
| 대상 브랜치 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-06` |
| 작성 근거 | 오늘 세션에서 실측: BE contract 12/24 fail + 목업 8 페이지 중 1장만 매치 |
| 이 문서의 역할 | 다음 세션에서 **이 문서만 열어도** 바로 이어서 실행 가능하도록 상태+경로+커맨드를 박제 |
| 상위 문서 | `docs/prd/sprint-08-full-mockup-match.md` (Phase/페이지별 상세 설계), `docs/qa/mockup-gap-analysis-2026-04-23.md` (목업 gap 원본 분석) |

---

## 0. 복귀 첫 5분 절차 (TL;DR)

```bash
cd /c/Users/ehgus/hacker-dashboard
git status                        # untracked 확인
git log --oneline -5              # 03abe91 이후 진전이 있는지 확인
git branch --show-current         # feat/qa-harness-20260422-111542-nl-copilot-sprint-06 기대
```

그 다음:

1. **이 파일의 §1 "현재 상태"** 훑어서 스냅샷 머릿속에 로드
2. **§2 경로 분기** 에서 PATH A / PATH B 중 하나 결정 (심사 일정 기준)
3. 결정한 PATH 의 섹션으로 이동 (§3 또는 §4)
4. 서버 기동이 필요하면 §5 치트시트 사용

**상시 금지 사항** (§6 도 참고):
- 새 `/harness-run` 을 메인 저장소에서 시작하지 말 것 — 기존 브랜치 컨텍스트 유지
- `main` 강제 푸시 금지
- BE 에서 `shared/openapi.json` **수동 편집** 금지 — 변경은 FastAPI 라우터/스키마에서 하고 `python -m app.export_openapi > shared/openapi.json` 으로 재생성해야 drift 안 생김 (03abe91 의 교훈)

---

## 1. 현재 상태 스냅샷 (2026-04-23 종료 시)

### 1.1 Git

- 브랜치: `feat/qa-harness-20260422-111542-nl-copilot-sprint-06` (origin 대비 22 commits ahead)
- 최근 커밋:
  - `03abe91 fix(be): contract 테스트 통과 위한 최소 수정` ← **부분 수정, 실제로는 여전히 FAIL** (§1.2 참고)
  - `689340e docs(adr): 0013 대시보드 Summary 스키마 확장 결정`
  - `f332b26 docs(qa): 모바일 스폿체크 이슈 2건 해소 재캡처`
  - `a6e048a feat(fe): 모바일 사이드바 drawer/햄버거 패턴 (<md)`
  - `e17ed99 fix(fe): 모바일 KPI 일간 변동 truncate 해소`
- untracked (의미 있는 것만):
  - `docs/prd/sprint-08-full-mockup-match.md` — Sprint-08 실행 계획 (커밋 안 했음)
  - `docs/qa/mockup-gap-analysis-2026-04-23.md` — 목업 gap 원본 분석
  - `current-*.png` 9장, `compare-*.png` 8장 — 대조용 캡처. `.playwright-mcp/` 로 옮기거나 .gitignore에 `current-*.png`, `compare-*.png` 추가 필요
  - `frontend/next-env.d.ts` (자동 생성, 무시)

### 1.2 품질 게이트 실측 (2026-04-23)

| 게이트 | 결과 | 세부 |
|---|---|---|
| BE contract (`schemathesis`) | **FAIL** | 24 collected → 12 pass / 12 fail. 고유 실패 카테고리 7개 (§3.1) |
| BE unit/integration (`pytest -x --ignore=contract`) | **1 fail** | `tests/golden/test_copilot_end_to_end.py::test_follow_up_2turn_golden` — 베이스라인 재생성 필요 |
| BE OpenAPI drift | **drift 있음** | `shared/openapi.json` vs 런타임 `/openapi.json`: `PATCH/DELETE /holdings/{id}`, `GET /portfolio/snapshots`(중복 파라미터) |
| FE lint / typecheck / vitest / build | ✅ | lint 0 warning, 135/135 pass, build 성공 (직전 세션 실측) |
| FE Playwright E2E 3종 | ✅ | 6.1s (직전 세션) |

### 1.3 목업 vs 현재 매치도 (8 페이지)

| # | 라우트 | 매치도 | 주요 gap | 상세 |
|---|---|---|---|---|
| 00 | `/` | 🟢 85% | KPI 5번(오늘손익) · 중단 좌-우 순서 · 보유TOP5 7컬럼 · 시장주도주 카드 · 디멘션 섹터축 | §4.3 C0 |
| 01 | `/portfolio` | 🟡 35% | KPI 3→5 · 보유자산 상단 이동 · 섹터 히트맵 · 월간 달력 · AI 인사이트 | §4.3 C1 |
| 02 | `/watchlist` | 🔴 0% | empty state만. 9컬럼 테이블·사이드패널·알림설정 전부 부재 | §4.3 C2 |
| 03 | `/symbol/{market}/{code}` | 🟡 40% | 타임프레임 탭·RSI/MACD·지표카드6·뉴스 패널 부재 | §4.3 C3 |
| 04 | `/analyze` (→ `/market-analyze`) | 🔴 0% | "준비중" 스텁. 지수 KPI·세계지도·섹터·코모디티 전부 부재 | §4.3 C4 |
| 05 | `/copilot` | 🔴 404 | 라우트 자체 없음 (현재는 헤더 Drawer 만) | §4.3 C5 |
| 06 | `/upload` | 🔴 404 | **심사기준 #2 직격**. 라우트·BE 파이프라인 모두 부재 | §4.3 C6 |
| 07 | `/settings` | 🔴 0% | "준비중" 스텁. 6 섹션 모두 부재 | §4.3 C7 |

캡처 파일 위치: 루트의 `compare-00-dashboard.png` ~ `compare-07-settings.png` (dark, 1920×1080 (16:9), 3종목 시드).
목업 원본: `/c/Users/ehgus/Downloads/KakaoTalk_20260423_185428043[_01..07].png`.

### 1.4 BE 데이터 상태

- `/portfolio/holdings`: **3종목 시드됨** — `KRW-BTC`(upbit) / `AAPL`(yahoo) / `005930`(naver_kr). 재기동해도 유지됨(Postgres persistent).
- seed 커맨드 주의: `market` 은 **`upbit` | `binance` | `yahoo` | `naver_kr`** 네 값만 허용(`backend/app/schemas/portfolio.py:12` 참고). 그 외 값은 422. `notes` 필드는 스키마에 없음 — 넣으면 422.

---

## 2. 경로 분기 — 지금 결정 필요

심사 일정에 따라 둘 중 하나 선택.

### PATH A. 심사 직통 (1~2 working day)

**목표**: 현 스코프(7 페이지 중 대시보드 1장만 완성) 유지, BE contract 정비 + 배포 + 8분 데모.
**언제**: 심사까지 1주 이내 · Sprint-08 완주 리스크 감당 불가.
**결과물**: 심사 가능한 배포 URL + 데모 스크립트 런스루.
**한계**: 목업 8장 대비 여전히 7 페이지가 스텁/404. 심사에서 화면별 평가 받으면 감점 소지.

### PATH B. Sprint-08 풀 목업 매치 (7~10 working day)

**목표**: 목업 8장 전부 1:1 매치 + BE 실데이터 대응 + 문서 retrofit + 배포.
**언제**: 심사까지 2주+ 여유 · 기술심사 기준 #2(임의 CSV → 대시보드) 서사를 완성하고 싶을 때.
**결과물**: 목업 수준 UI 8장 + ADR 0014~0018 + 배포.
**전제**: PATH A 의 BE contract 수정(§3.1) 은 Phase B0 로 **먼저** 수행. Golden 재생성도 선행.

### 추천

- 심사 일정 ≤ 1주 → **PATH A**
- 심사 일정 > 1주 → **PATH B** (Phase 순서만 지키면 병렬화로 1.5주 가능)

**현재 시점에서는 심사 날짜가 명시되지 않음** — 복귀 첫 행동으로 날짜 확인 후 선택.

---

## 3. PATH A 상세 — 심사 직통

### 3.1 BE contract 수정 (백엔드 엔지니어 위임)

오늘 실측 결과(schemathesis + pytest contract) 고유 실패 7 카테고리. 각 항목은 **코드를 고치고 `python -m app.export_openapi > shared/openapi.json` 로 재출력** 하는 것이 원칙.

- [ ] **A1-1. 404 미선언 4 엔드포인트에 responses 추가**
  - 대상:
    - `GET /market/quotes/{market}/{code}` (`backend/app/api/market.py`)
    - `GET /market/ohlc/{market}/{code}` (동)
    - `DELETE /market/watchlist/items/{item_id}` (동)
    - `GET /copilot/session/{session_id}` (`backend/app/api/copilot.py`)
  - 수정: 각 라우트 decorator 에 `responses={404: {"model": HTTPValidationError}}` 추가
  - 검증: `curl -s http://localhost:8000/market/ohlc/invalid/xxx -o /dev/null -w "%{http_code}\n"` → 404, 스키마 포함 여부 swagger-ui 로 확인
- [ ] **A1-2. `HTTPValidationError.detail` 을 배열 타입으로 통일**
  - 대상 (03abe91 에서 `POST /holdings` 만 고치고 나머지 누락):
    - `POST /market/watchlist/items` (`backend/app/api/market.py`) — 현재 `raise HTTPException(400, detail="...")` 를 `detail=[{"msg":"...","type":"business"}]` 형태로
    - 기타 `detail=str` 로 남아있는 400/422 전부 grep 해서 통일
  - 대안: `shared/openapi.json` 의 `HTTPValidationError.detail` 을 `anyOf: [string, array]` 로 선언 변경
  - 검증: `uv run schemathesis run ... --checks response_schema_conformance`
- [ ] **A1-3. `GET /portfolio/snapshots` 500 버그 수정 (`backend/app/api/portfolio.py`)**
  - 현상: `to=false` 같이 비날짜 문자열 입력 시 파싱 전 validation 없어 500
  - 수정: `from_`, `to` 파라미터를 단일 `Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")` 로 통일 + 파싱 실패 시 400
  - 부수 효과: 중복 파라미터 drift (런타임에 anyOf null + pattern 버전이 각각 2개씩 = 4개) 도 자연 해소
  - 검증: `curl 'http://localhost:8000/portfolio/snapshots?to=false'` → 422
- [ ] **A1-4. `POST /copilot/query` SSE 스키마 수정 (`backend/app/api/copilot.py`)**
  - 현상: response schema 가 `type: string` 인데 실제로는 SSE event object 반환
  - 수정 옵션 ①: `responses={200: {"content": {"text/event-stream": {"schema": {"type":"string"}}}}}` 로 미디어타입 명시
  - 수정 옵션 ② (권장): SSE 엔드포인트는 schemathesis 에서 제외. 테스트 picklist 에 `--exclude-path /copilot/query`
  - 검증: schemathesis CLI 재실행
- [ ] **A1-5. `POST /portfolio/rebalance` positive_data_acceptance 실패**
  - 현상: target_allocation 전부 0 허용하면 422
  - 수정: `RebalanceConstraints` pydantic validator 로 `sum(target_allocation.values()) > 0` 검증 + 422 메시지에 힌트
  - OR: schemathesis 에 `x-example` 로 유효 예시 제공
- [ ] **A1-6. `POST /analyze/csv` undocumented 400**
  - 현상: multipart parsing 실패 시 400 반환인데 responses 에 선언 안 돼 있음
  - 수정: `responses={400: {...}, 422: {...}}` 명시
- [ ] **A1-7. export 후 drift 0 확인**
  - `python -m backend.app.export_openapi > shared/openapi.json` 실행
  - `git diff shared/openapi.json` 로 변경 확인
  - schemathesis 재실행으로 전체 PASS 기대

### 3.2 Golden 재생성 (analyzer-designer 또는 backend-engineer)

- [ ] **A2-1. `tests/golden/baselines/follow_up_2turn.json` 재생성**
  - 원인: 직전 뉴스 데이터 변동으로 step.result 카드 내용 index 24 diverge
  - 방법:
    1. 파일 삭제
    2. `uv run pytest backend/tests/golden/test_copilot_end_to_end.py::test_follow_up_2turn_golden --update-baselines` (플래그 없으면 `BASELINE_UPDATE=1 pytest ...` 등 프로젝트 규약 확인)
    3. 재실행 후 PASS
  - 주의: 실제 diff 검토 후 "뉴스 본문만 바뀐 것인지, 로직 regression 인지" 먼저 판단

### 3.3 배포 체크리스트 (integration-qa)

전제: §3.1 §3.2 통과.

- [ ] 환경변수 dump (`.env.example` 기준) → Vercel + Fly.io dashboard 주입 (실제 시크릿은 로컬에서만)
- [ ] `fly deploy` (backend) — `backend/fly.toml` 사용
- [ ] `vercel --prod` (frontend) — `frontend/` 에서
- [ ] 배포 후 headcheck:
  - `curl https://<be>.fly.dev/health` → 200
  - `curl https://<fe>.vercel.app/` → 200
  - `curl https://<be>.fly.dev/portfolio/holdings` → 빈 배열 또는 seed
- [ ] CORS 점검: FE origin 이 BE 의 `allow_origins` 에 포함되는지
- [ ] demo-script 스킬로 "배포된 환경" 버전 리허설 재실행

### 3.4 8분 데모 리허설

- `demo-script` 스킬 실행 — 기존 `docs/qa/demo-rehearsal-2026-04-22.md` 기준
- HHI 12.4% vs 목업 68.3% 설명 대사(`eda3f18` 에서 추가됨) 숙지
- 네트워크 불량 fallback 대사 준비 (Fly.io 지역 지연 시)

---

## 4. PATH B 상세 — Sprint-08 풀 목업 매치

**상세 Phase/페이지 설계는** `docs/prd/sprint-08-full-mockup-match.md` **를 단일 진실로 사용**. 아래는 그 문서를 보완하는 "실행 레이어" 체크리스트.

### 4.0 전제 (Phase B0 — 반일)

Sprint-08 시작 전 **PATH A 의 §3.1(BE contract) + §3.2(golden)** 를 먼저 마무리해야 함. 안 그러면 Phase B 에서 엔드포인트 추가할 때마다 contract 빨강이 누적됨.

- [ ] B0-1. `§3.1 A1-1 ~ A1-7` 전부 완료
- [ ] B0-2. `§3.2 A2-1` 완료
- [ ] B0-3. `feat/sprint-08-full-mockup-match` 신규 브랜치 분기 (현 브랜치에서 squash 후 or rebase off main 고민 필요 — main 대비 22 commits ahead 상태)
- [ ] B0-4. `v0.3.0-sprint-07-complete` 태그 부여 후 롤백 앵커 확보

### 4.1 Phase A — 기반 (1일, A-0 → A-1/2/3 병렬)

목적: **공통 레이아웃 쉘 재구축(A-0) + 라우트 스켈레톤(A-1~A-3)**. Phase B/C 는 A-0 완료 후 착수. A-1~A-3 은 A-0 와 **병렬 가능** (파일 영역 분리).

- [ ] **A-0. Global Shell 재구축 (최우선, 목업 8장 공통 요소)** — 상세는 `docs/prd/sprint-08-full-mockup-match.md` §4.0
  - [ ] A-0-1. `components/layout/logo-badge.tsx` 신규 — "HACKER / DASHBOARD" 두 줄 배지 (접힘 시 "HD")
  - [ ] A-0-2. `components/layout/sidebar.tsx` 재편 — navItems 8개로 교체 (`대시보드/포트폴리오/워치리스트/종목분석/시장분석/코파일럿/업로드&분석/설정`), `/analyze` 엔트리 제거, `/news` 제거, `<LogoBadge />` 상단 통합
  - [ ] A-0-3. `components/layout/sidebar-user-card.tsx` 신규 — Demo User 프로필 (아바타 + 이름 + 이메일), `GET /users/me` stub 사용
  - [ ] A-0-4. `components/layout/market-status-card.tsx` 신규 — 세션 상태 + 현재 시각 + 거래량 배지 (클라이언트 시각 only, BE 연동 생략)
  - [ ] A-0-5. `components/layout/header.tsx` 리팩토링 — 중앙 CommandBar 제거 (⌘K 핫키로만 유지, Drawer 는 그대로), 좌측 페이지 제목 텍스트 제거, 우측에 `DateRangePicker` + `NotificationBell` + `CsvUploadButton` + 기존 theme/health 유지
  - [ ] A-0-6. `components/layout/date-range-picker.tsx` 신규 — react-day-picker 기반 shadcn wrapper. URL query string 과 동기화
  - [ ] A-0-7. `components/layout/notification-bell.tsx` 신규 — 벨 아이콘 + unread 배지 (stub 카운트)
  - [ ] A-0-8. `components/layout/csv-upload-button.tsx` 신규 — `Upload` 아이콘 outline 버튼 → `router.push('/upload')`
  - [ ] A-0-9. `components/layout/footer.tsx` 신규 — "데모용 • 가격 데이터: FinHub, IEX, Alpha Vantage, Bloomberg, Reuters / 실시간 지연 약 20분 / 업데이트: {Intl.DateTimeFormat}". `app/layout.tsx` 에 통합 (sticky bottom)
  - [ ] A-0-10. `tailwind.config.ts` + `globals.css` 팔레트 보정 — 카드 배경 `#0F1420~#131A2C`, accent 보라/청록
  - [ ] A-0-11. FE vitest 각 신규 컴포넌트 3 케이스 + `shell.spec.ts` E2E 1건 (8항목 존재 + 토글 + CSV 버튼 네비 + 풋터 텍스트)
  - [ ] A-0-12. 1920×1080 (16:9) dark 캡처 → 목업 00 과 공통 쉘 구조 매치 확인
- [ ] **A-1. 사이드바 IA 재편** (A-0-2 에 흡수됨 — 별도 작업 불필요)
  - 8 항목 순서: `대시보드 / 포트폴리오 / 워치리스트 / 종목 분석 / 시장 분석 / 코파일럿 / 업로드 & 분석 / 설정`
  - 현재 `뉴스` 엔트리 제거 (대시보드 우하단 패널로 흡수)
  - 각 엔트리 lucide 아이콘 매핑: `LayoutDashboard / Briefcase / Eye / LineChart / Globe / Sparkles / Upload / Settings`
  - 활성 상태 시각 (현재 스타일 유지) · mobile drawer 는 `a6e048a` 에서 이미 작업됨, 엔트리 수만 늘면 OK
- [ ] **A-2. 라우트 스켈레톤 3개 생성**
  - `frontend/app/copilot/page.tsx` (서버 컴포넌트 shell)
  - `frontend/app/upload/page.tsx`
  - `frontend/app/market-analyze/page.tsx` (기존 `analyze` 는 Sprint-08 후반에 리다이렉트 or 삭제 결정)
  - 각 파일은 `<PageShell title="...">준비 중 (Sprint-08)</PageShell>` 수준으로 시작 — Phase C 에서 실체 구현
- [ ] **A-3. OpenAPI drift 가드 CI 스크립트**
  - `backend/scripts/check_openapi_drift.py` 신규 또는 기존 export 스크립트에 `--check` 모드 추가
  - GitHub Action: BE 서버 기동 → `/openapi.json` fetch → `shared/openapi.json` 과 diff → fail

### 4.2 Phase B — BE 스키마 & 엔드포인트 (2~3일, 최대 7명 병렬)

병렬 가능 경계: 각 B-x 는 파일/서비스가 분리되어 있어 **동시 작업 OK**. Alembic 마이그레이션만 순차.

- [ ] **B-1. Portfolio 확장**
  - `backend/app/schemas/portfolio.py` `PortfolioSummary` 에 필드 추가: `win_rate_pct: float`, `market_leaders: list[MarketLeader]`
  - 신규 엔드포인트:
    - `GET /portfolio/sectors/heatmap` → `[{sector:"IT", weight_pct:32.1, return_pct:+4.2}, ...]`
    - `GET /portfolio/monthly-returns?year=2026` → `[{date:"2026-01-01", return_pct:+2.3, value:...}]` 365칸
    - `GET /portfolio/ai-insight` → `{headline, bullets:[3], stub: true}` — ADR 0012 stub 모드 재사용
  - 서비스: `backend/app/services/portfolio_service.py` 에 `calc_win_rate`, `sector_heatmap`, `monthly_returns` 추가
  - 테스트: unit 3, integration 3
- [ ] **B-2. Watchlist 풀 구현**
  - `GET /watchlist/items` (기존 있음)
  - 신규:
    - `GET /watchlist/summary` → KPI 4개 (count/rise_avg/fall_avg/top_performer)
    - `GET /watchlist/popular` → `[{symbol, views, change_pct}]` 5건
    - `GET /watchlist/gainers-losers` → `{gainers:[5], losers:[5]}`
  - `frontend/tests/mocks/watchlist.ts` 10종목 시드 (BTC/ETH/삼성전자/SK하이닉스/AAPL/TSLA/NVDA/MSFT/AMZN/META)
  - DB 영향: 기존 `watchlist_items` 테이블 사용 or 확장
- [ ] **B-3. Symbol indicators (기술지표 서버 계산)**
  - `GET /symbol/{market}/{code}/indicators?timeframe=1D` → `{rsi_14, macd:{line,signal,hist}, bollinger:{upper,mid,lower}, stochastic:{k,d}, obv, ma20, ma60}`
  - 계산 라이브러리: `ta-lib` 대체로 `pandas_ta` 또는 수동 구현(기존 ohlc 서비스 재사용)
  - 왜 서버 계산: 브라우저 부담 ↓ + 골든 회귀 테스트 가능
  - 골든: 8 심볼 스냅샷
- [ ] **B-4. Market 신규**
  - `GET /market/indices` → `{kospi, kosdaq, sp500, nasdaq, dow, vix, usd_krw}` — **stub JSON** 우선 (실 API 연동은 non-goal)
  - `GET /market/sectors` → `[{sector:"반도체", change_pct:+3.2, constituents:3}, ...]` 10~15 섹터
  - `GET /market/commodities` → `[{symbol:"GC=F", name:"금", price, change_pct}]` 5~6 종목
  - `GET /market/world-heatmap` → `[{region:"asia", country:"KR", return_pct:+1.2}]` — 옵션 F-2 면 구현, F-1 이면 생략
- [ ] **B-5. Upload 파이프라인**
  - `POST /upload/csv` (multipart) → `{upload_id, rows_total, rows_valid, rows_error, rows_warning, preview: [5 rows]}`
  - `POST /upload/analyze` (SSE stream) → ADR 0003 의 3단 게이트 진행 이벤트 스트림
  - `GET /upload/template` → text/csv 응답. sample 헤더
  - 검증 룰: 날짜 포맷 / 수량 양수 / 통화 enum
  - **심사 기준 #2 핵심**. 5종 샘플 CSV 구비 (정상 2 + 에러 있는 2 + 경고 1)
- [ ] **B-6. Users settings**
  - `GET /users/me/settings`, `PATCH /users/me/settings`
  - 필드: `name/email/language/timezone/theme/notifications/refresh_interval/auto_backup/connected_accounts`
  - 인증: 현재 프로젝트에 인증 레이어가 없음 — 우선 `X-User-Id` header 기반 fake auth 로 진행 (ADR 0004 참고)
- [ ] **B-7. Copilot 세션 히스토리**
  - `GET /copilot/sessions` → `[{session_id, title, last_message_at, preview}]` 최근 20건
  - 기존 `POST /copilot/query` 는 그대로 재사용. 세션 저장만 추가.
  - 저장 위치: 현재 InMemoryStore (ADR 0005). Postgres 전환은 non-goal.

### 4.3 Phase C — FE 컴포넌트 & 페이지 (3~4일, 병렬 가능)

병렬 경계: 각 C-x 는 `frontend/app/{route}/` 파일 단독이므로 **동시 작업 OK**. 공통 컴포넌트는 `components/ui/` 에만 두고 중복 정의 금지.

- [ ] **C-0. 대시보드 홈 미세 정리** (`frontend/app/page.tsx`)
  - KPI 5번 필드 변경: `최저 수익률` → `오늘 손익` (`total_pnl_today_krw`, `total_pnl_today_pct`)
  - 중단 row 좌-우 스왑: 왼쪽 = `자산 가치 추이 라인`, 중앙 = `AllocationBreakdown`
  - 헤더 우상단: `DateRangePicker` (shadcn) + `CSV 업로드` 버튼 (→ `/upload` 링크)
  - 하단 우 교체: `NewsPanel` → 신규 `<MarketLeaders>` 컴포넌트 (시장 주도주 3 카드). 뉴스는 유지하려면 별도 "관련 뉴스" 섹션에 이동
  - 보유 자산 TOP 5: 컬럼 2개 추가 (`평균가`, `현재가`)
  - 디멘션 분석 Y축: `asset_class` → `sector` 로 전환 (BE B-1 에서 `sector_heatmap` 확장 후)
- [ ] **C-1. 포트폴리오 풀 구현** (`frontend/app/portfolio/page.tsx`)
  - KPI 5 개: `총자산 / 총 평가손익 / 총 손익률 / 보유종목 / 승률 게이지`
  - 상단 중앙: `<HoldingsOverviewTable>` 10행 + 필터탭 (자산군/통화) + 정렬
  - 중단 우: `<AssetPieChart>` + 3컬럼 리스트
  - 중하: `<SectorHeatmap>` (신규, `components/portfolio/sector-heatmap.tsx`)
  - 좌하: `<PortfolioLineChart>` (기존 재사용)
  - 하중: `<MonthlyReturnCalendar>` (신규, GitHub contribution 스타일)
  - 우하: `<AiInsightCard>` (신규, stub 배지 + 3문장)
- [ ] **C-2. 워치리스트 풀 구현** (`frontend/app/watchlist/page.tsx`)
  - KPI 4 개
  - 메인: `<WatchlistTable>` 9컬럼 (심볼/현재가/변동/7일 스파크라인/거래량/시가총액/수익률/알림/삭제)
  - 사이드: `<PopularTop5>` + `<GainersLosersTop5>`
  - 하단: `<AlertSettings>` + `<CustomAlertSetup>` + `<RecentTrades>`
- [ ] **C-3. 종목 분석 확장** (`frontend/app/symbol/[market]/[code]/page.tsx`)
  - 상단 `<TimeframeTabs>` (1m/5m/15m/1h/4h/1d/1w/1m)
  - 메인 차트 아래 `<RsiPanel>` + `<MacdPanel>` 서브차트
  - 우: `<IndicatorPanel>` 숫자 리스트 + `<KeyIssuesList>`
  - 하단: `<IndicatorGrid>` 6 카드 + `<SymbolNewsPanel>`
- [ ] **C-4. 시장 분석** (`frontend/app/market-analyze/page.tsx`)
  - `<IndexKpiStrip>` 7 KPI (KOSPI/코스닥/S&P/나스닥/DOW/VIX/USD)
  - 옵션 F-1(권장): 세계지도 생략, 지역 KPI 3 카드로 대체
  - 옵션 F-2: `<WorldHeatmap>` (`react-simple-maps` 도입 — 번들 +150KB 감안)
  - `<SectorKpi>` + `<CommodityPanel>` + `<MarketNewsFeed>`
- [ ] **C-5. 코파일럿 풀페이지** (`frontend/app/copilot/page.tsx`, `frontend/app/copilot/[sessionId]/page.tsx`)
  - 좌 사이드: `<SessionSidebar>` 히스토리 (`GET /copilot/sessions`)
  - 중앙: `<ThreadView>` — 기존 `useCopilotSession` 훅 재사용
  - 우: `<QuickQuestions>` + `<PortfolioSummaryCard>` + `<AiInsightCard>` + `<RecentActivity>`
  - 헤더 Drawer 는 **유지** (dashboard 에서의 shortcut). 풀페이지는 `/copilot` 진입점 추가 형태
- [ ] **C-6. 업로드 & 분석** (`frontend/app/upload/page.tsx`) ★최우선
  - 5 카드 순차 레이아웃:
    1. `<DropzoneCard>` — drag&drop + 진행도
    2. `<ValidationCard>` — 전체/OK/오류/경고 카운트 대시
    3. `<PreviewTable>` 5행
    4. `<AnalyzerConfigCard>` — Analyzer select / 기간 / 통화
    5. `<AnalyzeProgressCard>` — Router → Schema → Domain → Critique 4단 배지 SSE
  - 하단: `<CsvTemplateCard>` + `<FaqPanel>`
- [ ] **C-7. 설정** (`frontend/app/settings/page.tsx`)
  - 6 섹션 2×3 그리드:
    - `<GeneralSettings>` (기본 form)
    - `<NotificationSettings>`
    - `<ThemeSettings>` (dark/light/system + 색상 팔레트)
    - `<DataSettings>` (refresh 주기, auto backup)
    - `<ConnectedAccounts>` (Google/Apple/Kakao stub)
    - `<SystemInfo>` (버전, API 상태, 캐시 clear)

### 4.4 Phase D — MSW + Golden 테스트 (0.5일)

- [ ] `frontend/tests/mocks/` 에 `watchlist.ts`, `market.ts`, `symbol-indicators.ts`, `copilot-sessions.ts`, `settings.ts`, `upload.ts` 신규
- [ ] 골든: `/upload` CSV 10종 (정상 5 + 오류 3 + 경고 2) → `backend/tests/golden/csv/`
- [ ] 골든: 시장 지수 스냅샷 5종 (장중/장후/주말/홀리데이/이상치)
- [ ] Playwright E2E 페이지당 1개 시나리오 (8 페이지 × 1 = 8 spec files)

### 4.5 Phase E — 문서 retrofit (반일)

완성된 코드 기준으로 ADR 신규 작성 ("감쪽같이 처음부터 이렇게 설계한 것처럼").

- [ ] `docs/adr/0014-dashboard-layout-rev.md` — 중단 좌-우 스왑 + market leaders 도입 근거
- [ ] `docs/adr/0015-portfolio-insight-trio.md` — sector heatmap + monthly calendar + ai insight 3-컴포넌트
- [ ] `docs/adr/0016-symbol-server-indicators.md` — RSI/MACD 서버 계산 선택 근거
- [ ] `docs/adr/0017-copilot-full-page-pivot.md` — Drawer → 풀페이지 전환
- [ ] `docs/adr/0018-csv-upload-pipeline.md` — 업로드 3단 게이트 파이프라인
- [ ] `docs/adr/0013-dashboard-summary-expansion.md` — `market_leaders` · `win_rate_pct` 필드 추가 반영 (기존 문서 갱신)
- [ ] `docs/qa/demo-rehearsal-2026-04-22.md` → 2026-04-3X 로 복제 · 8 페이지 서사로 재작성
- [ ] `CLAUDE.md` §공모전 심사 기준 정렬 테이블 업데이트

### 4.6 Phase F — 배포 + 리허설 (반일)

PATH A §3.3, §3.4 와 동일.

---

## 5. 서버 기동 · 검증 커맨드 치트시트

### BE 단독

```bash
cd /c/Users/ehgus/hacker-dashboard/backend
uv sync                    # 첫 실행 또는 의존성 바뀐 후
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# 확인: curl http://localhost:8000/health
# swagger-ui: http://localhost:8000/docs
```

### FE 단독

```bash
cd /c/Users/ehgus/hacker-dashboard/frontend
# 최초 또는 패키지 바뀐 후: npm ci
npm run dev
# 확인: http://localhost:3000 (⚠ `127.0.0.1:3000` 으로 들어가면 CORS fail — API 호출 실패함. `localhost` 로 접속 필수)
```

### MSW 모드 (BE 없이)

```bash
cd /c/Users/ehgus/hacker-dashboard/frontend
NEXT_PUBLIC_USE_MSW_WORKER=1 npm run dev
```

### OpenAPI 재출력

```bash
cd /c/Users/ehgus/hacker-dashboard
uv run python -m backend.app.export_openapi > shared/openapi.json
cd frontend && npm run gen:types   # package.json 확인 필요
```

### 품질 게이트 일괄

```bash
# BE
cd /c/Users/ehgus/hacker-dashboard/backend
uv run ruff check app tests
uv run mypy app
uv run pytest tests -x --ignore=tests/contract

# BE contract (BE 서버 기동 상태에서)
cd /c/Users/ehgus/hacker-dashboard
uv run schemathesis run shared/openapi.json --base-url http://127.0.0.1:8000 \
    --checks all --hypothesis-deadline=none --max-examples=30 \
    --exclude-checks negative_data_rejection

# FE
cd /c/Users/ehgus/hacker-dashboard/frontend
npm run lint
npm run typecheck
npm run test          # vitest
npm run test:e2e      # playwright
npm run build
```

### 3종목 시드 (테스트용)

```powershell
# PowerShell (bash 로는 JSON 이스케이프 문제로 422)
$h1 = '{"market":"upbit","code":"KRW-BTC","currency":"KRW","quantity":0.05,"avg_cost":95000000}'
$h2 = '{"market":"yahoo","code":"AAPL","currency":"USD","quantity":5,"avg_cost":200}'
$h3 = '{"market":"naver_kr","code":"005930","currency":"KRW","quantity":10,"avg_cost":75000}'
foreach ($h in @($h1,$h2,$h3)) { Invoke-RestMethod -Uri 'http://localhost:8000/portfolio/holdings' -Method Post -Body $h -ContentType 'application/json' }
```

### 다크모드 스크린샷 8장 (Playwright MCP)

- `mcp__playwright__browser_resize` 1920×1080 (16:9)
- 각 페이지 `browser_navigate` 후 `browser_evaluate` 로 `document.documentElement.classList.add('dark')` + `browser_wait_for` 3~5초 + `browser_take_screenshot` fullPage
- ⚠ 반드시 `http://localhost:3000` (127.0.0.1 아님)

---

## 6. 하지 말 것 (과거 실수 기록)

1. **`shared/openapi.json` 수동 편집 금지** — 03abe91 에서 수동 패치한 결과가 drift 로 남아 다음 세션에서 schemathesis 가 계속 false-positive 를 토했다. 반드시 BE 소스 → `export_openapi` 순서.
2. **`/harness-run` 을 메인 저장소에서 재시작 금지** — 기존 run id (`20260420-160548-competition-winner`) 이어가려면 `RESUME.md` 로 진입.
3. **Playwright MCP 로 `127.0.0.1:3000` 접근 금지** — FE의 `NEXT_PUBLIC_API_BASE` 는 `localhost:8000` 기본값이라 브라우저 CORS 가 다른 origin 으로 분리해 fetch 실패. 반드시 `localhost:3000`.
4. **홀딩 시드 시 `notes` 필드 금지** — `HoldingCreate` 스키마에 없어 422. `market` 은 `upbit/binance/yahoo/naver_kr` 만.
5. **Sprint-08 Phase B 먼저 들어가지 말 것** — Phase B0(§4.0) 의 contract + golden 정리가 선행되어야 함. 안 그러면 새 엔드포인트가 contract 빨강에 섞여 원인 분리 어려움.
6. **`current-*.png` / `compare-*.png` 커밋 금지** — 임시 비교용. `.playwright-mcp/` 로 이동하거나 .gitignore 등록.
7. **`/analyze` vs `/market-analyze`** — Sprint-08 이후 `/analyze` 는 폐기 예정. 새 기능은 `/market-analyze` 에만 붙일 것. 기존 링크는 Phase A-2 에서 리다이렉트 처리.

---

## 7. 의사결정 보류 중인 항목

아래는 다음 세션에서 사용자(본인) 확정이 필요한 항목. 메모가 있지만 실제 결정 전이라 코드 착수 불가.

- [ ] **Q-1**. 심사 일정이 언제인가? → PATH A / B 결정 직결
- [ ] **Q-2**. Sprint-08 실행 시 `feat/sprint-08-full-mockup-match` 신규 브랜치 vs 현 브랜치에서 squash? → 현재 현 브랜치가 22 커밋 ahead 라 squash 가 합리적이지만, 히스토리 보존 원한다면 신규 브랜치
- [ ] **Q-3**. 세계지도 heatmap (`/market-analyze` 옵션 F-2) 포함? → `react-simple-maps` 번들 +150KB 감안
- [ ] **Q-4**. 인증 레이어 — settings 를 위해 X-User-Id fake auth 로 갈지, 간단한 JWT 도입? → ADR 0004 재검토 필요
- [ ] **Q-5**. 업로드 CSV 의 실시간 3단 게이트 진행도 — SSE 유지 vs WebSocket? → SSE 가 기존 `/copilot/query` 와 일관되어 권장

---

## 8. 참조 포인터

- Sprint-08 상세 설계: `docs/prd/sprint-08-full-mockup-match.md`
- 목업 gap 원본: `docs/qa/mockup-gap-analysis-2026-04-23.md`
- 직전 이터 followups: `docs/prd/dashboard-iter2-followups.md`
- 데모 리허설: `docs/qa/demo-rehearsal-2026-04-22.md`
- 모바일 스폿체크: `docs/qa/dashboard-mobile-dark-spotcheck-2026-04-23.md`
- ADR: `docs/adr/0013-dashboard-summary-expansion.md`
- 하네스 일시중단: `.claude/harness/20260420-160548-competition-winner/RESUME.md` (별도 트랙 — Sprint-08 과는 독립)
- 메모리 인덱스: `C:\Users\ehgus\.claude\projects\c--Users-ehgus-hacker-dashboard\memory\MEMORY.md`

---

## 9. 본 문서의 수명

- 작성 근거가 된 실측(2026-04-23 BE contract fail 12/24, 목업 매치도)이 바뀌면 **이 문서를 먼저 갱신** 하고 메모리 포인터 최신화.
- PATH A 완료 시 §3 체크박스 전부 체크 후 "A 완료" 라는 한 줄과 머지 커밋 해시 추가.
- Sprint-08 시작하면 이 문서는 **Phase 체크리스트 용도** 로 유지. 상세 설계가 바뀌면 `sprint-08-full-mockup-match.md` 를 갱신.
- Sprint-08 완주 후 이 문서는 `archived/` 로 이동 + README 에 "다음 복귀 문서" 새 링크.
