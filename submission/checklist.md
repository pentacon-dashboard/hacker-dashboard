# 제출 전 최종 체크리스트

기준일: 2026-04-19

---

## 코드 & 품질

- [ ] `main` 브랜치 CI (ci.yml) 초록
- [ ] Contract test (contract.yml) 통과
- [ ] E2E (e2e.yml) 13 시나리오 통과
- [ ] Lighthouse Performance 90+ 확인
- [ ] `shared/openapi.json` 최신 (1692 라인)
- [ ] `.env*` 파일이 저장소에 없음 확인 (`git grep -r ANTHROPIC_API_KEY` 결과에 실 값 없음)

## 프로덕션 배포

- [ ] Neon Postgres 프로젝트 생성
- [ ] 로컬에서 `./scripts/run-prod-migration.sh` dry-run 성공
- [ ] Fly.io secrets 주입 (DATABASE_URL, ANTHROPIC_API_KEY, REDIS_URL)
- [ ] `fly deploy --remote-only` 성공
- [ ] `curl https://hacker-dashboard-api.fly.dev/health` status=ok
- [ ] Vercel 배포 URL에서 /portfolio 페이지에 5종 holdings 확인
- [ ] Vercel 배포 URL에서 /symbol/yahoo/AAPL 접속 시 "내 포트폴리오 반영" 토글 ON이 기본

## 배포

- [ ] BE Fly.io 헬스체크 통과: `curl https://hacker-dashboard-api.fly.dev/health`
- [ ] FE Vercel 접속 확인: `curl -I https://hacker-dashboard.vercel.app`
- [ ] `scripts/healthcheck.sh` 프로덕션 URL 로 실행 완료
- [ ] production smoke (production-smoke.yml) workflow_dispatch 수동 실행 통과

## 데이터

- [ ] Neon Postgres 마이그레이션 적용 (`alembic upgrade head`)
- [ ] 시드 데이터 삽입 (`make seed` 또는 `scripts/neon-setup.sql`)
- [ ] 데모 계정(demo) 보유자산 5종 확인

## 데모 시드

- [ ] 로컬 `make seed-db` 실행 후 /portfolio/holdings length == 5
- [ ] 프로덕션 시드 완료 (Neon 콘솔에서 테이블 5건 확인)
- [ ] 시드 재실행 시 idempotent 확인 (중복 없음)

## 데모

- [ ] `demo/scenario.md` 타임라인 리허설 완료 (스톱워치 8분 이내)
- [ ] CSV 시드 3종 준비: `demo/seeds/stocks.csv`, `crypto.csv`, `mixed.csv`
- [ ] 오프라인 녹화본 준비: `demo/recording/full-demo-v1.mp4`
- [ ] "Router 근거 보기" 토글 동작 확인
- [ ] Lighthouse 스크린샷: `docs/screenshots/lighthouse-final.png`

## 심사 rehearsal

- [ ] 8분 스톱워치 통과 (demo/scenario.md)
- [ ] CSV 3종 업로드 각각 성공 (stocks.csv, crypto.csv, mixed.csv)
- [ ] 개인화 토글 ON/OFF 즉시 전환 동작
- [ ] 집중도 경고 배너 시연 (BTC 시나리오)

## 제출 아티팩트

- [ ] `submission/README.md` — 심사위원용
- [ ] `submission/architecture.md` — 다이어그램 + 의사결정
- [ ] `submission/test-coverage.md` — 수치 표
- [ ] `submission/demo-video.md` — 영상 가이드 + 업로드 URL
- [ ] `README.md` (루트) — 배포 URL 실제 값 채워짐
- [ ] 배지 URL (`your-org` → 실제 org/repo 명으로 교체)

## #2 리밸런싱 제안 기능

- [ ] `POST /portfolio/rebalance` 동작 (`curl -X POST https://hacker-dashboard-api.fly.dev/portfolio/rebalance` 스모크)
- [ ] 골든 샘플 3종 PASS (`rebalance_balanced` / `rebalance_crypto_heavy` / `rebalance_constraint_violation`)
- [ ] FE `/portfolio` 하단에 리밸런싱 패널 표시 (슬라이더 4개 + 합계 배지)
- [ ] 프리셋 3종 (공격형 70/30 / 균형형 / 안정형 30/70) 슬라이더 자동 조정 동작
- [ ] 액션 테이블 Buy(초록) / Sell(빨강) 색상 구분 렌더
- [ ] 비교 차트 3색 시리즈 (현재 파랑 / 목표 초록 / 예상 보라) 렌더
- [ ] degraded 모드 배너 "LLM 해석 실패" 표시 확인
- [ ] E2E `e2e/rebalance.spec.ts` 스펙 4건 등록 (`npx playwright test --list` 확인)

## 비상 플랜 확인

- [ ] 로컬 `docker compose up -d --wait` 동작 확인
- [ ] 예비 배포 URL (있을 경우) 확인
- [ ] 네트워크 장애 대비 녹화본 재생 준비
