# FE 팀 셀렉터 요청 메모

작성일: 2026-04-19
작성자: integration-qa (week2)
대상: frontend-engineer (다음 세션)

**[week-3 업데이트: RESOLVED]**
fe-week3 가 모든 셀렉터 요청을 반영했습니다. 아래 항목은 히스토리 참조용입니다.

## 배경

E2E 테스트(`watchlist.spec.ts`, `symbol-detail.spec.ts`)가 `data-testid` 속성에 의존합니다.
아래 속성들이 대응 컴포넌트에 추가되면 `test.skip()` 없이 완전 통과 가능합니다.

---

## 워치리스트 페이지 (`/watchlist`)

| 요청 속성 | 위치 | 비고 |
|-----------|------|------|
| `data-testid="symbol-search"` | 심볼 검색 `<input>` | 현재 placeholder/aria-label fallback 사용 중 |
| `data-testid="watchlist-row"` | 워치리스트 테이블의 각 `<tr>` 또는 행 컴포넌트 | 행 수 카운트에 필요 |
| `data-testid="watchlist-delete"` | 각 행의 삭제 버튼 | aria-label fallback 있지만 testid 권장 |
| `data-updated` 속성 | `watchlist-row` 요소 | 가격 갱신 시 ISO timestamp 값으로 업데이트 — 실시간 갱신 감지용 |
| `role="listbox"` | 검색 드롭다운 컨테이너 | 이미 추가돼 있으면 OK |

### 현재 동작

검색 드롭다운 `role="listbox"` 가 없으면 시나리오 1이 `test.skip()` 으로 넘어갑니다.
`data-testid="watchlist-row"` 가 없으면 시나리오 2, 3도 스킵됩니다.

---

## 종목 상세 페이지 (`/symbol/[market]/[code]`)

| 요청 속성 | 위치 | 비고 |
|-----------|------|------|
| `data-testid="symbol-price"` | 현재가 표시 요소 | 없으면 숫자 패턴 fallback 사용 |
| `data-testid="change-pct"` | 변동률(%) 표시 요소 | 없으면 스킵 |
| `data-testid="candlestick-chart"` 또는 `data-testid="chart-container"` | TradingView/캔들차트 래퍼 | `canvas` selector fallback 있지만 명시적 testid 권장 |
| `data-testid="router-reason-toggle"` | Router 결정 근거 토글 버튼 | 없으면 시나리오 3 자동 skip |
| `data-testid="router-reason-content"` | 토글 후 보이는 근거 텍스트 영역 | `router_reason` 문자열 포함 여부 검증 |

### 현재 동작

`data-testid="router-reason-toggle"` 이 없으면 시나리오 3이 `test.skip()` 됩니다.
데모 시나리오 체크리스트에 "Router 결정 근거가 화면에 보이도록 토글"이 포함되어 있으므로
공모전 전까지 구현 권장.

---

## 구현 예시

```tsx
// 워치리스트 행 컴포넌트
<tr
  data-testid="watchlist-row"
  data-updated={lastUpdatedAt?.toISOString()}
>
  ...
  <button
    data-testid="watchlist-delete"
    aria-label="삭제"
    onClick={() => handleDelete(item.id)}
  >
    ...
  </button>
</tr>

// 종목 상세 — 가격 표시
<span data-testid="symbol-price">{formatPrice(quote.price)}</span>
<span data-testid="change-pct">{quote.change_pct.toFixed(2)}%</span>

// Router 결정 근거 토글
<button
  data-testid="router-reason-toggle"
  aria-label="Router 결정 근거 보기"
  onClick={() => setShowReason((v) => !v)}
>
  분석 근거
</button>
{showReason && (
  <div data-testid="router-reason-content">
    {analyzeResult.meta.router_reason}
  </div>
)}
```

---

## 우선순위

1. `data-testid="watchlist-row"` — 시나리오 1/2/3 전부 의존
2. `data-testid="router-reason-toggle"` + `router-reason-content` — 데모 체크리스트 필수
3. `data-testid="symbol-price"` — 시나리오 1 안정성
4. `data-updated` — 시나리오 2 실시간 갱신 감지
