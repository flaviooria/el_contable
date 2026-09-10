# Tasks

## 1. Schema
- [x] 1.1 Add `PeriodSummaryResponse` Pydantic schema to `schemas.py` with fields: account_id, period_start, period_end, income_total, expense_total, remaining_balance, income_count, expense_count

## 2. Service
- [x] 2.1 Add `get_period_summary(account_id, start_date)` method to `MovementsService` in `service.py`
- [x] 2.2 Implement period end detection: find next movement after start_date whose normalized concepto (lowercased, accents stripped) contains "nomina"
- [x] 2.3 Implement movement filtering: movements within [start_date, end_date) excluding the salary movement at start_date
- [x] 2.4 Implement aggregation: sum importe by tipo, count movements, get last disponible as remaining_balance
- [x] 2.5 Validate account exists before querying (raise ValueError if not found)

## 3. Router
- [x] 3.1 Add `GET /api/v1/movements/period-summary` endpoint to `router.py` with account_id and start_date query parameters
- [x] 3.2 Map ValueError to HTTP 404 for non-existent account

## 4. Tests
- [x] 4.1 Test get_period_summary returns correct totals when account has income and expense movements in period
- [x] 4.2 Test get_period_summary excludes nómina movement from income_total
- [x] 4.3 Test get_period_summary returns zero totals when no movements exist in period
- [x] 4.4 Test get_period_summary with open-ended period (no next nómina)
- [x] 4.5 Test get_period_summary with bounded period (next nómina exists)
- [x] 4.6 Test endpoint returns 404 for non-existent account
- [x] 4.7 Test endpoint returns 422 when account_id is missing
- [x] 4.8 Test endpoint returns 422 when start_date is missing

## 5. Expense sign, rounding, and remaining_balance fixes
- [x] 5.1 Report expense_total as a positive number (absolute sum of gasto importes)
- [x] 5.2 Round income_total, expense_total, and remaining_balance to 2 decimals
- [x] 5.3 Use the closing nómina's exact fecha_movimiento as the exclusive period end (not the start of its day), so same-day-before-salary movements are included
- [x] 5.4 Keep remaining_balance as the disponible of the last movement chronologically before the closing nómina
- [x] 5.5 Update/extend tests: positive expense_total, rounding, same-day-as-nómina movement included and feeds remaining_balance

## 6. Validation
- [x] 6.1 Run `make checks` and resolve all failures