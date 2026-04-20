# Neon Postgres 운영 런북

## 1. 프로젝트 생성

1. https://neon.tech 에서 새 프로젝트 생성
2. 리전: `ap-northeast-1` (Tokyo)
3. Postgres 버전: 16
4. 프로젝트명: `hacker-dashboard`

## 2. 브랜치 전략

| 브랜치명 | 용도 | connection string 보관 위치 |
|----------|------|--------------------------|
| `main`   | 프로덕션 | Fly.io secret `DATABASE_URL` |
| `preview`| PR 미리보기 / 스테이징 | Vercel preview env |
| `ci`     | GitHub Actions 테스트 | GitHub Actions secret `DATABASE_URL_CI` |

## 3. Connection String 가져오기

Neon 콘솔 > 프로젝트 > Connection Details:

```
postgresql://user:password@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require
```

`asyncpg` 드라이버 사용 시 scheme 을 `postgresql+asyncpg://` 로 변경:

```
postgresql+asyncpg://user:password@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require
```

**Connection Pooling (권장):** 동시 연결 수가 많은 환경에서는 Neon 콘솔 > Connection Details > Pooling enabled 를 활성화해 pooler 엔드포인트를 사용하세요.

```
postgresql+asyncpg://user:password@ep-xxx-pooler.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require
```

pooler 호스트명은 `-pooler.ap-northeast-1` 이 붙습니다.

## 4. Alembic 마이그레이션 적용

```bash
# backend/ 디렉토리에서 실행
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db?sslmode=require"
uv run alembic upgrade head
```

롤백:
```bash
uv run alembic downgrade -1
```

현재 리비전 확인:
```bash
uv run alembic current
```

`backend/alembic/env.py` 는 `DATABASE_URL` 환경변수를 읽어 `alembic.ini` 의 `sqlalchemy.url` 을 override 합니다.
따라서 `alembic.ini` 를 직접 수정하지 않고 환경변수만 설정하면 됩니다.

## 5. 시드 데이터 삽입

마이그레이션 완료 후 아래 세 가지 방법 중 하나를 선택하세요.

### 방법 A: SQL 파일 직접 실행 (psql)

DELETE + INSERT 방식으로 idempotent 보장. 스키마 변경 후에는 이 파일이 현재 컬럼 구조를 반영하는지 확인 필요.

```bash
# DATABASE_URL 은 psql 호환 형식 (postgresql:// — asyncpg 접두어 없이)
export DATABASE_URL="postgresql://user:pass@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require"
psql "$DATABASE_URL" -f scripts/neon-setup.sql
```

### 방법 B: Python ORM 스크립트 (권장)

`(user_id, market, code)` 중복 건을 건너뛰는 idempotent 방식. 컬럼 구조가 SQLAlchemy 모델과 자동으로 동기화됩니다.

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require"
uv run python scripts/seed_demo.py
```

### 방법 C: 원클릭 스크립트 (마이그레이션 + 시드 통합, 최초 배포 시 권장)

마이그레이션과 시드를 한 번에 처리합니다. `postgresql://` 스킴과 `?sslmode=require` 누락도 자동으로 보정합니다.

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require"
./scripts/run-prod-migration.sh

# 시드 없이 마이그레이션만:
./scripts/run-prod-migration.sh --skip-seed
```

## 6. 트러블슈팅

| 증상 | 확인 사항 |
|------|----------|
| `SSL connection required` | connection string 에 `?sslmode=require` 포함 여부 |
| `role does not exist` | Neon 콘솔에서 role/password 재확인 |
| `relation does not exist` | `alembic upgrade head` 미실행 |
| Connection 초과 | Neon 콘솔 > Monitoring > Connections 확인. pooler 연결 문자열 사용 권장 |
| `asyncpg` 드라이버 오류 | connection string 스킴이 `postgresql://` 이면 `postgresql+asyncpg://` 로 변경 필요. `run-prod-migration.sh` 는 자동 보정 |
| Fly.io 배포 후 DB 연결 안 됨 | `flyctl secrets list --app hacker-dashboard-api` 로 `DATABASE_URL` 주입 여부 확인. secrets set 후 앱 자동 재시작 |
| holdings 비어있음 | `run-prod-migration.sh` 의 시드 단계 실패 — Neon 콘솔 SQL 에디터에서 `scripts/neon-setup.sql` 직접 실행 |

## 7. Windows 로컬 환경 제약

### asyncpg + ProactorEventLoop 문제 (E.1에서 확인)

Windows 기본 이벤트 루프(`ProactorEventLoop`)는 asyncpg 와 호환되지 않아 `WinError 64` 가 발생할 수 있습니다.

`backend/alembic/env.py` 에 다음 패치가 적용되어 있습니다:

```python
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

이 덕분에 Git Bash 에서 `uv run alembic upgrade head` 가 정상 동작합니다.

`scripts/run-prod-migration.sh` 를 Git Bash 에서 실행하는 것을 권장합니다.
WSL2(Ubuntu) 환경에서도 동일하게 동작합니다.

### Neon 직접 연결 및 asyncpg WinError 10054

Windows Git Bash 에서 `alembic.exe` 를 직접 실행하면 `asyncpg.exceptions.ConnectionDoesNotExistError` (WinError 10054) 가 발생할 수 있습니다.
이는 `WindowsSelectorEventLoopPolicy` 패치에도 불구하고 asyncpg 가 Windows SelectorEventLoop 에서 특정 연결 시퀀스를 처리하지 못하는 알려진 환경 제약입니다.

권장 대안:

1. **CI (GitHub Actions `ubuntu-latest`) 사용** — 가장 안정적. GitHub Actions 에서 `run-prod-migration.sh` 워크플로를 트리거
2. **WSL2 (Ubuntu) 사용** — 로컬에서 Linux 환경 필요 시
3. **Neon 콘솔 SQL 에디터** — 마이그레이션 없이 시드만 필요한 경우 `scripts/neon-setup.sql` 을 콘솔에서 직접 실행
4. **docker exec** — 컨테이너 내 Python 환경 사용 시 (로컬 컨테이너 대상)

CI (GitHub Actions `ubuntu-latest`) 에서는 이 제약이 없으며 `run-prod-migration.sh` 가 정상 동작합니다.
