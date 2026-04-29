# Validation Rules

## Gates

1. Schema gate validates input/output shape.
2. Domain gate validates financial sanity and forbidden language.
3. Evidence gate verifies every numeric or factual claim has rows, metrics, API data, or fixtures.
4. Critique gate verifies narrative claims against rows, metrics, API data, or fixtures.

## Acceptance Criteria

- Valid CSV routes to an Analyzer or returns a clear validation error.
- Router reason is visible.
- UI metrics match backend deterministic output.
- LLM narrative cannot add unsupported facts.
- Portfolio context is opt-in and gracefully degrades.
- Rebalance actions survive LLM failure.
- Broker CSV mapping confidence below the auto-map threshold produces `needs_review`.
- Client report sections fail closed when evidence is missing.

## Test Selection

- Router/Analyzer: golden and unit tests.
- API: related API tests and OpenAPI regeneration.
- Frontend: Vitest and typecheck.
- Routed UX: Playwright.
- Reports: golden samples for section order, evidence links, and fail-safe states.
