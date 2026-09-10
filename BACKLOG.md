## EC-006 - Period summary endpoint

**Status:** pending
**Priority:** high
**Depends on:** none

### Description

Add a GET endpoint that returns accumulated income and expenses for a user-defined pay period. The period starts on a manually provided date and ends when the next "nómina" (salary) movement is found, or remains open if none exists. The salary movement that starts the period is excluded from income totals.

### Acceptance Criteria

- GET /api/v1/movements/period-summary accepts account_id and start_date query params.
- The period end is determined by the next movement whose concepto contains "nómina" (case-insensitive) after start_date.
- If no next nómina exists, the period is open-ended (up to the last movement).
- Income total excludes the nómina movement that starts the period.
- Expense total includes all gasto movements in the period.
- Remaining balance equals the last `disponible` value in the period.
- HTTP 404 when account does not exist.
- HTTP 422 for missing or invalid query parameters.
- Relevant behaviour and failure paths are covered by tests.

### Constraints

- No database migration required — the period is computed on-the-fly.
- Preserve existing /totals endpoint behaviour.
- Follow the service vs use-case aggregate rules in `docs/ARCHITECTURE.md`.
- Do not introduce a new dependency without explicit human approval.

### Planning

- Change: -
- Proposal: -
- Specs: -
- ADR: -

### Execution

- Commit: -
