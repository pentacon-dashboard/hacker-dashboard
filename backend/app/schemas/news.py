"""News/Filing RAG API 스키마.

sprint-02: Citation, NewsSearchRequest, IngestRequest 정의.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Citation(BaseModel):
    """RAG 검색 결과의 단일 인용 항목.

    plan.md 기준:
      doc_id, chunk_id, source_url, title, published_at, excerpt, score
    """

    doc_id: int = Field(..., description="Document 테이블 PK")
    chunk_id: int = Field(..., description="DocumentChunk 테이블 PK")
    source_url: str = Field(..., description="원문 URL")
    title: str = Field(..., description="문서 제목")
    published_at: str | None = Field(None, description="발행일 ISO-8601")
    excerpt: str = Field(..., description="관련 청크 텍스트 발췌")
    score: float = Field(..., description="L2 거리 기반 유사도 점수 (낮을수록 가까움)")


class NewsSearchRequest(BaseModel):
    """GET /search/news 쿼리 파라미터 모델."""

    query: str = Field(..., description="자연어 검색 질의")
    symbols: str | None = Field(None, description="쉼표 구분 티커 (AAPL,TSLA 등)")
    start_date: str | None = Field(None, description="시작일 YYYY-MM-DD")
    end_date: str | None = Field(None, description="종료일 YYYY-MM-DD")
    k: int = Field(5, ge=1, le=50, description="반환할 최대 청크 수")


class IngestRequest(BaseModel):
    """POST /search/news/ingest 요청 본문."""

    source_url: str = Field(..., description="원문 URL")
    title: str = Field("", description="문서 제목")
    published_at: str | None = Field(None, description="발행일 ISO-8601")
    text: str = Field(..., description="전문 텍스트 (512자 이상 권장)")


class IngestResponse(BaseModel):
    """POST /search/news/ingest 응답."""

    document_id: int
    chunk_count: int
    is_new: bool
