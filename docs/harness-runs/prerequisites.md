# `/harness-run` 실전 투입 체크리스트

이 문서는 `/harness-run` 스킬을 **처음 실행하기 전** 확인·설치해야 할 항목을 정리한다. 한 번만 하면 되는 작업이 대부분이다.

## 자동 완료된 항목

다음은 이 레포 설정 시 자동으로 처리되었다. 재확인만 필요:

- [x] **Git 초기 커밋** — `master` + `main` 브랜치에 `db56f5a chore: initial commit` 존재. 스프린트 브랜치가 여기서 분기된다
- [x] **`.gitignore`** — `.venv/`, `.env*`, `.claude/harness/`, `node_modules/` 모두 제외. `backend/.env` 시크릿 보호됨
- [x] **Docker Compose healthcheck 수정** — BE 컨테이너가 `wget` 미설치로 unhealthy 표시되던 문제. `curl -fsS`로 변경됨
- [x] **ESLint 9 flat config** — `frontend/eslint.config.mjs` 최소 설정. `make lint`가 실행 가능해짐 (2 warnings, 0 errors 베이스라인)
- [x] **`npm run lint` 스크립트** — `frontend/package.json`에 누락되어 있던 것 추가
- [x] **FE 베이스라인 통과** — typecheck ✅ / lint ✅ (warnings만) / unit tests 77/77 ✅

## 사용자가 수동으로 해야 할 것

### 1. `uv` 설치 (필수)

`.claude/rules/backend.md`가 `uv`를 패키지 매니저로 고정. Makefile의 `typecheck / lint / test / contract` 모두 `uv run`을 호출한다.

```bash
# Windows (PowerShell 관리자 권한)
winget install astral-sh.uv

# 또는 pip로
pip install --user uv

# 검증
uv --version
```

설치 후:
```bash
cd backend && uv sync   # .venv를 uv가 관리하는 상태로 동기화
```

### 2. Playwright 크로미움 설치 (선택, E2E 점수 필요 시)

기본 설정에서 E2E는 `iter == max_iter`일 때만 돌아가는 binary-gate다. max_iter를 짧게(2~3) 쓰면 실행 기회가 적지만, 통과시키려면 필요.

```bash
cd frontend && npx playwright install chromium
```

### 3. `ANTHROPIC_API_KEY` 확인 (LLM 호출 필요 시)

골든 샘플 회귀 테스트(`backend/tests/golden/`)는 실제 Claude 호출을 녹화한 fixture를 검증할 뿐 실시간 호출 아님. 하지만 Generator가 analyzer 프롬프트를 만지면 BE 서버가 실제 LLM을 호출할 수 있다.

```bash
# backend/.env 에 이미 설정되어 있는지 확인
grep ANTHROPIC_API_KEY backend/.env
# 없거나 placeholder면 실 키 주입 (커밋 금지)
```

### 4. BE 스택 기동 확인

`docker compose ps`로 4개 서비스 모두 healthy 상태가 이상적.

```bash
cd C:/Users/ehgus/hacker-dashboard
docker compose up -d          # 이미 up이면 무해
curl -f http://localhost:8000/health
# {"status":"ok"} 가 나와야 함
```

healthcheck 수정 후 기존 컨테이너는 다시 빌드해야 반영됨:
```bash
docker compose up -d --build backend
```

## 첫 실행 추천 레시피

### 레시피 A — 가장 가벼운 FE-only 실전 (비용 ~$3, 시간 ~20분)

```
/harness-run "헤더 우측에 다크모드 토글 버튼을 추가한다. 선택은 localStorage에 저장된다" --threshold 7 --max-iter 2
```

- BE 변경 없음 → `contract` 보류(자동으로 8점 척도 환산)
- max_iter=2로 비용·시간 상한
- threshold 7 = unit + typecheck + lint + golden 통과 정도

### 레시피 B — BE 포함 소규모 (비용 ~$8, 시간 ~40분)

```
/harness-run "포트폴리오에 총자산 변화율(1일/7일/30일)을 계산해 홈 상단에 표시한다" --threshold 7 --max-iter 3
```

- BE 엔드포인트 1개 + FE 카드 1개 → 스프린트 2~3개
- `contract` 포함 (schemathesis가 openapi.json 검증)

### 레시피 C — 금지 (첫 실행에서는)

```
/harness-run "<여러 analyzer를 동시에 수정하는 요청>"
```

3단 게이트·프롬프트·골든 샘플이 얽혀 있어 실패 확률 높고 비용 폭증.

## 첫 실행 후 체크 리스트

루프가 끝나면 반드시 육안 검토:

1. `docs/harness-runs/<timestamp>/summary.md` — 스프린트별 status
2. `git log --oneline feat/qa-harness-<run-id>-*` — 커밋 이력이 Conventional Commits인지
3. `git diff main feat/qa-harness-<run-id>-sprint-01` — 변경 범위가 contract의 글롭 안에 있는지
4. `.claude/harness/<run-id>/eval-*.json`의 `failures[].specific` — Evaluator 피드백 품질
5. 의심되는 스프린트는 직접 브랜치 체크아웃해서 `make ci-local` 재실행

## 알려진 제약

| 제약 | 영향 | 완화 |
|---|---|---|
| Playwright Windows Git Bash 플레이키 | E2E 간헐 실패 | Evaluator가 binary-gate로 격리 |
| BE 미기동 시 contract 보류 | 점수 척도 10→8 | Evaluator가 자동으로 비례 환산 |
| LLM 비용 예측 어려움 | $10 초과 가능 | `--max-iter 2` + `--sprints-only` 조합으로 상한 |
| `.claude/harness/`는 git 제외 | 하네스 실행 이력 사라질 수 있음 | 중요 run은 종료 후 사용자가 별도 아카이브 |
| Direction-pivot이 항상 성공 보장 X | max_iter 도달 시 degraded | `handoff-<sprint>.md` 읽고 사람이 인계 |

## 문제 발생 시 롤백

하네스가 뭘 망쳤다 싶으면:

```bash
# 하네스가 만든 브랜치 모두 제거 (main/master는 안전)
git branch --list 'feat/qa-harness-*' | xargs -r -n1 git branch -D

# 워크스페이스 정리 (.gitignore에 있으므로 git에는 영향 없음)
rm -rf .claude/harness/

# 커밋되지 않은 파일 변경 되돌리기 (신중히)
git status
git restore .    # 안 돌리고 싶은 건 빼고 개별 파일로
```
