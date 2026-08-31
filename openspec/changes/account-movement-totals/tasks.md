# Tasks

## 1. Schema & Endpoint
- [x] 1.1 Add `MovementTotalsResponse` and `MovementTypeTotals` Pydantic schemas to `schemas.py`
- [x] 1.2 Add `get_totals` method to `MovementsService` in `service.py` that queries movement sums grouped by type for a given account
- [x] 1.3 Add `GET /api/v1/movements/totals` endpoint to `router.py` with `account_id` query parameter
- [x] 1.4 Validate that the account exists before querying totals (return 404 if not found)

## 2. Tests
- [x] 2.1 Test `get_totals` returns correct sums when account has both income and expense movements
- [x] 2.2 Test `get_totals` returns zero totals when account has no movements
- [x] 2.3 Test endpoint returns 404 for non-existent account
- [x] 2.4 Test endpoint returns 422 when `account_id` is missing

## 3. Validation
- [x] 3.1 Run `make checks` and resolve all failures
