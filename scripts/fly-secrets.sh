#!/usr/bin/env bash
# scripts/fly-secrets.sh — Fly.io 앱에 프로덕션 비밀값을 실제로 주입하는 스크립트.
#
# 사용법:
#   export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.ap-northeast-1.aws.neon.tech/hacker_dashboard?sslmode=require"
#   export ANTHROPIC_API_KEY="sk-ant-..."
#   export REDIS_URL="redis://default:pass@host:6379"
#   export APP_VERSION="1.0.0"   # 선택 사항
#   ./scripts/fly-secrets.sh
#
# 전제조건:
#   - flyctl auth login 완료
#   - FLY_APP 환경변수 또는 기본값 hacker-dashboard-api 가 올바른 앱 이름이어야 함
#
# 주의: 실 키는 이 파일에 하드코딩 금지. 반드시 환경변수로만 전달할 것.
# .env* 파일을 저장소에 커밋하지 말 것.

set -euo pipefail

PREFIX="[fly-secrets]"
APP_NAME="${FLY_APP:-hacker-dashboard-api}"

echo "$PREFIX 앱: $APP_NAME"
echo "$PREFIX 비밀값 검증 중..."

# ── 필수 환경변수 존재 확인 ────────────────────────────────────────────────────
MISSING=()

if [ -z "${DATABASE_URL:-}" ]; then
  MISSING+=("DATABASE_URL (Neon connection string — postgresql+asyncpg://...?sslmode=require)")
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  MISSING+=("ANTHROPIC_API_KEY (Anthropic API 키 — sk-ant-...)")
fi

if [ -z "${REDIS_URL:-}" ]; then
  MISSING+=("REDIS_URL (Upstash 또는 Fly.io Redis — redis://...)")
fi

if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "$PREFIX ERROR: 다음 환경변수가 설정되지 않았습니다:" >&2
  for var in "${MISSING[@]}"; do
    echo "$PREFIX   - $var" >&2
  done
  echo "$PREFIX export 후 다시 실행하세요." >&2
  exit 1
fi

echo "$PREFIX 필수 환경변수 확인됨."

# ── flyctl 존재 확인 ──────────────────────────────────────────────────────────
if ! command -v flyctl >/dev/null 2>&1; then
  echo "$PREFIX ERROR: flyctl 을 찾을 수 없습니다. https://fly.io/docs/hands-on/install-flyctl/ 를 참고해 설치하세요." >&2
  exit 1
fi

# ── 비밀값 주입 ───────────────────────────────────────────────────────────────
echo "$PREFIX flyctl secrets set 실행 중..."

SECRET_ARGS=(
  "DATABASE_URL=${DATABASE_URL}"
  "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
  "REDIS_URL=${REDIS_URL}"
)

# APP_VERSION 은 선택 사항
if [ -n "${APP_VERSION:-}" ]; then
  SECRET_ARGS+=("APP_VERSION=${APP_VERSION}")
  echo "$PREFIX APP_VERSION 포함."
fi

if flyctl secrets set "${SECRET_ARGS[@]}" --app "$APP_NAME"; then
  echo "$PREFIX 비밀값 주입 성공."
else
  echo "$PREFIX ERROR: flyctl secrets set 실패." >&2
  exit 1
fi

# ── 주입 결과 확인 ────────────────────────────────────────────────────────────
echo "$PREFIX 주입된 secret 목록 확인:"
flyctl secrets list --app "$APP_NAME"

echo "$PREFIX 완료."
echo "$PREFIX 참고: Fly.io 는 secrets set 후 자동으로 앱을 재시작합니다."
echo "$PREFIX 앱 상태 확인: flyctl status --app $APP_NAME"
