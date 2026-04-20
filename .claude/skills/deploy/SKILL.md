---
name: deploy
description: 금융 대시보드를 Vercel(FE) + Fly.io/Render(BE) + Neon(Postgres) 조합으로 배포하거나 재배포한다. 배포, 롤백, 환경변수 동기화, 헬스체크 작업 시 호출.
---

# Skill — Deploy

공모전 제출용 배포 절차 표준화. 이 스킬은 개발 편의용이며 최종 프로덕트에 포함되지 않습니다.

## 전제

- Vercel 프로젝트: `hacker-dashboard-fe` (main 브랜치 연동)
- Fly.io 앱: `hacker-dashboard-be` (Dockerfile from `backend/`)
- Neon DB: `hacker-dashboard` (pooled connection string)
- GitHub Actions 가 PR 머지 시 자동 트리거 — 수동은 rollback/hotfix 전용

## 최초 배포 체크리스트

1. [ ] Vercel env: `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_WS_BASE`
2. [ ] Fly secrets: `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`
3. [ ] Alembic 마이그레이션 `alembic upgrade head` 원격 실행
4. [ ] 시드 데이터 로드 (`backend/scripts/seed_demo.py`)
5. [ ] `/healthz` (BE), `/api/health` (FE) 200 확인
6. [ ] Lighthouse 수동 리포트 캡처

## 재배포 / 핫픽스

```bash
# FE
vercel --prod

# BE
fly deploy --remote-only --config backend/fly.toml

# DB 마이그레이션이 있는 경우
fly ssh console -C "alembic upgrade head"
```

## 롤백

```bash
# FE: Vercel 대시보드 → Previous Deployment → Promote to Production
# BE:
fly releases --app hacker-dashboard-be
fly deploy --image registry.fly.io/hacker-dashboard-be:<prev-tag>
```

## 주의

- 프로덕션 DB 마이그레이션 **다운타임 위험 있는 변경**(컬럼 제거, 타입 변경) 은 스킬로 처리하지 말고 사람이 감독
- `ANTHROPIC_API_KEY` 등 시크릿을 절대 로그로 출력하지 말 것
