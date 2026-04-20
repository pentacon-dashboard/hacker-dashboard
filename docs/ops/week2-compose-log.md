# Week-2 Docker Compose 검증 로그

측정일: 2026-04-19

## 환경

- OS: Windows 10 Home (10.0.19045)
- Shell: Git Bash (bash via win32)
- Docker Client: 29.2.1 (context: desktop-linux)
- Docker Desktop 서버: 미기동 (Docker Desktop 앱이 실행되지 않은 상태)

## docker compose config --quiet 파싱 결과

```
exit code: 0
```

`docker-compose.yml` 구문 검증 PASS.

4개 서비스 정의 확인:
- `postgres` (postgres:16-alpine) — healthcheck: `pg_isready -U hacker -d hacker_dashboard`
- `redis` (redis:7-alpine) — healthcheck: `redis-cli ping`
- `backend` (./backend/Dockerfile) — depends_on: postgres(healthy) + redis(healthy), healthcheck: `wget -qO- http://localhost:8000/health`
- `frontend` (frontend/Dockerfile, context=root) — depends_on: backend(healthy)

## docker compose up 실검 결과

Docker Desktop 데몬이 로컬에서 기동되지 않아 `docker compose up` 실행 불가.

**스킵 사유:** Windows 10 Home 환경에서 Docker Desktop 앱이 활성화되지 않음.

### CI 에서의 실행 경로

`e2e.yml` 및 `ci.yml` 의 playwright job 이 ubuntu-latest GitHub Actions 러너에서 Postgres + Redis 서비스 컨테이너를 통해 동등한 환경을 검증함.

## 재실행 가이드 (Docker Desktop 활성화 후)

```bash
cd /path/to/hacker-dashboard

# 기동
docker compose up -d --wait --timeout 120

# 상태 확인
docker compose ps
# 기대값: postgres, redis, backend, frontend 모두 Status=running, Health=healthy

# 헬스체크
curl http://localhost:8000/health   # 200 {"status":"ok"}
curl -I http://localhost:3000       # 200 또는 3xx

# 종료 (볼륨 포함 정리)
docker compose down -v
```

## 예상 정상 출력 샘플 (placeholder)

```
NAME                    IMAGE                STATUS          PORTS
hd-postgres-1           postgres:16-alpine   healthy         0.0.0.0:5432->5432/tcp
hd-redis-1              redis:7-alpine       healthy         0.0.0.0:6379->6379/tcp
hd-backend-1            hd-backend           healthy         0.0.0.0:8000->8000/tcp
hd-frontend-1           hd-frontend          running         0.0.0.0:3000->3000/tcp
```
