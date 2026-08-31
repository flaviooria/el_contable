# Account Movement Totals Endpoint

## Why
Users need a quick way to see the accumulated total of income and expenses for a specific account without fetching all individual movements. This is foundational for the dashboard and financial reporting capabilities described in `FUNCTIONAL.md`.

## What Changes
- Add a new `GET /api/v1/movements/totals` endpoint that returns the sum of movement amounts grouped by type (`ingreso` / `gasto`) for a given account.
- The endpoint accepts an `account_id` query parameter and returns structured totals.

## Out of Scope
- Filtering by date range (future enhancement)
- Filtering by category or concept
- Dashboard UI or charts
- Aggregation across multiple accounts

## Impact
- Capabilities: `upload_movements` (extends read queries within the same feature)
- Architecture: Single-aggregate read-only query, no structural changes
- Data/migrations: None

## Risks / Decisions
- No material risks. This is a straightforward read operation against existing data.
