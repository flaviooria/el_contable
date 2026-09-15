---
name: commit-change
description: Create the final Git commit for an approved and fully verified change. Use only after explicit human approval, a current tester PASS, a reviewer PASS, and completed intended work. Inspect the diff, stage only change-related files, follow the repository's existing commit style, commit, and never push automatically.
---

# Commit Change

Commit only a change that has passed every previous gate.

## Preconditions

Require all of the following from the orchestrator context:

- the OpenSpec plan received explicit human approval;
- backend implementation is complete;
- the latest tester result is `PASS`;
- the latest reviewer result is `PASS`;
- no code or test changes occurred after those current PASS results;
- intended OpenSpec implementation tasks are complete.

If any precondition is missing, return `BLOCKED` and do not commit.

## Workflow

1. Inspect the working tree:

```bash
git status --short
git diff --check
git diff
```

2. Identify the files belonging to the approved change.
3. Leave unrelated working-tree changes unstaged.
4. Inspect recent commit subjects to match the repository's existing style:

```bash
git log -5 --oneline
```

5. Stage only the intended files.
6. Review the staged diff before committing.
7. Create one coherent commit for the approved change.
8. Return the commit hash and subject.

## Safety rules

- Never run `git push`.
- Never use `git add .` when unrelated changes are present.
- Never commit secrets, environment credentials, generated caches, or unrelated local files.
- Never amend or rewrite existing commits unless explicitly requested by the human.
- Never bypass Git hooks or project checks.
- If intended and unrelated changes cannot be separated confidently, return `BLOCKED`.
