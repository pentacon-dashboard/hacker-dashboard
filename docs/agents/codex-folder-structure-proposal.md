# Codex 공식 구조 기반 폴더 구조 최종안

작성일: 2026-04-29

## 1. 목적

`hacker-dashboard`를 PB/WM 투자 데이터 통합 분석 및 고객 브리핑 리포팅 솔루션으로 운영하기 위한 Codex 최종 폴더 구조를 정의한다.

핵심 원칙은 다음과 같다.

- `AGENTS.md`는 프로젝트 작업 지침이다.
- `.codex/`는 Codex 실행 설정, agent, rules, 대회 제출 명세를 관리한다.
- `.agents/skills/`는 실제 Codex Skill을 관리한다.
- `Skills.md`는 심사용 루트 요약 문서다.
- `.claude/`는 legacy context로만 유지한다.

## 2. 최종 폴더 구조

```text
hacker-dashboard/
├─ AGENTS.md
├─ Skills.md
├─ .codex/
│  ├─ config.toml
│  ├─ README.md
│  ├─ project.md
│  ├─ agents/
│  │  ├─ analyzer-designer.toml
│  │  ├─ backend-engineer.toml
│  │  ├─ frontend-engineer.toml
│  │  └─ integration-qa.toml
│  ├─ rules/
│  │  └─ hacker-dashboard.rules
│  ├─ instructions/
│  ├─ prompts/
│  └─ competition/
│     └─ Skills.md
├─ .agents/
│  └─ skills/
│     └─ investment-dashboard/
│        ├─ SKILL.md
│        └─ references/
│           ├─ analysis-rules.md
│           ├─ broker-csv-adapter-rules.md
│           ├─ client-normalization-rules.md
│           ├─ quant-metric-rules.md
│           ├─ evidence-compliance-rules.md
│           ├─ report-rules.md
│           ├─ visualization-rules.md
│           ├─ insight-rules.md
│           └─ validation-rules.md
├─ backend/
├─ frontend/
├─ shared/
├─ demo/
├─ docs/
├─ submission/
└─ .claude/
```

## 3. 파일별 의미

| 경로 | 의미 |
|---|---|
| `AGENTS.md` | Codex가 작업 전 읽는 최상위 프로젝트 지시문. 개발 규칙, 검증 명령, 금융 분석 금지 규칙, PB/WM fail-safe 원칙을 담는다. |
| `Skills.md` | 대회 심사용 루트 요약 문서. PB/WM 투자 분석, Meta Router, Quant Engine, Gate, 리포트 흐름을 짧게 설명한다. |
| `.codex/config.toml` | 프로젝트별 Codex 실행 설정. sandbox, approval, web search, agent thread, env 제외 목록을 관리한다. |
| `.codex/project.md` | 프로젝트 압축 컨텍스트. 제품 요약, 아키텍처, 피벗 방향을 짧게 담는다. |
| `.codex/agents/*.toml` | 역할별 subagent 정의. 분석 설계, backend, frontend, QA를 분리한다. |
| `.codex/rules/*.rules` | shell 명령 승인 정책. 위험 명령 차단과 검증 명령 허용 기준을 둔다. |
| `.codex/instructions/` | 작업 영역별 보조 지침. frontend, backend, analyzer, QA 규칙을 담는다. |
| `.codex/prompts/` | planner, generator, evaluator 등 재사용 프롬프트를 둔다. |
| `.codex/competition/Skills.md` | 대회 제출용 상세 명세. 루트 `Skills.md`보다 자세한 분석/리포팅 규칙을 담는다. |
| `.agents/skills/investment-dashboard/SKILL.md` | Codex가 실제로 사용하는 투자 분석 Skill 진입점이다. |
| `.agents/skills/investment-dashboard/references/` | Skill 세부 규칙. 분석, 정규화, 수치 계산, 근거 검증, 리포트 규칙을 나눈다. |
| `.claude/` | 기존 Claude workflow의 legacy context. 신규 규칙은 추가하지 않는다. |

## 4. PB/WM Skill 흐름

```text
CSV 업로드
→ Broker CSV Adapter
→ Client Normalization
→ Meta Router
→ Quant Metric Engine
→ Schema/Domain/Evidence/Critique Gates
→ Dashboard + Client Briefing Report
```

## 5. reference 파일 역할

| 파일 | 역할 |
|---|---|
| `analysis-rules.md` | Router, asset-class 분류, 기본 분석 규칙 |
| `broker-csv-adapter-rules.md` | 증권사/거래소 CSV 컬럼 매핑과 confidence 규칙 |
| `client-normalization-rules.md` | 고객, 계좌, 통화, 시장, 보유종목 통합 규칙 |
| `quant-metric-rules.md` | 수익률, MDD, 변동성, HHI, PnL, drift 계산 규칙 |
| `evidence-compliance-rules.md` | 모든 수치와 문장을 근거에 연결하는 규칙 |
| `report-rules.md` | 고객 브리핑 리포트 구조와 PB 의견 작성 규칙 |
| `visualization-rules.md` | KPI, chart, table, evidence panel, gate badge UI 규칙 |
| `insight-rules.md` | LLM narrative, confidence, 금지 문장 규칙 |
| `validation-rules.md` | schema, domain, critique gate와 테스트 선택 규칙 |

## 6. 최종 기획 문장

본 프로젝트는 Codex 공식 구조에 맞춰 `AGENTS.md`를 프로젝트 작업 지침, `.codex/config.toml`을 실행 설정, `.codex/agents`를 역할 기반 서브에이전트, `.codex/rules`를 명령 승인 정책, `.agents/skills/investment-dashboard`를 투자 분석 도메인 Skill로 분리한다. `Skills.md`는 심사용 요약 문서로 유지하고, `.codex/competition/Skills.md`는 PB/WM 투자 데이터 통합 분석과 고객 브리핑 리포트 생성 규칙을 담는 상세 명세로 사용한다.
