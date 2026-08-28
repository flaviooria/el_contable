# Proposal: Movement Upload

## Intent

Let the user upload `.xlsx`/`.csv` files with financial transactions, validate them against previously stored data to avoid duplicates, and store them temporarily for later processing.

## Scope

In scope:
- Upload endpoint accepting `.xlsx` and `.csv`
- Parse fields: `Fecha`, `Concepto`, `Movimiento`, `Importe`, `Disponible`
- Duplicate detection based on the remaining amount (`Disponible`) strategy
- Import cutoff based on the last upload date
- Temporary storage with expiration for privacy compliance
- Official Excel template endpoint as the single source of truth

Out of scope:
- Dashboards and charts
- Fixed/variable expense classification
- Virtual piggy banks

## Approach

Use Polars for parsing. Validate that the file `Disponible` matches the stored balance; when it differs, cross-check and import only the missing movements. Compare with the last upload date to decide the import starting point.
