# upload_movements Specification

## Purpose

Enable the user to upload Excel/CSV files containing financial transactions, validate them against existing transactions using
a unique key strategy, and store them for subsequent processing.

## Requirements

### Requirement: Valid file types

The system SHALL only accept files with `.xlsx` or `.csv` extension.

#### Scenario: Valid file extension

- GIVEN a user has selected a file
- WHEN the file has `.xlsx` or `.csv` extension
- THEN process the file with Polars

#### Scenario: Invalid file extension

- GIVEN a user has selected a file
- WHEN the file has an extension other than `.xlsx` or `.csv`
- THEN return HTTP 400 with message "Unsupported file type"

### Requirement: Field extraction

The system SHALL extract the following fields from each row in the file:

- `Fecha`: date of the movement (REQUIRED, invalid if missing) — parsed as a date-only value
- `Concepto`: payment type (e.g., "Transferencia", "Pago servicios")
- `Movimiento`: additional details (to whom, what it is) (OPTIONAL, can be empty)
- `Importe`: movement amount (positive = income, negative = expense/withdrawal)
- `Disponible`: remaining amount after the movement

#### Scenario: Combine Concepto and Movimiento

- GIVEN fields `Concepto` and `Movimiento` exist
- WHEN processing the movement
- THEN concatenate as `concept` = "Concepto - Movimiento"
- OR if `Movimiento` is empty: `concept` = "Concepto"
- AND use `Importe` to determine `type` (positive = "ingreso", negative = "gasto")

#### Scenario: Missing Fecha field

- GIVEN a row without `Fecha` or with empty `Fecha`
- WHEN processing the row
- THEN mark the movement as invalid
- AND skip it during import

### Requirement: Duplicate validation - Unique key strategy

The system SHALL deduplicate movements using the composite key `(movement_date, amount, available_balance)`.

#### Scenario: Within-file duplicate

- GIVEN a file contains two or more rows with identical `movement_date`, `amount`, and `available_balance`
- WHEN processing the file
- THEN keep only the first occurrence
- AND skip all subsequent duplicates

#### Scenario: Duplicate across uploads

- GIVEN a row already exists in the database with matching `movement_date`, `amount`, and `available_balance`
- WHEN a new file is uploaded containing that same row
- THEN skip that row
- AND do not insert a duplicate

#### Scenario: New unique row

- GIVEN a file contains a row whose composite key does not exist in the database
- WHEN processing the file
- THEN insert that row as a new movement

### Requirement: Ascending order by date

The system SHALL insert all movements in ascending order by `movement_date`, regardless of the order in which they appear in the uploaded file.

#### Scenario: File with unsorted dates

- GIVEN a file contains rows in a random date order
- WHEN processing the file
- THEN insert all rows sorted by `movement_date` ascending

### Requirement: Movement storage

The system SHALL store movements in the `movements` table.

#### Scenario: Insert valid movements

- GIVEN a file with valid and non-duplicate movements
- WHEN all validations pass
- THEN insert into `movements` table
- AND save fields: `id` (UUID), `account_id`, `movement_date`, `concept`, `amount`, `type`, `available_balance`, `created_at`, `order_statement`

#### Scenario: Movement identifiers are UUIDs

- GIVEN a movement has been inserted
- WHEN the movement is returned by an API response
- THEN its `id` is a UUID
- AND no `expires_at` field is present

### Requirement: Template endpoint

The system SHALL provide an official template as the single source of truth.

#### Scenario: Download template

- GIVEN a user requests the template
- WHEN calling `GET /api/v1/movements/template`
- THEN return Excel file with columns: `Fecha`, `Concepto`, `Movimiento`, `Importe`, `Disponible`

### Requirement: Upload endpoint

The system SHALL expose an endpoint to upload files.

#### Scenario: Successful upload

- GIVEN a valid file with movements
- WHEN calling `POST /api/v1/movements/upload`
- THEN parse, validate and insert movements
- AND return HTTP 201 with summary: `inserted_count`, `skipped_count`, `available_balance`

#### Scenario: Upload with errors

- GIVEN an invalid file or with parsing errors
- WHEN calling `POST /api/v1/movements/upload`
- THEN return HTTP 400 with error details
