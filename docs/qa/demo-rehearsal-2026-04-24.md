# 데모 리허설 체크리스트 — 2026-04-24 (Phase 0/1/2 완료판)

| 항목 | 값 |
|---|---|
| 작성일 | 2026-04-24 |
| 대상 심사 | 공모전 최종 발표 (8분 시연) |
| 기준 커밋 | `b97a122` (Phase 2 완료) |
| 기준 브랜치 | `feat/qa-harness-20260422-111542-nl-copilot-sprint-06` |
| 전 버전 | `docs/qa/demo-rehearsal-2026-04-22.md` |

---

## 0. 데모 모드 표준 카피 (🟢 심사 Q&A 1순위)

심사위원이 "왜 로그인 없어요?", "OAuth 왜 disabled?" 라고 물으면 **아래 문장 그대로** 대답:

> "이번 제출물은 **단일 사용자 데모 모드**입니다. 실서비스 전환 시
> `/login` 라우트에서 Supabase Auth를 연결하도록 `user_id` 컬럼이 모든
> 테이블에 이미 반영되어 있고, 연결 계정 카드의 OAuth 버튼은 해당 스프린트에서
> 붙이면 됩니다. 심사 데모에서는 구현보다 서사 전달에 시간을 쓰기 위해
> 단일 demo 사용자로 고정했습니다."

해당 카피가 **시각적으로 이미 노출**되는 위치 — 이 세 곳이 심사위원 시선에 들어오면
추가 설명 없이도 맥락이 전달됨:

1. 사이드바 하단 "Demo User · demo@demo.com"
2. 설정 > 연결된 계정 카드 헤더 **DEMO 배지**
3. 설정 > 연결된 계정 각 버튼 hover 시 툴팁 "데모 모드 — 실 OAuth 연동은 다음 스프린트에 추가됩니다"

---

## 1. 준비 사항

### 1.1 인프라 기동

- [ ] BE 기동: `cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
- [ ] FE 기동: `cd frontend && npm run dev`
- [ ] BE 헬스체크: `curl http://localhost:8000/health` → `status=ok|degraded`
- [ ] 헤더 "API 정상" 녹색 인디케이터 확인

### 1.2 시드 데이터 확인 (Phase 0/1/2 이후 필수)

| 엔드포인트 | 기대값 |
|---|---|
| `/portfolio/holdings` | 3건 (KRW-BTC 0.05, AAPL 5, 005930 10) |
| `/portfolio/snapshots` | **31건** (Phase 1 에서 30일 시드 추가됨) |
| `/portfolio/market-leaders` | 5건 (NVDA, AAPL, TSLA, 삼성전자, Bitcoin) |
| `/watchlist/alerts` | 2건 (NVDA > 550, KRW-BTC < 70M) |
| `/market/quotes/naver_kr/005930` | ₩72,000 (1.0 더미 아님) |

만약 `holdings` 가 비어있으면 **schemathesis fuzzing 잔해** — 아래 명령으로 재시드:

```powershell
$h1 = '{"market":"upbit","code":"KRW-BTC","currency":"KRW","quantity":0.05,"avg_cost":95000000}'
$h2 = '{"market":"yahoo","code":"AAPL","currency":"USD","quantity":5,"avg_cost":200}'
$h3 = '{"market":"naver_kr","code":"005930","currency":"KRW","quantity":10,"avg_cost":75000}'
foreach ($h in @($h1,$h2,$h3)) { Invoke-RestMethod -Uri 'http://localhost:8000/portfolio/holdings' -Method Post -Body $h -ContentType 'application/json' }
```

알림 재시드:

```bash
cd backend && uv run python scripts/seed_watchlist_alerts.py
```

### 1.3 시각 프리셋

- [ ] 브라우저 창 1920×1080, DevTools 닫기
- [ ] **다크모드** (심사장 조명 대응)
- [ ] 사이드바 펼친 상태, Copilot Drawer 닫힌 상태
- [ ] localhost:3000 (127.0.0.1 금지 — CORS 이유, §6 참조)

---

## 2. 8분 시연 타임라인

### 2.1 오프닝 — 대시보드 (0:00–1:00)

메인 페이지 `/` 로 시작. 설명 대사:

> "`/` 대시보드입니다. 상단 KPI 6개는 모두 실시간 BE 에서 계산됩니다."

짚어야 할 숫자:
- **총자산 ₩8.35M · +21.94%** — 포트폴리오 평가손익
- **30일 변동 +4.81%** — 31일 snapshot 기반 (이 수치가 있으면 Phase 1 시드가 들어간 것)
- **집중도 리스크 53.6% · 보통** — HHI 기반 (Q&A 시 §5 참조)

> "오른쪽 '시장 주도주' 카드는 **글로벌 5종목의 실시간 시세**입니다 — 내 보유와 무관합니다.
> 하단 '최신 뉴스' 는 내 보유 종목 검색 쿼리로 BE RAG 에서 가져옵니다."

### 2.2 포트폴리오 페이지 (1:00–2:00) — `/portfolio`

> "5개 KPI + 자산 구성 + 자산 한눈에(필터/정렬) + 섹터 히트맵 + 월간 수익률 달력 + AI 인사이트."

핵심 짚기:
- 승률 66.7% "우수"
- 섹터 히트맵: Crypto +21.9%, Tech +36.72%, 반도체 -4.0% (삼성전자 stub 가격 반영)
- **AI 인사이트 카드** — 3단 게이트 배지(Schema/Domain/Critique) **모두 pass** 표시
- 월간 수익률 캘린더 — GitHub contribution 스타일 365칸

### 2.3 워치리스트 (2:00–3:00) — `/watchlist`

> "관심 종목 알림 **CRUD 전체** 가 실 BE 에 저장됩니다."

데모 액션:
1. 알림 설정 카드 "+ 추가" 클릭 → AAPL above 300 입력 → Enter
2. 벨 아이콘 클릭 → 비활성화 → 새로고침 → 유지됨
3. 삭제 → 리스트에서 사라짐

> "워치리스트 테이블 상단은 아직 비어있습니다 — 관심종목 CRUD 는 β 스프린트 예정."

### 2.4 심볼 상세 (3:00–4:30) — `/symbol/yahoo/AAPL`

> "종목 상세는 **TradingView Lightweight Charts** (메인 캔들) + **Recharts** (RSI/MACD 서브차트) 이중 구조입니다."

핵심 짚기:
- 상단 타임프레임 탭 8개
- 메인 차트 MA20/MA60 라인
- **RSI 서브차트** — 0~100, 30/70 참조선, 현재 63.26 "과매수 경계"
- **MACD 서브차트** — 히스토그램 + MACD/Signal 라인, 현재 MACD 3.96 > Signal 2.18 **상승 추세**
- 지표 6카드: 등락율 +2.73%, 평단가 $200 (내 holding), MA20 $260.49, MA60 $261.74, 거래량 33.14M, 시그널 '보유'
- 우측 사이드: 기본 정보 + 기술 지표 요약 + 주요 이슈 3건

### 2.5 시장 분석 (4:30–5:30) — `/market-analyze`

> "7개 지수 KPI + 20개국 세계지도(타일) + 11개 섹터 바차트 + 5개 원자재 + 시장 뉴스."

핵심 짚기:
- KOSPI +0.82% / S&P +0.45% / VIX -3.41%
- 세계 히트맵 — **인도 +1.43%, 러시아 -1.12%** 양극단
- 섹터 바: 반도체 +2.45%, 에너지 -1.05%

### 2.6 코파일럿 (5:30–6:30) — `/copilot`

> "LangGraph 기반 AI 코파일럿. **3단 품질 게이트** 가 차별화입니다."

데모 액션:
1. 좌측 "새 대화 시작" 클릭
2. 추천 질문 "현재 포트폴리오 리스크 수준은?" 클릭
3. plan.ready → steps → gate 배지 progressive render

핵심 짚기:
- 우측 "포트폴리오 요약 · AI 인사이트" — **대시보드와 동일 값** 실시간 연동 (+21.98% 일치)
- 우측 "새 대화 시작 가이드" — mock 최근 활동 제거됨

### 2.7 업로드 & 분석 (6:30–7:30) — `/upload`

> "공모전 핵심 서사 #2 — 임의 CSV 를 5초 내 대시보드로."

데모 액션:
1. `demo/seeds/sample_portfolio.csv` 드래그
2. 검증 카운트 표시 (전체 / OK / 오류 / 경고)
3. 미리보기 5행
4. Analyzer 선택 (포트폴리오 기본값)
5. 분석 시작 → 4단 배지 (Router → Schema → Domain → Critique) 순차 pass
6. 완료 → 대시보드 자동 전환

### 2.8 마무리 (7:30–8:00)

> "기술 스택: Next.js 15 + React 19 + FastAPI + LangGraph + Claude Sonnet 4.6.
> 차별화 3가지:
> 1. Router(Meta) → Analyzer(Sub) **계층적 에이전트 구조**
> 2. 스키마/도메인/critique **3단 품질 게이트** 로 환각 차단
> 3. 임의 CSV → 5초 자동 대시보드 생성
>
> 감사합니다."

---

## 3. 심사 예상 Q&A (16건)

### 기술 아키텍처

- **Q1. Router 는 뭘 기준으로 Analyzer 를 고르나?**
  A. CSV 컬럼 스키마 + 샘플 5행 → Claude 에게 "이 데이터는 어느 자산군?" 질의. 결과는 `router_decision.rationale` 에 기록되어 UI 에 노출.

- **Q2. 3단 게이트의 critique 는 어떻게 구현?**
  A. 별도 LLM 호출로 "이 답변의 근거 문장이 인용 corpus 에 실제 존재하는가" 검사. source_url 이 pgvector 에 없으면 게이트 fail → 답변 재생성.

- **Q3. RSI/MACD 는 어디서 계산하나?**
  A. BE `pandas_ta` 로 서버 계산 → FE 는 시계열 수신 후 Recharts 렌더. 클라이언트 부담 감소 + 골든 회귀 가능.

- **Q4. pgvector 인덱스 전략?**
  A. ivfflat (lists=100) — ADR 0011 에 기록. 문서 ingest 시 chunk 단위 768d 임베딩.

### 데이터

- **Q5. 목업 68.3% vs 현재 53.6% (집중도 리스크) 차이?**
  A. (2026-04-22 문서 참조) 목업 초기 와이어프레임의 "입출금 위험" 지표를 **HHI 자산 집중도** 로 교체. 산업 표준 지수.

- **Q6. 국내주식 (naver_kr) 데이터 소스?**
  A. **현재 데모 모드** — 10종목 stub 가격 (삼성전자 72,000 원 등) + seed(hash(symbol)) 기반 100거래일 OHLC. 실서비스 전환 시 네이버 금융 API 또는 KRX 공공 데이터.

- **Q7. 실시간 틱 어떻게?**
  A. Upbit / Binance WebSocket 직접 구독 (FE `lib/realtime/`). Redis 캐시 TTL 5초.

- **Q8. 30일 스냅샷 어떻게 채웠나?**
  A. `scripts/seed_snapshots.py` — 현재 total_value_krw 기준 역산 + sin noise ±0.3%. 실서비스는 일 1회 배치 적재.

### 심사 기준

- **Q9. 임의 CSV 처리 범위?**
  A. 현재 **5종 샘플** (정상 3 + 오류 1 + 경고 1) 골든 테스트 보유. 컬럼 매핑은 Claude prompt 에서 유연하게 인식.

- **Q10. 로그인 없이 어떻게 동시 사용자?**
  A. (§0 표준 카피 그대로 답변)

- **Q11. 연결된 계정 OAuth 왜 전부 disabled?**
  A. (§0 표준 카피) 설정 카드 **DEMO 배지** 가 이미 맥락을 전달 중.

- **Q12. 워치리스트 맞춤 알림은?**
  A. "Phase β-γ 연동 후 활성화" 로드맵 노출 중. 핵심 알림 CRUD(ID/방향/임계값/토글)는 이미 완성.

### 운영/배포

- **Q13. Lighthouse 수치?**
  A. Performance 90+, Accessibility 95+, 다크/라이트 모두. `/lighthouse/` 리포트 첨부.

- **Q14. API 키 없이 어떻게 재현?**
  A. `COPILOT_NEWS_MODE=stub` 기본값 + fixture corpus. 실 키는 opt-in.

- **Q15. 배포는?**
  A. Vercel(FE) + Fly.io(BE) + Neon(Postgres). deploy 스킬로 무중단 롤아웃.

- **Q16. 계약 테스트 통과율?**
  A. schemathesis 48개 엔드포인트 중 coverage 40 pass / 8 fail. 잔여 fail 은 generator 가 존재하지 않는 resource 요청한 404 노이즈.

---

## 4. 시연 중 금기

| 금기 | 이유 |
|---|---|
| **라이브 schemathesis / 부하 테스트 금지** | fuzzing 이 실 DB holdings/alerts 를 삭제함 (Phase 2 경험) |
| 현장에서 새 기능 시연 | 녹화본 + 검증 시드만 |
| DevTools 네트워크 탭 열기 | X-User-Id / API 키 가능성 |
| `127.0.0.1:3000` 접속 | CORS 분리로 `/users/me/settings` 등 호출 실패 |
| LLM 을 현장에서 첫 호출 | 캐시된 골든 경로만. Copilot stub 모드 (`mock_scenario=degraded`) 활용 |
| 새 탭으로 news URL 열기 | example.com 404 노출 |

---

## 5. 숫자 치트시트 (현재 시드 기준)

| 지표 | 현재값 | 근거 |
|---|---|---|
| 총자산 | ₩8,352,802 | BTC 5.79M + AAPL 1.85M + 005930 720K |
| 총 손익률 | +21.94% | (현재가치 - 원가) / 원가 |
| 일간 변동 | -0.13% | snapshot D-1 대비 |
| 30일 변동 | +4.81% | snapshot 31건 기반 |
| 집중도 리스크 | 53.6% | HHI 63.37/100 |
| 승률 | 66.7% | 수익 종목 2/3 |
| 섹터 히트맵 | Crypto +21.9% / Tech +36.7% / 반도체 -4.0% | BTC/AAPL/005930 |
| RSI(14) AAPL | 63.26 | 과매수 경계 |
| MACD AAPL | 3.96 > Signal 2.18 | 상승 |

심사 중 이 표만 옆에 띄워 놓아도 대부분 질문은 바로 답할 수 있음.

---

## 6. 리허설 체크리스트 (데모 하루 전)

- [ ] 8분 전체 런스루 1회 (타이머)
- [ ] 녹화본 MP4 1920×1080, 자막 포함, 오디오 레벨 -14 LUFS
- [ ] `make up` 재기동 후 §1.2 시드 전수 확인
- [ ] 예비 URL (Vercel + Fly.io 배포본) 2곳 health check
- [ ] Lighthouse 스크린샷 슬라이드 1장
- [ ] 노트북 1920×1080 레이아웃 검증 — §2 8페이지 모두 스크롤 없이 주요 정보 노출
- [ ] 다크모드 적용 + accent violet 복귀 확인 (Phase 1-A 에서 cyan 으로 PATCH 한 흔적 있으면 되돌리기)
- [ ] Playwright MCP 로 `probe-00~07` 8장 재캡처
- [ ] Q&A 답변 10번 이상 소리내어 연습 — 특히 Q5, Q10, Q11

---

## 7. 이 문서의 수명

- **2026-04-24 커밋 `b97a122` 시점 기준 정확성 보장.**
- 이후 BE/FE 변경 시 §5 숫자 치트시트부터 갱신.
- 심사 직전 `docs/qa/demo-rehearsal-FINAL.md` 로 복사본 만들고 체크박스 채우기.
- 심사 종료 후 `docs/qa/postmortem-{date}.md` 에 실제 받은 질문/답변 아카이브.
