---
name: deploy
description: Deploy or verify hacker-dashboard production rollout using Vercel for frontend, Fly.io for backend, and Neon Postgres. Use for commit/push/deploy, rollback, env sync, migrations, production health checks, and release readiness.
---

# Deploy

Use this skill for production release work in `C:\Users\ehgus\hacker-dashboard`.

## Current Targets

- GitHub repo: `https://github.com/pentacon-dashboard/hacker-dashboard.git`
- Frontend: Vercel project `hacker-dashboard-fe`, linked from `frontend/.vercel/project.json`
- Backend: Fly.io app `hacker-dashboard-api`, configured by `backend/fly.toml`
- Backend URL: `https://hacker-dashboard-api.fly.dev`
- Production DB: Neon Postgres project `hacker-dashboard`, injected through Fly secret `DATABASE_URL`
- Frontend production URL: `https://hacker-dashboard.vercel.app`

## Release Flow

1. Verify local status and stage only intended files.
2. Run the relevant local checks before commit.
3. Commit with a Korean commit message.
4. Push `main` to `origin`.
5. Confirm GitHub Actions deploys backend when `backend/**` or `.github/workflows/fly-deploy.yml` changed.
6. Confirm Vercel deployment for `hacker-dashboard-fe`.
7. Check production health and demo routes.

## Required Checks

Run these before a production push when feasible:

```powershell
powershell -ExecutionPolicy Bypass -File .agents/skills/harness-run/scripts/check-demo-preflight.ps1
cd backend; uv run pytest -q
cd frontend; npm run typecheck
cd frontend; npm run lint
cd frontend; npm run test
cd frontend; npm run build
```

For skill-only or documentation-only releases, record any skipped full checks and why.

## Backend Deploy

Automatic deploy:

- `.github/workflows/fly-deploy.yml` deploys `hacker-dashboard-api` on `main` pushes that touch `backend/**` or the workflow file.
- The workflow verifies `https://hacker-dashboard-api.fly.dev/health`.

Manual deploy:

```bash
cd backend
fly deploy --remote-only --strategy rolling
```

`backend/fly.toml` runs `alembic upgrade head` as the Fly release command.

## Frontend Deploy

Automatic deploy:

- Vercel is linked to project `hacker-dashboard-fe`.
- Pushing `main` should create a production deployment through the GitHub integration.

Manual deploy:

```bash
cd frontend
vercel --prod
```

Required production env:

- `NEXT_PUBLIC_API_BASE=https://hacker-dashboard-api.fly.dev`
- `NEXT_PUBLIC_WS_BASE=wss://hacker-dashboard-api.fly.dev`

## Production Verification

Check:

```bash
curl -fsS https://hacker-dashboard-api.fly.dev/health
curl -fsSI https://hacker-dashboard.vercel.app
```

Then verify in browser-use or Playwright:

- `/` renders the customer book.
- `/clients/client-003` loads past skeleton and shows non-empty KPI/holdings UI.
- Console error count is zero.

## Safety

- Do not print secret values.
- Do not commit `.env*`, deployment tokens, screenshots, caches, or local reports.
- If Fly health is degraded because DB is unreachable, stop and fix `DATABASE_URL` or migration state before marking deployment healthy.
- If a linked client route is empty, classify it as missing ledger data unless the task explicitly tests empty-state behavior.
