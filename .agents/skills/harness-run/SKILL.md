---
name: harness-run
description: Run the hacker-dashboard development harness for feature requests, QA sweeps, or skill self-checks using a Codex-native plan, work, review, compound, and repeat loop. Use when the user invokes /harness-run or $harness-run, asks for automated iterative implementation, wants sprint worktrees, wants review-driven compounding of project instructions, or wants a documented harness run summary.
---

# Skill - harness-run

Use this skill to run a bounded Codex development harness for `C:\Users\ehgus\hacker-dashboard`.

The loop is:

```text
plan -> work -> review -> compound -> repeat
```

`compound` is not context compression. It is harness learning: promote review lessons into repo-local documentation, skill references, instructions, or guarded follow-up candidates so later runs improve.

## Mode Boundary

- In Plan Mode, only do `plan`. Do not edit files, create branches, create worktrees, generate images, or run code-changing commands.
- In Default Mode, run `work`, `review`, `compound`, and `repeat`.
- If a user asks to execute while still in Plan Mode, return a decision-complete plan and stop.

## Quick Start

Parse:

```text
/harness-run <feature_request> [--threshold 8.0] [--max-iter 5] [--sprints-only sprint-01,sprint-02]
```

Defaults:

- `threshold`: `8.0`
- `max_iter`: `5`
- first validation target for this skill: `스킬 자체 검증`

Create a stable run id:

```text
run_id = <YYYYMMDD-HHMMSS>-<ascii-slug-or-hash>
```

Use these paths:

- Run artifacts: `.harness/runs/<run_id>/`
- Sprint worktree: `.harness/worktrees/<run_id>/<sprint_id>/`
- Tracked final summary: `docs/harness-runs/<YYYYMMDD-HHMMSS>/`

Use these branches:

- Run base branch: `dorec/harness-<run_id>`
- Sprint branch: `dorec/harness-<run_id>-<sprint_id>`

## Required References

Read only the references needed for the current phase:

- `references/loop-contract.md`: phase responsibilities, stop rules, scoring, and compounding policy.
- `references/artifacts.md`: required artifact filenames and schemas.
- `references/worktrees-and-agents.md`: branch/worktree/session orchestration.
- `references/image-policy.md`: always-allowed image generation capability, budget, and asset manifest.
- `references/mock-boundary.md`: required guardrails when work touches demo data, MSW, Copilot, Docker env, or live API wiring.
- `references/demo-preflight.md`: required DB, customer-ledger, and browser checks when work touches customer books, upload/import, portfolio APIs, Docker/Postgres, demo seeds, or browser smoke.

For investment-domain changes, also use `$investment-dashboard`.

## Phase Summary

### 1. Plan

Run from the main checkout and keep it read-only.

Produce:

- `<run_artifacts>/plan.md`
- `<run_artifacts>/sprints/<sprint_id>/contract.md`

Each sprint contract must include:

- objective and non-goals
- allowed write scope
- acceptance criteria
- verification commands
- demo runtime preflight requirements, when the sprint touches customer books, upload/import, portfolio APIs, Docker/Postgres, demo seeds, or browser smoke
- risk notes
- expected artifacts
- max iteration and score threshold

### 2. Work

Run in the sprint worktree only.

For each iteration:

- implement only the current sprint contract
- record changed files, commands, results, blockers, and image requests
- run `.agents/skills/harness-run/scripts/check-demo-preflight.ps1` before browser smoke when customer-book or portfolio demo data is in scope
- write `<run_artifacts>/work-<sprint_id>-<iter>.md`

Image generation is always allowed as a worker capability. It must follow `references/image-policy.md`.

### 3. Review

Review independently from implementation.

Write:

- `<run_artifacts>/review-<sprint_id>-<iter>.json`
- `<run_artifacts>/review-<sprint_id>-<iter>.md`

Lead with blocking findings. Score only against the contract and evidence.
Block demo readiness if required customer-ledger preflight was skipped, if a linked client detail route is empty, or if a skeleton screenshot is treated as a pass.

### 4. Compound

Convert review lessons into harness learning.

Immediate document promotion is allowed only for:

- `.agents/skills/harness-run/SKILL.md`
- `.agents/skills/harness-run/references/*`
- `AGENTS.md`
- `.codex/instructions/*`
- `docs/harness-runs/*`

Do not automatically add product code, tests, lint rules, scripts, CI, or API contracts during compound. Record them as promotion candidates instead.

Write:

- `<run_artifacts>/compound-<sprint_id>-<iter>.md`

### 5. Repeat

After review and compound:

- pass if `normalized_score >= threshold` and there are no blocking findings
- continue if below threshold and `iter < max_iter`
- set `suggest_direction_pivot=true` if three iterations improve by `<= 0.5`
- mark degraded and write handoff if `max_iter` is reached

When a sprint passes, merge or fast-forward the sprint branch into the run base branch so compound document promotions carry into the next sprint.

## Finalization

Write:

- `<run_artifacts>/summary.md`
- `docs/harness-runs/<timestamp>/summary.md`
- final review JSON files
- final compound summaries
- final image manifest, if images were generated

Report changed files, checks run, checks not run, branch/worktree status, and residual risks.
For demo/customer-book work, include the preflight result and the exact client routes verified in the browser.
