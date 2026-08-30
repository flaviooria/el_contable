# account_balance Specification

## Purpose

Store the authoritative current available balance per account. This balance serves as the single source of truth for gap detection in subsequent uploads and for front-end visualizations.

## Requirements

### Requirement: Per-account balance storage

The system SHALL store exactly one row in ``account_balances`` per account.

#### Scenario: Single row per account

- GIVEN an account has no balance record
- WHEN the first upload completes successfully for that account
- THEN insert a row with ``account_id`` and ``balance`` set to the file's first ``Disponible`` value
- AND ``updated_at`` set to the current timestamp

#### Scenario: Subsequent balance updates

- GIVEN ``account_balances`` already contains a row for the account
- WHEN a new upload completes successfully for that account
- THEN update that row's ``balance`` to the new file's first ``Disponible`` value
- AND set ``updated_at`` to the current timestamp

### Requirement: Read balance for deduplication

The system SHALL read the stored balance before processing a new upload to support gap detection.

#### Scenario: Read existing balance

- GIVEN ``account_balances`` contains a row with ``account_id`` = X and ``balance`` = Y
- WHEN a new upload is processed for account X
- THEN use Y as the reference balance for gap detection
- AND compare the file's first ``Disponible`` against Y to determine if rows are missing

#### Scenario: Empty balance on first upload

- GIVEN ``account_balances`` has no row for the account
- WHEN the first upload is processed
- THEN treat the reference balance as ``None``
- AND insert all valid rows without gap validation

### Requirement: Upsert after commit

The ``account_balances`` table SHALL be updated only after the movements commit succeeds, to avoid desynchronization if the commit fails.

#### Scenario: Upload succeeds

- GIVEN all validations pass and movements are committed
- WHEN the upload completes
- THEN upsert the new balance into ``account_balances`` for the corresponding account

#### Scenario: Upload fails before commit

- GIVEN an error occurs before the movements are committed
- THEN the ``account_balances`` table MUST NOT be updated
- AND the previous balance remains unchanged
