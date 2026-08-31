# movements Delta

## ADDED Requirements

### Requirement: Movement totals by type
The system SHALL return the accumulated sum of movement amounts grouped by type for a specific account.

#### Scenario: Account with income and expense movements
- **WHEN** the user requests totals for an account that has both income and expense movements
- **THEN** return the sum of `importe` for each type (`ingreso` and `gasto`) separately, along with the count of movements per type

#### Scenario: Account with no movements
- **WHEN** the user requests totals for an account with no movements
- **THEN** return zero totals for both types with zero counts

#### Scenario: Non-existent account
- **WHEN** the user requests totals for an account ID that does not exist
- **THEN** return HTTP 404 with message "Account not found"

#### Scenario: Account ID missing
- **WHEN** the user requests totals without providing an `account_id`
- **THEN** return HTTP 422 with validation error
