# 006 - Movements UUID Primary Key and English Schema

## Context

Every aggregate in the system already uses a UUID primary key (`accounts`, `piggy_banks`), but `movements` still uses a sequential bigint `id`. The sequential key was originally convenient as an implicit chronological tiebreaker, but EC-007 introduced `orden_extracto` (statement order, unique per account), which fully decoupled chronology from the primary key. In addition, `movements` is the only table still carrying Spanish column identifiers, a `DateTime(timezone=True)` date column for date-only bank data, and a dead `expires_at` column from an earlier temporary-storage idea.

## Decision

For EC-009 ("English schema for movements"):

- `movements.id` becomes a UUID primary key, generated with PostgreSQL `gen_random_uuid()` during migration backfill and `default=uuid.uuid4` (SQLAlchemy) for new rows — matching the `accounts`/`piggy_banks` precedent.
- All `movements` columns are renamed to English: `fecha_movimiento` → `movement_date`, `concepto` → `concept`, `importe` → `amount`, `tipo` → `type`, `disponible` → `available_balance`, `orden_extracto` → `order_statement`.
- `movement_date` becomes a plain `Date` (bank statements are date-only; the fabricated `00:00 UTC` time component is removed).
- `expires_at` is dropped from the model, schemas, and database.
- The EC-007 unique constraint `(account_id, order_statement)` is renamed to `uq_movements_account_order_statement` and kept as the per-account chronological index.
- `movements_piggy_banks.movement_id` migrates to UUID, referencing the new `movements.id`.

## Why

- **Consistency**: UUID PKs are already the established pattern for every aggregate; a bigint-only exception adds cognitive and integration overhead for no benefit.
- **Chronology is explicit**: `order_statement` carries statement order; the PK no longer needs to encode it.
- **English identifiers** satisfy `code_style.md`, which the accounts/piggy_banks rename already enforced.
- **Date-only** matches the true domain (bank statements have no time component) and removes the same-day ordering ambiguity that motivated timezone-fabricated timestamps.

## Alternatives Considered

- **Keep sequential bigint**: rejected — inconsistent with the rest of the schema, and EC-007 removed its only functional reason.
- **UUID v7 (time-ordered)**: rejected — not builtin in PG 13, adds a dependency for no current need; `order_statement` already provides order.
- **Single-column index on `order_statement`**: rejected — all chronological reads filter by `account_id` first, so the composite unique constraint is the sufficient index.
- **Keep `DateTime(timezone=True)`**: rejected — it fabricates time information and shifts the same-day-ordering burden back onto tiebreakers.

## Consequences

- **Public API break**: movement `id` becomes a UUID string in upload responses (breaking change, explicitly approved).
- **Migration complexity**: PK-type change with an existing FK requires a sequenced migration (add UUID column → backfill → recreate FKs → promote PK → drop legacy columns), done in a single transaction with a working downgrade.
- **Downgrade fidelity**: UUID → bigint regeneration is best-effort (sequential ids re-derived from `order_statement`).

## Status

Proposed - 2026-09-12 (awaiting approval with EC-009)

Related work item: EC-009
Related change: `english-movements-schema`