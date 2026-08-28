# 001 - Movements Upload Strategy

## Context

We needed to define the strategy for uploading financial movements from Excel/CSV files. The system must:

1. Accept `.xlsx` and `.csv` files with specific columns: `Fecha`, `Concepto`, `Movimiento`, `Importe`, `Disponible`
2. Validate movements against existing data to avoid duplicates
3. Use the `Disponible` (remaining balance) as the primary validation mechanism
4. Store movements temporarily for privacy compliance
5. Provide an official template as the single source of truth

## Decision

We will implement:

1. **Vertical slicing architecture** - Group code by feature (`features/movements/`) rather than by layer
2. **Polars for parsing** - Efficient Excel/CSV parsing
3. **Deduplication strategy - Unique key**:
   - Deduplicate by composite key ``(fecha_movimiento, importe, disponible)``
   - Within the same file: keep first occurrence of each unique key
   - Against the database: skip rows whose unique key already exists
   - Insert all rows in ascending order by ``fecha_movimiento``
4. **FastAPI Dependency Injection** - Use native DI via `Depends()` for service injection
5. **Official template** - Single Excel template with required columns

## Resolution

The implementation provides:

- **Template endpoint** (`GET /api/v1/movements/template`) - Downloads official template
- **Upload endpoint** (`POST /api/v1/movements/upload`) - Processes and imports movements
- **Validation logic** - Detects duplicates via `Disponible` comparison
- **Temporary storage** - With expiration for privacy compliance

## Why

### Vertical Slicing vs Layered Architecture

**Vertical slicing** keeps all code related to a feature together (router, service, parser, models, schemas), making it:
- Easier to understand the complete feature in one place
- Simpler to modify and test
- More scalable as each feature can evolve independently

### Polars vs Pandas

Polars is:
- Faster for large Excel files
- Written in Rust, more memory efficient
- Has better support for lazy evaluation
- Native to the Python ecosystem

### Dependency Injection with FastAPI

FastAPI's native DI:
- Makes services easily mockable for testing
- Clear dependency graph
- Automatic garbage collection of dependencies
- Standard Python pattern

### Unique Key Deduplication

Using ``(fecha_movimiento, importe, disponible)`` as the deduplication key:
- Rows are uniquely identified by their date, amount, and resulting balance
- Concept is excluded because users may enter it slightly differently across uploads
- Directly catches duplicates even when concepts differ slightly
- ``Disponible`` is included because a row with the same date and amount but different balance represents a different economic event

## Related Decisions

- (future) 002 - Authentication strategy
- (future) 003 - Balance calculation strategy

## Status

Accepted - 2026-08-24
