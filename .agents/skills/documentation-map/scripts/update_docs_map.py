#!/usr/bin/env python3
"""Generate or validate the canonical documentation map in AGENTS.md."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

START_MARKER = "<!-- DOCS_MAP_START -->"
END_MARKER = "<!-- DOCS_MAP_END -->"
METADATA_PATTERN = re.compile(r"<!--\s*docs-map:\s*(.*?)\s*-->", re.IGNORECASE)
CANONICAL_ROOTS = (Path("docs"), Path("openspec/specs"))
METADATA_SCAN_LINES = 20


@dataclass
class TreeNode:
    """A node in the generated documentation tree."""

    name: str
    is_file: bool = False
    description: str | None = None
    children: dict[str, "TreeNode"] = field(default_factory=dict)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate or validate the Documentation Map in AGENTS.md."
    )
    parser.add_argument("mode", choices=("update", "check"))
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current working directory.",
    )
    return parser.parse_args()


def read_description(path: Path) -> str | None:
    """Read lightweight docs-map metadata from the beginning of a Markdown file."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= METADATA_SCAN_LINES:
                    break
                if match := METADATA_PATTERN.search(line):
                    description = " ".join(match.group(1).split())
                    return description or None
    except UnicodeDecodeError as exc:
        raise ValueError(f"Cannot decode Markdown as UTF-8: {path}") from exc
    return None


def discover_files(repo_root: Path) -> tuple[list[Path], list[Path]]:
    """Return canonical Markdown files and files missing docs-map metadata."""
    discovered: list[Path] = []
    missing_metadata: list[Path] = []

    for relative_root in CANONICAL_ROOTS:
        absolute_root = repo_root / relative_root
        if not absolute_root.exists():
            continue
        if not absolute_root.is_dir():
            raise ValueError(f"Canonical documentation root is not a directory: {relative_root}")

        for path in absolute_root.rglob("*.md"):
            if not path.is_file():
                continue
            relative_path = path.relative_to(repo_root)
            discovered.append(relative_path)
            if read_description(path) is None:
                missing_metadata.append(relative_path)

    discovered.sort(key=lambda item: item.as_posix().lower())
    missing_metadata.sort(key=lambda item: item.as_posix().lower())
    return discovered, missing_metadata


def add_path(root: TreeNode, parts: tuple[str, ...], description: str | None) -> None:
    node = root
    for index, part in enumerate(parts):
        is_file = index == len(parts) - 1
        child = node.children.get(part)
        if child is None:
            child = TreeNode(name=part, is_file=is_file)
            node.children[part] = child
        elif child.is_file != is_file and is_file:
            raise ValueError(f"Tree path collision at {'/'.join(parts)}")
        node = child
    node.description = description


def build_tree(repo_root: Path, files: list[Path]) -> TreeNode:
    root = TreeNode(name="")
    for relative_path in files:
        description = read_description(repo_root / relative_path)
        add_path(root, relative_path.parts, description)
    return root


def ordered_children(node: TreeNode) -> list[TreeNode]:
    return sorted(
        node.children.values(),
        key=lambda child: (not child.is_file, child.name.lower()),
    )


def render_branch(node: TreeNode, prefix: str, is_last: bool) -> list[str]:
    connector = "└── " if is_last else "├── "
    suffix = "" if node.is_file else "/"
    lines = [f"{prefix}{connector}{node.name}{suffix}"]

    continuation = "    " if is_last else "│   "
    child_prefix = f"{prefix}{continuation}"

    if node.is_file:
        if node.description:
            lines.append(f"{child_prefix}# {node.description}")
        return lines

    children = ordered_children(node)
    for index, child in enumerate(children):
        lines.extend(render_branch(child, child_prefix, index == len(children) - 1))
    return lines


def render_map(tree: TreeNode) -> str:
    sections: list[str] = []

    docs_node = tree.children.get("docs")
    if docs_node is not None:
        lines = ["docs/"]
        children = ordered_children(docs_node)
        for index, child in enumerate(children):
            lines.extend(render_branch(child, "", index == len(children) - 1))
        sections.append("\n".join(lines))

    openspec_node = tree.children.get("openspec")
    if openspec_node is not None:
        lines = ["openspec/"]
        children = ordered_children(openspec_node)
        for index, child in enumerate(children):
            lines.extend(render_branch(child, "", index == len(children) - 1))
        sections.append("\n".join(lines))

    body = "\n\n".join(sections)
    return f"\n```text\n{body}\n```\n"


def replace_generated_block(agents_text: str, generated: str) -> str:
    start_count = agents_text.count(START_MARKER)
    end_count = agents_text.count(END_MARKER)
    if start_count != 1 or end_count != 1:
        raise ValueError(
            "AGENTS.md must contain exactly one DOCS_MAP_START marker and one DOCS_MAP_END marker."
        )

    start_index = agents_text.index(START_MARKER) + len(START_MARKER)
    end_index = agents_text.index(END_MARKER)
    if start_index >= end_index:
        raise ValueError("DOCS_MAP_START must appear before DOCS_MAP_END in AGENTS.md.")

    return f"{agents_text[:start_index]}{generated}{agents_text[end_index:]}"


def print_metadata_warnings(missing_metadata: list[Path]) -> None:
    for path in missing_metadata:
        print(
            f"warning: {path.as_posix()} has no docs-map metadata in its first "
            f"{METADATA_SCAN_LINES} lines",
            file=sys.stderr,
        )


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    agents_path = repo_root / "AGENTS.md"

    if not agents_path.is_file():
        print(f"error: AGENTS.md not found at {agents_path}", file=sys.stderr)
        return 2

    try:
        files, missing_metadata = discover_files(repo_root)
        tree = build_tree(repo_root, files)
        generated = render_map(tree)
        current_text = agents_path.read_text(encoding="utf-8")
        expected_text = replace_generated_block(current_text, generated)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print_metadata_warnings(missing_metadata)

    if args.mode == "check":
        if current_text != expected_text:
            print(
                "error: Documentation Map is stale. Run:\n"
                "  python .agents/skills/documentation-map/scripts/update_docs_map.py update",
                file=sys.stderr,
            )
            return 1
        print(f"Documentation Map is synchronized ({len(files)} files).")
        return 0

    if current_text == expected_text:
        print(f"Documentation Map already synchronized ({len(files)} files).")
        return 0

    agents_path.write_text(expected_text, encoding="utf-8")
    print(f"Updated Documentation Map in AGENTS.md ({len(files)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
