<!-- docs-map: System architecture, aggregate boundaries, dependencies, transaction ownership, and design constraints. -->

# Architecture

## Overview

El Contable is a FastAPI application for personal accounting and financial management.

The application follows a feature-based modular architecture.
Business functionality should be grouped by domain feature rather than by technical layer whenever possible.

## Project Structure

```text
src/el_contable/
├── main.py
├── database.py
├── features/
│   └── movements/
└── templates/
    └── plantilla_movimientos.xlsx
```

## Application Entry Point

`main.py`: `main.py` is responsible for application composition.

Its responsibilities include:

- creating and configuring the FastAPI application;
- registering feature routers;
- configuring application-level dependencies;
- configuring application lifecycle behaviour.

> Business logic should not be implemented directly in `main.py`.

## Database Infrastructure

`database.py`: contains shared database infrastructure.

Its responsibilities may include:

- SQLAlchemy engine configuration;
- session management;
- shared database dependencies.

> Feature-specific persistence logic should remain inside the corresponding feature whenever possible.

## Feature Architecture

Business capabilities are organized under:
`src/el_contable/features/`

Each business domain should normally have its own directory:

```text
features/
└── <feature>/
    ├── router.py
    ├── schemas.py
    ├── models.py
    ├── service.py
    └── use_case.py      # Optional: only when multi-aggregate orchestration is required
```

A feature may contain its own:

- API endpoints;
- schemas;
- application logic;
- business logic;
- persistence logic;
- domain models;
- use cases;
- tests.

> The exact internal structure of a feature may evolve as complexity grows.
> Avoid introducing abstraction layers before they provide a clear benefit.

## Services & Use Cases

Application logic is divided between **services** and **use cases** according to the aggregate boundaries involved in a business operation.

### Services

A service contains reusable operations that belong to a **single aggregate**.

Examples include:

- creating an account;
- adjusting an account balance;
- creating or updating a movement;
- creating a piggy bank;
- adjusting a piggy-bank balance.

Services live inside their owning feature:

```text
features/
└── accounts/
    └── service.py
```

A service:

- operates within one aggregate boundary;
- owns application operations for that aggregate;
- may read or modify entities owned by its feature;
- may use `flush()` when persistence or validation inside the current transaction requires it;
- must not call `commit()`;
- must not orchestrate services from other features.

> A service MUST NOT import another feature's service to coordinate a business operation.

Do not create one service file or class per method. Keep cohesive single-aggregate operations together in the owning feature's `service.py` unless complexity clearly justifies another documented structure.

### Use Cases

A use case represents a complete business operation that coordinates **multiple aggregates**.

Examples include:

- moving a movement to a piggy bank;
- moving money between an account and a piggy bank;
- transferring money between accounts;
- any operation that must update multiple aggregates as one business action.

A use case owns orchestration while each aggregate service remains responsible for its own operations.

For example:

```text
MoveMovementToPiggyBankUseCase
```

may coordinate:

```text
MovementService
        +
PiggyBankService
        +
AccountService
```

without those services depending directly on each other.

The dependency direction is:

```text
Router
  ↓
Use Case
  ↓
Aggregate Services
  ↓
Persistence
```

For single-aggregate operations, the shorter path is valid:

```text
Router
  ↓
Service
  ↓
Persistence
```

The following dependency is forbidden for cross-aggregate orchestration:

```text
Service
  ↓
Another Feature Service
```

### Use Case Location

A use case should live in the feature that represents the **natural entry point** of the business operation.

For example, an operation initiated by moving a movement to a piggy bank belongs to the movements feature:

```text
features/
└── movements/
    ├── router.py
    ├── schemas.py
    ├── models.py
    ├── service.py
    └── use_case.py
```

with a named application class such as:

```text
MoveMovementToPiggyBankUseCase
```

Keep `use_case.py` while the number and complexity of use cases remain small.
If the feature grows enough to require a `use_cases/` package, treat that restructuring as an architectural evolution rather than creating it preemptively.

### Transaction Ownership

Services and use cases participate in the transaction associated with the request/application boundary.

- Services may call `flush()` when required.
- Use cases may coordinate multiple service operations using the same session/transaction.
- Services and use cases must not call `commit()`.
- The FastAPI request/application boundary commits only after the complete operation succeeds.
- A failed multi-aggregate operation must not leave a partially persisted business action.

Multi-aggregate operations that represent one business action must be atomic whenever the domain requires all affected state changes to succeed or fail together.

## Request Flow

The expected application flow is:

```text
HTTP Request
    ↓
FastAPI endpoint
    ↓
Single aggregate? ── yes ──→ Service ──────────┐
    │                                          │
    no                                         ↓
    ↓                                      Persistence
Use Case                                       │
    ↓                                          ↓
Aggregate Services                         PostgreSQL
    ↓
Persistence
    ↓
PostgreSQL
```

HTTP-specific concerns should stay at the API boundary.
Business logic should not depend directly on FastAPI request objects.

## Dependency Injection

Use FastAPI's `Depends` mechanism for dependency injection.
Dependencies may provide components such as:

- database sessions;
- services;
- use cases;
- repositories when explicitly introduced by an approved architectural decision;
- authentication dependencies;
- request-scoped infrastructure.

> Dependency injection should allow business logic to be tested independently from FastAPI whenever practical.

## Persistence

PostgreSQL is the primary persistent data store.
SQLAlchemy is used for database access.
Feature-specific queries and persistence rules should remain owned by the corresponding feature rather than accumulating in shared database infrastructure.

## Feature Boundaries

Features should remain loosely coupled.
A feature should not depend directly on the internal implementation of another feature.

When functionality must be shared:

- determine whether it represents a genuine shared abstraction;
- expose the smallest practical interface;
- avoid circular dependencies;
- keep ownership clear.

Cross-feature business orchestration belongs in a use case rather than in a feature service.

> Cross-feature dependencies that materially change the architecture should be documented.

## Movement Uploads

Movement upload behaviour belongs to the movements feature.
Detailed expected behaviour is defined in:
`openspec/specs/upload_movements/spec.md`

Relevant architectural decisions are documented in:
`docs/decisions/001-movements-upload-strategy.md`

> Do not duplicate those details in this document.

## Architectural Decisions

Significant architectural decisions are stored as ADRs under:
`docs/decisions/`

Create an ADR when a decision:
Using the skill inside `.agents/skills/architecture-decision` folder, you can create an ADR when a decision:

- materially constrains future implementation;
- involves meaningful alternatives or trade-offs;
- affects multiple parts of the system;
- would otherwise require future contributors to rediscover why the decision was made.

> `ARCHITECTURE.md` describes the current architecture.
> ADRs explain why important architectural choices were made.

## Architectural Principles

- Organize business functionality by feature.
- Keep business logic independent of the HTTP layer.
- Prefer explicit dependencies.
- Keep feature boundaries clear.
- Use services for single-aggregate operations.
- Use named use cases for multi-aggregate orchestration.
- Services must not orchestrate or depend on services from other features.
- Keep transaction ownership explicit and commits outside services/use cases.
- Preserve atomicity for multi-aggregate business operations when required by the domain.
- Avoid premature abstractions.
- Keep shared infrastructure minimal.
- Keep feature-specific persistence close to its feature.
- Document significant architectural decisions.
- Keep detailed feature behaviour in OpenSpec.
- Avoid duplicating documentation across sources of truth.
