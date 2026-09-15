---
name: quality-gate
description: Verify an approved backend change with specification-driven tests and the project's complete quality suite. Use after implementation or fixes to run tests, Ruff lint/format validation, mypy, and project checks, and to produce an explicit PASS/FAIL result without hiding production defects.
---

# Quality Gate

Verify behaviour first, then enforce the full project quality gate.

## Workflow

1. Read the approved OpenSpec delta specs and relevant tasks.
2. Derive or update tests for every important observable scenario.
3. Add regression and failure-path tests required by the specification.
4. For multi-aggregate operations, test atomicity and relevant domain invariants.
5. Run targeted tests while developing the test suite when useful.
6. Run the canonical full gate:

```bash
make checks
```

7. Return `PASS` only when the complete command succeeds.

## Rules

- Treat `make checks` as the canonical source of truth for linting, formatting, mypy, and tests.
- Do not weaken tests, type checking, Ruff configuration, or project configuration to obtain a pass.
- Do not silently modify production code from the tester workflow.
- When a failure originates in production code, report the exact failure so the leader can delegate it to the backend agent.
- When specification behaviour is ambiguous or missing, return `BLOCKED` rather than inventing expected behaviour.

## Result format

Return:

```text
STATUS: PASS | FAIL | BLOCKED
COMMAND: make checks
TESTS: <summary>
FAILURES: <none or concise diagnostics>
TASKS_VERIFIED: <OpenSpec task IDs>
```
