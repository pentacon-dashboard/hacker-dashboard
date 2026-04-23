# 모바일/다크모드 스폿체크 — 2026-04-23

캡처일: 2026-04-23
브랜치: `feat/qa-harness-20260422-111542-nl-copilot-sprint-06`
스크립트: `frontend/scripts/dashboard-mobile-dark-snap.mjs`
dev 서버: `NEXT_PUBLIC_COPILOT_MOCK=1` 기동

## 스크린샷 경로

| 파일명 | 경로 |
|---|---|
| `dashboard-mobile-375.png` | `C:/Users/ehgus/AppData/Local/Temp/dashboard-mobile-375.png` |
| `dashboard-dark.png` | `C:/Users/ehgus/AppData/Local/Temp/dashboard-dark.png` |
| `dashboard-dark-mobile.png` | `C:/Users/ehgus/AppData/Local/Temp/dashboard-dark-mobile.png` |

---

## viewport 1: 375x812 (iPhone SE, 라이트 모드)

**이상 없음 (OK)**

- KPI 카드 2×3 그리드 정상 — 6개 카드가 2열 3행으로 깔끔하게 배치됨.
- 기간 탭(1W/1M/3M/1Y) + 날짜 범위 텍스트가 좁은 화면에서 줄바꿈 발생. 날짜("2026-03-24 ~ 2026-04-23")가 두 줄로 표시됨. 시각적으로 어색하지는 않으나 단일 행으로 개선하면 더 깔끔함 (nice-to-have).
- AllocationBreakdown 도넛 차트가 1열 레이아웃으로 전환되어 전체 너비 차지 — 의도대로.
- 일간 변동 KPI 값("+2.0...") 이 카드 너비 부족으로 truncate 됨. 수치가 잘려 "+2.0..." 으로 표시 — 주요 이슈, 다음 세션에서 값 포맷 단축(M/B 단위) 검토 권장.

**블로킹 여부:** 심사 데모 블로킹 아님. 기록만 남김.

---

## viewport 2: 1440x900 (데스크탑, 다크 모드)

**이상 없음 (OK)**

- `document.documentElement.classList.add('dark')` 주입 후 다크 팔레트 전환 정상 확인.
- 배경색, 카드, 텍스트, 차트 선/배경 모두 다크 토큰으로 교체됨.
- KPI 카드 6개 1행 배치, RiskGauge, DimensionBars, NewsPanel 모두 가시성 양호.
- 뉴스 패널 썸네일 이미지 5개 렌더 확인.

**블로킹 여부:** 없음.

---

## viewport 3: 375x812 (iPhone SE, 다크 모드)

**이상 없음 (OK)**

- 라이트 모바일과 동일한 레이아웃에 다크 팔레트 적용.
- KPI 카드 2×3 그리드, 다크 배경 적용 정상.
- 일간 변동 truncate 이슈는 라이트 모드와 동일하게 재현됨 (동일 원인).
- 네비게이션 사이드바 텍스트가 모바일 뷰에서 세로 방향으로 표시됨 ("대\n시\n보\n드" 식). 사이드바 모바일 collapse 처리가 완전히 되지 않은 것으로 추정. 심사 데모에서는 데스크탑 화면으로만 시연할 예정이므로 블로킹 아님.

**블로킹 여부:** 없음. 다음 세션: (1) 일간 변동 truncate 수치 포맷 단축, (2) 모바일 사이드바 collapse 처리를 `frontend-engineer` 에게 전달.

---

## 수정 권장 (다음 세션)

| 우선순위 | 이슈 | 대상 |
|---|---|---|
| 보통 | 모바일 375px 일간 변동 KPI truncate — "+2.0..." 로 잘림 | `frontend-engineer` |
| 낮음 | 모바일 기간 탭 날짜 범위 줄바꿈 | `frontend-engineer` |
| 낮음 | 모바일 사이드바 미collapse | `frontend-engineer` |

심사 전 수정 필수 항목은 없음.

---

## 2026-04-23 재캡처 해소

재캡처 일시: 2026-04-23
브랜치: `feat/qa-harness-20260422-111542-nl-copilot-sprint-06`
커밋: `e17ed99` (KPI 포맷), `a6e048a` (사이드바 드로어)

### 이슈 1: 일간 변동 KPI truncate — 해소

**수정 내용**
- `frontend/app/page.tsx`: `formatKRW` → `formatKRWCompact` 로 교체. 양수 부호(`+`) 명시 유지.
- `frontend/components/dashboard/kpi-card.tsx`: value 폰트 `text-base sm:text-lg md:text-xl` 로 반응형 clamp 추가.

**재캡처 확인**: 375x812 라이트/다크 모드 양쪽에서 "+2.04%" 및 "+₩373.1K" 모두 잘림 없이 표시됨.

### 이슈 2: 모바일 사이드바 미collapse — 해소

**수정 내용**
- `frontend/stores/ui.ts`: `mobileMenuOpen` / `toggleMobileMenu` / `setMobileMenuOpen` 추가.
- `frontend/components/layout/sidebar.tsx`: 고정(`fixed`) 햄버거 버튼 제거, 드로어 열림 상태를 Zustand store 에서 관리.
- `frontend/components/layout/header.tsx`: 햄버거 버튼을 Header 좌측 `md:hidden` 전용으로 이동. "금융 대시보드" 텍스트는 `hidden md:inline` 처리로 모바일 여백 확보.

**재캡처 확인**: 375x812 에서 사이드바가 화면에 노출되지 않음. 햄버거 버튼 클릭 시 Sheet 드로어 정상 오픈. 데스크탑(1440x900) 레이아웃 변경 없음.

### 품질 게이트 결과

| 게이트 | 결과 |
|---|---|
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm run test -- --run` | PASS (135/135) |
| `npm run build` | PASS |
| 재캡처 스크린샷 | `C:/Users/ehgus/AppData/Local/Temp/dashboard-mobile-375.png` 등 3장 갱신 |
