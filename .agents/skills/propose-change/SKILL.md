---
name: propose-change
description: Create or update a reviewable OpenSpec-style change plan before implementation. Use for feature requests, API changes, business-rule changes, schema-affecting work, or any implementation request that needs proposal.md, delta specs, optional design.md, optional ADRs, and tasks.md followed by an explicit human approval gate. Never implement application code.
---

# Propose Change

Create the complete reviewable change plan and stop before implementation.

## Workflow

1. Read `AGENTS.md` first and follow its documentation routing rules.
2. Identify the affected capability or capabilities from `openspec/specs/`.
3. Read only relevant functional requirements, architecture sections, specs, and ADRs.
4. Choose a concise kebab-case change ID that describes the requested outcome.
5. Load the `openspec-artifacts` skill.
6. Use it to manually create or update:
   - `openspec/changes/<change-id>/proposal.md`;
   - delta specs under `openspec/changes/<change-id>/specs/<capability>/spec.md`;
   - `design.md` when the change meets the design conditions below;
   - `tasks.md` after specs/design are settled.
7. Decide whether the change introduces a new material architecture decision.
8. If it does, load the `architecture-decision` skill and create a proposed ADR. If it only applies an existing architecture rule, do not create an ADR.
9. Validate the manual OpenSpec artifacts using the validator provided by `openspec-artifacts` when shell execution is available.
10. Return a concise planning summary and mark the state as `AWAITING_HUMAN_APPROVAL`.
11. Stop. Do not modify application code.

Do not require or invoke the OpenSpec CLI or library.

## Design conditions

Create `design.md` when any of the following is true:

- the database schema or migration changes;
- the change coordinates multiple aggregates;
- the change introduces or modifies cross-feature dependencies;
- the change changes transaction boundaries;
- a new dependency or infrastructure component is proposed;
- authentication, authorization, security, or privacy behaviour changes;
- a material technical decision has alternatives or trade-offs that need review.

Do not create `design.md` for a straightforward implementation whose design is already fully determined by existing architecture and ADRs.

## ADR decision

Create an ADR only when the plan introduces a new architecture decision that materially constrains future implementation or records a meaningful trade-off.

Do not create an ADR for:

- applying an existing rule from `docs/ARCHITECTURE.md`;
- routine implementation details;
- behaviour already decided by an existing ADR;
- feature requirements that do not change architecture.

When unsure, let `architecture-decision` evaluate whether an ADR is required.

## Multi-aggregate planning

When the requested operation affects multiple aggregates:

- reflect observable behaviour and failure cases in the delta spec;
- describe orchestration in `design.md`;
- plan a named use case rather than placing orchestration in a service;
- include transaction atomicity and rollback-oriented tests in `tasks.md` when relevant.

Do not put implementation details such as Python class names into behavioural requirements unless they are externally observable. Put those details in `design.md` and tasks.

## Human gate

Never proceed from planning to implementation inside this skill.

The plan must be reviewed by the human. Return:

- change ID;
- affected capabilities;
- whether `design.md` was required;
- ADR path or `none`;
- important architectural decisions;
- unresolved questions, if any;
- manual validation result;
- status: `AWAITING_HUMAN_APPROVAL`.

Do not interpret silence as approval. Approval must be explicit.
