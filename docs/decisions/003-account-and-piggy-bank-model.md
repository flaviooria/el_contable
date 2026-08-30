# 003 - Account and PiggyBank Model

## Context

We needed to model user accounts and sub-accounts (PiggyBanks) to support money allocation and separation. Key decisions were required around:

- The relationship between Account, PiggyBank, and Movement
- How PiggyBank balances are calculated
- Whether PiggyBanks track their own balance or derive it from movements
- Unique constraints for PiggyBank names

## Decision

We implement:

**Account**
- ``accounts`` table with UUID primary key
- ``base_balance`` — the user's total money
- ``entry_date`` — account creation date
- ``created_at`` — record creation timestamp

**PiggyBank**
- ``piggy_banks`` table with UUID primary key
- ``account_id`` — FK to ``accounts``
- ``name`` — user-defined label
- ``max_balance`` — optional savings goal (informational only)
- ``created_at`` — record creation timestamp
- Unique constraint: ``(name, account_id)`` — same name allowed in different accounts

**Movement → Account**
- ``movements`` gets ``account_id`` FK to ``accounts``
- All movements belong to an account

**Movement ↔ PiggyBank**
- Junction table ``movements_piggy_banks`` links ``movement_id`` and ``piggy_bank_id``
- A movement may be linked to zero or more PiggyBanks
- A PiggyBank's balance is **calculated** from linked movements, not stored

## Why

### PiggyBank balance as derived value

Storing ``balance`` in PiggyBank would require recalculating it on every movement link/unlink and on every upload. Calculating from ``movements_piggy_banks`` is simpler, always accurate, and avoids synchronization issues.

### ``max_balance`` is informational only

The user may set a savings target. The system shows progress toward that target but does not enforce it. Enforcement would require complex rules (e.g., what happens when a savings PiggyBank exceeds the target?).

### Unique ``(name, account_id)``

Two accounts may have a PiggyBank named "Ahorro" independently. Within the same account, PiggyBank names must be unique to avoid ambiguity.

### Why junction table instead of nullable FK on Movement

A movement can contribute to multiple PiggyBanks (e.g., a purchase split across categories). The junction table supports this cleanly without complicating the Movement model.

## Status

Accepted - 2026-08-28
