# hacker-dashboard — 심사위원용 제출 요약

## 제품

임의 투자 데이터 스키마에서 자동으로 분석 뷰를 생성하는 범용 금융 대시보드.
CSV 파일 드롭 한 번으로 5초 내 국내주식·해외주식·코인 통합 분석 화면을 구성합니다.

## 배포 URL

| 서비스 | URL |
|--------|-----|
| Frontend | https://hacker-dashboard.vercel.app |
| Backend API | https://hacker-dashboard-api.fly.dev |
| Swagger | https://hacker-dashboard-api.fly.dev/docs |

## 시드 데이터

### 데모 포트폴리오 (5종)

심사용 고정 샘플. 실거래 데이터 아님.

| Market | Code | Quantity | Avg Cost | Currency | 의도 |
|---|---|---|---|---|---|
| naver_kr | 005930 | 10 | 75,000 | KRW | 한국주식 (삼성전자) |
| yahoo | AAPL | 5 | 185.00 | USD | 미국주식 |
| yahoo | TSLA | 3 | 250.00 | USD | 미국주식 |
| upbit | KRW-BTC | 0.05 | 85,000,000 | KRW | 코인 |
| upbit | KRW-ETH | 1.2 | 4,500,000 | KRW | 코인 |

자산군 분산: 주식 우위 + 코인 비중으로 크로스-자산 분석을 시연하기 위한 구성.

삽입 방법:
- 로컬: `make seed-db`
- 프로덕션: `./scripts/run-prod-migration.sh` (자세한 내용: [docs/ops/neon-runbook.md](../docs/ops/neon-runbook.md))

## 테스트 수치

| 영역 | 결과 |
|------|------|
| BE pytest | 322 통과 |
| FE vitest | 77 통과 |
| E2E Playwright | 21 시나리오 |
| 골든 샘플 | 26종 |
| Router heuristic 커버리지 | 100% |
| Lighthouse Performance | 90+ |

증가 상세:
- BE pytest: 276 → 322 (리밸런싱 서비스 26 + 엔드포인트 9 + analyzer 10 + 기타 1 = +46)
- FE vitest: 60 → 77 (RebalancePanel / RebalanceActionTable / AllocationCompareChart +17)
- E2E: 13 → 21 (rebalance.spec.ts 4건 + portfolio 확장 4건)
- 골든 샘플: 23 → 26 (rebalance_balanced / rebalance_crypto_heavy / rebalance_constraint_violation +3)

## 로컬 실행

```bash
git clone <repo>
cd hacker-dashboard
cp frontend/.env.production.example frontend/.env.local
# .env.local 에서 ANTHROPIC_API_KEY 설정

docker compose up -d --wait
# FE: http://localhost:3000
# BE: http://localhost:8000/docs
```

마이그레이션:
```bash
cd backend && DATABASE_URL="postgresql+asyncpg://hacker:hacker@localhost:5432/hacker_dashboard" uv run alembic upgrade head
```

데모 시드 삽입:
```bash
make seed-db
```

시드 후 `/portfolio` 페이지에 5종 holdings가 즉시 표시됩니다.

## 데모 시나리오

[demo/scenario.md](../demo/scenario.md) — 8분 타임라인 + 리허설 체크리스트

## 아키텍처

[submission/architecture.md](architecture.md)

## 전체 테스트 커버리지

[submission/test-coverage.md](test-coverage.md)
