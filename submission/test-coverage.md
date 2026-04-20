# 테스트 커버리지 최종 수치

기준일: 2026-04-19

## 요약

| 영역 | 수치 | 상태 |
|------|------|------|
| Backend pytest | **211** 통과 | 통과 |
| Frontend vitest | **54** 통과 | 통과 |
| E2E Playwright | **13** 시나리오 통과 | 통과 |
| Router heuristic 커버리지 | **100%** | 통과 |
| Contract (schemathesis) | 통과 | 통과 |
| OpenAPI 스키마 | **1692** 라인 | - |

---

## Backend pytest (211)

| 모듈 | 테스트 수 |
|------|----------|
| `app/routes/` | ~60 |
| `app/services/` | ~70 |
| `app/agents/router` | ~30 |
| `app/agents/analyzers` | ~35 |
| `app/quality_gate/` | ~16 |

커버리지 목표: 80% (CI `--cov-fail-under` 점진 상향 예정)

---

## Frontend vitest (54)

| 모듈 | 테스트 수 |
|------|----------|
| 컴포넌트 단위 | ~30 |
| 훅 (usePortfolio, useWatchlist 등) | ~14 |
| 유틸 / 스키마 | ~10 |

---

## E2E Playwright (13)

| 파일 | 시나리오 |
|------|---------|
| `smoke.spec.ts` | 3 (홈 렌더, 다크모드, BE health) |
| `watchlist.spec.ts` | 3 |
| `symbol-detail.spec.ts` | 3 |
| `portfolio.spec.ts` | 3 |
| `production.spec.ts` | 3 (프로덕션 smoke) |

---

## Router Heuristic 커버리지 (100%)

자산군 판별 규칙 케이스:
- 국내주식 (KRX/KOSPI 티커 패턴)
- 해외주식 (NYSE/NASDAQ)
- 코인 (Upbit KRW-*, Binance USDT)
- 환율 (통화쌍 패턴)
- 혼합 (2종 이상 자산군)
- 알 수 없음 → fallback

---

## Contract (schemathesis)

`shared/openapi.json` (1692 라인) 대상 schemathesis 전수 검사:
- 상태코드 계약
- 응답 스키마 일치
- 에러 응답 포맷

---

## Lighthouse (최종)

[docs/perf/final-scores.md](../docs/perf/final-scores.md) 참조.

목표: Performance 90+, Accessibility 90+
