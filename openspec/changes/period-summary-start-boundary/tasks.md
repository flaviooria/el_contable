# Tasks

## 1. Implementation

- [x] 1.1 In `MovementsService.get_period_summary` (`src/el_contable/features/movements/service.py`), replace the start-nómina exclusion: when a start-date nómina exists, exclude from the period the nómina itself AND any INGRESO movement with `orden_extracto <=` the start nómina's; keep all GASTO movements (asymmetric boundary)
- [x] 1.2 Update the `get_period_summary` docstring/comment to state the start boundary rule (period begins strictly after the start nómina for income; start-date expenses are kept)

## 2. Tests

- [x] 2.1 Add a regression test: income on start_date chronologically before the start nómina (lower `orden_extracto`) is excluded from `income_total` and `income_count` (real-case shape: start nómina + earlier same-day income, then later incomes)
- [x] 2.2 Add a test: expense on start_date chronologically before the start nómina remains included in `expense_total` and `expense_count`
- [x] 2.3 Add a test: income on start_date chronologically after the start nómina remains included
- [x] 2.4 Keep the existing suite green (period-summary, totals, upload regression)

## 3. Validation

- [x] 3.1 Run `make checks` (lint, format, mypy, tests) and resolve all failures
