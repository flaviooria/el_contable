---
name: add-adr
description: Create a new Architecture Decision Record in docs/decisions/ following the project's numbered ADR format. Use this after a spec-driven change has been approved and implemented, whenever a decision was made that future contributors need context on (a new dependency, a schema/model change, a chosen pattern over an alternative, a reversal of a prior approach).
license: MIT
compatibility: opencode
metadata:
  audience: leader
  workflow: adr
---

## What I do

I write a single new ADR file into `docs/decisions/` that documents a decision made during an approved change, following the project's existing ADR conventions exactly.

## When to use me

Use this after implementation, tests, and review have passed for a change — right before commit — when the change involved a decision worth recording for future contributors: a new dependency, a schema or model change, a chosen pattern over a rejected alternative, a reversal of a prior decision, or anything a future reader would otherwise have to reverse-engineer from the diff.

Skip me for purely mechanical changes (typo fixes, formatting, dependency bumps with no design impact) — not every change needs an ADR.

## How I work

### 1. Determine the next ADR number

- List `docs/decisions/*.md`.
- Files are named `NNN-title-slug.md` with `NNN` a zero-padded 3-digit sequence (`001`, `002`, `003`, `004`, ...).
- The next number is the highest existing `NNN` + 1, zero-padded to 3 digits.

### 2. Derive the filename

- Slugify the ADR title: lowercase, spaces → hyphens, strip punctuation.
- Filename: `docs/decisions/<NNN>-<slug>.md`.
- Example: title "Shared Declarative Base" with number `004` → `docs/decisions/004-shared-declarative-base.md`.

### 3. Gather the decision content

Pull this from the approved OpenSpec change (`proposal.md`, `design.md` if present) and from what was actually implemented — never invent context that wasn't part of the approved change:

- **What changed** — the concrete before/after (a code snippet showing both when the change is code-shaped, like a moved class or a new relationship).
- **Why it changed** — the concrete problem that forced the decision (a constraint, an error, a limitation being worked around).
- **What else was considered and rejected**, and the concrete reason each alternative was rejected.

If the OpenSpec change doesn't make one of these clear, ask a short clarifying question rather than guessing.

### 4. Write the ADR using this exact structure

```markdown
# <NNN> - <Title>

## Context

<What was true before, and the concrete constraint or problem that forced a decision.
Use ``double backticks`` for inline code/identifiers, matching project convention.>

## Decision

<What was decided, stated plainly. If the decision is code-shaped, show it:>

**Before:**

\`\`\`python
# old code
\`\`\`

**After:**

\`\`\`python
# new code
\`\`\`

## Why

### <Reason heading>

<Explanation.>

### <Reason heading>

<Explanation.>

## Alternatives Considered

### <Alternative name>

<What it was and the concrete reason it was rejected.>

### <Alternative name>

<What it was and the concrete reason it was rejected.>

## Status

Accepted - <YYYY-MM-DD>
```

- `## Status` always uses today's date, in `YYYY-MM-DD`, and starts as `Accepted` (the change was already approved through the human approval gate before this skill runs).
- Keep headings and section order exactly as above — don't add, remove, or reorder sections.
- Use ``double backticks`` for inline code identifiers (class names, file names, module paths) to match the existing ADRs' style; use fenced ```` ```python ```` blocks only for multi-line before/after snippets.

### 5. Write the file

- Create the file at `docs/decisions/<NNN>-<slug>.md`. Never overwrite an existing ADR — if the target number/file already exists, something upstream miscounted; re-check the listing.
- Do not modify any other file.

## Output

Report back: the ADR number, filename, and a one-line summary of the decision recorded — so the calling agent can reference it in the commit.