# Harness Artifacts

Use this reference for artifact names and minimum schemas.

## Directory Layout

```text
.harness/runs/<run_id>/
  plan.md
  sprints/
    <sprint_id>/
      contract.md
  work-<sprint_id>-<iter>.md
  review-<sprint_id>-<iter>.json
  review-<sprint_id>-<iter>.md
  compound-<sprint_id>-<iter>.md
  image-request-<asset_slug>.md
  image-manifest.json
  handoff-<sprint_id>.md
  summary.md

.harness/worktrees/<run_id>/<sprint_id>/
  <git worktree checkout>

docs/harness-runs/<timestamp>/
  summary.md
  final-review-<sprint_id>.json
  final-compound-<sprint_id>.md
  image-manifest.json
  assets/
```

## Review JSON

```json
{
  "run_id": "20260430-120000-example",
  "sprint_id": "sprint-01",
  "iteration": 1,
  "status": "passed | repeat | pivot | degraded",
  "normalized_score": 8.4,
  "threshold": 8.0,
  "blocking_findings": [
    {
      "title": "string",
      "file": "path or null",
      "line": 0,
      "details": "string"
    }
  ],
  "non_blocking_findings": [],
  "missing_tests": [],
  "commands_reviewed": [],
  "evidence": [],
  "suggest_direction_pivot": false,
  "next_actions": []
}
```

## Compound Markdown

```markdown
# Compound - <sprint_id> iter <iter>

## Learned Principle
<one durable lesson>

## Immediate Document Promotion
<files changed or "none">

## Promotion Candidates
| Type | Candidate | Reason | Owner |
|---|---|---|---|

## Entropy Risk
<risk of bad pattern propagation>

## Next Loop Delta
<contract or approach change for the next iteration>

## Direction Pivot
true|false - <why>
```

## Work Markdown

```markdown
# Work - <sprint_id> iter <iter>

## Scope
- Contract: <path>
- Branch: <branch>
- Worktree: <path>

## Changes
- <file>: <change>

## Commands
| Command | Result | Notes |
|---|---|---|

## Images
- <asset slug or none>

## Blockers
- <blocker or none>

## Reviewer Notes
<anything the reviewer needs>
```

## Summary Markdown

```markdown
# Harness Run Summary - <run_id>

## Request
<original request>

## Settings
threshold=<n>, max_iter=<n>

## Branches
- Run base: <branch>
- Sprint branches: <list>

## Sprint Results
| Sprint | Status | Iter | Score | Branch | Handoff |
|---|---|---:|---:|---|---|

## Compounding
<document promotions and candidates>

## Images
<manifest summary or none>

## Checks
<commands and outcomes>

## Residual Risks
<risks>
```
