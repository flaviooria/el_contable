# Explicit chronological ordering for movements (orden_extracto)

## Why

The application determines "before/after a given movement" (e.g. period-summary boundary detection) using `id` order as a proxy for chronology. This is fragile: `created_at` is shared across an entire import batch, and `id` may not remain a sequential bigint if the schema migrates to UUID. Same-day movements (a "nómina" and an income on the same date) expose the problem — their true order exists only in the bank statement. EC-006's review also flagged the same-day `id DESC` tiebreaker as untested (finding F1). This change adds an explicit, per-account chronological position decoupled from the primary key.

## What Changes

- New `orden_extracto` integer column on `movements`, unique per `account_id`; ascending value equals the application's chronological order (the order currently reconstructed via `ORDER BY fecha_movimiento, id DESC`).
- Upload assigns `orden_extracto` to newly inserted movements (continuing per-account sequence), never derived from `id` or `created_at`.
- One-time backfill migration populates the column for existing rows.
- `GET /api/v1/movements/period-summary` determines boundaries and ordering using `orden_extracto` instead of `fecha_movimiento`/`id`; its public response is unchanged.

## Out of Scope

- Changing the public response shape of `/period-summary` or `/totals`.
- Changing the upload sort order used for insertion (remains as today — the new column is assigned independently).
- Reassigning ordinals when historically older files are imported later (forward-only uploads are assumed; see design.md risks).
- Fixing the pre-existing `commit()` inside `MovementsService.upload` (documented transaction-ownership debt, unrelated to this change).

## Impact

- Capabilities: `upload_movements`
- Architecture: single-aggregate (movements), service-only — no use case, no cross-feature dependency
- Data/migrations: one Alembic migration (add column + backfill + NOT NULL + unique constraint)

## Risks / Decisions

- Same-date ordering convention assumes the reverse-chronological statement format this product ingests (matching the assumption the current `id DESC` reconstruction already makes).
- The AC backfill formula ("order by fecha_movimiento, id") leaves the same-day tie direction ambiguous; this plan fixes it as `id DESC` to preserve the shipped, user-validated same-day ordering. A plain `id ASC` would invert same-day order and change visible behaviour.
- `orden_extracto` values are not gapless per account (deduplicated rows are not inserted); only uniqueness is guaranteed.
- No ADR is proposed: the decision and trade-offs are recorded in `design.md` (the environment restricts artifact creation to `openspec/changes/` during planning). An ADR can be added at implementation time if desired.