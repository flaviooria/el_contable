# Documentation Map Contract

Read this reference only when changing or troubleshooting documentation-map generation.

## AGENTS.md markers

`AGENTS.md` must contain exactly one pair of markers in this order:

```markdown
## Documentation Map
<!-- DOCS_MAP_START -->
```text
...
```
<!-- DOCS_MAP_END -->
```

The generator replaces only the content between the two markers.

## Canonical roots

Include:

```text
docs/**/*.md
openspec/specs/**/*.md
```

Exclude everything else, especially:

```text
openspec/changes/**
.agents/**
BACKLOG.md
README.md
```

The root README can still be routed explicitly from `AGENTS.md` if the project later decides it is canonical documentation; it is not part of this generated map by default.

## Document metadata

Canonical Markdown files should start with a lightweight description:

```markdown
<!-- docs-map: System architecture, boundaries, dependencies, and design constraints. -->
```

Rules:

- Keep it on one line.
- Keep it concise.
- Describe purpose/relevance, not document contents in detail.
- Do not put task state or temporary change information here.

The generator inspects only the first 20 lines for this comment.

If metadata is missing, the path remains in the map and generation emits a warning.

## Ordering

Generation is deterministic:

1. `docs/`
2. `openspec/specs/`
3. Within a directory, Markdown files before subdirectories.
4. Alphabetical ordering within each group, case-insensitive.

## Generated shape

Example:

```text
docs/
├── ARCHITECTURE.md
│   # System architecture and boundaries.
├── FUNCTIONAL.md
│   # Product capabilities and business rules.
└── decisions/
    └── 001-example.md
        # Rationale for an architectural decision.

openspec/
└── specs/
    └── upload_movements/
        └── spec.md
            # Canonical movement-upload contract.
```

The generated block intentionally contains paths and one-line descriptions only.
