---
## EC-006 - Period summary endpoint

**Status:** done
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

- Change: period-summary
- Proposal: openspec/changes/period-summary/proposal.md
- Specs: openspec/changes/period-summary/specs/movements/spec.md
- ADR: docs/decisions/005-period-summary.md

### Execution

- Commit: 0b348f9 (endpoint: 8f05887)

## EC-007 - Explicit chronological ordering for movements (orden_extracto)

**Status:** ready-to-commit
**Priority:** high
**Depends on:** EC-006

### Description

Current logic for determining "before/after a given movement" (e.g. detecting the period after a nómina) relies on `id` or `created_at`. Both are fragile: `created_at` is shared across an entire import batch (same timestamp for many rows), and `id` may not remain a sequential bigint if the schema migrates to UUID. Add an explicit `orden_extracto` column that records the true chronological position of each movement as it appeared in the original bank statement/import, decoupled from the primary key.

### Acceptance Criteria

- New integer column `orden_extracto` added to `movements`.
- On each import, `orden_extracto` is assigned as the sequential position of the movement within that statement/file (1, 2, 3...), not derived from `id` or `created_at`.
- Uniqueness of `orden_extracto` is scoped per `account_id`.
- One-time backfill migration populates `orden_extracto` for existing rows, using `row_number() over (partition by account_id order by fecha_movimiento, id)` as the best-effort reconstruction.
- EC-006 (period-summary endpoint) is updated to determine period boundaries and ordering using `orden_extracto` instead of `fecha_movimiento`/`id`.
- No change to the public response shape of `/api/v1/movements/period-summary` or `/totals`.
- Tests cover: multiple same-day movements ordered correctly, backfill producing a valid strictly-increasing sequence per account, and period-summary boundary detection using the new column.

### Constraints

- Requires a database migration (add column) plus a one-time data backfill — unlike EC-006, this is not computed on-the-fly.
- Follow the service vs use-case aggregate rules in `docs/ARCHITECTURE.md`.
- Do not introduce a new dependency without explicit human approval.
- Import/ingestion code path must be updated to populate `orden_extracto` going forward; existing import logic that inserts movements needs identifying first.

### Planning

- Change: movement-ordering
- Proposal: openspec/changes/movement-ordering/proposal.md
- Specs: openspec/changes/movement-ordering/specs/upload_movements/spec.md
- ADR: none (decision recorded in design.md)

### Execution

- Commit: -
---
