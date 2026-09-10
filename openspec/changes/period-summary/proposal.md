# Period Summary Endpoint

## Why
Users need to see accumulated income, expenses, and remaining balance for a specific pay period — not just all-time totals. A period starts on a user-provided date and ends when the next salary ("nómina") movement appears, or remains open. This is foundational for the dashboard and financial reporting capabilities described in `FUNCTIONAL.md`.

## What Changes
- Add a new `GET /api/v1/movements/period-summary` endpoint that returns income total, expense total, remaining balance, and movement counts for a user-defined pay period.
- The endpoint accepts `account_id` and `start_date` query parameters.
- Period end is auto-detected by the next movement whose normalized concepto (lowercased, accents stripped) contains "nomina" after `start_date`. This matches both "nómina" and "nomina" spellings that may appear in bank exports.
- The salary movement that starts the period is excluded from income totals.

## Out of Scope
- Automatic period detection (user provides start_date manually)
- Category breakdown within a period (future enhancement when EC-005 lands)
- Dashboard UI or charts
- Persisted period entities — periods are computed on-the-fly

## Impact
- Capabilities: `upload_movements` (extends read queries within the same feature)
- Architecture: Single-aggregate read-only query, no structural changes
- Data/migrations: None

## Risks / Decisions
- No material risks. This is a straightforward read operation against existing data.
- Salary identification relies on concepto containing "nómina" — if the bank labels it differently, the period end detection won't trigger.
