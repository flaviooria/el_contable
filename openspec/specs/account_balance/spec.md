# account_balance Specification

## Purpose

Store the authoritative current available balance after each movement upload. This balance serves as the single source of truth for gap detection in subsequent uploads and for front-end visualizations.

## Requirements

### Requirement: Singleton storage

The system SHALL store exactly one row in the ``account_balances`` table containing the current balance and the timestamp of the last update.

#### Scenario: Single row guarantee

- GIVEN the system has no rows in ``account_balances``
- WHEN the first upload completes successfully
- THEN insert a single row with ``balance`` set to the file's first ``Disponible`` value
- AND ``updated_at`` set to the current timestamp

#### Scenario: Subsequent updates

- GIVEN ``account_balances`` already contains one row
- WHEN a new upload completes successfully
- THEN update that row's ``balance`` to the new file's first ``Disponible`` value
- AND set ``updated_at`` to the current timestamp

### Requirement: Read balance for deduplication

The system SHALL read the stored balance before processing a new upload to support gap detection.

#### Scenario: Read existing balance

- GIVEN ``account_balances`` contains a row with ``balance`` = X
- WHEN a new upload is processed
- THEN use X as the reference balance for gap detection
- AND compare the file's first ``Disponible`` against X to determine if rows are missing

#### Scenario: Empty balance table on first upload

- GIVEN ``account_balances`` is empty (no rows)
- WHEN the first upload is processed
- THEN treat the reference balance as ``None``
- AND insert all valid rows without gap validation

### Requirement: Upsert after commit

The ``account_balances`` table SHALL be updated only after the movements commit succeeds, to avoid desynchronization if the commit fails.

#### Scenario: Upload succeeds

- GIVEN all validations pass and movements are committed
- WHEN the upload completes
- THEN upsert the new balance into ``account_balances``

#### Scenario: Upload fails before commit

- GIVEN an error occurs before the movements are committed
- THEN the ``account_balances`` table MUST NOT be updated
- AND the previous balance remains unchanged
