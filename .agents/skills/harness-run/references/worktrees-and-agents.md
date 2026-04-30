# Worktrees And Agents

Use this reference to isolate harness execution.

## Branch Model

Use one integration branch per run and one branch/worktree per sprint:

```text
run base branch: dorec/harness-<run_id>
sprint branch:   dorec/harness-<run_id>-<sprint_id>
sprint worktree: .harness/worktrees/<run_id>/<sprint_id>/
run artifacts:   .harness/runs/<run_id>/
```

The main checkout is the control plane. Do not make product changes there during work/review/compound.

## Execution Order

1. Create or identify `run_id`.
2. Write the plan and sprint contracts.
3. Create run base branch from the current base branch.
4. For each sprint in order:
   - create sprint branch from current run base branch
   - create sprint worktree
   - run work/review/compound iterations in that worktree
   - if passed, merge or fast-forward sprint branch into run base branch
   - if degraded, keep sprint branch and record handoff
5. Start the next sprint from the updated run base branch.
6. Write tracked final summary under `docs/harness-runs/<timestamp>/`.

## Session Strategy

Preferred project-scoped roles:

- `harness_planner`: plan and contract writing
- `harness_worker`: scoped implementation in sprint worktree
- `harness_reviewer`: independent review
- `harness_compounder`: document promotion and harness learning

Fallback if those roles are not available in the current session:

- planner: main agent
- worker: `worker`, `backend_engineer`, `frontend_engineer`, or `analyzer_designer` based on write scope
- reviewer: `integration_qa` or main agent in review stance
- compounder: main agent

Only spawn subagents when the user explicitly asks for subagent orchestration, delegation, or parallel agent work. `/harness-run` and `$harness-run` count as that request for this skill.

## Merge Policy

Passed sprint:

- Prefer fast-forward into run base branch.
- If fast-forward is impossible because compound/document changes overlap, do a normal merge and resolve deliberately.
- Do not squash by default; sprint iteration history is useful evidence.

Degraded sprint:

- Do not merge into run base branch.
- Keep branch and worktree until the user approves cleanup.
- Write `handoff-<sprint_id>.md`.

Cleanup:

- `.harness/` is ignored and may be deleted after final summary is saved.
- Do not delete sprint branches automatically unless the user asks.

## Safety

- Never run `git reset --hard` or destructive cleanup without explicit user approval.
- Before creating worktrees, check `git status --short`.
- Do not touch unrelated dirty files.
- If an uncommitted user change overlaps a sprint write scope, stop and ask for direction.
