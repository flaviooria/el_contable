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
`main.py`: main.py is responsible for application composition.

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
```
A feature may contain its own:

- API endpoints;
- schemas;
- application logic;
- business logic;
- persistence logic;
- domain models;
- tests.

> The exact internal structure of a feature may evolve as complexity grows.
Avoid introducing abstraction layers before they provide a clear benefit.

## Request Flow

The expected application flow is:
```text
HTTP Request
    ↓
FastAPI endpoint
    ↓
Application / business logic
    ↓
Persistence layer
    ↓
PostgreSQL
```
HTTP-specific concerns should stay at the API boundary.
Business logic should not depend directly on FastAPI request objects.

## Dependency Injection
Use FastAPI's `Depends` mechanism for dependency injection.
Dependencies may provide components such as:

- database sessions;
- repositories;
- application services;
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

- materially constrains future implementation;
- it involves meaningful alternatives or trade-offs;
- it affects multiple parts of the system;
- it would otherwise require future contributors to rediscover why the decision was made.

> `ARCHITECTURE.md `describes the current architecture.
ADRs explain why important architectural choices were made.

## Architectural Principles

- Organize business functionality by feature.
- Keep business logic independent of the HTTP layer.
- Prefer explicit dependencies.
- Keep feature boundaries clear.
- Avoid premature abstractions.
- Keep shared infrastructure minimal.
- Keep feature-specific persistence close to its feature.
- Document significant architectural decisions.
- Keep detailed feature behaviour in OpenSpec.
- Avoid duplicating documentation across sources of truth.