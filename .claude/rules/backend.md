---
description: Backend (FastAPI + LangGraph) 작업 규약
paths:
  - "backend/**"
  - "shared/**/*.py"
---

# Backend 규약

## 스택 고정값

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), asyncpg
- LangGraph 로 Router/Analyzer 오케스트레이션. LangChain Expression Language 는 단순 체인에만
- LLM: `anthropic` SDK 직접 사용. 기본 `claude-sonnet-4-6`, 고난도 분석 `claude-opus-4-7`
- 패키지 매니저: `uv`. `pip`/`poetry` 혼용 금지

## 디렉토리

```
backend/
├── app/
│   ├── api/                # FastAPI 라우터 (얇은 계층)
│   ├── core/               # 설정·로깅·예외
│   ├── services/           # 도메인 서비스 (순수 로직)
│   ├── agents/
│   │   ├── router.py       # Meta Router 노드
│   │   ├── analyzers/      # 자산군별 서브그래프
│   │   └── gates/          # 3단 품질 게이트
│   ├── db/                 # 모델·리포지토리
│   └── schemas/            # Pydantic 입출력
├── tests/
├── alembic/
└── pyproject.toml
```

## API 설계

- RESTful. 리소스 중심. 동사 엔드포인트 금지 (`/analyze`는 예외로 허용)
- 응답은 항상 Pydantic 모델. `dict` 직반환 금지
- OpenAPI export: `python -m app.export_openapi > openapi.json` (CI 에서 자동 갱신)
- 에러: `HTTPException` + 구조화 `code` 필드 (`{"code": "UPSTREAM_TIMEOUT", "detail": "..."}`)

## LangGraph 노드 규칙

- 노드는 순수함수로. 부수효과는 `tools/` 에 격리
- 상태 객체는 `TypedDict` + Pydantic 검증. 불변 업데이트 (`{**state, ...}`)
- Router 는 **결정 근거** (선택한 analyzer + 이유) 를 상태에 기록 → 디버깅·데모용
- 모든 LLM 호출에 프롬프트 캐시 활용 (system prompt 를 cache_control 블록으로)

## 3단 품질 게이트 (반드시 순서대로)

1. **Schema gate**: Pydantic 으로 LLM 출력 파싱. 실패 시 1회 재시도 + 수정 지시
2. **Domain gate**: 가격 > 0, 날짜 단조 증가, 자산군 일관성 등 sanity check
3. **Critique gate**: 별도 LLM 호출로 "근거 문장이 실제 데이터에 있는가" 검증

각 gate 통과 여부는 응답 메타에 `gates: {schema: "pass", ...}` 로 노출.

## DB

- 마이그레이션은 Alembic. 수동 SQL 금지
- 모든 쿼리는 비동기. `session.execute(select(...))` 패턴
- 가격 시계열은 하루 1회 배치 적재 + 실시간은 Redis 캐시 (`TTL 5s`)

## 테스트

- pytest + pytest-asyncio + httpx.AsyncClient
- LLM 테스트는 `respx` 로 Anthropic 응답 고정 + 골든 샘플
- 컨트랙트 테스트: `schemathesis run openapi.json`
