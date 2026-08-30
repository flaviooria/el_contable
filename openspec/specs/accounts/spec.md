# accounts Specification

## Purpose

Provide account management for users, allowing a single account to hold all movements and support multiple PiggyBanks (sub-accounts) for money allocation.

## Requirements

### Requirement: Account structure

Each user has exactly one account. The account stores the base balance and entry date.

#### Scenario: Account creation

- GIVEN no account exists for the user
- WHEN an account is created
- THEN store the initial ``base_balance`` and ``entry_date``
- AND generate a UUID identifier

### Requirement: PiggyBank creation

A PiggyBank is a sub-account linked to an account, used to reserve money for specific purposes (savings, leisure, etc.).

#### Scenario: Create PiggyBank

- GIVEN an account exists
- WHEN a PiggyBank is created with a ``name`` and optional ``max_balance``
- THEN generate a UUID for the PiggyBank
- AND associate it with the account via ``account_id``
- AND ``name`` + ``account_id`` must be unique together

#### Scenario: PiggyBank balance

- GIVEN a PiggyBank exists
- WHEN its balance is queried
- THEN calculate it as the sum of all ``importe`` values of movements linked to that PiggyBank
- AND return ``max_balance`` for informational purposes only (no validation or enforcement)

### Requirement: Movement assignment

All movements belong to an account. A movement may optionally be linked to a PiggyBank.

#### Scenario: Assign movement to PiggyBank

- GIVEN a movement exists in an account
- AND a PiggyBank exists in the same account
- WHEN the movement is associated with the PiggyBank
- THEN create a link in ``movements_piggy_banks`` junction table
- AND the movement's ``importe`` contributes to the PiggyBank's calculated balance

#### Scenario: Movement without PiggyBank

- GIVEN a movement belongs to an account
- WHEN it is not linked to any PiggyBank
- THEN it appears only in the account-level movement list
- AND does not contribute to any PiggyBank balance

### Requirement: CRUD operations

The system SHALL expose endpoints to:

- Create an account
- Get account details and balance
- Create, list, update, and delete PiggyBanks within an account

#### Scenario: List PiggyBanks

- GIVEN an account exists
- WHEN the user requests PiggyBanks for that account
- THEN return all PiggyBanks with their calculated balances
- AND include ``max_balance`` if it was set
