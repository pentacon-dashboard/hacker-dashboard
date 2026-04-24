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
