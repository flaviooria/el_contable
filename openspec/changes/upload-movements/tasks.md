# Tasks

## 1. Model
- [ ] 1.1 Define `Movement` SQLAlchemy model with fields: `fecha_movimiento`, `concepto`, `importe`, `tipo`, `disponible`, `created_at`, `expires_at`

## 2. Schemas
- [ ] 2.1 Define Pydantic schemas for requests and responses
- [ ] 2.2 Define `MovementRow` with validation flags

## 3. Parser
- [ ] 3.1 Parse `.xlsx` and `.csv` with Polars
- [ ] 3.2 Validate required columns
- [ ] 3.3 Handle missing/invalid `Fecha` as invalid rows
- [ ] 3.4 Combine `Concepto` and `Movimiento` into a single concept
- [ ] 3.5 Derive movement type from `Importe` sign

## 4. Validator
- [ ] 4.1 Compare file `Disponible` with last stored balance
- [ ] 4.2 Filter movements by last upload date when balances differ

## 5. Service
- [ ] 5.1 Orchestrate parser, validator, and persistence
- [ ] 5.2 Insert non-duplicate movements with expiration date
- [ ] 5.3 Return insert/skip counts and final balance

## 6. Router
- [ ] 6.1 `GET /api/v1/movements/template` endpoint
- [ ] 6.2 `POST /api/v1/movements/upload` endpoint with DI

## 7. Template
- [ ] 7.1 Create official Excel template with required columns
