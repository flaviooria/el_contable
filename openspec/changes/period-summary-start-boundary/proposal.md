# Exclude pre-nómina same-day income from period start boundary

## Why

`GET /api/v1/movements/period-summary` builds the period from 00:00 of `start_date` and excludes only the start nómina itself. Income on `start_date` chronologically BEFORE the start nómina (lower `orden_extracto`) leaks into the period. Real-data report: for `start_date = 2026-08-27`, `income_total` returned 243.81 / count 3; expected 30.19 / count 2 — the 213.62 income received that day before the salary belongs to the previous period.

## What Changes

- In `MovementsService.get_period_summary`, when a start-date nómina exists, exclude from the period the nómina itself AND any INGRESO movement with `orden_extracto <=` the start nómina's (comparison on `orden_extracto`, not on date or `id`).
- GASTO movements on `start_date` — including those chronologically before the start nómina — remain included in `expense_total`/`expense_count` (explicit user decision: asymmetric boundary).
- INGRESO movements on `start_date` after the start nómina remain included.
- Docstring updated to state the start boundary rule.
- Public response shape, rounding, 404/422 behaviour, and the end boundary (closing nómina, including same-day movements before it) are unchanged.

## Out of Scope

- Changing the end boundary (closing nómina) semantics.
- Any schema or migration change.
- Any other endpoint (`/totals`, upload).

## Impact

- Capabilities: `movements` (period-summary).
- Architecture: single-aggregate change inside `MovementsService`; no use case, no cross-feature dependency, no migration.
- Decision: asymmetric start boundary (income at/before the start nómina is excluded; expenses on start_date are kept) — explicit product decision by the user, 2026-09-12.

## Risks

- None material: behaviour only changes for periods whose `start_date` contains pre-nómina same-day income (the reported bug). If `start_date` has no nómina, behaviour is unchanged.
