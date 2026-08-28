# 002 - Account Balance Storage

## Context

We needed a reliable, authoritative source for the current available balance. This is required for:
1. **Gap detection** — comparing the stored balance against the incoming file's first ``Disponible`` to detect missing movements
2. **Front-end display** — showing the user their current available balance without recalculating from all movements

The previous approach relied on the ``disponible`` of the last inserted movement. However:
- Movements are inserted in descending chronological order (newest first) so the last inserted row has the oldest balance
- The file's first ``Disponible`` (always the newest balance from the bank statement) is the authoritative figure
- These two values are different, making the previous approach unreliable

## Decision

We store the authoritative balance in a dedicated singleton table ``account_balances``:

- **Table**: ``account_balances`` with columns ``id``, ``balance`` (float), ``updated_at`` (timestamp)
- **Write**: After movements commit succeeds, upsert the file's first ``Disponible`` as the new balance
- **Read**: Before processing a new upload, read the stored balance for gap detection
- **Upsert after commit**: The upsert happens only after the movements are committed, to avoid desynchronization on failure

## Why

### Singleton table vs last movement's disponible

Using the last inserted movement's ``disponible`` is incorrect when inserting in descending order (newest first). The bank file always shows the newest balance as the first row, which is the authoritative figure.

### Upsert after commit

If the balance were updated before the movements commit, a commit failure would leave the balance out of sync with the actual movements. By upserting only after successful commit, we guarantee consistency.

### Dedicated table vs embedding in movements

A dedicated ``account_balances`` table:
- Makes the balance intent explicit and easy to query
- Avoids relying on ordering assumptions in the movements table
- Can be extended to support multiple accounts in the future

## Status

Accepted - 2026-08-28
