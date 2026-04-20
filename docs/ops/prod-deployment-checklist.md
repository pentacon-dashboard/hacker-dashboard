# 프로덕션 배포 체크리스트

대회 심사 전에 한 번 쭉 훑어 모든 박스가 체크되면 배포 완료.

## 1. Neon Postgres

- [ ] Neon 계정 생성 & 프로젝트 `hacker-dashboard` 생성 (리전: ap-northeast-1)
- [ ] main 브랜치의 connection string 복사 (Neon 콘솔 > Connection Details)
- [ ] `postgresql+asyncpg://...?sslmode=require` 형식 확인 (`postgresql://` 이면 변환 필요)
- [ ] 로컬에서 마이그레이션 + 시드 적용:
  ```bash
  export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require"
  ./scripts/run-prod-migration.sh
  ```
- [ ] Neon 콘솔 > Tables 에서 `holdings` 5건 확인 (005930, AAPL, TSLA, KRW-BTC, KRW-ETH)

## 2. Fly.io (Backend)

- [ ] `flyctl` 설치 및 로그인 (`flyctl auth login`)
- [ ] `fly apps create hacker-dashboard-api` (이미 있으면 스킵)
- [ ] secrets 주입:
  ```bash
  export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require"
  export ANTHROPIC_API_KEY="sk-ant-..."
  export REDIS_URL="redis://default:pass@host:6379"
  ./scripts/fly-secrets.sh
  ```
- [ ] `flyctl secrets list --app hacker-dashboard-api` 로 주입 확인 (값은 숨겨지고 이름만 표시됨)
- [ ] backend/ 에서 배포:
  ```bash
  cd backend
  fly deploy --remote-only
  ```
- [ ] health check 통과:
  ```bash
  curl https://hacker-dashboard-api.fly.dev/health
  # 기대 응답: {"status":"ok","services":{"db":"ok",...}}
  ```
- [ ] holdings API 응답 확인:
  ```bash
  curl https://hacker-dashboard-api.fly.dev/portfolio/holdings
  # 기대: 5종 holdings JSON 배열
  ```

## 3. Vercel (Frontend)

- [ ] Vercel 프로젝트를 GitHub repo 에 연결
- [ ] 환경변수 설정 (Vercel 대시보드 > Settings > Environment Variables):
  - `NEXT_PUBLIC_API_BASE` = `https://hacker-dashboard-api.fly.dev`
- [ ] main 브랜치 자동 배포 트리거 확인 (push 또는 Vercel 대시보드 > Deployments > Redeploy)
- [ ] 배포된 URL 접속 (예: `https://hacker-dashboard.vercel.app`)
- [ ] /portfolio 페이지에서 5종 종목 카드 렌더링 확인
- [ ] 다크모드 전환 정상 동작 확인
- [ ] 모바일 반응형 확인 (Chrome DevTools > 375px)

## 4. E2E 연기 확인

- [ ] Playwright 핵심 시나리오 3개 통과:
  - 시나리오 1: CSV 업로드 → 자동 분석 뷰 생성
  - 시나리오 2: /portfolio 진입 → holdings 5건 표시
  - 시나리오 3: Router 결정 근거 토글 표시
- [ ] Lighthouse 점수 확인 (목표: Performance/Accessibility 각 90+):
  ```bash
  npx lighthouse https://hacker-dashboard.vercel.app --output html --output-path ./lighthouse-report.html
  ```

## 5. 심사 rehearsal

- [ ] 데모 시나리오 8분 스톱워치 통과
- [ ] /symbol/yahoo/AAPL "Router 결정 근거" 토글 화면에 표시되는지 확인
- [ ] 비상 플랜(로컬 docker-compose) 사전 검증:
  ```bash
  docker compose up -d
  # http://localhost:3000 접속 확인
  ```
- [ ] 오프라인 시나리오 녹화본 준비 (네트워크 장애 대비)
- [ ] 시드 데이터셋 3종 파일 경로 확인:
  - 주식 CSV
  - 코인 CSV
  - 혼합 CSV

## 자주 발생하는 문제

| 증상 | 해결책 |
|------|--------|
| SSL 에러 | connection string 에 `?sslmode=require` 누락. `run-prod-migration.sh` 는 자동 추가 |
| 401 in LLM | `ANTHROPIC_API_KEY` secret 미주입 또는 placeholder 값. `fly-secrets.sh` 재실행 |
| holdings 비어있음 | `run-prod-migration.sh` 의 시드 단계 실패 — Neon 콘솔 SQL 에디터에서 `scripts/neon-setup.sql` 직접 실행 |
| Fly.io 앱 기동 안 됨 | `flyctl logs --app hacker-dashboard-api` 로 오류 확인 |
| Vercel CORS | `NEXT_PUBLIC_API_BASE` 에 trailing slash 없이 설정 (`https://...fly.dev`) |
| Windows에서 asyncpg 오류 | Git Bash 에서 `run-prod-migration.sh` 실행. 또는 WSL2 사용 |
