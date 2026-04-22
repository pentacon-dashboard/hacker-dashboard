"""텍스트 청킹 유틸리티.

sprint-02: 문서를 일정 크기의 chunk 로 분할한다.
기본 전략: 512 토큰 (근사: 문자 기준 2048자), 64자 오버랩.
"""
from __future__ import annotations

CHUNK_SIZE = 2048  # 문자 기준
OVERLAP = 256


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """텍스트를 chunk_size 문자 단위로 분할한다. 경계는 공백 기준으로 자른다."""
    if not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        # 문장 경계 탐색 (마지막 공백까지)
        if end < length:
            # 공백을 역탐색
            space_pos = text.rfind(" ", start, end)
            if space_pos > start:
                end = space_pos

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # 다음 start: overlap 만큼 뒤로
        start = end - overlap if end - overlap > start else end

    return chunks
