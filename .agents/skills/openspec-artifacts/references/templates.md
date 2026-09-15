# OpenSpec Artifact Templates

Use these shapes as defaults. Adapt content to the actual change without adding empty sections.

## proposal.md

```markdown
# <Change title>

## Why
<Problem, need, or product outcome.>

## What Changes
- <Behaviour/capability change>
- <Behaviour/capability change>

## Out of Scope
- <Explicitly excluded work>

## Impact
- Capabilities: `<capability>`
- Architecture: <none or concise impact>
- Data/migrations: <none or concise impact>

## Risks / Decisions
- <Only material risks or decisions requiring review>
```

## Delta spec

```markdown
# <Capability> Delta

## ADDED Requirements

### Requirement: <Requirement name>
The system MUST <observable behaviour>.

#### Scenario: <Scenario name>
- **WHEN** <condition/action>
- **THEN** <observable result>
```

For changes to existing behaviour use `## MODIFIED Requirements` and restate the full resulting requirement and its scenarios.

## design.md

```markdown
# Design: <Change title>

## Context
<Only technical context needed to understand the decision.>

## Aggregate Boundaries
- Entry-point feature: `<feature>`
- Aggregates involved: `<aggregate-a>`, `<aggregate-b>`
- Orchestration: `<NamedUseCase>`
- Participating services: `<ServiceA>`, `<ServiceB>`

## Transaction Boundary
<Describe atomicity, flush/commit ownership, rollback expectations.>

## Decisions
### <Decision>
- Choice: <selected approach>
- Rationale: <why>
- Alternatives considered: <only meaningful alternatives>

## Risks
- <Technical risk and mitigation>
```

Omit `Aggregate Boundaries` when the change does not coordinate multiple aggregates.

## tasks.md

```markdown
# Tasks

## 1. Implementation
- [ ] 1.1 <Concrete task>
- [ ] 1.2 <Concrete task>

## 2. Tests
- [ ] 2.1 <Spec-driven test task>
- [ ] 2.2 <Failure/edge-case test task when relevant>

## 3. Validation
- [ ] 3.1 Run `make checks` and resolve all failures
```
