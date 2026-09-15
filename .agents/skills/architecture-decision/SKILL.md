---
name: architecture-decision
description: Decide whether a project change requires an Architecture Decision Record and create a proposed ADR when a new material architectural choice, constraint, trade-off, dependency, boundary, persistence strategy, or transaction strategy must be recorded. Use during planning before implementation; do not create ADRs for routine implementation or for applying an existing documented decision.
---

# Architecture Decision

Evaluate architectural significance before creating an ADR.

## Workflow

1. Read `AGENTS.md`.
2. Read the relevant sections of `docs/ARCHITECTURE.md`.
3. Read only ADRs related to the proposed decision.
4. Read the current change proposal and `design.md` when present.
5. Decide whether a new ADR is required using the criteria below.
6. If no ADR is required, return `ADR_NOT_REQUIRED` with a short reason and stop.
7. If an ADR is required, inspect existing files under `docs/decisions/` to match the repository convention and choose the next available numeric prefix.
8. If the repository has no established ADR format, read [references/adr-template.md](references/adr-template.md) and use that structure.
9. Create one proposed ADR for one coherent decision.
10. Return the ADR path and the decision summary to the planning workflow.

Do not modify production code.

## When an ADR is required

Create an ADR when a new decision:

- materially constrains future implementation;
- changes an architectural boundary or dependency direction;
- introduces a new framework, infrastructure component, or major dependency;
- changes persistence or transaction strategy;
- establishes a reusable cross-feature pattern;
- replaces or supersedes an existing architectural decision;
- has meaningful alternatives and trade-offs future contributors would otherwise need to rediscover.

## When an ADR is not required

Do not create an ADR for:

- applying a rule already documented in `docs/ARCHITECTURE.md`;
- applying an existing ADR;
- routine endpoint, schema, model, service, or test implementation;
- naming a use case because the architecture already requires use cases for multi-aggregate orchestration;
- product requirements with no new architectural consequence;
- trivial refactors with no lasting architectural constraint.

## Decision quality

An ADR must explain:

- the context and forces that make the decision necessary;
- the chosen decision;
- meaningful alternatives considered;
- consequences and trade-offs;
- related OpenSpec change or work item when known.

Keep the ADR focused on the decision. Do not duplicate full specifications, task lists, or implementation code.

## Existing decisions

Never silently rewrite an accepted ADR to change history.

If a new decision supersedes an old one, create a new ADR and record the relationship according to the repository's existing convention.

## Human gate

Create new ADRs with a proposed/unaccepted status when the repository convention supports status.

The human approves the architecture decision together with the rest of the change plan. This skill must not mark the ADR accepted on its own.
