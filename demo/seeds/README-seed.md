# 데모 시드 데이터 설명

공모전 데모용 샘플 CSV. 실제 거래 데이터가 아닌 **고정 placeholder 값**입니다.

## stocks.csv

| 컬럼 | 의미 |
|---|---|
| ticker | 종목 코드 (US: AAPL, TSLA, NVDA / KR: 005930 삼성전자, 000660 SK하이닉스) |
| date | 거래일 (YYYY-MM-DD) |
| open / high / low / close | OHLC 가격 |
| volume | 거래량 (주) |
| market | 상장 시장 (US / KR) |
| currency | 가격 통화 (USD / KRW) |

Router 가 `market`, `currency` 컬럼을 보고 **StockAnalyzer** 를 선택합니다.

## crypto.csv

| 컬럼 | 의미 |
|---|---|
| pair | 거래 페어 (KRW-BTC, USDT-ETH 등) |
| timestamp | ISO 8601 UTC 타임스탬프 |
| open / high / low / close | OHLC 가격 |
| volume_base | 기준 자산 거래량 |
| volume_quote | 견적 자산 거래량 |
| exchange | 거래소 (Upbit / Binance) |

Router 가 `pair` 컬럼 패턴(XXX-YYY)을 보고 **CryptoAnalyzer** 를 선택합니다.

## mixed.csv

주식 + 코인이 혼재된 시트. Router 의 **자산 분류 능력**을 시연하기 위한 시나리오.

| 컬럼 | 의미 |
|---|---|
| asset_id | 자산 식별자 (종목코드 또는 페어) |
| asset_type | `stock` 또는 `crypto` |
| date | 거래일 (YYYY-MM-DD) |
| price | 종가 |
| volume | 거래량 |
| currency | 가격 통화 |
| exchange | 거래소 / 시장 |
| market_cap_usd | 시가총액 (USD 환산, 참고용) |

Router 는 `asset_type` 컬럼이 있으면 이를 우선 활용하고, 없을 경우 `asset_id` 패턴으로 분류합니다.
