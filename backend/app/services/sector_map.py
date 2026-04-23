"""섹터 매핑 테이블 — 티커 → 섹터 (하드코드 stub).

20~30 종목 매핑. 미매핑 종목은 "기타" 반환.
sprint-08 Phase B-1.
"""
from __future__ import annotations

_SECTOR_MAP: dict[str, str] = {
    # 한국 주식
    "005930": "반도체",
    "000660": "반도체",
    "035420": "인터넷",
    "035720": "인터넷",
    "005380": "자동차",
    "000270": "자동차",
    "068270": "바이오",
    "207940": "바이오",
    "006400": "2차전지",
    "051910": "2차전지",
    "028260": "금융",
    "055550": "금융",
    # 미국 주식
    "AAPL": "Tech",
    "MSFT": "Tech",
    "GOOGL": "Tech",
    "GOOG": "Tech",
    "NVDA": "반도체",
    "AMD": "반도체",
    "TSLA": "EV/에너지",
    "AMZN": "커머스/클라우드",
    "META": "소셜미디어",
    "NFLX": "스트리밍",
    "JPM": "금융",
    "BAC": "금융",
    "V": "금융",
    "JNJ": "헬스케어",
    "UNH": "헬스케어",
    "XOM": "에너지",
    "CVX": "에너지",
    # 암호화폐
    "KRW-BTC": "Crypto",
    "KRW-ETH": "Crypto",
    "KRW-SOL": "Crypto",
    "KRW-XRP": "Crypto",
    "BTCUSDT": "Crypto",
    "ETHUSDT": "Crypto",
}


def get_sector(ticker: str) -> str:
    """ticker 로 섹터 조회. 미매핑은 '기타' 반환."""
    return _SECTOR_MAP.get(ticker.upper(), _SECTOR_MAP.get(ticker, "기타"))


def get_sector_map() -> dict[str, str]:
    """전체 섹터 맵 반환 (읽기 전용 복사본)."""
    return dict(_SECTOR_MAP)
