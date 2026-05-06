---
name: demo-script
description: Use when preparing or updating the hacker-dashboard 8-minute competition demo script, rehearsal checklist, demo runtime gate, judge-facing presentation flow, or final demo-readiness notes.
---

# Demo Script

이 스킬은 `hacker-dashboard`의 공모전 심사용 8분 데모 흐름, 리허설 체크리스트, 런타임 게이트를 관리한다. 개발 작업 설명이 아니라 심사자가 보는 제품 가치, 안정성, 근거 기반 분석을 짧은 시간 안에 전달하는 데 집중한다.

## 사용 시점

- 8분 데모 스크립트나 발표 순서를 만들거나 수정할 때
- 심사 전 리허설 체크리스트를 점검할 때
- 고객장부, CSV 업로드, Router, Analyzer, evidence gate, rebalance, Copilot, report 흐름을 발표용으로 정리할 때
- 데모 URL, seed data, DB health, client workspace 상태를 final check할 때

## 데모 스토리

| 시간 | 섹션 | 핵심 메시지 |
| --- | --- | --- |
| 0:00-0:30 | 오프닝 | "서로 다른 투자 CSV와 고객 포트폴리오를 자동으로 정규화하고, 근거가 있는 PB/WM 대시보드로 바꿉니다." |
| 0:30-2:00 | CSV 업로드와 schema detection | 임의 broker CSV를 업로드하고, 컬럼 감지, mapping confidence, PB 확인 흐름을 보여준다. |
| 2:00-3:30 | Router decision evidence | Router가 자산군과 Analyzer를 고르는 이유, 입력 컬럼/심볼/시장 근거, gate 상태를 보여준다. |
| 3:30-5:00 | 고객장부와 client workspace | `/` 고객장부에서 KPI와 고객 목록을 보여주고, `/clients/<client_id>`에서 보유자산과 allocation을 확인한다. |
| 5:00-6:15 | Deterministic metrics and rebalance | 수익률, 변동성, MDD, HHI, 집중도, drift, rebalance action이 deterministic code로 계산됨을 설명한다. |
| 6:15-7:15 | Evidence gates and degraded states | LLM은 계산된 metric을 설명만 하며, 근거 부족 시 degraded 또는 `insufficient_data`로 내려가는 모습을 보여준다. |
| 7:15-8:00 | Architecture and close | FastAPI, Next.js, Router/Analyzer/Gates, OpenAPI shared contract, 테스트/데모 readiness를 요약한다. |

## Runtime Gate

심사용 데모를 ready로 표시하기 전에 확인한다.

- Backend `/health`가 응답하고 `services.db=ok`여야 한다.
- `/` 고객장부가 skeleton 이후 KPI, 고객 목록, 선택 고객 summary를 표시해야 한다.
- 발표에서 여는 `/clients/<client_id>` route는 holdings가 1개 이상이어야 한다.
- 고객장부/portfolio demo mock은 UI shell rehearsal에만 사용할 수 있다.
- frontend-only MSW 상태를 backend, production, 또는 demo readiness evidence로 말하지 않는다.
- Copilot, news, market, quote, watchlist, upload, settings, realtime checks는 browser mock이 아니라 backend route나 명시적 test fixture 기준으로 확인한다.
- 발표 전 `.agents/skills/harness-run/scripts/check-demo-preflight.ps1`를 실행하고 결과를 기록한다.

## Rehearsal Checklist

- [ ] 발표에 사용할 seed CSV와 client id를 고정했다.
- [ ] backend, database, frontend가 같은 데이터셋을 보고 있다.
- [ ] `/health`의 `services.db=ok`를 확인했다.
- [ ] `/` 고객장부가 KPI와 고객 목록을 로드한다.
- [ ] 발표용 `/clients/<client_id>`가 non-empty holdings UI를 표시한다.
- [ ] CSV 업로드 실패/검증 실패/degraded 상태를 짧게 보여줄 수 있다.
- [ ] Router reason, gate badge, confidence, evidence panel을 한 번 이상 보여준다.
- [ ] deterministic metric과 LLM narrative의 역할 분리를 말할 수 있다.
- [ ] 네트워크/API 장애에 대비한 녹화본 또는 fallback 경로가 있다.
- [ ] 1920x1080 발표 환경에서 텍스트와 주요 차트가 겹치지 않는다.
- [ ] 8분 안에 끝나는 리허설을 1회 이상 완료했다.

## 말하면 안 되는 것

- 보장 수익, 확정 수익, 특정 가격 방향의 단정
- 입력이나 fixture에 없는 고객 성향, 투자 목적, 자문 적합성
- LLM이 metric을 직접 계산한다는 표현
- frontend-only mock 화면을 live backend 검증 결과처럼 설명
- API key, DB URL, secret, 계정 정보

## 발표 멘트 기준

좋은 표현:

- "이 수치는 업로드된 보유자산과 deterministic metric service에서 계산된 값입니다."
- "LLM은 계산 결과를 설명하지만, 근거가 없으면 정상 결과로 렌더링하지 않습니다."
- "Router는 심볼, 시장, 컬럼 근거를 우선 사용하고 불확실하면 confidence를 낮춥니다."

피해야 할 표현:

- "이 종목은 반드시 오릅니다."
- "LLM이 알아서 수익률을 계산했습니다."
- "mock 데이터이지만 production readiness로 봐도 됩니다."

## 관련 파일

- 발표문: `demo/script-ko.md`
- 제출 문서: `submission/`
- 심사용 Skill 요약: `Skills.md`
- 확장 Skill 명세: `.codex/competition/Skills.md`
- 데모 run evidence: `docs/harness-runs/`
- 데모 preflight: `.agents/skills/harness-run/scripts/check-demo-preflight.ps1`

## 완료 보고

데모 스크립트 작업을 마칠 때는 다음을 보고한다.

- 수정한 발표/문서 파일
- 실행한 preflight 또는 browser smoke
- 확인한 URL과 client id
- 실행하지 못한 체크와 이유
- 남은 demo risk
