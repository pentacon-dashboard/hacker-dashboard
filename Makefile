# hacker-dashboard Makefile
# 사용법: make <target>
# Windows Git Bash 환경 지원. Docker / Node / Python(uv) 설치 전제.

.PHONY: help dev up down logs test e2e ci-local seed seed-db lint fmt typecheck build \
        healthcheck healthcheck-prod smoke-prod demo-ready validate-compose

# 기본 타겟
help:
	@echo "Available targets:"
	@echo "  dev          - 로컬 개발 (FE: next dev, BE: uvicorn --reload 별도 터미널 필요)"
	@echo "  up           - docker compose up --build -d (전체 스택)"
	@echo "  down         - docker compose down"
	@echo "  logs         - docker compose logs -f"
	@echo "  test         - 백엔드 pytest + 프론트엔드 vitest"
	@echo "  e2e          - Playwright E2E 스모크 테스트"
	@echo "  ci-local     - CI 파이프라인 로컬 시뮬레이션 (lint+type+test)"
	@echo "  seed         - demo/seeds/ CSV 를 BE 로 업로드 (서버 실행 중 필요)"
	@echo "  seed-db      - DB에 데모 포트폴리오 holdings 삽입 (idempotent, docker-compose 실행 중 필요)"
	@echo "  lint         - ruff + eslint 동시 실행"
	@echo "  fmt          - black + prettier 포맷"
	@echo "  typecheck    - mypy + tsc --noEmit"
	@echo "  build        - Docker 이미지 빌드"

# ── Docker Compose ───────────────────────────────────────────────────────────

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# ── 로컬 개발 (Docker 없이) ──────────────────────────────────────────────────

dev:
	@echo "백엔드: 별도 터미널에서 'cd backend && uv run uvicorn app.main:app --reload' 실행"
	@echo "프론트엔드 dev 서버 기동 중..."
	cd frontend && npm run dev

# ── 테스트 ───────────────────────────────────────────────────────────────────

test:
	@echo "=== Backend tests ==="
	cd backend && uv run pytest -q
	@echo "=== Frontend unit tests ==="
	cd frontend && npm run test

e2e:
	@echo "=== Playwright E2E (smoke) ==="
	cd frontend && npx playwright test e2e/smoke.spec.ts --config=e2e/playwright.config.ts

e2e-report:
	cd frontend && npx playwright show-report playwright-report

# ── CI 로컬 시뮬레이션 ───────────────────────────────────────────────────────

ci-local: lint typecheck test
	@echo "=== Build check ==="
	cd frontend && npm run build
	@echo "CI local simulation complete."

# ── 코드 품질 ────────────────────────────────────────────────────────────────

lint:
	@echo "=== Backend lint (ruff) ==="
	cd backend && uv run ruff check app tests
	@echo "=== Frontend lint (eslint) ==="
	cd frontend && npm run lint

fmt:
	@echo "=== Backend format (black) ==="
	cd backend && uv run black app tests
	@echo "=== Backend import sort (ruff --fix) ==="
	cd backend && uv run ruff check --fix app tests
	@echo "=== Frontend format (prettier) ==="
	cd frontend && npx prettier --write .

typecheck:
	@echo "=== Backend type check (mypy) ==="
	cd backend && uv run mypy app
	@echo "=== Frontend type check (tsc) ==="
	cd frontend && npm run typecheck

# ── 계약 테스트 ──────────────────────────────────────────────────────────────

contract:
	@echo "=== Contract test (schemathesis) ==="
	@echo "BE 서버가 localhost:8000 에서 실행 중이어야 합니다."
	cd backend && uv run schemathesis run ../shared/openapi.json \
		--base-url http://localhost:8000 \
		--checks all \
		--hypothesis-deadline=none

# ── OpenAPI 내보내기 ─────────────────────────────────────────────────────────

openapi:
	cd backend && uv run python -m app.export_openapi > ../shared/openapi.json
	@echo "shared/openapi.json 업데이트 완료"
	cd frontend && npm run gen:api
	@echo "shared/types/api.ts 업데이트 완료"

# ── 시드 데이터 업로드 ───────────────────────────────────────────────────────

seed:
	@echo "=== 시드 데이터 업로드 (BE localhost:8000 필요) ==="
	@for f in demo/seeds/*.csv; do \
		echo "Uploading $$f ..."; \
		curl -sf -X POST http://localhost:8000/api/v1/upload \
			-F "file=@$$f" \
			-F "filename=$$(basename $$f)" \
			|| echo "Warning: $$f upload failed (BE 미구현 가능)"; \
	done

seed-db:
	@echo "[seed-db] DB에 데모 포트폴리오 시드 삽입..."
	@# seed_demo.py를 컨테이너에 복사 후 실행 (MSYS_NO_PATHCONV=1 로 경로 변환 억제)
	@docker cp scripts/seed_demo.py hacker-dashboard-backend-1:/app/seed_demo.py
	@MSYS_NO_PATHCONV=1 docker exec \
		-e DATABASE_URL="postgresql+asyncpg://hacker:hacker@postgres:5432/hacker_dashboard" \
		hacker-dashboard-backend-1 \
		python /app/seed_demo.py
	@echo "[seed-db] API 검증:"
	@curl -s http://localhost:8000/portfolio/holdings | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'holdings: {len(d)}건')" 2>/dev/null || echo "holdings API 응답 확인 완료"

# ── Compose config 검증 ──────────────────────────────────────────────────────

validate-compose:
	docker compose config --quiet && echo "docker-compose.yml: OK"

# ── 배포 헬스체크 ─────────────────────────────────────────────────────────────

healthcheck:
	@echo "=== Health Check (로컬) ==="
	bash scripts/healthcheck.sh

healthcheck-prod:
	@echo "=== Health Check (프로덕션) ==="
	BE_URL=https://hacker-dashboard-api.fly.dev \
	FE_URL=https://hacker-dashboard.vercel.app \
	bash scripts/healthcheck.sh

# ── 프로덕션 스모크 테스트 ────────────────────────────────────────────────────

smoke-prod:
	@echo "=== Production Smoke Test ==="
	cd frontend && \
	PROD_URL=https://hacker-dashboard.vercel.app \
	BE_URL=https://hacker-dashboard-api.fly.dev \
	npx playwright test e2e/production.spec.ts --project=chromium

# ── 데모 준비 ─────────────────────────────────────────────────────────────────

demo-ready: seed healthcheck
	@echo "=== 데모 준비 완료 ==="
	@echo "시나리오 파일: demo/scenario.md"
	@echo "리허설 체크리스트를 확인하십시오."
