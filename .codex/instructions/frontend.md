# Frontend Instructions

## Stack

- Next.js App Router, React, TypeScript, Tailwind, shadcn/ui.
- Server state: TanStack Query.
- UI state: Zustand.
- Charts: lightweight-charts for price charts, Recharts for allocation and summary charts.

## Dashboard UX

- First useful view after upload must show KPI, primary chart, and first insight.
- Always include loading, empty, error, and degraded states.
- Show Router reason, gate status, evidence, and confidence for analysis outputs.
- Keep operational dashboard density; avoid marketing-style landing pages.

## Tests

- Run focused Vitest for changed components.
- Run `npm run typecheck` for typed API/UI changes.
- Use Playwright for routed visual workflows.
