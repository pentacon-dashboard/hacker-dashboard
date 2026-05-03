# Harness Loop Contract

Use this reference to execute `/harness-run` after the skill has been triggered.

## Plan

Purpose: turn an ambiguous feature request into bounded, reviewable sprint contracts.

Plan must be read-only. Do not create branches, worktrees, commits, generated images, or product changes during Plan Mode.

`plan.md` must contain:

- original feature request
- parsed options: threshold, max_iter, sprints_only
- run_id and artifact paths
- sprint list in execution order
- risk register
- verification matrix
- demo runtime preflight matrix, when customer books, upload/import, portfolio APIs, Docker/Postgres, demo seeds, or browser smoke are in scope
- stop rules

Each `sprints/<sprint_id>/contract.md` must contain:

- objective
- non-goals
- allowed write scope
- required evidence
- acceptance criteria
- verification commands
- required demo preflight commands and browser routes, when applicable
- expected artifacts
- image generation allowance, if relevant
- compound opportunities to watch for

## Work

Purpose: implement exactly one sprint contract in a sprint worktree.

Rules:

- Work only in `.harness/worktrees/<run_id>/<sprint_id>/`.
- Keep changes inside the contract's allowed write scope.
- If a required change falls outside scope, stop and record a scope exception.
- Prefer existing project patterns and instructions.
- For frontend visual work, image generation is allowed without additional user confirmation unless CLI/API fallback is required.
- Write `work-<sprint_id>-<iter>.md` before handing off to review.

`work-*.md` must record:

- contract path
- branch and worktree path
- changed files
- commands run and outcomes
- demo preflight result and browser routes checked, when applicable
- tests not run and why
- image requests and generated assets
- blockers or scope exceptions
- implementation notes for reviewer

## Review

Purpose: evaluate the implementation independently against the contract.

Review stance:

- Lead with blocking bugs, regressions, missing tests, unsupported claims, and scope violations.
- Do not reward work that lacks evidence.
- Do not accept product behavior that violates AGENTS.md or investment-dashboard rules.
- Do not accept customer-book demo readiness without the demo preflight result and loaded client-detail browser evidence.
- If the implementation is partial but useful, score it below threshold and provide precise next actions.

Review dimensions:

- contract fit
- correctness
- regression risk
- test evidence
- demo runtime evidence for customer-book, upload/import, portfolio API, Docker/Postgres, or browser-smoke work
- UX/evidence quality for frontend work
- deterministic financial/evidence compliance for investment work
- maintainability and scope control

`normalized_score` is 0 to 10:

- 9-10: contract satisfied, strong evidence, low residual risk
- 8-8.9: acceptable with minor non-blocking issues
- 6-7.9: useful but missing evidence, polish, or edge cases
- 4-5.9: partial, risky, or hard to validate
- 0-3.9: blocked, wrong direction, or unsafe

Blocking findings must force repeat or degraded handoff even if the score is high.

## Compound

Purpose: make the harness better from the review result.

Compound is not a summary. It decides what should be promoted into repo-local harness knowledge.

Immediate document promotion is allowed for:

- `.agents/skills/harness-run/SKILL.md`
- `.agents/skills/harness-run/references/*`
- `AGENTS.md`
- `.codex/instructions/*`
- `docs/harness-runs/*`

Candidate-only promotion for:

- product code
- tests
- lint rules
- scripts
- CI workflows
- API contracts
- generated shared types

`compound-*.md` must include:

- learned principle
- immediate document promotion made
- promotion candidates
- entropy risk
- next loop delta
- whether direction pivot is recommended

## Repeat

Repeat decision:

- `passed`: `normalized_score >= threshold` and no blocking findings
- `repeat`: score below threshold, no terminal blocker, iterations remain
- `pivot`: three consecutive iterations improved by `<= 0.5` or reviewer explicitly requests a different approach
- `degraded`: max_iter reached, external blocker, or contract cannot be safely completed

When passed:

1. ensure `work`, `review`, and `compound` artifacts exist
2. merge or fast-forward sprint branch into run base branch
3. start next sprint from updated run base branch

When degraded:

1. keep the sprint branch
2. write `handoff-<sprint_id>.md`
3. record blocker and next actions in summary
4. continue only if later sprints do not depend on the degraded sprint
