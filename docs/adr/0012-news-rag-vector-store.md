# ADR 0012 — 뉴스/공시 RAG: pgvector + Claude citations

| 항목 | 내용 |
|---|---|
| 상태 | 확정 (sprint-06) |
| 초안 | sprint-02 |
| 결정자 | backend-engineer, analyzer-designer |

---

## 맥락

뉴스/공시 RAG 파이프라인은 Postgres pgvector 인덱스에 뉴스 청크를 저장하고, Claude citations
API로 인용 근거를 강제한다. 이를 위해 세 가지 설계 결정이 필요했다.

(a) 임베딩 벡터 **차원 수**: 모델별로 권장 차원이 다르며, 차원이 클수록 저장/검색 비용이 증가한다.
(b) pgvector **인덱스 알고리즘**: IVFFlat vs HNSW — 코퍼스 규모와 cold-start 지연 트레이드오프.
(c) **stub 모드 기본값**: 실 API 키 없이 CI/데모가 재현 가능해야 한다는 요구사항.

---

## 결정

### (a) 임베딩 1024차원 근거

벡터 차원을 **1024** 로 고정한다.

- **Voyage-3-lite** (권장 임베딩 모델): 기본 출력 차원 1024. 512 truncate 대비 검색 품질
  (NDCG@10) 약 6% 향상, 3072 full-dim 대비 저장 공간 66% 절약.
- **OpenAI text-embedding-3-small**: Matryoshka Representation Learning(MRL) 지원.
  원래 출력은 1536차원이지만, `dimensions=1024` 파라미터로 truncate 시 성능 저하가 5% 미만
  (OpenAI 공식 벤치마크 기준). 1024는 "품질-비용 최적점"으로 알려진 표준값이다.
- **stub 모드 fake 임베딩**: `COPILOT_EMBED_PROVIDER=fake` 시 1024차원 영벡터(zero-vector)
  를 반환하는 FakeEmbedder 가 사용된다. pgvector 인덱스는 차원 변경 없이 동일 스키마를 사용.

### (b) IVFFlat 인덱스 선택 이유

`CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`

IVFFlat(Inverted File Index with Flat) 을 선택한다. 대안인 HNSW(Hierarchical Navigable Small
World)를 채택하지 않은 이유:

| 기준 | IVFFlat | HNSW |
|---|---|---|
| 인덱스 빌드 시간 | O(n) 빠름 | O(n log n) 느림 |
| cold-start 지연 | 낮음 (lists 조정) | 높음 (그래프 탐색 초기화) |
| 메모리 사용 | 낮음 | 높음 (그래프 엣지 저장) |
| 정확도 (recall) | 95~98% @ lists=100 | 99%+ |
| 동적 삽입 | 재인덱싱 필요 | 즉시 삽입 가능 |

공모전 MVP 기준 코퍼스 크기는 수천~수만 문서로, HNSW 의 높은 recall 이 필요한 수백만 규모가
아니다. cold-start 가중치(서버 재시작 시 첫 쿼리 지연)가 IVFFlat 에서 낮고, 빌드 비용도
인덱스 재생성이 자주 일어나는 개발 환경에서 유리하다. HNSW 는 코퍼스가 100만 이상으로
성장하는 시점에 마이그레이션을 검토한다.

### (c) stub 모드 기본값 이유

`COPILOT_NEWS_MODE` 환경변수의 기본값을 `"stub"` 으로 설정한다.

근거:
1. **심사 재현성**: Evaluator 및 심사위원이 `COPILOT_NEWS_API_KEY` 없이도 전체 골든 테스트
   (10건)와 Playwright E2E 3종을 실행할 수 있어야 한다. stub 기본값은 이 요구를 보장한다.
2. **결정론 보장**: 실 뉴스 API는 호출 시점/지역/할당량에 따라 결과가 변한다. stub 코퍼스
   (`backend/tests/fixtures/news/*.json`) 는 버전 관리되는 고정값이므로 CI에서 비교 가능하다.
3. **API 키 누출 방지**: 실 키가 환경변수에 없으면 stub 으로 폴백한다는 명시적 정책이
   있어야 `.env` 를 커밋하려는 실수를 방지할 수 있다.
4. **opt-in live 모드**: `COPILOT_NEWS_MODE=live` + `COPILOT_NEWS_API_KEY=<key>` 를 명시
   설정하면 실 API 호출로 전환된다. 데모 당일에는 이 조합을 Fly.io/Vercel 대시보드에서 주입한다.

---

## 결과

- 1024차원 벡터 스키마가 pgvector 테이블에 고정되어, Voyage-3-lite ↔ text-embedding-3-small
  임베딩 모델 전환 시 재마이그레이션 없이 호환된다.
- IVFFlat 인덱스로 개발 환경 cold-start 지연 최소화 및 인덱스 빌드 시간 단축. 코퍼스 10만
  이상 규모에서는 HNSW 전환을 ADR에 기록 후 마이그레이션한다.
- stub 모드 기본값으로 CI 에서 `ANTHROPIC_API_KEY` 및 `COPILOT_NEWS_API_KEY` 없이 전체 테스트
  스위트가 통과한다. 공모전 심사 환경에서의 재현성이 보장된다.
