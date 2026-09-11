# upload_movements Delta

## MODIFIED Requirements

### Requirement: Ascending order by date

The system SHALL insert all movements in ascending order by ``fecha_movimiento``, regardless of the order in which they appear in the uploaded file, and SHALL assign each inserted movement an explicit chronological position ``orden_extracto`` that is unique within the account and ordered chronologically (ascending ``orden_extracto`` equals chronological order, including same-date statement order).

#### Scenario: File with unsorted dates

- **WHEN** a file contains rows in a random date order
- **THEN** insert all rows sorted by ``fecha_movimiento`` ascending
- **AND** assign ``orden_extracto`` so that earlier dates receive lower values

## ADDED Requirements

### Requirement: Chronological position (orden_extracto)

The system SHALL persist an explicit per-account chronological position ``orden_extracto`` for each movement, decoupled from the primary key and from ``created_at``.

#### Scenario: New import assigns continuing positions

- **WHEN** a file with new movements is uploaded for an account
- **THEN** each inserted movement receives an ``orden_extracto`` continuing the account's sequence after the maximum existing value (1, 2, 3, ...) in chronological order
- **AND** no value is derived from ``id`` or ``created_at``

#### Scenario: Same-day movements keep statement order

- **WHEN** two movements share the same ``fecha_movimiento`` within one import
- **THEN** their ``orden_extracto`` values are assigned per statement order (the chronologically earlier movement gets the lower value)

#### Scenario: Re-upload does not reassign

- **WHEN** a file containing already-imported movements is uploaded again
- **THEN** existing movements are deduplicated (not re-inserted)
- **AND** their ``orden_extracto`` is not reassigned

#### Scenario: Unique per account

- **WHEN** movements are inserted for two different accounts
- **THEN** each account has its own independent ``orden_extracto`` sequence
- **AND** the pair ``(account_id, orden_extracto)`` is unique

#### Scenario: Backfill of existing rows

- **WHEN** the one-time backfill migration runs over pre-existing movements
- **THEN** each account's movements receive a strictly increasing ``orden_extracto`` sequence ordered by ``fecha_movimiento`` with same-date order matching the currently shipped chronological reconstruction

### Requirement: Period summary uses chronological position

The system SHALL determine period boundaries and movement ordering for the period-summary endpoint using ``orden_extracto`` instead of ``id`` or ``created_at``, without changing the public response shape.

#### Scenario: Same-day movement before closing nómina

- **WHEN** a movement shares the same date as the closing nómina but is chronologically before it (lower ``orden_extracto``)
- **THEN** the movement is included in the period
- **AND** it is the source of ``remaining_balance``
- **AND** ``period_end`` equals the closing nómina's date

#### Scenario: Boundary detection

- **WHEN** the period-summary endpoint runs for an account whose movements have ``orden_extracto`` populated
- **THEN** the closing nómina is detected using chronological position after ``start_date``
- **AND** the returned response shape is unchanged from EC-006