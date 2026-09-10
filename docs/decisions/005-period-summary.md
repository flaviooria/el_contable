# 005 - Period Summary Pay Period

## Context

Users needed to see accumulated income, expenses, and remaining balance for a **pay period** — the window between two salary payments — rather than all-time totals. The existing ``GET /api/v1/movements/totals`` endpoint only aggregates across all movements with no date window.

The salary cycle does not align with calendar months: a salary received on 27-06-2026 defines the period that closes when the next salary arrives on 27-07-2026. Bank exports may label the salary as "Nómina" or "nomina" (accent may be lost in CSV/XLSX files), and the salary amount itself can change between periods.

## Decision

Add ``GET /api/v1/movements/period-summary`` accepting ``account_id`` and ``start_date`` (the salary date, provided manually by the user):

- The period runs ``[start_date, next_nomina_date)`` where the next salary is the first movement whose **normalized** concepto (lowercased, accents stripped via ``unicodedata`` NFKD) contains ``"nomina"``.
- If no subsequent salary movement exists, the period is open-ended (``period_end`` is ``null``) and includes all movements from ``start_date`` onward.
- The salary movement at ``start_date`` is excluded from ``income_total``.
- ``expense_total`` sums all ``gasto`` movements in the period.
- ``remaining_balance`` is the ``disponible`` value of the last movement in the period.
- The period is computed **on-the-fly** — no new table, no migration.

## Why

### Accent-insensitive salary detection

Bank CSV/XLSX exports frequently drop the accent ("nomina" instead of "nómina"), and the salary amount may change between periods when the user gets a raise or cut. Normalizing the concepto (lowercase + strip accents) makes detection robust to both spellings and independent of the salary amount.

### Start-date salary excluded from income

The summary is meant to answer "how much did I earn (beyond salary), how much did I spend, and what is left" — including the gross salary in ``income_total`` would misrepresent the money available for the period.

### On-the-fly computation

A persisted ``period`` entity was unnecessary: the period is fully derivable from existing movements, and the user provides the start date manually. This keeps the change free of schema changes and migrations.

## Alternatives Considered

### Persisted period entity

A dedicated ``periods`` table would store period boundaries explicitly. Rejected because the periods are fully derivable from existing movements and ``start_date`` input — persisting them adds a migration and synchronization burden without user-visible benefit yet.

### Match salary by importe equal to ``base_balance``

Identify the salary as any ``ingreso`` whose amount equals the account's ``base_balance``. Rejected because the salary amount can change between periods (raise, cut, proration); the concepto keyword is more stable.

## Status

Accepted - 2026-09-10