---
description: 전 역할 공통 규약 (항상 주입)
---

# 공통 규약

## 커밋 & PR

- **Conventional Commits**: `feat(fe): ...`, `fix(be): ...`, `refactor(agent): ...`, `chore: ...`
- 한 커밋 = 한 논리 단위. 여러 파일이라도 하나의 의도로 묶이면 OK
- PR 본문 템플릿: **요약 → 변경 이유 → 스크린샷/로그 → 테스트 계획 → 영향 범위**

## 브랜치 네이밍

| 역할 | prefix |
|---|---|
| frontend-engineer | `feat/fe-*` |
| backend-engineer | `feat/be-*` |
| analyzer-designer | `feat/agent-*` |
| integration-qa | `feat/qa-*`, `chore/ci-*` |

## FE ↔ BE 계약

- `backend/openapi.json` 이 단일 진실. BE 변경 시 즉시 export
- FE 는 `shared/types/` 에 `openapi-typescript` 로 생성된 타입만 사용. 수동 재선언 금지
- Breaking change 는 반드시 PR 라벨 `breaking:api` + 상대 역할 리뷰

## 네이밍

- 코드 식별자·파일명·디렉토리명: **영어, kebab-case (파일) / camelCase (TS) / snake_case (Python)**
- 주석·커밋의 WHY·PR 본문: 한국어 허용. WHAT 은 코드에 맡긴다

## 에러 처리

- 시스템 경계(외부 API, 사용자 입력, LLM 응답)에서만 방어적 검증
- 내부 함수끼리는 타입 신뢰. `try/except` 남발 금지
- 에러는 삼키지 말고 상위로 전파 또는 구조화된 로그로 남기기

## 테스트 원칙

- 도메인 로직: 단위 테스트 필수
- API 계약: contract test (schemathesis 또는 openapi validator)
- LLM 체인: 골든 샘플 10종 이상 + 회귀 diff
- UI: Playwright 로 핵심 시나리오 3개 (업로드 → 분석 → 렌더)

## 금지

- `any` / `# type: ignore` 무단 사용 (PR 에서 사유 명시 필요)
- LLM 결과를 3단 게이트 없이 UI 직결
- `.env*` 커밋, 실거래 키 커밋
- 포매터·린터 수동 우회
