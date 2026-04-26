# ADR 0013 — 대시보드 Summary 스키마 확장 (sprint-07)

| 항목 | 내용 |
|---|---|
| 상태 | 확정 (sprint-07) |
| 초안 | sprint-07 (2026-04-23) |
| 결정자 | backend-engineer, frontend-engineer, analyzer-designer |

---

## 맥락

sprint-07 에서 제공받은 목업과 기존 `/portfolio/summary` 응답의 필드 매핑이 1:1 로 떨어지지
않았다. 목업은 다음 네 가지 위젯을 요구했다.

- **보유 종목 수·최하위 자산·리스크 점수** 3 칩 (상단 KPI)
- **1W / 1M / 3M / 1Y 탭 수익률** (중단 Period Tabs)
- **비중·수익률 2시리즈 바차트** (dimension breakdown)
- **뉴스 카드 썸네일** (좌측 이미지 박스)

이를 지원하기 위해 BE 스키마와 FE 컴포넌트를 확장했고 (커밋 63c49b3, bdc0e80, 85198cf),
그 과정에서 세 가지 설계 결정이 필요했다.

(a) 리스크 점수를 어떤 **정량 지표**로 표현할 것인가 — 목업은 "입출금 위험 분석 68.3%" 를
    그대로 보여주지만, 해당 수치의 출처/계산식이 불명확해 MVP 에서 재현 불가능하다.
(b) period 전환을 **프리셋 탭** 으로 고정할지, **임의 range picker** 로 열 것인가.
(c) 뉴스 썸네일을 BE 에서 **필수 필드** 로 강제할지, **optional** 로 둘 것인가.

---

## 결정

### (a) HHI 기반 `risk_score_pct` 채택

`PortfolioSummary.risk_score_pct` 는 **허핀달-허쉬만 지수(HHI)** 를 0~100 스케일로 환산한 값으로
정의한다. 계산식:

```
HHI = Σ (weight_i)² × 100
```

- `weight_i` : 포트폴리오 내 자산 i의 비중 (0~1)
- 단일 자산 100% 집중 시 HHI = 100, 완전 분산(N종 균등) 시 HHI = 100/N
- 구현: `backend/app/services/portfolio.py` 에서 `sum(w ** 2 for w in weights) * 100`

대안 지표와의 비교:

| 지표 | 입력 요구사항 | MVP 재현성 | 설명 난이도 | 채택 여부 |
|---|---|---|---|---|
| HHI (집중도) | 현재 비중만 | 높음 (업로드 CSV로 즉시 계산) | 낮음 ("한 종목 몰빵 위험") | **채택** |
| VaR (95%) | 시세 시계열 + 분산/공분산 | 낮음 (일별 종가 최소 60일 필요) | 높음 (분포 가정 설명 필요) | 보류 |
| Beta | 시장 인덱스 + 무위험 수익률 | 낮음 (KOSPI/S&P 매핑 + 무위험 기준) | 중 (회귀 기반) | 보류 |
| Sharpe | 수익률 시계열 + 무위험 수익률 | 중 (스냅샷 있으나 무위험 기준 미정) | 중 | 보류 |

채택 근거:
1. **설명 가능성**: 심사위원·일반 사용자에게 "한 종목 편중도 = 리스크" 가 직관적으로 전달된다.
   VaR/Beta 는 단위·분포 가정 설명에 시간이 걸린다.
2. **MVP 입력 제약**: 임의 CSV 업로드만으로 계산 가능해야 한다. 시세 시계열/무위험 수익률이
   없어도 비중만 있으면 HHI 가 산출된다.
3. **목업 68.3% 대체**: 사용자 승인 (2026-04-23). 목업 하드코딩 수치 대신 실제 업로드 데이터를
   반영하는 정량 값으로 치환한다. VaR/Beta 는 데이터 파이프라인이 성숙한 이후 ADR 로 추가 검토.

### (b) Period 프리셋 4종 고정 (1W / 1M / 3M / 1Y)

`PortfolioSummary.period_days` 는 `{7, 30, 90, 365}` 중 하나로 제한한다. 임의 `from/to` range
picker 는 도입하지 않는다.

근거:
1. **캐싱 단순화**: Redis 캐시 키를 `summary:{user}:{period_days}` 4종으로 고정. 임의 range 는
   키 폭발로 캐시 효율이 급락한다.
2. **URL 상태 최소화**: `/dashboard?period=30` 한 파라미터로 공유·북마크가 가능하다. 임의
   range 는 `from=&to=` 두 파라미터가 필요하고 타임존 이슈가 따라붙는다.
3. **스냅샷 버킷 일치**: `backend/app/services/portfolio.py` 가 snapshot 을 `period_days`
   offset 으로 필터링한다. 버킷을 고정하면 누락일(주말/공휴일) 보간 로직을 4 케이스만
   테스트하면 된다.
4. **확장 경로**: 추후 "Custom" 프리셋 추가 시 `period_days` 를 optional 로 바꾸고 `from/to` 를
   병행 수용하는 마이그레이션을 새 ADR 로 기록한다.

### (c) `Citation.thumbnail_url` optional 추가

`backend/app/schemas/news.py::Citation` 에 `thumbnail_url: str | None = None` 필드를 추가한다.
BE 는 누락을 허용하고, FE 에서 폴백을 책임진다.

근거:
1. **소스 이질성**: 뉴스 공급자마다 썸네일 메타 위치·해상도가 제각각 (OpenGraph `og:image`,
   RSS `media:thumbnail`, 공시 API 는 아예 없음). BE 에서 필수로 강제하면 정규화 로직이
   공급자마다 분기되어 유지보수 비용이 커진다.
2. **stub 코퍼스 재현성**: `backend/tests/fixtures/news/*.json` 은 `picsum.photos/seed/<id>`
   로 채워 결정론적이고 CI 친화적인 이미지 URL 을 제공한다. Live 모드에서 누락 시 FE 가
   이니셜 박스(제목 첫 글자 + 브랜드 컬러) 로 폴백한다.
3. **FE 폴백 단일 지점**: `frontend/components/dashboard/NewsPanel.tsx` 가 `thumbnail_url`
   존재 여부에 따라 `<Image>` ↔ `<InitialBox>` 분기를 책임진다. BE 가 강제하지 않으므로
   공급자 추가 시 BE 스키마 변경이 불필요하다.

---

## 결과

- `PortfolioSummary` 에 `holdings_count`, `worst_asset_pct`, `risk_score_pct`,
  `period_change_pct`, `period_days`, `dimension_breakdown` 6 필드가 추가되어 목업 1:1 매치가
  완료되었다 (FE 컴포넌트 AllocationBreakdown / PeriodTabs / TopHoldingsTable /
  DimensionBars / NewsPanel).
- HHI 산식이 `backend/app/services/portfolio.py` 에 단일 함수로 구현되어 골든 샘플 회귀
  테스트 대상이 된다. VaR/Beta 도입은 시세 시계열 파이프라인 구축 후 신규 ADR 로 기록한다.
- Period 4 프리셋 + HHI 단일 리스크 지표 조합으로 `/portfolio/summary` 응답이 period 당
  1 캐시 엔트리로 수렴하여 데모 당일 5초 내 렌더 목표(공모전 심사 기준 2) 에 기여한다.
- `Citation.thumbnail_url` optional 정책으로 stub ↔ live 모드 전환 시 BE 스키마 변경이
  불필요해졌고, 뉴스 공급자 추가는 FE 폴백 로직만으로 흡수 가능하다.
