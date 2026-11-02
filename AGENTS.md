# El Contable
Web application for personal accounting and financial management.

## Commands
- `make dev` — Start the FastAPI development server.
- `make checks` — Run the complete validation suite: lint, formatting, type checking, and tests.
- `make db-up` / `make db-down` — Start/stop the PostgreSQL container.
- `make migrate` — Apply database migrations (Alembic `upgrade head`).
- `make revision m="message"` — Generate a new migration (Alembic autogenerate).
- All tasks are also available via mise: `mise run <task>` (e.g. `mise run checks`).

## Project
- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL
- uv
- Feature-based modular architecture
- Source root: `src/el_contable`

## Architecture
Business functionality is organized by feature under:
`src/el_contable/features/`

Each feature should own its HTTP layer, application/business logic, and persistence concerns whenever possible.
Use FastAPI dependency injection through `Depends` to keep components decoupled and testable.
For architectural rules and module boundaries, read `docs/ARCHITECTURE.md`.

## 👤 Human-in-the-Loop

Work autonomously when the requested change is local, reversible, and consistent
with existing specifications, architecture, and project conventions.

Human approval is required before:

- changing an established architectural decision;
- introducing a new dependency;
- introducing a new framework, architectural pattern, or infrastructure component;
- changing database schema or migration strategy;
- modifying authentication, authorization, security, or privacy behaviour;
- changing externally observable business rules not covered by an existing specification;
- deleting persisted data or introducing destructive operations;
- making a breaking API change;
- resolving ambiguity that materially affects product behaviour.

## 📋 Work Management

`BACKLOG.md` is the source of truth for project work and orchestration state.

- The Leader owns work-item lifecycle transitions.
- Backend, Tester, and Reviewer must not mutate work-item state.
- Use the `work-intake` skill to select, validate, and update work items.
- A work item must reach `awaiting-approval` before implementation.
- Implementation requires explicit human approval.
- Record generated OpenSpec artifacts and ADRs as paths in the corresponding work item.
- Record the final commit before marking work as `done`.

Expected lifecycle:

`pending → planning → awaiting-approval → approved → implementing → testing → reviewing → ready-to-commit → done`

## Documentation Rules
Do not load all project documentation by default.
Use progressive disclosure:

1. Read this file first.
2. Identify the type of task.
3. Read only the documentation relevant to that task.
4. Inspect implementation details only when required.

### Context Efficiency

Minimize context loading.

- Do not preload project documentation.
- Read only the files required for the current responsibility.
- Prefer canonical sources over summaries copied into prompts or other documents.
- Do not load `openspec/changes/` globally. Active change artifacts are discovered through the selected `BACKLOG.md` work item.
- Do not read unrelated ADRs, specifications, or feature documentation.
- When a deterministic script can answer a structural question, prefer running the script instead of loading the entire source document into context.

When creating, deleting, moving, or renaming documentation under `docs/` or `openspec/specs/`, regenerate the Documentation Map with the `documentation-map` skill.
Do not manually edit the generated section between `DOCS_MAP_START` and `DOCS_MAP_END`.

## Documentation Map
<!-- DOCS_MAP_START -->
```text
docs/
├── ARCHITECTURE.md
│   # System architecture, aggregate boundaries, dependencies, transaction ownership, and design constraints.
├── code_style.md
├── FUNCTIONAL.md
├── runbook_tecnico.md
│   # Runbook del despliegue continuo a VPS: credenciales, pasos por entorno y diagnóstico de fallos.
└── decisions/
    ├── 001-movements-upload-strategy.md
    ├── 002-account-balance.md
    ├── 003-account-and-piggy-bank-model.md
    ├── 004-shared-declarative-base.md
    ├── 005-period-summary.md
    └── 006-movements-uuid-primary-key.md

openspec/
└── specs/
    ├── account_balance/
    │   └── spec.md
    ├── accounts/
    │   └── spec.md
    └── upload_movements/
        └── spec.md
```
<!-- DOCS_MAP_END -->

## Documentation Routing
- Current work item and orchestration state → `BACKLOG.md` through the `work-intake` skill
- Active change artifacts → paths recorded in the selected `BACKLOG.md` work item
- Business rules or expected behaviour → `docs/FUNCTIONAL.md`
- Architecture, module boundaries, or dependencies → `docs/ARCHITECTURE.md`
- Writing or modifying Python code → `docs/code_style.md`
- Movement uploads → `openspec/specs/upload_movements/spec.md`
- Understanding an architectural decision → relevant file under `docs/decisions/`

## Development Rules
- Prefer implementing business functionality inside the corresponding feature under `src/el_contable/features/`.
- Keep `main.py` focused on application composition and startup.
- Keep generic database infrastructure separate from feature-specific persistence logic.
- Do not introduce cross-feature dependencies without checking `docs/ARCHITECTURE.md`.
- Do not change an established architectural decision without reviewing the relevant ADR.
- Follow `docs/code_style.md` when modifying Python code.
- Run `make checks` after code changes.

## Sources of Truth
Use the following hierarchy:

1. Product behaviour → `docs/FUNCTIONAL.md`
2. System organization → `docs/ARCHITECTURE.md`
3. Feature contracts → `openspec/specs/`
4. Architectural rationale → `docs/decisions/`

Avoid duplicating the same rule across multiple documentation files.
