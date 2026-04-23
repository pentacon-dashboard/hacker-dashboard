# 대시보드 2차 이터 — 부족한 부분 / 다음 세션 할 일

작성일: 2026-04-23
브랜치: `feat/qa-harness-20260422-111542-nl-copilot-sprint-06`

2차 이터(픽셀 gap #1~#9) 로 목업과 시각적으로 1:1 매치는 완료. 단, 다음 항목들이 남아 있음.

## 1. 테스트 커버리지 공백 (우선순위 高)

신규·변경 컴포넌트에 vitest 유닛이 전혀 없음. `format.ts` 에만 유닛이 추가됨.

| 컴포넌트 | 필요한 테스트 |
|---|---|
| `KpiCard` | `accent` prop → 배경 클래스 매핑, `icon` 유무 렌더 |
| `AllocationBreakdown` | 빈 데이터 empty state, 정렬 순서(ratio desc), 금액·퍼센트 포맷 |
| `PeriodTabs` | 클릭 시 `onChange` 호출, 활성 탭 `aria-selected=true` |
| `TopHoldingsTable` | 6컬럼 헤더, `totalValueKrw` 미제공 시 fallback 계산, 비중 소수점 |
| `DimensionBars` | 비중·수익률 2 시리즈 Bar 존재, Legend 엔트리 2개 |
| `NewsPanel` | `thumbnail_url` 있을 때 `<img>` 렌더, 없을 때 이니셜 박스 fallback |

목표: 기능당 3~5 케이스, 총 ~25 테스트.

## 2. MSW 핸들러의 `period_days` 반영 누락

`frontend/tests/mocks/dashboard.ts` 의 `/portfolio/summary` 핸들러가 `period_days` 쿼리를 에코만 하고 실제 수치는 동일. 그래서 기간 탭(1W/1M/3M/1Y) 클릭해도 시각적으로 아무 변화가 없음 → 탭이 "작동"하는지 사용자가 확신할 수 없음.

**해결**: `period_days` → `period_change_pct` 를 서로 다른 값으로 매핑(`7→0.41`, `30→1.23`, `90→3.82`, `365→12.70`) + snapshots 길이도 days 만큼 조정.

## 3. 뉴스 썸네일 broken image fallback 없음

`next/image unoptimized` 로 `picsum.photos` 를 그대로 띄우는데, 네트워크 실패나 404 시 broken image 심볼만 보임. `<Image>` 의 `onError` 로 이니셜 박스로 폴백하거나, 서버측에서 thumbnail_url 유효성 검증 필요.

## 4. `next.config.ts` remotePatterns 가 너무 관대

`hostname: "**"` 는 내부 테스트엔 편하지만 프로덕션 릴리스 전에는 화이트리스트로 좁혀야 함 (naver, reuters, bloomberg, coindesk, samsung, picsum 등).

## 5. E2E 시나리오 미갱신

`frontend/e2e/*.spec.ts` 에 대시보드용 신규 시나리오 없음. 추가 후보:
- 기간 탭 클릭 → URL · 데이터 갱신 확인
- AllocationBreakdown 의 금액 테이블 5행 이상 존재
- 뉴스 패널 `<img alt="">` 썸네일 5개

smoke.spec.ts 는 의도적으로 loose selector 라 브레이크 없음.

## 6. 리스크 게이지 카피 혼선

목업의 68.3% "입출금 위험 분석" vs 현재 12.4% "집중도 리스크 / 양호". 사용자 결정으로 HHI 유지지만, 심사 현장에서 "목업이랑 수치가 왜 달라요?" 질문 가능성 있음. 데모 스크립트에 "집중도는 HHI 로, 단일 자산 편중을 잡는 지표입니다" 한 줄 대사 삽입 권장.

## 7. ADR 미작성

sprint-07 대시보드 확장 결정 — `PortfolioSummary` 에 `holdings_count`/`worst_asset_pct`/`risk_score_pct`(HHI×100)/`period_change_pct`/`period_days`/`dimension_breakdown` 추가, `Citation.thumbnail_url` 추가 — 가 ADR 로 기록되지 않음. `docs/adr/0007-dashboard-summary-expansion.md` 로 요약 필요.

## 8. 모바일/다크모드 스폿체크

스크린샷은 `viewport: 1440×900` 데스크탑으로만 캡처. 모바일(375px) 에서 KPI 2×3 그리드·AllocationBreakdown md 미만 1열·TOP5 테이블 overflow scroll 이 의도대로인지 수동 확인 안 됨. 다크모드도 미확인.

## 9. `AssetPie` 컴포넌트 재사용처 확인됨 — cleanup 불필요

대시보드 홈은 `AllocationBreakdown` 으로 교체됐지만 `components/dashboard/watchlist-summary.tsx`, `app/portfolio/page.tsx`, `components/portfolio/asset-pie-chart.tsx` 에서 여전히 사용 중. 삭제 금지.

## 10. Lint 기존 warning 4건

내 변경과 무관하지만 남아있음:
- `symbol-analysis-section.tsx:54` unused eslint-disable
- `hooks/use-copilot-session.ts:3` unused `useEffect`
- `lib/realtime/use-realtime-ticker.ts:142` unused eslint-disable
- `public/mockServiceWorker.js:1` unused eslint-disable

별도 chore PR 로 정리 권장.

## 11. BE contract 테스트 미실행

`uv run pytest -k "(portfolio or news) and contract"` 는 `localhost:8000` 서버 띄워야 해서 로컬 실행 생략. CI 파이프라인에서는 돌아가야 함 — `Citation.thumbnail_url` 추가로 contract 가 깨지지 않는지 CI 결과 확인 필요.

## 우선순위 요약

- **다음 세션 첫 할 일**: #1 테스트 + #2 MSW 다양화 (탭이 "살아 있음" 시연 효과)
- **심사 전 필수**: #6 데모 스크립트 한 줄, #7 ADR
- **릴리스 전**: #3 fallback, #4 remotePatterns, #5 E2E, #11 contract CI 확인
- **Nice to have**: #8 모바일/다크 스폿체크, #10 lint cleanup
