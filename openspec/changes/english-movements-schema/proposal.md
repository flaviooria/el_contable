# English schema for movements

## Why

`code_style.md` requires English identifiers, and the accounts/piggy_banks rename already set the precedent. The `movements` table is the only remaining Spanish-identifiers surface: its columns (`fecha_movimiento`, `concepto`, `importe`, `tipo`, `disponible`, `orden_extracto`) leak into models, schemas, service code, and tests. In addition, `expires_at` is dead weight from an earlier temporary-storage idea, `fecha_movimiento` is `DateTime(timezone=True)` although bank statements are date-only, and `movements.id` is a sequential bigint while every other aggregate in the system already uses UUID (accounts, piggy_banks). EC-007 decoupled chronology from the PK via `orden_extracto`, so switching the PK to UUID is now safe.

## What Changes

- All `movements` DB columns and Python identifiers become English; `orden_extracto` → `order_statement` (user's wording).
- `expires_at` is dropped from model, schemas, upload flow, and database.
- The movement date is a plain `Date` (date-only), eliminating the artificial `00:00 UTC` time component.
- `movements.id` becomes a UUID primary key, with FKs (e.g. `movements_piggy_banks.movement_id`) migrated and preserved.
- A per-account chronological-read index strategy is decided (see design.md).
- One Alembic migration (and a working downgrade) preserves existing rows, backfilling generated UUIDs.

## Out of Scope

- Changing the external upload file format: columns `Fecha`, `Concepto`, `Movimiento`, `Importe`, `Disponible` stay as-is (spec `upload_movements`).
- Changing `account_balances`, `accounts`, or `piggy_banks` schemas.
- Replacing the nómina-detection rule ("concept contains nomina") decided in EC-006/EC-008.
- Any behavioural change to `/totals` or `/period-summary` response shapes (identifiers only move to English internally; public fields of those endpoints do not expose Spanish movement columns).

## Impact

- Capabilities: `upload_movements` (canonical spec), `movements` feature (internals)
- Architecture: PK strategy and index strategy for `movements` (see proposed ADR 006)
- Data/migrations: one Alembic migration (UUID PK + column renames + Date + drop `expires_at`) with downgrade; existing rows preserved

## Risks / Decisions

- Breaking public API + schema: the upload response movement `id` becomes a UUID string instead of an integer (explicitly approved by the human at this gate).
- Exact English column names are reviewed at this gate (`movement_date`, `concept`, `amount`, `type`, `available_balance`, `order_statement`).
- UUID backfill uses PostgreSQL `gen_random_uuid()` (PG 13+ builtin, no new dependency); new rows default via SQLAlchemy `uuid.uuid4` (matches accounts precedent).
- PK-type change on a table with FKs is the riskiest part of the migration; the plan sequences the steps so constraints are recreated, never dangling.