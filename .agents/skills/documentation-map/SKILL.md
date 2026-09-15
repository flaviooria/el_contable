---
name: documentation-map
description: Regenerate and validate the Documentation Map in AGENTS.md from canonical Markdown documentation. Use after creating, deleting, moving, or renaming files under docs/ or openspec/specs/, after creating an ADR, or when checking that AGENTS.md progressive-disclosure routing is synchronized. Excludes transient openspec/changes/ artifacts.
---

# Documentation Map

Keep the generated documentation tree in `AGENTS.md` synchronized with canonical project documentation.

## Workflow

1. Read `AGENTS.md` before mutating documentation state.
2. Treat only these paths as canonical documentation for the global map:
   - `docs/**/*.md`
   - `openspec/specs/**/*.md`
3. Never add `openspec/changes/`, `BACKLOG.md`, generated artifacts, or Skill documentation to the global map.
4. After creating, deleting, moving, or renaming a canonical documentation file, run:

   ```bash
   python .agents/skills/documentation-map/scripts/update_docs_map.py update
   ```

5. After the update, verify synchronization with:

   ```bash
   python .agents/skills/documentation-map/scripts/update_docs_map.py check
   ```

6. Continue only when `check` succeeds.

## Progressive Disclosure Contract

The map is an index, not a knowledge dump.

- Keep descriptions to one short line.
- Prefer lightweight metadata at the top of each canonical document:

  ```markdown
  <!-- docs-map: Short description of when or why this document is relevant. -->
  ```

- The script reads only the beginning of each Markdown file to extract this metadata.
- Missing metadata does not exclude a document from the tree; the script emits a warning instead.
- Do not duplicate document contents in `AGENTS.md`.

Read [references/document-map-format.md](./references/document-map-format.md) only when changing the map contract or troubleshooting generation.

## Boundaries

- Modify only the content between `<!-- DOCS_MAP_START -->` and `<!-- DOCS_MAP_END -->`.
- Never rewrite unrelated `AGENTS.md` content.
- Never manually maintain entries inside the generated block.
- Never include transient OpenSpec change artifacts in the global map.
- Never delete or rename documentation as part of map synchronization.

## Integration

Agents that create canonical documentation must invoke this Skill before declaring their work complete.

Typical triggers include:

- `architecture-decision` creates or renames an ADR under `docs/decisions/`;
- an approved change updates canonical specs under `openspec/specs/`;
- architecture, functional, or code-style documentation is created, moved, or renamed.

For CI or `make checks`, use `check` mode so stale documentation maps fail without modifying files.

## Gotchas

- `openspec/changes/` is work-in-progress state and belongs to the active backlog/change context, not the global documentation map.
- A new Markdown file without `docs-map` metadata must still appear in the tree.
- Do not infer descriptions by loading whole documents; keep generation cheap and deterministic.
- If markers are missing or duplicated, stop with an error rather than guessing where to write.
