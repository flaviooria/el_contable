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

**Status:** done
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

- Commit: a77aaf3

## EC-008 - Exclude pre-nómina same-day income from period start boundary

**Status:** done
**Priority:** high
**Depends on:** EC-007

### Description

`GET /api/v1/movements/period-summary` includes all movements from 00:00 of `start_date` and only excludes the start nómina itself. Same-day income chronologically BEFORE the start nómina (lower `orden_extracto`) leaks into the period and inflates `income_total` (real case: 2026-08-27 income 213.62 counted → income_total 243.81 / count 3 instead of 30.19 / count 2). The start boundary must use `orden_extracto`: exclude the start nómina AND any income at or before it. Expenses on `start_date` (even chronologically before the nómina) remain included — explicit user decision (asymmetric boundary).

### Acceptance Criteria

- The period excludes the start-date nómina and any INGRESO movement with `orden_extracto <=` the start nómina's.
- GASTO movements on start_date before the start nómina remain included in `expense_total`/`expense_count`.
- INGRESO movements on start_date after the start nómina (higher `orden_extracto`) remain included.
- Behavior is unchanged when `start_date` has no nómina movement.
- Response shape, rounding, 404 and 422 behaviour are unchanged; end boundary (closing nómina) is unchanged.
- Real-data check: income_total 30.19 / income_count 2 for start_date 2026-08-27.
- Tests cover the new boundary rule and the full suite stays green.

### Constraints

- No schema changes; no new dependencies.
- Single-aggregate change inside `MovementsService`; follow `docs/ARCHITECTURE.md`.

### Planning

- Change: period-summary-start-boundary
- Proposal: openspec/changes/period-summary-start-boundary/proposal.md
- Specs: openspec/changes/period-summary-start-boundary/specs/movements/spec.md
- ADR: none

### Execution

- Commit: 2767e5e

## EC-009 - English schema for movements (UUID PK, Date type, drop expires_at, indexed statement order)

**Status:** done
**Priority:** high
**Depends on:** EC-008

### Description

Modernize the `movements` table schema and rename all identifiers to English (code_style mandates English identifiers; precedent: the accounts/piggy_banks column rename):

- Rename Spanish columns to English: `fecha_movimiento`, `concepto`, `importe`, `tipo`, `disponible`, `orden_extracto` → English equivalents.
- Rename `orden_extracto` → `order_statement` (user's wording; exact final name to confirm at approval) and add a database index supporting per-account chronological ordering.
- Drop the `expires_at` column.
- The movement date column becomes pure `Date` type (bank statements are date-only; currently `DateTime(timezone=True)`).
- Primary key `id` becomes UUID (currently sequential bigint); every FK referencing `movements.id` (e.g. `movements_piggy_banks`) migrates accordingly.
- Update all code reading/writing these fields: models, parser, validator, service (upload, totals, period-summary), Pydantic schemas, router, tests, and OpenSpec specs.

This completes EC-007's rationale: chronology is already decoupled from the PK via the statement-order column, so a UUID PK is safe.

### Acceptance Criteria

- All `movements` columns and code identifiers are in English; no Spanish identifiers remain.
- `expires_at` removed from model, schemas, and database.
- Movement date column is `Date`; parser/validator/service/tests adapted (period-summary date handling revisited, no `datetime.combine` leftovers on a Date column).
- `id` is UUID in database and API responses (breaking API change — explicitly approved).
- FK columns referencing `movements.id` are UUID and constraints survive the migration.
- A database index exists for the statement-order column (single vs composite `(account_id, order_statement)` decided at planning).
- Alembic migration(s) with working downgrade; existing rows preserved with generated UUIDs.
- Per-account uniqueness of the statement-order column (EC-007 invariant) survives the rename.
- Full test suite and `make checks` green.

### Constraints

- Breaking schema AND public API change — requires the human approval gate at planning; an ADR is expected (PK strategy is a material architectural decision).
- Follow `docs/code_style.md` (English identifiers) and `docs/ARCHITECTURE.md` aggregate rules.
- No new dependencies without explicit approval (UUID generation via stdlib/SQLAlchemy defaults or PostgreSQL `gen_random_uuid()`; decide at planning).
- Must be sequenced after EC-008 (same code paths).

### Planning

- Change: english-movements-schema
- Proposal: openspec/changes/english-movements-schema/proposal.md
- Specs: openspec/changes/english-movements-schema/specs/upload_movements/spec.md
- ADR: docs/decisions/006-movements-uuid-primary-key.md

### Execution

- Commit: 3b518aa
---
