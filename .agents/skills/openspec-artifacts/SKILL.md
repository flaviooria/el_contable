---
name: openspec-artifacts
description: Manually create, update, and structurally validate OpenSpec-style change artifacts without requiring the OpenSpec CLI or library. Use when planning a change under openspec/changes/ and the project needs proposal.md, delta specs, optional design.md, and tasks.md authored directly from existing specs, architecture, ADRs, and functional requirements.
---

# OpenSpec Artifacts

Author OpenSpec-style planning artifacts directly in the repository. Do not call or require the `openspec` CLI, package, library, or generated instructions.

## Workflow

1. Read `AGENTS.md` and follow its progressive-disclosure routing.
2. Read only the affected canonical specs under `openspec/specs/` plus relevant functional, architecture, and ADR documents.
3. Choose or reuse a concise kebab-case change ID.
4. Create `openspec/changes/<change-id>/` when it does not exist.
5. Write artifacts in this order:
   1. `proposal.md`;
   2. delta specs under `specs/<capability>/spec.md`;
   3. `design.md` only when architectural reasoning is required;
   4. `tasks.md` last.
6. Read `references/templates.md` for the required artifact shapes.
7. Run `scripts/validate_change.py openspec/changes/<change-id>` when shell execution is available.
8. Fix structural validation errors before returning control to the calling workflow.

## Proposal rules

Keep `proposal.md` short and reviewable. State:

- why the change is needed;
- what behaviour or capability changes;
- what is explicitly out of scope;
- affected capabilities and architectural areas;
- risks or decisions requiring human attention.

Do not turn the proposal into an implementation plan.

## Delta spec rules

Write behavioural contracts rather than Python implementation details.

Use only the relevant operation sections:

- `## ADDED Requirements`
- `## MODIFIED Requirements`
- `## REMOVED Requirements`
- `## RENAMED Requirements`

For a modified requirement, include the complete resulting requirement rather than a partial textual patch.

Use normative `MUST` or `SHALL` language for requirements.

Every added or modified requirement must contain at least one scenario with this structure:

```markdown
#### Scenario: Descriptive scenario name
- **WHEN** a concrete condition or action occurs
- **THEN** the observable expected result
```

Add additional `AND` clauses only when they improve precision.

Reuse the same capability path that exists under `openspec/specs/` whenever the change affects an existing capability.

## Design rules

Create `design.md` when the change affects architecture, including any of these conditions:

- database schema or migrations;
- multiple aggregates;
- cross-feature dependencies;
- transaction boundaries;
- new dependencies or infrastructure;
- authentication, authorization, security, or privacy;
- a technical choice with meaningful alternatives or trade-offs.

For multi-aggregate operations, explicitly document:

- involved aggregates;
- the natural entry-point feature;
- the named use case that coordinates the operation;
- participating services;
- transaction and rollback expectations;
- why orchestration does not belong inside a service.

Do not duplicate stable architectural rules already defined in `docs/ARCHITECTURE.md`; reference them and document only change-specific decisions.

## Task rules

Write `tasks.md` only after proposal, specs, and any required design are settled.

Use ordered, checkable Markdown tasks:

```markdown
- [ ] 1.1 Concrete implementation task
- [ ] 1.2 Concrete verification task
```

Tasks must be traceable to the approved spec/design and include required tests and quality validation. Do not add speculative scope.

For multi-aggregate changes include tasks for use-case orchestration, aggregate-specific service work where needed, atomicity/rollback behaviour, and specification-driven tests.

## Boundaries

- Never modify production application code.
- Never invent a new capability when the correct existing capability should be changed.
- Never rely on an OpenSpec executable being installed.
- Never mark planning as approved; approval belongs to the human gate in the caller workflow.
