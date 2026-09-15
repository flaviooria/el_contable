---
name: work-intake
description: Read, validate, select, retrieve, and transition project work items stored in BACKLOG.md. Use when a coding-agent harness needs to find the next pending task, resolve task dependencies, load one work item without reading the whole backlog, start planning, record planning artifacts, or update lifecycle state without relying on an external tracker.
---

# Work Intake

Treat `BACKLOG.md` as the source of truth for project work state.

Keep this skill focused on intake and state transitions. Do not generate OpenSpec artifacts, ADRs, implementation code, tests, or commits here; delegate those responsibilities to the appropriate skill or agent.

## Workflow

1. Read `AGENTS.md` before mutating project state.
2. Locate `BACKLOG.md` at the repository root.
3. If the backlog format is unfamiliar or invalid, read [references/backlog-format.md](references/backlog-format.md).
4. Validate the backlog before changing it when shell execution is available:

   ```bash
   python .agents/skills/work-intake/scripts/backlog.py validate BACKLOG.md
   ```

5. To choose work automatically, run:

   ```bash
   python .agents/skills/work-intake/scripts/backlog.py next BACKLOG.md
   ```

6. Retrieve only the selected item when possible:

   ```bash
   python .agents/skills/work-intake/scripts/backlog.py get BACKLOG.md <work-item-id>
   ```

7. Select only an item whose status is `pending` and whose dependencies are all `done`.
8. Prefer higher priority first. For equal priority, preserve backlog order.
9. Change the selected item's status from `pending` to `planning` before planning begins.
10. Return the selected work context to the orchestrator.
11. Re-validate `BACKLOG.md` after every mutation.

## Context Efficiency

Prefer deterministic backlog commands over loading the complete `BACKLOG.md`.

- Use `next` to discover the next eligible work item.
- Use `get` to load only the selected work item.
- Do not read completed, cancelled, blocked, or unrelated work items unless required to resolve dependencies or historical planning metadata.
- Read the complete backlog only when the requested operation genuinely requires global backlog information.

## Work Context

Return at least:

- work item ID;
- title;
- priority;
- description;
- acceptance criteria;
- constraints;
- dependencies;
- current status.

When planning already exists, also return the recorded change ID, proposal, spec deltas, ADR, and commit if present.

## State Ownership

Only the Leader/orchestrator, or a human explicitly requesting the transition, may change work-item status or orchestration metadata.

Backend, Tester, and Reviewer agents may report outcomes but must not advance `BACKLOG.md` directly.

Use this lifecycle:

```text
pending
  -> planning
  -> awaiting-approval
  -> approved
  -> implementing
  -> testing
  -> reviewing
  -> ready-to-commit
  -> done
```

`blocked` and `cancelled` are terminal side states until a human explicitly changes them.

Do not skip `awaiting-approval` or infer human approval from silence.

## Planning Metadata

After planning succeeds, record paths rather than duplicating artifact content in the backlog:

- `Change` -> OpenSpec change ID;
- `Proposal` -> `proposal.md` path;
- `Specs` -> one or more spec-delta paths;
- `ADR` -> ADR path or `none`.

Then move the work item to `awaiting-approval` and stop.

## Gotchas

- `BACKLOG.md` is workflow state, not a second specification system. Keep requirements in OpenSpec after planning starts.
- Do not create an ADR merely because a known architectural rule is being applied. Create one only when a new material architecture decision is required.
- Do not select a task with unresolved dependencies.
- Do not rewrite unrelated backlog items while updating one item.
- Do not reorder backlog items as a side effect of state changes.
- Do not mark work `done` until the commit has been recorded.

## Validation Loop

After modifying `BACKLOG.md`:

1. Run the validator.
2. Fix every reported structural error.
3. Run it again.
4. Continue only after validation passes.
