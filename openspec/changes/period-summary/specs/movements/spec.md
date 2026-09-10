# movements Delta

## ADDED Requirements

### Requirement: Period summary
The system MUST return accumulated income and expenses for a user-defined pay period.

#### Scenario: Period with both income and expense movements
- **WHEN** the user requests a period summary with a valid account_id and start_date, and movements exist within the period
- **THEN** return income_total (sum of ingreso movements excluding the salary that starts the period), expense_total (sum of gasto movements), remaining_balance (last `disponible` value), income_count, and expense_count

#### Scenario: Period with no movements
- **WHEN** the user requests a period summary for a date range with no movements
- **THEN** return zero totals for income and expenses, zero counts, and remaining_balance of 0.0

#### Scenario: Open-ended period (no next nómina)
- **WHEN** the user requests a period summary and no subsequent movement contains "nomina" in its normalized concepto after start_date
- **THEN** the period remains open-ended (up to the last movement) and period_end is null

#### Scenario: Period bounded by next nómina
- **WHEN** the user requests a period summary and a subsequent movement contains "nomina" in its normalized concepto after start_date
- **THEN** the period ends the day before that nómina movement (exclusive end) and period_end is set to that date

#### Scenario: Nómina without accent mark
- **WHEN** a movement's concepto contains "nomina" without the accent mark (e.g., bank CSV/Excel exports)
- **THEN** it is still recognized as the salary movement closing the period

#### Scenario: Non-existent account
- **WHEN** the user requests a period summary for an account ID that does not exist
- **THEN** return HTTP 404 with message "Account not found"

#### Scenario: Missing account_id
- **WHEN** the user requests a period summary without providing an account_id
- **THEN** return HTTP 422 with validation error

#### Scenario: Missing start_date
- **WHEN** the user requests a period summary without providing a start_date
- **THEN** return HTTP 422 with validation error
