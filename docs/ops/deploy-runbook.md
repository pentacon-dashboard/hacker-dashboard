# 배포 런북

최종 수정: 2026-04-19

---

## 1. 사전 조건

| 도구 | 버전 | 설치 |
|------|------|------|
| flyctl | latest | `curl -L https://fly.io/install.sh \| sh` |
| Vercel CLI | latest | `npm i -g vercel` |
| Node | 20 | nvm 또는 직접 설치 |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker Desktop | 4+ | Windows 10 에서 필수 (로컬 테스트용) |

> Windows 10 Home 환경 제약: Docker Desktop 은 WSL2 백엔드 필요.
> CI (GitHub Actions ubuntu-latest) 로 대체 가능.

---

## 2. BE — Fly.io 배포

### 2-1. 최초 배포

```bash
cd backend

# Fly.io 로그인
flyctl auth login

# 앱 생성 (fly.toml 이미 존재하므로 --no-deploy 플래그)
flyctl launch --no-deploy --copy-config

# 비밀값 주입 (scripts/fly-secrets.sh 참고)
flyctl secrets set \
  ANTHROPIC_API_KEY=sk-ant-xxxx \
  DATABASE_URL=postgresql+asyncpg://user:pass@host/db?sslmode=require \
  REDIS_URL=redis://default:pass@host:6379

# 배포
flyctl deploy --remote-only
```

### 2-2. 이후 배포 (업데이트)

```bash
cd backend
flyctl deploy --remote-only
```

### 2-3. 상태 확인

```bash
flyctl status --app hacker-dashboard-api
flyctl logs --app hacker-dashboard-api -n 50

# 헬스체크
curl https://hacker-dashboard-api.fly.dev/health | jq .
```

### 2-4. 롤백

```bash
flyctl releases list --app hacker-dashboard-api
flyctl deploy --image <이전 이미지 digest> --app hacker-dashboard-api
```

---

## 3. FE — Vercel 배포

### 3-1. 최초 배포

```bash
cd frontend

# Vercel CLI 로그인
vercel login

# 프로젝트 연결
vercel link

# 환경변수 설정
vercel env add NEXT_PUBLIC_API_BASE production
# 입력: https://hacker-dashboard-api.fly.dev

# 프로덕션 배포
vercel --prod
```

### 3-2. 이후 배포

```bash
cd frontend
vercel --prod
```

또는 `main` 브랜치에 push 하면 Vercel GitHub 연동으로 자동 배포.

### 3-3. 상태 확인

```bash
vercel inspect <deployment-url>
curl -I https://hacker-dashboard.vercel.app
```

---

## 4. DB — Neon Postgres 마이그레이션

Neon 런북: [docs/ops/neon-runbook.md](neon-runbook.md)

```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://..."
uv run alembic upgrade head
```

---

## 5. 전체 헬스체크

```bash
BE_URL=https://hacker-dashboard-api.fly.dev \
FE_URL=https://hacker-dashboard.vercel.app \
bash scripts/healthcheck.sh
```

---

## 6. CI/CD 시크릿 설정 (GitHub Actions)

GitHub 저장소 > Settings > Secrets and variables > Actions:

| 시크릿 이름 | 값 |
|------------|-----|
| `FLY_API_TOKEN` | `flyctl tokens create deploy` 출력값 |
| `ANTHROPIC_API_KEY` | Anthropic 콘솔에서 발급 |
| `DATABASE_URL` | Neon main 브랜치 connection string |
| `REDIS_URL` | Upstash Redis connection string |

---

## 7. 자동 배포 (선택)

BE 자동 배포 workflow 추가 시 `.github/workflows/deploy-be.yml` 생성:

```yaml
name: Deploy BE to Fly.io
on:
  push:
    branches: [main]
    paths: ["backend/**"]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        working-directory: backend
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

---

## 8. 공모전 당일 체크리스트

- [ ] `scripts/healthcheck.sh` 통과 (BE + FE)
- [ ] `/health` 응답 200 확인
- [ ] 시드 데이터 삽입 확인 (`make seed`)
- [ ] 배포 URL 2곳 접속 확인
- [ ] 예비 로컬 환경 (`docker compose up`) 동작 확인
- [ ] 오프라인 녹화본 위치 확인 (`demo/recording/`)
