# Skills.md - PB/WM 투자 분석 및 리포팅 생성 규칙

## 1. 문서 목적

이 문서는 `hacker-dashboard`가 PB/WM 조직을 위한 투자 데이터 통합 분석 및 고객 브리핑 리포팅 솔루션으로 동작하기 위한 제출용 Skill 명세다.

Codex는 이 규칙을 기준으로 브로커 CSV 스키마 해석, 고객 포트폴리오 정규화, Meta Router 분류, deterministic metric 계산, 차트 선택, evidence-backed insight, 품질 게이트, 고객 리포트 생성을 구현한다.

## 2. 입력 데이터 처리

### 2.1 Broker CSV Adapter

- 입력은 CSV, JSON rows, portfolio holdings, 자연어 query 중 하나일 수 있다.
- CSV는 증권사, 거래소, 고객 제공 계좌 파일일 수 있다.
- 컬럼명, 첫 5개 행, 값 패턴, 심볼 형식, 시장, 통화, 계좌 단서를 함께 분석한다.
- 원본 컬럼명과 source row index는 evidence 추적을 위해 보존한다.
- confidence가 95% 이상인 필드만 자동 매핑한다.
- 불확실한 필드는 `needs_review`로 남기고 PB 확인을 요구한다.

### 2.2 표준 필드

- symbol: `symbol`, `ticker`, `code`, `pair`, `종목코드`, `티커`
- name: `name`, `asset_name`, `종목명`, `상품명`
- date: `date`, `timestamp`, `datetime`, `거래일`
- price: `close`, `price`, `trade_price`, `current_price`, `현재가`
- quantity: `quantity`, `qty`, `shares`, `units`, `보유수량`
- cost: `avg_cost`, `avg_price`, `average_price`, `매입가`, `평균단가`
- market: `market`, `exchange`, `broker`, `거래소`, `시장`
- currency: `currency`, `ccy`, `통화`
- account: `account`, `account_no`, `계좌`, `계좌번호`
- client_id: `client_id`, `customer_id`, `고객ID`

누락 필드는 추정하지 않고 validation issue로 남긴다.

### 2.3 Client Normalization

- 고객 단위 분석은 `client_id` 또는 명시적으로 선택된 고객 컨텍스트가 필요하다.
- 여러 계좌, 시장, 통화, 자산군을 통합하되 source row를 보존한다.
- 통화 변환은 환율, 기준일, 출처를 evidence로 남긴다.
- 고객 성향, 투자 목적, 적합성 정보는 입력에 없으면 생성하지 않는다.

## 3. Router 분류

Router는 LLM보다 deterministic rule을 우선한다.

| 자산군 | 판별 근거 |
|---|---|
| `portfolio` | `market/code/quantity/avg_cost`, 또는 `quantity + avg_cost + code|symbol + market|currency` |
| `crypto` | `KRW-BTC`, `BTC-USD`, `BTC/USDT`, `upbit`, `binance`, `USDT-*` |
| `stock` | `005930.KS`, `000660.KS`, `AAPL`, `TSLA`, `NVDA`, 거래소 컬럼 |
| `fx` | `USDKRW=X`, `USD/KRW`, `EURUSD`, `rate`, `exchange_rate` |
| `macro` | `cpi`, `gdp`, `unemployment`, `yield_10y`, `fed_rate`, `inflation` |
| `mixed` | 두 개 이상의 자산군이 동시에 유효하게 감지됨 |

Router 결과는 `asset_class`, `router_reason`, `confidence`, `detected_symbols`, `needs_review`를 포함한다.

## 4. Quant Metric 규칙

모든 수치 지표는 deterministic code가 계산한다.

- 기간 수익률: `(last - first) / first * 100`
- 변동성: 관측 구간 로그수익률 표준편차
- MDD: running peak 대비 최저 drawdown
- HHI: 자산군 또는 종목 비중 제곱합
- PnL: `total_value - total_cost`
- PnL%: `pnl / total_cost * 100`
- Drift: `current_allocation - target_allocation`
- Rebalance quantity: target value delta를 검증된 reference price로 나눈 값

지표 데이터가 부족하면 숫자를 생성하지 않고 `insufficient_data` 상태를 표시한다. LLM은 수치를 만들지 않고 계산된 지표를 설명한다.

## 5. 시각화 선택 규칙

| 데이터 형태 | 시각화 |
|---|---|
| 가격 시계열 | line chart 또는 candlestick |
| OHLC | lightweight-charts candlestick |
| 자산군 비중 | donut/pie, 범주가 많으면 bar |
| 목표 대비 drift | zero-centered diverging bar |
| holdings/actions | sortable table |
| 월간 수익률 | calendar heatmap |
| validation issue | warning badge |
| evidence | source row/metric/API panel |
| client report | sectioned preview with evidence chips |

## 6. Evidence 및 품질 게이트

모든 분석 결과는 렌더링 전 gate를 통과해야 한다.

1. Schema Gate: 입력/출력 shape, 필수 필드, 타입 검증.
2. Domain Gate: 음수 가격, 잘못된 수량, 비정상 allocation, 금지 문장 검증.
3. Evidence Gate: 모든 숫자와 사실 주장에 rows, metrics, API data, fixture 근거 연결.
4. Critique Gate: AI narrative와 리포트 문장이 계산 결과와 원본 데이터에 부합하는지 검증.

Gate 실패 시 정상 인사이트나 고객용 리포트로 표시하지 않고 degraded 또는 `insufficient_data` 상태를 반환한다.

## 7. Insight 규칙

- `headline`: 가장 강한 근거 기반 사실 1개.
- `narrative`: 2~4문장.
- `highlights`: 근거가 있는 2~5개 bullet.
- `warnings`: trigger된 risk note.
- `evidence`: claim-to-source mapping.
- `confidence`: 0~1.

금지 항목:

- 보장 수익률.
- 확정적 시장 방향.
- 근거 없는 미래 예측과 인과관계.
- 입력에 없는 ticker, price, date, allocation, client profile.
- 직접적인 개인화 매수/매도 지시.

## 8. Client Briefing Report 규칙

고객 브리핑 리포트는 다음 순서를 따른다.

1. 요약
2. 성과 기여도
3. 리스크 분석
4. 리밸런싱 제안
5. PB 의견

각 섹션은 최소 하나 이상의 deterministic metric 또는 source row evidence를 가진다. PB 의견은 추천 강요가 아니라 설명과 선택지 제시 형태로 작성한다. Evidence 또는 gate 검증이 부족하면 최종 리포트가 아니라 검토 필요 상태를 반환한다.

## 9. 출력 프로토콜

```json
{
  "status": "success | warning | degraded | insufficient_data | error",
  "client_context": {
    "client_id": "string",
    "risk_profile": "string | null"
  },
  "router": {
    "asset_class": "portfolio | stock | crypto | fx | macro | mixed",
    "router_reason": "string",
    "confidence": 0.0,
    "needs_review": []
  },
  "metrics": {
    "calculated_values": {},
    "insufficient": []
  },
  "ai_insights": [
    {
      "type": "opportunity | risk | warning",
      "content": "string",
      "evidence": []
    }
  ],
  "gate_results": {
    "schema": true,
    "domain": true,
    "evidence": true,
    "critique": "verified"
  },
  "report": {
    "export_ready": true,
    "sections": []
  }
}
```

## 10. Codex 실행 기준

- 반복적인 분석/대시보드/리포팅 작업은 `$investment-dashboard`를 사용한다.
- `AGENTS.md`는 프로젝트 최상위 지시문이다.
- `.agents/skills/investment-dashboard/SKILL.md`는 Codex-readable Skill 진입점이다.
- 세부 규칙은 `.agents/skills/investment-dashboard/references/`에서 관리한다.
- `.claude/`는 legacy context이며 신규 규칙을 추가하지 않는다.
