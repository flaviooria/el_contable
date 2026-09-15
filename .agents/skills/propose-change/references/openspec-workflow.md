# Manual OpenSpec Planning Rules

This project authors OpenSpec-style artifacts directly in the repository and does not require the OpenSpec CLI or library.

Use the `openspec-artifacts` skill as the source of truth for artifact structure, delta-spec rules, templates, and local validation.

## Artifact order

1. `proposal.md`
2. delta specs and optional `design.md`
3. `tasks.md`
4. implementation only after explicit human approval

## Storage

```text
openspec/changes/<change-id>/
├── proposal.md
├── design.md                  # optional
├── specs/
│   └── <capability>/
│       └── spec.md
└── tasks.md
```

Do not modify canonical specs under `openspec/specs/` during planning. The change directory contains the proposed delta until the change is accepted/merged by the project's normal process.
