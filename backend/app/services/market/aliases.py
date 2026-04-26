"""한글 alias 폴백 사전.

한글명(소문자, 공백 제거)으로 SymbolInfo 를 즉시 반환한다.
점수: 정확일치 2000, startswith 1500 — 어댑터 결과보다 항상 우선.
"""

from __future__ import annotations

from app.schemas.market import SymbolInfo

# (market, symbol, asset_class, name_en, exchange, currency)
# key: 한글명 소문자 + 공백 제거
_RAW: list[tuple[str, str, str, str, str, str, str]] = [
    # key, market, symbol, asset_class, name_en, exchange, currency
    # ── 해외 주식 30개 ──────────────────────────────────────────────────
    ("테슬라", "yahoo", "TSLA", "stock", "Tesla", "NASDAQ", "USD"),
    ("애플", "yahoo", "AAPL", "stock", "Apple", "NASDAQ", "USD"),
    ("엔비디아", "yahoo", "NVDA", "stock", "NVIDIA", "NASDAQ", "USD"),
    ("마이크로소프트", "yahoo", "MSFT", "stock", "Microsoft", "NASDAQ", "USD"),
    ("구글", "yahoo", "GOOGL", "stock", "Alphabet", "NASDAQ", "USD"),
    ("알파벳", "yahoo", "GOOGL", "stock", "Alphabet", "NASDAQ", "USD"),
    ("아마존", "yahoo", "AMZN", "stock", "Amazon", "NASDAQ", "USD"),
    ("메타", "yahoo", "META", "stock", "Meta Platforms", "NASDAQ", "USD"),
    ("에이엠디", "yahoo", "AMD", "stock", "AMD", "NASDAQ", "USD"),
    ("인텔", "yahoo", "INTC", "stock", "Intel", "NASDAQ", "USD"),
    ("넷플릭스", "yahoo", "NFLX", "stock", "Netflix", "NASDAQ", "USD"),
    ("디즈니", "yahoo", "DIS", "stock", "Walt Disney", "NYSE", "USD"),
    ("코카콜라", "yahoo", "KO", "stock", "Coca-Cola", "NYSE", "USD"),
    ("펩시", "yahoo", "PEP", "stock", "PepsiCo", "NASDAQ", "USD"),
    ("나이키", "yahoo", "NKE", "stock", "Nike", "NYSE", "USD"),
    ("맥도날드", "yahoo", "MCD", "stock", "McDonald's", "NYSE", "USD"),
    ("비자", "yahoo", "V", "stock", "Visa", "NYSE", "USD"),
    ("제이피모건", "yahoo", "JPM", "stock", "JPMorgan Chase", "NYSE", "USD"),
    ("버크셔해서웨이", "yahoo", "BRK-B", "stock", "Berkshire Hathaway", "NYSE", "USD"),
    ("유나이티드헬스", "yahoo", "UNH", "stock", "UnitedHealth", "NYSE", "USD"),
    ("일라이릴리", "yahoo", "LLY", "stock", "Eli Lilly", "NYSE", "USD"),
    ("엑슨모빌", "yahoo", "XOM", "stock", "ExxonMobil", "NYSE", "USD"),
    ("에이티앤티", "yahoo", "T", "stock", "AT&T", "NYSE", "USD"),
    ("버라이즌", "yahoo", "VZ", "stock", "Verizon", "NYSE", "USD"),
    ("보잉", "yahoo", "BA", "stock", "Boeing", "NYSE", "USD"),
    ("캐터필러", "yahoo", "CAT", "stock", "Caterpillar", "NYSE", "USD"),
    ("쉐브론", "yahoo", "CVX", "stock", "Chevron", "NYSE", "USD"),
    ("월마트", "yahoo", "WMT", "stock", "Walmart", "NYSE", "USD"),
    ("코스트코", "yahoo", "COST", "stock", "Costco", "NASDAQ", "USD"),
    ("피앤지", "yahoo", "PG", "stock", "Procter & Gamble", "NYSE", "USD"),
    ("애보트", "yahoo", "ABT", "stock", "Abbott", "NYSE", "USD"),
    ("써모피셔", "yahoo", "TMO", "stock", "Thermo Fisher", "NYSE", "USD"),
    ("어도비", "yahoo", "ADBE", "stock", "Adobe", "NASDAQ", "USD"),
    ("세일즈포스", "yahoo", "CRM", "stock", "Salesforce", "NYSE", "USD"),
    # ── 코인 30개 ────────────────────────────────────────────────────────
    ("비트코인", "upbit", "KRW-BTC", "crypto", "Bitcoin", "Upbit", "KRW"),
    ("이더리움", "upbit", "KRW-ETH", "crypto", "Ethereum", "Upbit", "KRW"),
    ("솔라나", "upbit", "KRW-SOL", "crypto", "Solana", "Upbit", "KRW"),
    ("리플", "upbit", "KRW-XRP", "crypto", "Ripple", "Upbit", "KRW"),
    ("에이다", "upbit", "KRW-ADA", "crypto", "Cardano", "Upbit", "KRW"),
    ("도지코인", "upbit", "KRW-DOGE", "crypto", "Dogecoin", "Upbit", "KRW"),
    ("아발란체", "upbit", "KRW-AVAX", "crypto", "Avalanche", "Upbit", "KRW"),
    ("폴카닷", "upbit", "KRW-DOT", "crypto", "Polkadot", "Upbit", "KRW"),
    ("폴리곤", "upbit", "KRW-MATIC", "crypto", "Polygon", "Upbit", "KRW"),
    ("체인링크", "upbit", "KRW-LINK", "crypto", "Chainlink", "Upbit", "KRW"),
    ("라이트코인", "upbit", "KRW-LTC", "crypto", "Litecoin", "Upbit", "KRW"),
    ("비트코인캐시", "upbit", "KRW-BCH", "crypto", "Bitcoin Cash", "Upbit", "KRW"),
    ("트론", "upbit", "KRW-TRX", "crypto", "TRON", "Upbit", "KRW"),
    ("코스모스", "upbit", "KRW-ATOM", "crypto", "Cosmos", "Upbit", "KRW"),
    ("니어프로토콜", "upbit", "KRW-NEAR", "crypto", "NEAR Protocol", "Upbit", "KRW"),
    ("아비트럼", "upbit", "KRW-ARB", "crypto", "Arbitrum", "Upbit", "KRW"),
    ("옵티미즘", "upbit", "KRW-OP", "crypto", "Optimism", "Upbit", "KRW"),
    ("수이", "upbit", "KRW-SUI", "crypto", "Sui", "Upbit", "KRW"),
    ("앱토스", "upbit", "KRW-APT", "crypto", "Aptos", "Upbit", "KRW"),
    ("파일코인", "upbit", "KRW-FIL", "crypto", "Filecoin", "Upbit", "KRW"),
    ("인터넷컴퓨터", "upbit", "KRW-ICP", "crypto", "Internet Computer", "Upbit", "KRW"),
    ("스텔라루멘", "upbit", "KRW-XLM", "crypto", "Stellar", "Upbit", "KRW"),
    ("알고랜드", "upbit", "KRW-ALGO", "crypto", "Algorand", "Upbit", "KRW"),
    ("더샌드박스", "upbit", "KRW-SAND", "crypto", "The Sandbox", "Upbit", "KRW"),
    ("디센트럴랜드", "upbit", "KRW-MANA", "crypto", "Decentraland", "Upbit", "KRW"),
    ("에이브", "upbit", "KRW-AAVE", "crypto", "Aave", "Upbit", "KRW"),
    ("유니스왑", "upbit", "KRW-UNI", "crypto", "Uniswap", "Upbit", "KRW"),
    ("컴파운드", "upbit", "KRW-COMP", "crypto", "Compound", "Upbit", "KRW"),
    ("메이커", "upbit", "KRW-MKR", "crypto", "MakerDAO", "Upbit", "KRW"),
    ("그래프", "upbit", "KRW-GRT", "crypto", "The Graph", "Upbit", "KRW"),
    ("렌더토큰", "upbit", "KRW-RNDR", "crypto", "Render", "Upbit", "KRW"),
    # ── 국내 주식 20개 ───────────────────────────────────────────────────
    # Yahoo Finance 티커 형식 사용: KOSPI → {code}.KS, KOSDAQ → {code}.KQ
    # → 워치리스트 추가 후 Yahoo 어댑터로 실시간 시세/OHLC 자동 조회 가능
    ("삼성전자", "yahoo", "005930.KS", "stock", "Samsung Electronics", "KOSPI", "KRW"),
    ("sk하이닉스", "yahoo", "000660.KS", "stock", "SK Hynix", "KOSPI", "KRW"),
    ("현대차", "yahoo", "005380.KS", "stock", "Hyundai Motor", "KOSPI", "KRW"),
    ("기아", "yahoo", "000270.KS", "stock", "Kia", "KOSPI", "KRW"),
    ("네이버", "yahoo", "035420.KS", "stock", "NAVER", "KOSPI", "KRW"),
    ("카카오", "yahoo", "035720.KS", "stock", "Kakao", "KOSPI", "KRW"),
    ("lg에너지솔루션", "yahoo", "373220.KS", "stock", "LG Energy Solution", "KOSPI", "KRW"),
    ("셀트리온", "yahoo", "068270.KS", "stock", "Celltrion", "KOSPI", "KRW"),
    ("포스코", "yahoo", "005490.KS", "stock", "POSCO Holdings", "KOSPI", "KRW"),
    ("kb금융", "yahoo", "105560.KS", "stock", "KB Financial", "KOSPI", "KRW"),
    ("신한지주", "yahoo", "055550.KS", "stock", "Shinhan Financial", "KOSPI", "KRW"),
    ("삼성sdi", "yahoo", "006400.KS", "stock", "Samsung SDI", "KOSPI", "KRW"),
    ("삼성바이오로직스", "yahoo", "207940.KS", "stock", "Samsung Biologics", "KOSPI", "KRW"),
    ("lg화학", "yahoo", "051910.KS", "stock", "LG Chem", "KOSPI", "KRW"),
    ("현대모비스", "yahoo", "012330.KS", "stock", "Hyundai Mobis", "KOSPI", "KRW"),
    ("kt", "yahoo", "030200.KS", "stock", "KT Corp", "KOSPI", "KRW"),
    ("sk텔레콤", "yahoo", "017670.KS", "stock", "SK Telecom", "KOSPI", "KRW"),
    ("한화에어로스페이스", "yahoo", "012450.KS", "stock", "Hanwha Aerospace", "KOSPI", "KRW"),
    ("hmm", "yahoo", "011200.KS", "stock", "HMM", "KOSPI", "KRW"),
    ("대한항공", "yahoo", "003490.KS", "stock", "Korean Air", "KOSPI", "KRW"),
]

# 정규화 키 → (market, symbol, asset_class, name_en, exchange, currency)
ALIASES: dict[str, tuple[str, str, str, str, str, str]] = {
    _key.lower().replace(" ", ""): (_market, _sym, _ac, _name, _ex, _cur)
    for _key, _market, _sym, _ac, _name, _ex, _cur in _RAW
}


def _normalize(query: str) -> str:
    """공백 제거 + 소문자 정규화."""
    return query.lower().replace(" ", "")


def lookup(query: str) -> list[tuple[SymbolInfo, int]]:
    """한글 alias 조회. (SymbolInfo, score) 튜플 리스트 반환.

    점수:
    - 정확일치: 2000
    - startswith: 1500
    """
    norm = _normalize(query)
    results: list[tuple[SymbolInfo, int]] = []
    seen: set[str] = set()

    for key, (market, symbol, asset_class, name_en, exchange, currency) in ALIASES.items():
        score: int | None = None
        if key == norm:
            score = 2000
        elif key.startswith(norm) or norm.startswith(key):
            score = 1500

        if score is not None and symbol not in seen:
            seen.add(symbol)
            info = SymbolInfo(
                symbol=symbol,
                name=name_en,
                asset_class=asset_class,
                exchange=exchange,
                market=market,
                currency=currency,
            )
            results.append((info, score))

    return results
