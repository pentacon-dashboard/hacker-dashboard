#!/usr/bin/env bash
# scripts/run-prod-migration.sh
# 프로덕션(Neon) Postgres에 Alembic 마이그레이션 + 데모 시드 적용.
#
# 사용법:
#   export DATABASE_URL="postgresql+asyncpg://<user>:<pass>@<host>/<db>?sslmode=require"
#   ./scripts/run-prod-migration.sh [--skip-seed]
#
# 동작:
#   1. DATABASE_URL 환경변수 존재 여부 확인 (없으면 에러)
#   2. postgresql:// 만 있으면 postgresql+asyncpg:// 로 자동 교체 (Neon 콘솔 기본값 호환)
#   3. SSL 모드 필수 - ?sslmode=require 없으면 추가
#   4. alembic upgrade head 실행
#   5. --skip-seed 가 아니면 python scripts/seed_demo.py 실행
#   6. curl 가능하면 $BACKEND_URL/portfolio/holdings 로 최종 확인 (선택)

set -euo pipefail

PREFIX="[prod-migrate]"

# ── 인자 파싱 ──────────────────────────────────────────────────────────────────
SKIP_SEED=false
for arg in "$@"; do
  case "$arg" in
    --skip-seed) SKIP_SEED=true ;;
    *) echo "$PREFIX 알 수 없는 옵션: $arg" >&2; exit 1 ;;
  esac
done

# ── 스텝 1: DATABASE_URL 존재 확인 ────────────────────────────────────────────
echo "$PREFIX 스텝 1/5: DATABASE_URL 환경변수 확인..."
if [ -z "${DATABASE_URL:-}" ]; then
  echo "$PREFIX ERROR: 환경변수 DATABASE_URL 필수 — Neon 콘솔의 connection string을 export 하세요" >&2
  echo "$PREFIX 예시:" >&2
  echo "$PREFIX   export DATABASE_URL=\"postgresql+asyncpg://user:pass@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require\"" >&2
  exit 1
fi
echo "$PREFIX DATABASE_URL 확인됨."

# ── 스텝 2: postgresql:// -> postgresql+asyncpg:// 자동 교체 ──────────────────
echo "$PREFIX 스텝 2/5: 드라이버 스킴 확인 및 보정..."
if echo "$DATABASE_URL" | grep -q "^postgresql://"; then
  DATABASE_URL="${DATABASE_URL/postgresql:\/\//postgresql+asyncpg://}"
  echo "$PREFIX 스킴 보정 완료: postgresql:// -> postgresql+asyncpg://"
elif echo "$DATABASE_URL" | grep -q "^postgresql+asyncpg://"; then
  echo "$PREFIX 스킴 확인됨: postgresql+asyncpg://"
else
  echo "$PREFIX WARNING: 예상치 못한 스킴입니다. postgresql+asyncpg:// 로 시작해야 합니다." >&2
fi
export DATABASE_URL

# ── 스텝 3: ?sslmode=require 누락 시 추가 (외부 호스트 전용) ─────────────────
echo "$PREFIX 스텝 3/5: SSL 모드 확인..."
# localhost / 127.0.0.1 / Docker 내부망 은 SSL 불필요 — 외부 호스트만 강제
_IS_LOCAL=false
if echo "$DATABASE_URL" | grep -qE "@(localhost|127\.0\.0\.1|postgres)(:|/)"; then
  _IS_LOCAL=true
fi

if echo "$DATABASE_URL" | grep -q "sslmode="; then
  echo "$PREFIX SSL 모드 파라미터 확인됨 (기존 값 유지)."
elif [ "$_IS_LOCAL" = true ]; then
  echo "$PREFIX 로컬/도커 호스트 감지 — SSL 모드 추가 생략."
else
  # 외부 호스트(Neon 등)이고 sslmode 가 없으면 require 추가
  if echo "$DATABASE_URL" | grep -q "?"; then
    DATABASE_URL="${DATABASE_URL}&sslmode=require"
  else
    DATABASE_URL="${DATABASE_URL}?sslmode=require"
  fi
  echo "$PREFIX 외부 호스트 감지 — SSL 모드 추가 완료: ?sslmode=require"
  export DATABASE_URL
fi

# ── 프로젝트 루트 감지 ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "$PREFIX 프로젝트 루트: $PROJECT_ROOT"
echo "$PREFIX 백엔드 디렉토리: $BACKEND_DIR"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "$PREFIX ERROR: backend/ 디렉토리를 찾을 수 없습니다: $BACKEND_DIR" >&2
  exit 1
fi

# ── 스텝 4: Alembic 마이그레이션 실행 ─────────────────────────────────────────
echo "$PREFIX 스텝 4/5: Alembic 마이그레이션 실행 (backend/ 에서)..."
cd "$BACKEND_DIR"

# uv 탐색: PATH 외에 일반적인 설치 위치도 확인
_UV_CMD=""
if command -v uv >/dev/null 2>&1; then
  _UV_CMD="uv"
elif [ -f "$HOME/.cargo/bin/uv" ]; then
  _UV_CMD="$HOME/.cargo/bin/uv"
elif [ -f "$HOME/.local/bin/uv" ]; then
  _UV_CMD="$HOME/.local/bin/uv"
fi

# venv 내 alembic 탐색 (Windows .exe 포함)
_ALEMBIC_CMD=""
if [ -f "$BACKEND_DIR/.venv/Scripts/alembic.exe" ]; then
  _ALEMBIC_CMD="$BACKEND_DIR/.venv/Scripts/alembic.exe"
elif [ -f "$BACKEND_DIR/.venv/bin/alembic" ]; then
  _ALEMBIC_CMD="$BACKEND_DIR/.venv/bin/alembic"
elif command -v alembic >/dev/null 2>&1; then
  _ALEMBIC_CMD="alembic"
fi

if [ -n "$_UV_CMD" ]; then
  echo "$PREFIX uv 발견: $_UV_CMD"
  if "$_UV_CMD" run alembic upgrade head; then
    echo "$PREFIX 마이그레이션 성공."
  else
    echo "$PREFIX ERROR: alembic upgrade head 실패." >&2
    exit 1
  fi
elif [ -n "$_ALEMBIC_CMD" ]; then
  echo "$PREFIX uv 없음. venv alembic 사용: $_ALEMBIC_CMD"
  echo "$PREFIX 참고: Windows 환경에서 asyncpg 연결 오류 발생 시 WSL2 또는 CI(GitHub Actions) 에서 실행을 권장합니다."
  if "$_ALEMBIC_CMD" upgrade head; then
    echo "$PREFIX 마이그레이션 성공."
  else
    echo "$PREFIX ERROR: alembic upgrade head 실패." >&2
    echo "$PREFIX Windows Git Bash 환경에서 asyncpg 오류 발생 시: WSL2 또는 CI 실행을 권장합니다." >&2
    exit 1
  fi
else
  echo "$PREFIX ERROR: alembic 실행 파일을 찾을 수 없습니다." >&2
  echo "$PREFIX  - uv 설치: https://docs.astral.sh/uv/getting-started/installation/" >&2
  echo "$PREFIX  - 또는 backend/ 에서 python -m pip install alembic" >&2
  exit 1
fi
cd "$PROJECT_ROOT"

# ── 스텝 5: 시드 삽입 ─────────────────────────────────────────────────────────
if [ "$SKIP_SEED" = true ]; then
  echo "$PREFIX 스텝 5/5: --skip-seed 옵션으로 시드 건너뜀."
else
  echo "$PREFIX 스텝 5/5: 데모 시드 삽입 (scripts/seed_demo.py)..."
  if command -v uv >/dev/null 2>&1; then
    if uv run python scripts/seed_demo.py; then
      echo "$PREFIX 시드 삽입 성공."
    else
      echo "$PREFIX ERROR: seed_demo.py 실패." >&2
      exit 1
    fi
  else
    if python scripts/seed_demo.py; then
      echo "$PREFIX 시드 삽입 성공."
    else
      echo "$PREFIX ERROR: seed_demo.py 실패." >&2
      exit 1
    fi
  fi
fi

# ── 스텝 6(선택): BACKEND_URL health check ────────────────────────────────────
if [ -n "${BACKEND_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  echo "$PREFIX 스텝 6(선택): $BACKEND_URL/portfolio/holdings 최종 확인..."
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/portfolio/holdings" || true)
  if [ "$HTTP_STATUS" = "200" ]; then
    echo "$PREFIX health check 통과: HTTP $HTTP_STATUS"
  else
    echo "$PREFIX WARNING: health check HTTP $HTTP_STATUS — 서버 기동 후 수동 확인 필요."
  fi
else
  echo "$PREFIX 스텝 6(선택): BACKEND_URL 미설정 또는 curl 없음 — 최종 확인 건너뜀."
fi

echo "$PREFIX 완료: 마이그레이션$([ "$SKIP_SEED" = false ] && echo ' + 시드 삽입' || echo '') 성공."
