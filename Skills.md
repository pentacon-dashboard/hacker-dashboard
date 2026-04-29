# Skills.md - PB/WM 투자 분석 및 리포팅 규칙 엔트리

이 문서는 `hacker-dashboard` 제출물의 대회용 Skills 진입점입니다.

## 목적

Codex가 PB/WM 조직용 투자 데이터 통합 분석 워크스페이스를 일관되게 만들고 검증할 수 있도록 다음 규칙을 정의합니다.

- 임의의 투자 CSV, 브로커 계좌 파일, 포트폴리오 데이터를 분류한다.
- 매번 달라지는 스키마를 표준 필드로 정규화하되 원본 근거와 매핑 신뢰도를 보존한다.
- 투자 지표, 리스크, 리밸런싱 수량은 deterministic code로 먼저 계산한다.
- LLM은 계산된 수치와 검증된 근거를 고객 설명용 문장으로만 재구성한다.
- 데이터 형태와 PB 업무 흐름에 맞춰 차트, evidence panel, gate badge, 고객 브리핑 리포트를 선택한다.
- 모든 인사이트와 리포트 섹션은 rows, metrics, API data, fixture 중 하나 이상의 근거를 가진다.
- 검증 게이트를 통과하지 못한 금융 주장은 정상 인사이트나 고객용 리포트 문장으로 표시하지 않는다.

## Canonical Files

- 프로젝트 지시문: `AGENTS.md`
- 프로젝트 Codex 설정: `.codex/config.toml`
- 확장 제출 명세: `.codex/competition/Skills.md`
- Codex Skill 구현: `.agents/skills/investment-dashboard/SKILL.md`
- 상세 분석 규칙: `.agents/skills/investment-dashboard/references/`

## Required Analysis Flow

1. 업로드 파일의 컬럼, 첫 행 샘플, 심볼 패턴, 시장/통화 단서를 읽어 broker CSV adapter를 선택한다.
2. `symbol`, `date`, `price`, `quantity`, `avg_cost`, `market`, `currency`, `account`, `client_id` 같은 alias를 탐지한다.
3. 확신도 95% 이상인 필드만 자동 매핑하고, 나머지는 PB 확인이 필요한 `needs_review` 상태로 남긴다.
4. LLM 사용 전에 데이터를 `portfolio`, `stock`, `crypto`, `fx`, `macro`, `mixed` 중 하나로 deterministic routing 한다.
5. return, volatility, MDD, HHI, PnL, allocation, drift, rebalance quantity를 코드로 계산한다.
6. schema gate, domain gate, evidence gate, critique gate를 통과한 결과만 정상 UI 인사이트와 리포트 문장으로 표시한다.
7. 고객 브리핑 리포트는 `[요약] -> [성과 기여도] -> [리스크 분석] -> [리밸런싱 제안] -> [PB 의견]` 순서를 따른다.
8. 입력 데이터, 근거, 계산 결과, LLM 출력 중 하나라도 부족하면 degraded 또는 `insufficient_data` 상태로 안전하게 표시한다.

## Forbidden Output

- 보장 수익률 또는 확정적 시장 방향.
- deterministic service output과 evidence 없는 개인화 매수/매도 지시.
- 입력에 없는 ticker, price, date, allocation, causal claim.
- 코드가 먼저 계산하지 않은 LLM 생성 지표.
- 고객 성향, 계좌, 리포트 수신자 정보를 추측해서 채우는 행위.

이 저장소에서 반복적인 분석/대시보드/리포팅 작업을 할 때는 `$investment-dashboard`를 사용한다.
