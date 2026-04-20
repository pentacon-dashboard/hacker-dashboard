# Week-3 Docker Compose 검증 로그

측정일: 2026-04-19

## 환경

- OS: Windows 10 Home (10.0.19045)
- Shell: Git Bash (bash via win32)
- Docker Desktop: 미기동 (로컬 검증 제한)

## docker compose config --quiet 파싱 결과

```
exit code: 0
```

`docker-compose.yml` 구문 검증 PASS.

## 서비스 구성 (week-3 기준)

4개 서비스 정의 확인:

| 서비스 | 이미지 / Dockerfile | 주요 변경 |
|--------|---------------------|-----------|
| `postgres` | postgres:16-alpine | week-3 신규 테이블: `holdings`, `portfolio_snapshots` |
| `redis` | redis:7-alpine | 변경 없음 |
| `backend` | ./backend/Dockerfile | `portfolio.router`, `ws.router` 추가 마운트 확인 |
| `frontend` | frontend/Dockerfile | `/portfolio` 라우트 추가 |

## backend 라우터 등록 확인 (week-3 신규)

`app/main.py` 에 등록된 라우터:

- `health.router` — GET /health
- `market.router` — GET/POST /market/*
- `ws.router` — WS /ws/*
- `analyze.router` — POST /analyze
- `portfolio.router` — GET/POST/PATCH/DELETE /portfolio/*  (week-3 신규)

`portfolio.router` 가 `app/api/portfolio.py` 에 정의되어 있고
Holdings CRUD + Summary + Snapshots 엔드포인트를 포함함.

## docker compose up 실검 결과

Docker Desktop 데몬이 로컬에서 기동되지 않아 `docker compose up` 실행 불가.

**스킵 사유:** Windows 10 Home 환경에서 Docker Desktop 앱이 활성화되지 않음.

### CI 에서의 검증 경로

`ci.yml` backend job: postgres + redis 서비스 컨테이너 → pytest 전체 통과로 동등 검증.
`ci.yml` playwright job: BE + FE 모두 기동 후 E2E 통과로 4-서비스 통합 검증.

## 재실행 가이드 (Docker Desktop 활성화 후)

```bash
cd /path/to/hacker-dashboard

# Alembic 마이그레이션 포함 기동
docker compose up -d --wait --timeout 120

# 상태 확인
docker compose ps
# 기대값: postgres, redis, backend, frontend 모두 Status=running, Health=healthy

# 헬스체크
curl http://localhost:8000/health   # 200 {"status":"ok"}
curl -I http://localhost:3000       # 200 또는 3xx

# 포트폴리오 API 연기 테스트
curl http://localhost:8000/portfolio/holdings  # 200 []
curl http://localhost:8000/portfolio/summary   # 200 {total_value_krw: ...}

# 정리
docker compose down -v
```

## week-3 신규 이슈 없음

`portfolio.router` 와 `ws.router` 추가 후 `docker compose config --quiet` 통과.
포트 충돌 없음. healthcheck 설정 변경 없음.
