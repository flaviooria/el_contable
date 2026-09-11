# Design: Explicit chronological ordering for movements (orden_extracto)

## Context

The period-summary endpoint reconstructs same-day chronology with `ORDER BY (fecha_movimiento, id DESC)` because imported rows share `created_at` within a batch and `id` order happens to track insertion order. That works only while `id` is a sequential bigint aligned with insertion order. It breaks if the primary key migrates to UUID, and `created_at` is uniform within an import batch. EC-006's review (finding F1) confirmed the same-date tiebreaker is untested and rests on an undocumented statement-order assumption. This change introduces an explicit ordering column so chronology never depends on key or timestamp internals.

## Aggregate Boundaries

- Entry-point feature: `movements`
- Aggregates involved: `movements` (single)
- Orchestration: none — both the upload path and period-summary are single-aggregate operations inside `MovementsService`
- Participating services: none beyond `MovementsService` (and `AccountBalanceService` already involved in upload, untouched)

## Transaction Boundary

- Upload: new movements (with their assigned `orden_extracto`) are created, flushed, and committed within the existing upload transaction; ownership is unchanged (service never calls `commit()`; HTTP boundary commits).
- Backfill: the assignment runs inside the Alembic migration transaction. Sequence: add nullable column → backfill via `UPDATE ... FROM row_number()` → `ALTER COLUMN SET NOT NULL` → `ADD CONSTRAINT UNIQUE (account_id, orden_extracto)`. Any failure rolls back atomically, so the table can never be left with null/missing ordinals and a NOT NULL constraint.

## Decisions

### 1. `orden_extracto` semantics

- **Choice**: ascending `orden_extracto` equals the application's chronological order — precisely the order currently produced by `ORDER BY fecha_movimiento ASC, id DESC` (chronological for the reverse-chronological statement format this product ingests; same-date rows ordered income-before-later-nómina).
- **Rationale**: a single invariant shared by imports, backfill, and reads. It preserves the shipped, user-validated period-summary behaviour (income on the closing-nómina day is included and feeds `remaining_balance`) while decoupling from `id`/`created_at`.
- **Alternatives considered**:
  - Raw statement file order (row 1 of the export = newest): rejected — it inverts every boundary comparison and is inconsistent with the chronological backfill formula; ordering logic would constantly need reverse comparisons.
  - `created_at`: rejected — uniform within import batches, provides no intra-batch order.

### 2. Import assignment

- **Choice**: after building the insertion list (existing sort, file order preserved for ties by the stable sort), assign `orden_extracto = max_existing + (n - i)` for `i` in iteration order, so the first inserted row (latest date, lowest new id) receives the highest ordinal and the chronologically earliest row receives `max_existing + 1`.
- **Rationale**: minimal change to the upload path; produces the invariant above for the ingested statement format. Requires only one `SELECT MAX(orden_extracto)` per account before inserting.
- **Limitation (flag)**: forward-only uploads are assumed — new files are chronologically newer than stored data. Importing historically older files later would place their ordinals above newer data, breaking the chronological invariant; acceptable today, requires a recomputation pass if that use case appears (documented, not implemented).

### 3. Backfill direction

- **Choice**: `row_number() over (partition by account_id order by fecha_movimiento, id DESC)`.
- **Rationale**: within a date, `id DESC` reproduces the same-day order the shipped period-summary logic already produces (higher id = chronologically earlier income). A plain `id ASC` (the literal AC text) would invert same-day order and change user-visible behaviour. The AC's formula leaves the tie direction ambiguous; this plan fixes it explicitly. Backfill is best-effort: `id` is the only signal available for legacy same-date rows.

### 4. Migration sequence

- **Choice**: one Alembic migration: add nullable `orden_extracto` → backfill → `SET NOT NULL` → `ADD CONSTRAINT uq_movements_account_orden UNIQUE (account_id, orden_extracto)`.
- **Rationale**: standard safe pattern; the DB-level constraint enforces the per-account guarantee independent of application code.

### 5. Period-summary

- **Choice**: replace `ORDER BY (fecha_movimiento, id DESC)` with `ORDER BY orden_extracto`; detect the closing nómina and period bounds with ordinal comparisons; keep the coarse `fecha >= start_date` filter and the start-date nómina income exclusion; response shape and 404/422 behaviour unchanged.
- **Rationale**: one source of truth for chronology; removes the undocumented `id DESC` heuristic flagged in the EC-006 review.

## Risks

- Same-date statement-order convention assumes reverse-chronological bank exports (matching the current reconstruction). A forward-chronological source would need the tie direction flipped; no such source is ingested today — if one appears, document it.
- Historical backfill is best-effort for same-date rows (only `id` order is available).
- Ordinals are per-account unique but not gapless (deduplicated rows are not inserted); no logic may assume contiguity.