# Account Balance Feature — Proposal

## Intent

Introduce a singleton ``account_balances`` table to store the authoritative current balance after each movement upload. This replaces the previous approach of relying on the last inserted movement's ``disponible``, which was incorrect when inserting in descending chronological order.

## Scope

- Create ``features/account_balance/`` vertical slice (models, service)
- Add ``account_balances`` table via Alembic migration
- Integrate balance read/write into ``MovementsService.upload()``
- Update OpenSpec spec and create ADR

## Motivation

- The bank statement file shows the newest balance as the **first row**
- Movements are inserted in descending order (newest date first) so the last stored row has the **oldest balance**
- These two values differ, making the previous ``last_movement.disponible`` approach unreliable for gap detection and front-end display

## Approach

1. **Table**: ``account_balances`` — singleton with ``id``, ``balance``, ``updated_at``
2. **Write**: After movements commit, upsert the file's first ``Disponible`` as the new balance
3. **Read**: Before processing upload, read stored balance from ``account_balances`` for gap detection
4. **Atomicity**: Upsert only after movements commit succeeds

## Impact

- No breaking changes to the upload API response
- New ``account_balances`` table added
- ``MovementsService._get_last_balance()`` now reads from ``account_balances`` instead of ``last_movement.disponible``
