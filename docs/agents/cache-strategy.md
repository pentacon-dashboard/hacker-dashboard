# Prompt Cache Strategy

## 배경

Anthropic 의 **prompt caching** 은 동일한 system prompt prefix 에 대해
토큰당 비용을 최대 10배 절감한다. `/analyze` 플로우는 Router 1회 + Analyzer
1~2회 + Schema/Critique Gate 1~2회로 호출이 많아 캐시 히트율이 그대로 비용·
지연으로 연결된다.

## 현재 구조

`backend/app/agents/llm.py::_with_cache_control` 이 system prompt 를 블록
리스트로 래핑해 Anthropic 에 전달한다. 단일 파일 통째로 감싸면 파일이 바뀔
때마다 캐시가 무효화된다. Week-4 에서 다음 규약을 도입했다:

```
# Role: ... (고정 지침 — 역할 설명, 출력 스키마, 공통 규칙)

<!-- DYNAMIC -->

## 호출 시점에 달라질 수 있는 변수
- 날짜 문맥
- 실험 플래그
```

- 마커 `<!-- DYNAMIC -->` 이전은 `cache_control: {"type": "ephemeral"}` 가
  붙은 단일 블록 → Anthropic 이 장기 캐싱
- 이후는 별도 블록, 캐시 대상 아님
- 마커가 없으면 전체 파일을 단일 cached 블록으로 래핑 (기존 동작)

## 기대 히트율

골든 샘플 회귀(163 테스트) 기준 다음과 같은 caching 이 기대된다:

| 호출 경로 | system prompt | 평균 static/dynamic split | 기대 히트율 |
|---|---|---|---|
| Router LLM fallback | `router_system.md` | 100% static | 95%+ (prompt 변경 없을 때) |
| Stock Analyzer | `stock_system.md` | 100% static | 95%+ |
| Crypto Analyzer | `crypto_system.md` | 100% static | 95%+ |
| FX Analyzer | `fx_system.md` | 100% static | 95%+ |
| Macro Analyzer | `macro_system.md` | 100% static | 95%+ |
| Portfolio Analyzer | `portfolio_system.md` | 100% static | 95%+ |
| Mixed Analyzer | `mixed_system.md` | 100% static | 95%+ |
| Schema retry | 교정 지시 포함 동적 | static 80% | 60%+ (재시도 1회) |
| Critique Gate | `critique_system.md` | 100% static | 95%+ |

prompt 파일이 일단 배포되면 바뀌지 않으므로 cold start (첫 요청) 이후 모든
호출이 캐시 히트 대상이다. 첫 요청은 write (캐시 생성) 비용만 추가된다.

## 측정 지점

- `llm.py::_last_cache_metrics` — 현재 요청에서 누적된 토큰/캐시 통계
  - `cache_read_input_tokens` / `cache_creation_input_tokens` / `input_tokens` / `output_tokens`
- `/analyze` 응답의 `meta.cache` 필드에 그대로 노출
  ```json
  {
    "meta": {
      "cache": {
        "read_tokens": 3850,
        "creation_tokens": 0,
        "input_tokens": 120,
        "output_tokens": 420
      }
    }
  }
  ```
- `core/logging.py::log_analyze_event` 이 구조화 로그에 포함해 Grafana/Loki
  등으로 보낼 수 있다. 필드:
  - `cache_tokens.read_tokens` : 캐시 히트 토큰 (높을수록 저렴)
  - `cache_tokens.creation_tokens` : 최초 write (재시도 시 0)
  - `x_cache: HIT|MISS` : API 레벨 캐시 히트(결과 캐시) 여부. 별도 차원

히트율 지표: `read_tokens / (read_tokens + creation_tokens + input_tokens)`.
골든 회귀에서 평균 90% 이상이면 목표 달성으로 본다.

## 실전 팁

1. prompt 파일 수정 시 **파일 끝에 공백 추가도 캐시 miss** 를 유발한다.
   포매터 적용 후 한 번에 커밋 → 캐시가 장기간 유효하게.
2. 재시도 경로 (schema gate) 는 교정 메시지가 dynamic 블록에 들어가므로
   `<!-- DYNAMIC -->` 로 분리하면 static 파트 캐시가 유지된다. (현재 schema
   gate 는 재시도 프롬프트를 user content 에 넣으므로 system 캐시는 그대로.)
3. model 이 바뀌면 캐시도 분리된다. sonnet/opus 승급은 행 수 300 기준으로만
   일어나므로 자주 바뀌지 않는다.
4. Router heuristic 이 결정한 경우 LLM 호출 자체가 일어나지 않아 캐시조차
   타지 않는다 — **가장 싸고 빠른 경로**. Week-4 확장으로 18종 기존 샘플 +
   4종 CSV 샘플 22종 중 **22종 모두 heuristic 결정** (LLM 호출 0).

## 운영 체크리스트

- [ ] prompt 파일 수정 PR 시 본 문서의 기대 히트율 표와 대조
- [ ] `meta.cache.read_tokens == 0` 이 연속 5회 이상 나오면 alert (캐시 파괴 가능성)
- [ ] 신규 analyzer 추가 시 `prompts/*.md` 에 `<!-- DYNAMIC -->` 마커 고려
- [ ] `_last_cache_metrics` 는 request scope — 동시 요청 격리는 FastAPI 의
      context 로 커버 (background task 로 lift 하지 말 것)
