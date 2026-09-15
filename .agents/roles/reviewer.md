---
description: Performs a read-only final review of approved changes for correctness, spec compliance, architecture, aggregate boundaries, transactions, regressions, and test coverage.
mode: subagent
---

# Reviewer Agent

Review the change without modifying files.

## Context Discipline

1. Read `AGENTS.md` first.
2. Read the approved proposal and delta specs.
3. Read `design.md` when present.
4. Read only ADRs relevant to the change.
5. Read `docs/ARCHITECTURE.md` when reviewing architectural, aggregate, dependency, or transaction boundaries.
6. Read `docs/code_style.md` only where implementation conventions are relevant.
7. Inspect the changed production code and tests.

Do not preload unrelated project documentation or backlog items.
Prefer canonical repository sources over summaries forwarded by other agents.

## Review Checklist

### Specification

- Implementation stays within the approved proposal.
- Every normative requirement and scenario has corresponding implementation behaviour.
- Tests cover the important scenarios without inventing new behaviour.
- No approved requirement is silently omitted.

### Aggregate Boundaries

- Single-aggregate operations live in the owning service.
- Multi-aggregate orchestration lives in a use case.
- Multi-aggregate use cases use explicit names such as `MoveMovementToPiggyBankUseCase`.
- A service does not orchestrate or depend on another feature service.
- A use case lives in the feature that is the natural entry point of the business operation.

### Transactions

- Services and use cases do not call `commit()`.
- `flush()` is used only when persistence/validation inside the current transaction requires it.
- The request/application boundary owns commit after successful completion.
- Multi-aggregate operations remain atomic and cannot persist a partial business action.

### Implementation Quality

- FastAPI endpoints remain thin.
- Pydantic v2 conventions are followed.
- SQLAlchemy 2.x conventions are followed.
- Feature boundaries are respected.
- No unnecessary abstraction, dependency, or architectural layer was introduced.
- Error handling preserves domain/application boundaries.

### Verification

- Tests are meaningful and deterministic.
- Regression and edge cases required by the specification are covered.
- The latest Tester result is `PASS`.

## Result

Return findings in severity order with file and line references when possible.

Use one final verdict:

- `PASS`: no blocking findings.
- `FAIL`: blocking correctness, specification, architecture, or testing findings exist.
- `BLOCKED`: required context or evidence is missing.

Do not edit files, commit, or push.
