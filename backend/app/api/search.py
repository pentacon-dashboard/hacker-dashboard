"""뉴스/공시 RAG 검색 API 라우트.

sprint-02:
  GET  /search/news         — 질의 + 심볼 + 기간 → top-k Citation[]
  POST /search/news/ingest  — 문서 적재 (stub 모드: fixture no-op)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.news import Citation, IngestRequest, IngestResponse
from app.services.news.ingest import ingest_document
from app.services.news.search import search_news

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "/news",
    response_model=list[Citation],
    summary="뉴스/공시 RAG 검색",
    description=(
        "자연어 질의 + 심볼 + 기간으로 pgvector 인덱스에서 top-k 청크를 검색해 "
        "Citation 배열로 반환한다. stub 모드에서는 결정론적으로 동작한다."
    ),
)
async def get_search_news(
    query: str = Query(..., description="자연어 검색 질의"),
    symbols: str | None = Query(None, description="쉼표 구분 티커 (AAPL,TSLA 등)"),
    start_date: str | None = Query(None, description="시작일 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="종료일 YYYY-MM-DD"),
    k: int = Query(5, ge=1, le=50, description="반환 최대 청크 수"),
) -> list[Citation]:
    symbol_list = [s.strip() for s in symbols.split(",")] if symbols else None

    try:
        citations = await search_news(
            query=query,
            symbols=symbol_list,
            start_date=start_date,
            end_date=end_date,
            k=k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SEARCH_ERROR", "detail": str(exc)},
        ) from exc

    return citations


@router.post(
    "/news/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="뉴스/공시 문서 적재 (internal/admin)",
    description=(
        "URL 또는 텍스트를 pgvector에 적재한다. "
        "stub 모드에서는 in-memory 저장소에 적재한다. "
        "동일 source_url 은 멱등 처리 (중복 청크 미생성)."
    ),
    responses={400: {"description": "Invalid request body (JSON parse error)"}},
)
async def post_news_ingest(body: IngestRequest) -> IngestResponse:
    doc = {
        "source_url": body.source_url,
        "title": body.title,
        "published_at": body.published_at,
        "text": body.text,
    }

    try:
        result = await ingest_document(doc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INGEST_ERROR", "detail": str(exc)},
        ) from exc

    return IngestResponse(**result)
