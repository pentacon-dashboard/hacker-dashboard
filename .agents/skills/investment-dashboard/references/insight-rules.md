# Insight Rules

## Output Shape

Use:

- `headline`: one strongest supported fact.
- `narrative`: 2 to 4 sentences.
- `highlights`: 2 to 5 supported bullets.
- `warnings`: 0 to 3 triggered risk notes.
- `evidence`: claim-to-source mapping.
- `confidence`: 0 to 1.
- `report_sections`: optional PB/client report sections, each with section-level evidence.

## Tone

- Korean for user-facing narrative unless surrounding UI is English.
- Keep ticker and market symbols canonical.
- Use uncertainty language when appropriate.
- Inform, do not command.
- PB-facing copy should sound professional, concise, and explainable.
- Client-facing copy should avoid pressure, guarantees, or unsupported personalization.

## Forbidden

- Guaranteed returns or certain direction.
- Unsupported future forecasts.
- Unsupported causality.
- Tickers, prices, dates, or weights absent from data.
- Direct personalized investment advice.
- Client risk profile, objective, or account context not present in input.
- Professional terms such as alpha, beta, correlation, or duration when the required metric was not calculated.

## Confidence

- `0.85-0.95`: complete data and all gates pass.
- `0.70-0.84`: enough data with minor optional gaps.
- `0.50-0.69`: degraded or partial validation.
- `<0.50`: show validation problem, not strong insight.
