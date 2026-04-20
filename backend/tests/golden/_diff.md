# Prompt Diff Log

규약: 프롬프트 파일(`backend/app/agents/prompts/*.md`) 을 수정할 때마다
**변경 이유 + 핵심 diff** 를 여기에 남긴다. 회귀 테스트(`test_regression_runner.py`)
가 통과하는지 `backend/tests/golden/_last_run.json` 으로 확인한 뒤 커밋한다.

---

## 2026-04-19 — Week-2 OHLC 지표 기반 해석 보강

### 배경

Week-1 프롬프트는 사용자 업로드 rows 만 가정해 3~5행짜리 샘플에 최적화되어 있었음.
Week-2 에서 `market adapter` 가 90일 OHLC 를 프리패치해 주입하기 시작하면서,
정량 지표(MA20/MA60 교차, 변동성 표준편차, 최대낙폭)를 프롬프트에 함께 넘기도록
구조를 잡았다. Analyzer 는 이 `indicators` 블록을 우선 인용해야 hallucination 이 줄어든다.

### stock_system.md

- **추가**: `headline`, `narrative`, `signals`, `confidence` 필드를 산출 스키마에 포함
- **추가**: `indicators.ma_cross / volatility_pct / max_drawdown_pct` 해석 룰 섹션
- **강화**: `evidence[].claim` 은 원본 rows 또는 indicators 의 실제 수치만 허용
- **유지**: `summary` 는 legacy 호환으로 살려둠 (headline 과 동일 가능)

### crypto_system.md

- **추가**: `headline`, `narrative`, `signals`, `confidence`, `max_drawdown_pct`, `ma_20/60`
- **추가**: 변동성 버킷 (>=3% medium, >=5% high), 일간 변동률 50% 초과 시 risk signal
- **강화**: `quote_currency` 추론 규칙 명확화

### critique_system.md

- **추가**: `headline` 필드도 검증 대상으로 명시
- **강화**: 반올림 허용 규칙(유효숫자 3자리까지 supported 취급)
- **추가**: `metrics.period_return_pct` 등 유도값의 ±1% 오차 허용 체크 포인트

### fx_system.md

- 이번 라운드에서는 변경 없음 (환율은 OHLC 어댑터가 아직 연동되지 않음)

### 영향 범위

- 기존 12개 골든 샘플 회귀: 모두 `headline` 없이 `summary` 만 포함 → `AnalyzerOutput` 스키마를
  `summary | headline` OR 로 완화해 하위 호환 유지. `test_regression_runner.py` 전량 pass.
- 새 테스트 `test_analyze_with_ohlc.py` 2종 추가 (crypto/stock OHLC 주입 케이스).

### Rollback 포인트

문제 발생 시 프롬프트는 Week-1 버전(`summary/highlights/metrics/evidence` 만)으로 되돌리고,
`AnalyzerOutput.summary` 를 다시 required 로 복구하면 된다.
