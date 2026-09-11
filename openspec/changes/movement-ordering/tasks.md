# Tasks

## 1. Schema & migration

- [x] 1.1 Add `orden_extracto: Mapped[int]` (non-null, `mapped_column(Integer, nullable=False)`) to the `Movement` model in `src/el_contable/features/movements/models.py`
- [x] 1.2 Create one Alembic migration that: adds a nullable `orden_extracto` column; backfills it with `row_number() over (partition by account_id order by fecha_movimiento, id DESC)`; sets `NOT NULL`; adds a `UNIQUE (account_id, orden_extracto)` constraint
- [x] 1.3 Verify `make migrate` (upgrade head) and the migration's `downgrade` run cleanly

## 2. Import assignment

- [x] 2.1 In `MovementsService.upload`, query the per-account maximum `orden_extracto` (coalesce to 0) before inserting and assign continuing positions so ascending `orden_extracto` equals chronological order (first inserted row = highest ordinal, earliest row = max_existing + 1)
- [x] 2.2 Confirm deduplicated/skipped rows are never re-assigned and the upload response (`UploadResponse`) is byte-identical in shape

## 3. Period-summary

- [x] 3.1 In `get_period_summary`, replace `ORDER BY (fecha_movimiento, id DESC)` with `ORDER BY orden_extracto`
- [x] 3.2 Use ordinal comparisons for closing-nómina detection and period bounds; keep the `fecha >= start_date` coarse filter, the strictly-after-`start_date` closing detection, and the start-date nómina income exclusion
- [x] 3.3 Verify the response shape, rounding, 404 (non-existent account) and 422 behaviour are unchanged

## 4. Tests

- [x] 4.1 Add a same-timestamp regression test: income and closing nómina share an identical `fecha_movimiento`, income is included in the period and feeds `remaining_balance`, `period_end` equals the nómina date (closes EC-006 review finding F1)
- [x] 4.2 Add a test that backfill logic produces a strictly increasing, gapless per-account sequence ordered chronologically
- [x] 4.3 Add/extend tests for period-summary boundary detection via `orden_extracto` (movement same day as closing nómina included; open-ended and bounded periods unchanged)
- [x] 4.4 Add a test that `(account_id, orden_extracto)` uniqueness is enforced
- [x] 4.5 Add a test that re-uploading an already-imported file does not reassign existing `orden_extracto` values
- [x] 4.6 Keep existing `/totals` and `/period-summary` response-shape tests green (regression)

## 5. Validation

- [x] 5.1 Run `make checks` (lint, format, mypy, tests) and resolve all failures