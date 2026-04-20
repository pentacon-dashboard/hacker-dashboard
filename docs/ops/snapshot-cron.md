# Portfolio Snapshot 크론 운영 가이드

## 개요

매일 23:55 KST (UTC 14:55) 에 GitHub Actions 워크플로(`snapshot.yml`)가 실행되어
전체 사용자의 포트폴리오 스냅샷을 `portfolio_snapshots` 테이블에 기록합니다.

스냅샷은 당일 총 자산 가치(KRW 환산), 손익, 자산군별 비중, 홀딩 상세를 포함합니다.
이 데이터가 `/portfolio` 대시보드의 `networth-chart` (순자산 시계열) 에 사용됩니다.

## 워크플로 위치

`.github/workflows/snapshot.yml`

## 스케줄

| 항목 | 값 |
|------|-----|
| cron (UTC) | `55 14 * * *` |
| KST | 매일 23:55 |
| 실행 시간 | ~2분 (마이그레이션 + 스냅샷 기록) |
| 타임아웃 | 10분 |
| 실패 시 동작 | `continue-on-error: true` — 다른 워크플로에 영향 없음 |

## 수동 실행 (GitHub Actions UI)

1. GitHub 저장소 → Actions 탭 → "Daily Portfolio Snapshot" 워크플로 선택
2. "Run workflow" 버튼 클릭
3. `user_id` 입력 (기본값: `demo`)
4. "Run workflow" 확인

## 로컬 수동 실행

### 사전 조건

- Python 3.12 + uv 설치
- Postgres 및 Redis 실행 중 (docker compose 또는 로컬 설치)
- `.env` 파일에 환경변수 설정 (절대 커밋 금지)

### 실행 명령

```bash
# 1. 백엔드 디렉토리로 이동
cd backend

# 2. 의존성 설치
uv sync --all-extras

# 3. 환경변수 설정 (예시 — 실제 값은 플랫폼 secret 에서)
export DATABASE_URL="postgresql+asyncpg://hacker:hacker@localhost:5432/hacker_dashboard"
export REDIS_URL="redis://localhost:6379/0"
export ANTHROPIC_API_KEY="sk-ant-..."  # 실 키 필요 (시세 조회용)
export SNAPSHOT_USER_ID="demo"         # 스냅샷 대상 user_id

# 4. 스냅샷 실행
uv run python -m app.services.portfolio_snapshot
```

### Docker Compose 환경에서 실행

```bash
# 스택이 기동 중인 상태에서
docker compose exec backend python -m app.services.portfolio_snapshot
```

## 스냅샷 모듈 구조

`backend/app/services/portfolio_snapshot.py`

주요 함수:

| 함수 | 역할 |
|------|------|
| `take_snapshot(session, user_id)` | 현재 시점 스냅샷 1건 생성 또는 upsert |
| `seed_dummy_snapshots(session, user_id, days)` | 개발/데모용 더미 스냅샷 N일치 삽입 |
| `__main__` 블록 | 크론 진입점 — DB 연결 후 `take_snapshot` 호출 |

## 데이터 보존

- 스냅샷 로그 Artifact: GitHub Actions → 7일 보존
- DB 레코드: `portfolio_snapshots` 테이블 — 별도 보존 정책 없음 (운영 DB 기준)

## 장애 대응

| 증상 | 원인 | 조치 |
|------|------|------|
| 워크플로 실패 | DB 접속 불가 | Neon/Supabase 대시보드 확인, DB_URL secret 점검 |
| 스냅샷 값이 0 | 시세 API 오류 | ANTHROPIC_API_KEY 만료 또는 거래소 API 장애 확인 |
| 중복 스냅샷 | upsert 미작동 | `uq_snapshot_user_date` 제약 확인, Alembic 마이그레이션 상태 점검 |

## CI secret 설정

GitHub 저장소 → Settings → Secrets and variables → Actions:

| Secret 이름 | 설명 |
|-------------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 (시세/분석용) |
| `DATABASE_URL` | 프로덕션 Neon/Supabase 연결 문자열 |
| `REDIS_URL` | Upstash Redis 또는 Fly.io Redis URL |

> 비밀값은 절대 저장소에 커밋하지 않습니다.
