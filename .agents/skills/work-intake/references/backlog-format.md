# BACKLOG.md Format

Read this reference when creating `BACKLOG.md`, parsing an unfamiliar item, or fixing validator failures.

## File Shape

Use one level-two Markdown heading per work item:

```markdown
# Backlog

## EC-001 — Add category type to movements

**Status:** pending  
**Priority:** high  
**Depends on:** none

### Description

Movements must support a category type used when classifying expenses.

### Acceptance Criteria

- A movement can reference a category type.
- Existing movements remain valid.
- The API exposes the category type.
- Relevant behaviour is covered by tests.

### Constraints

- Preserve existing movement upload behaviour.

### Planning

- Change: —
- Proposal: —
- Specs: —
- ADR: —

### Execution

- Commit: —
```

## Required Fields

Every work item must contain:

- ID and title in the `## <ID> — <title>` heading;
- `Status`;
- `Priority`;
- `Depends on`;
- `Description`;
- `Acceptance Criteria`;
- `Constraints`;
- `Planning`;
- `Execution`.

Use `none` when a task has no dependencies.

Use `—` for planning or execution metadata that has not been produced yet.

## Status Values

Allowed values:

```text
pending
planning
awaiting-approval
approved
implementing
testing
reviewing
ready-to-commit
done
blocked
cancelled
```

## Priority Values

Allowed values, highest first:

```text
critical
high
normal
low
```

If priority is omitted conceptually, write `normal`; do not leave the field absent.

## Dependencies

Use either:

```markdown
**Depends on:** none
```

or comma-separated work item IDs:

```markdown
**Depends on:** EC-001, EC-003
```

A task is eligible for automatic selection only when every referenced dependency exists and has status `done`.

## Planning Metadata

Use paths relative to the repository root:

```markdown
### Planning

- Change: `add-movement-category-type`
- Proposal: `openspec/changes/add-movement-category-type/proposal.md`
- Specs:
  - `openspec/changes/add-movement-category-type/specs/movements/spec.md`
- ADR: —
```

Do not paste proposal, spec, or ADR contents into the backlog.

## Execution Metadata

Record the final commit only after the quality and review gates pass:

```markdown
### Execution

- Commit: `8c472ac`
```

## Selection Rule

For automatic intake:

1. consider only `pending` items;
2. exclude items with dependencies not in `done`;
3. sort by `critical`, `high`, `normal`, `low`;
4. preserve document order for equal priority.
