from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    analyze,
    copilot,
    health,
    market,
    notifications,
    portfolio,
    search,
    upload,
    user,
    watchlist,
    ws,
)
from app.core.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging, logger, set_request_id


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.debug)
    app.state.started_at = time.time()
    logger.info("Starting Hacker Dashboard API", extra={"version": settings.app_version})

    # sprint-02: stub 모드에서 fixture corpus 사전 로드
    import os

    if os.environ.get("COPILOT_NEWS_MODE", "stub").lower() == "stub":
        from app.services.news.ingest import load_fixture_corpus

        load_fixture_corpus()
        logger.info("stub 모드: news fixture corpus 로드 완료")

    market.seed_default_watchlist()

    # sprint-integration: 격리 harness 환경에서 sqlite 스키마 자동 생성
    # BACKEND_DB_AUTOCREATE=1 일 때만 실행 — 운영 환경에서는 alembic 이 담당
    if os.environ.get("BACKEND_DB_AUTOCREATE", "0") == "1":
        try:
            from app.db.models import Base
            from app.db.session import engine

            # SQLite 격리 환경에서는 JSONB / Vector 컴파일러가 없으므로
            # create_all 전에 해당 컬럼 타입을 JSON / Text 로 오버라이드한다.
            # 이 오버라이드는 프로세스 내 in-memory 패치이며 운영 PG 에는 영향 없음.
            _db_url_str = str(engine.url)
            if _db_url_str.startswith("sqlite"):
                from sqlalchemy import JSON, Text
                from sqlalchemy.dialects.postgresql import JSONB

                # JSONB 컬럼을 JSON 으로 재선언
                for _table in Base.metadata.tables.values():
                    for _col in _table.columns:
                        if isinstance(_col.type, JSONB):
                            _col.type = JSON()
                        # pgvector Vector 는 Text 로 폴백
                        elif type(_col.type).__name__ == "Vector":
                            _col.type = Text()

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("BACKEND_DB_AUTOCREATE: Base.metadata.create_all 완료 (격리 환경)")
        except Exception as _create_exc:
            # SQLite 타입 변환 후에도 실패하는 경우 경고만 남기고 계속 기동
            logger.warning("BACKEND_DB_AUTOCREATE: create_all 건너뜀 (%s)", _create_exc)

    # DB/Redis 연결 실패해도 앱은 뜬다 (/health 가 degraded 로 응답)
    yield
    logger.info("Shutting down Hacker Dashboard API")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="임의 투자 데이터 스키마에서 자동 분석 뷰를 생성하는 금융 대시보드 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Response:
    """X-Request-ID 헤더를 자동 생성하거나 클라이언트 값을 전파한다."""
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


app.include_router(health.router)
app.include_router(market.router)
app.include_router(analyze.router)
app.include_router(portfolio.router)
app.include_router(ws.router)
app.include_router(copilot.router)
app.include_router(search.router)
app.include_router(upload.router)  # sprint-08 B-5: CSV 업로드 파이프라인
app.include_router(watchlist.router)  # sprint-08 B-2: watchlist
app.include_router(user.router)  # sprint-08 B-6: users settings
app.include_router(notifications.router)  # 알림 엔드포인트
