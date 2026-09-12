# Design: English schema for movements

## Context

`movements` is the only table still using Spanish column identifiers, a sequential bigint PK, a `DateTime(timezone=True)` date column, and a dead `expires_at`. EC-007 already decoupled chronology from the PK via `orden_extracto` (unique per account), so moving to a UUID PK no longer loses chronological ordering information.

This is a single-aggregate schema change (`movements` and its junction `movements_piggy_banks`), coordinated entirely inside the migration. No cross-feature orchestration is involved.

## Decisions

### 1. English column names
- `fecha_movimiento` → `movement_date`
- `concepto` → `concept`
- `importe` → `amount`
- `tipo` → `type`
- `disponible` → `available_balance`
- `orden_extracto` → `order_statement`
- `expires_at` → dropped
- `created_at`, `account_id` stay unchanged

**Alternatives considered:** `available` instead of `available_balance` (rejected: column is the running balance after the movement; parity with `account_balances.balance` concept and clarity win). `type` shadows a Python builtin only as a class attribute — safe and matches the already-existing Pydantic field `type` in `MovementTypeTotals`.

### 2. UUID primary key
- DB type: `UUID` (PostgreSQL), values generated with `gen_random_uuid()` (builtin since PG 13 — no `pgcrypto` extension, no new dependency).
- ORM default: `default=uuid.uuid4` in SQLAlchemy, matching `accounts`/`piggy_banks` precedent.
- `movements_piggy_banks.movement_id` migrates `int` → `UUID` referencing `movements.id`.

**Alternatives considered:** keeping sequential bigint (rejected: inconsistent with every other aggregate; EC-007 removed the only ordering reason for a sequential key); UUID v7 (rejected: not builtin in PG 13, adds a dependency for no current benefit).

### 3. Date-only `movement_date`
- DB type: `Date`. The parser/validator produce a `datetime.date`, no artificial `00:00 UTC` time component.
- `period_summary` no longer performs `datetime.combine` on a date column; all comparisons use date-only bounds (see tasks).

**Rationale:** bank statements are date-only; the time component is a fabrication that forced same-day ordering to rely on `order_statement` anyway.

### 4. Index strategy for statement order
- The EC-007 unique constraint `(account_id, order_statement)` is renamed to `uq_movements_account_order_statement` and **kept as the per-account chronological index** — a composite `(account_id, order_statement)` index already supports all chronological reads (queries always filter by `account_id`).
- No additional single-column index on `order_statement`.

**Alternatives considered:** adding a single-column index (`order_statement`) — rejected: nothing queries by statement order without an `account_id`, so the composite unique constraint is sufficient and avoids index duplication.

### 5. Migration sequencing (PG-safe)
The PK-type change with an existing FK cannot be done in place; the migration:

1. Add nullable `id_uuid UUID` to `movements`; backfill with `gen_random_uuid()`.
2. Add nullable `movement_id_uuid UUID` to `movements_piggy_banks`; backfill by joining old `id`.
3. Drop the FK and legacy PK/columns on `movements_piggy_banks`.
4. Rename remaining `movements` columns, alter `movement_date` to `Date`, drop `expires_at`, drop old `id`, promote `id_uuid` to non-null PK `id` (rename to `id`).
5. Recreate `movements_piggy_banks` PK + FK to the new UUID `movements.id`.
6. Rename the unique constraint to `uq_movements_account_order_statement`.
7. Downgrade reverses the sequence (UUID → bigint sequence is regenerated in chronological order via `order_statement`, best-effort).

All steps run inside the single Alembic migration transaction; `op.execute` with raw SQL is used where Alembic ops cannot express the change. `make migrate` must be rerun to verify on a non-empty database.

## Risks

- **Constraint recreation** during PK swap: each step keeps referential integrity by only dropping constraints after their replacement exists. Verified by migration test on a non-empty dataset with linked `movements_piggy_banks` rows.
- **Downgrade fidelity**: back to sequential bigint uses `row_number() over (partition by account_id order by order_statement)`; UUID→bigint is lossy by nature but the sequence is stable and documented as best-effort.
- **Public API break**: movement `id` becomes a UUID string in upload responses; flagged to the human at the approval gate (no compatibility shim).