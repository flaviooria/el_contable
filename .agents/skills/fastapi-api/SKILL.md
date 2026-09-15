---
name: fastapi-api
description: Implement approved FastAPI backend changes using the project's feature-based architecture, Pydantic v2, SQLAlchemy 2.x, dependency injection, and transaction conventions. Use for API endpoints, feature scaffolding, schemas, models, services, and multi-aggregate use cases after an OpenSpec change has received human approval.
---

# FastAPI API

Implement only approved backend scope and preserve the project's architectural boundaries.

## Required context

1. Read `AGENTS.md`.
2. Read the approved OpenSpec change.
3. Read `docs/ARCHITECTURE.md`.
4. Read `docs/code_style.md`.
5. Read only directly relevant specs and ADRs.

## Decide service vs use case first

Before writing application logic, count the aggregates involved in the business operation.

### One aggregate

Use the owning feature's `service.py`.

Keep reusable single-aggregate operations in that service. Do not create one file per service method.

### Multiple aggregates

Use the natural entry feature's `use_case.py` and create a named use-case class.

Example:

```text
MoveMovementToPiggyBankUseCase
```

A use case may coordinate services such as:

```text
MovementService
PiggyBankService
AccountService
```

Enforce these invariants:

- a service must not orchestrate another feature service;
- a service must not own a cross-aggregate workflow;
- the use case owns orchestration, not low-level persistence details;
- services and use cases must not commit;
- multi-aggregate changes must participate in one atomic transaction when the business action requires atomicity.

Do not create a `use_cases/` package merely because one use case exists. Keep `use_case.py` until the feature's complexity justifies a structural change already allowed by the architecture or an approved decision.

## Feature scaffold

For a new feature, or when required modules are missing, use the bundled scaffold script rather than inventing a new layout:

```bash
uv run python .agents/skills/fastapi-api/scripts/scaffold_feature.py <feature-name>
```

For a feature that needs multi-aggregate orchestration:

```bash
uv run python .agents/skills/fastapi-api/scripts/scaffold_feature.py <feature-name> --with-use-case
```

The script never overwrites existing files. Inspect the result before implementation.

Do not scaffold unrelated modules for an existing feature.

## FastAPI boundaries

- Keep routers focused on HTTP parsing, dependency orchestration, response construction, and the request-level commit.
- Keep business logic outside route handlers.
- Use FastAPI `Depends` for dependencies.
- Use Pydantic models for request and response schemas.
- Keep FastAPI-specific exceptions out of domain/business logic when practical.

## Persistence

- Use SQLAlchemy 2.x APIs only.
- Use `Mapped[...]` and `mapped_column()` for declarative mappings.
- Use `select()`, `insert()`, `update()`, and `delete()` rather than legacy `Query` APIs.
- Keep persistence operations in the feature that owns the data.
- Allow services/use cases to call `flush()` when required.
- Never call `commit()` from a service or use case.
- Commit only at the request/application boundary after successful completion.

## Schemas

Use Pydantic v2 conventions only, including `model_validate()`, `model_dump()`, `ConfigDict`, `field_validator`, and `model_validator` when appropriate.

Do not introduce Pydantic v1 compatibility patterns.

## Scope control

Do not:

- introduce a new dependency without approved scope;
- replace established project tooling;
- introduce repositories, ports/adapters, CQRS, event buses, or other architectural layers unless explicitly approved;
- modify product behaviour beyond the delta specs;
- commit or push.

If implementation reveals a material decision not covered by the approved change, stop and return it as a blocker.
