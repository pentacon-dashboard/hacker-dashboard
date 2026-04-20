# ── 빌드 스테이지 ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# uv 설치 (공식 바이너리 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# 의존성 레이어를 먼저 캐시하기 위해 lock/project 파일만 먼저 복사
COPY pyproject.toml uv.lock* ./

# 가상 환경 생성 및 의존성 설치 (dev 제외)
# uv.lock 이 있으면 --frozen (재현 가능 빌드), 없으면 최신 호환 버전으로 resolve
RUN uv venv /opt/venv && \
    if [ -f uv.lock ]; then \
        UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev --no-install-project --frozen; \
    else \
        UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev --no-install-project; \
    fi

# 소스 복사 (alembic 마이그레이션 포함)
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# ── 런타임 스테이지 ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# 비-root user 생성 (uid 1000)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --no-create-home appuser

WORKDIR /app

# curl 설치 (HEALTHCHECK 용)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 빌더에서 venv 복사
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./alembic.ini

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 앱 파일 소유권을 비-root user 로 이전
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--loop", "uvloop", "--http", "httptools"]
