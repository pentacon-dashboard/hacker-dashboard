# QA Instructions

## Required Coverage Areas

- CSV upload and schema validation.
- Router classification and reason display.
- Analyzer output structure and gate metadata.
- Portfolio context opt-in and graceful degradation.
- Rebalance deterministic actions with LLM failure fallback.
- Dashboard loading, empty, error, and degraded states.

## Evidence

Use these evidence sources:

- `backend/tests/golden/samples/`.
- `docs/harness-runs/*/summary.md`.
- `submission/test-coverage.md`.
- Playwright screenshots only when they are intentionally captured for review.

## Reporting

Lead with failing behavior, regression risk, and missing tests. Keep summaries secondary.
