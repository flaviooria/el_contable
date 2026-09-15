#!/usr/bin/env python3
"""Validate BACKLOG.md, select the next eligible work item, or retrieve one item."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOWED_STATUSES = {
    "pending",
    "planning",
    "awaiting-approval",
    "approved",
    "implementing",
    "testing",
    "reviewing",
    "ready-to-commit",
    "done",
    "blocked",
    "cancelled",
}
PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}
REQUIRED_SECTIONS = {
    "Description",
    "Acceptance Criteria",
    "Constraints",
    "Planning",
    "Execution",
}
ITEM_HEADING = re.compile(r"^##\s+([A-Za-z][A-Za-z0-9-]*)\s+[—-]\s+(.+?)\s*$")
META_FIELD = re.compile(r"^\*\*(Status|Priority|Depends on):\*\*\s*(.*?)\s*$")
SECTION_HEADING = re.compile(r"^###\s+(.+?)\s*$")
NONE_DEPENDENCY = re.compile(r"^none(?:\s*\(.*\))?$", re.IGNORECASE)


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    title: str
    status: str
    priority: str
    dependencies: tuple[str, ...]
    order: int
    sections: frozenset[str]
    start: int
    end: int


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def parse_backlog(path: Path) -> tuple[list[WorkItem], list[str]]:
    if not path.exists():
        return [], [f"Backlog not found: {path}"]

    lines = _read_lines(path)
    starts: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        if match := ITEM_HEADING.match(line):
            starts.append((index, match))

    if not starts:
        return [], ["No work items found. Expected headings like '## EC-001 — Title'."]

    items: list[WorkItem] = []
    errors: list[str] = []

    for order, (start, heading) in enumerate(starts):
        end = starts[order + 1][0] if order + 1 < len(starts) else len(lines)
        block = lines[start + 1 : end]
        work_id = heading.group(1)
        title = heading.group(2).strip()

        metadata: dict[str, str] = {}
        sections: set[str] = set()
        for line in block:
            if match := META_FIELD.match(line):
                metadata[match.group(1)] = match.group(2).strip()
            elif match := SECTION_HEADING.match(line):
                sections.add(match.group(1).strip())

        status = metadata.get("Status", "")
        priority = metadata.get("Priority", "")
        depends_raw = metadata.get("Depends on", "")

        if not status:
            errors.append(f"{work_id}: missing Status metadata.")
        elif status not in ALLOWED_STATUSES:
            errors.append(f"{work_id}: invalid status '{status}'.")

        if not priority:
            errors.append(f"{work_id}: missing Priority metadata.")
        elif priority not in PRIORITY_ORDER:
            errors.append(f"{work_id}: invalid priority '{priority}'.")

        if not depends_raw:
            errors.append(f"{work_id}: missing Depends on metadata.")
            dependencies: tuple[str, ...] = ()
        elif NONE_DEPENDENCY.match(depends_raw):
            dependencies = ()
        else:
            dependencies = tuple(part.strip() for part in depends_raw.split(",") if part.strip())

        missing_sections = REQUIRED_SECTIONS - sections
        for section in sorted(missing_sections):
            errors.append(f"{work_id}: missing section '### {section}'.")

        items.append(
            WorkItem(
                work_id=work_id,
                title=title,
                status=status,
                priority=priority,
                dependencies=dependencies,
                order=order,
                sections=frozenset(sections),
                start=start,
                end=end,
            )
        )

    by_id = {item.work_id: item for item in items}
    if len(by_id) != len(items):
        errors.append("Duplicate work item IDs found.")

    for item in items:
        for dependency in item.dependencies:
            if dependency == item.work_id:
                errors.append(f"{item.work_id}: task cannot depend on itself.")
            elif dependency not in by_id:
                errors.append(f"{item.work_id}: dependency '{dependency}' does not exist.")

    return items, errors


def eligible_items(items: list[WorkItem]) -> list[WorkItem]:
    by_id = {item.work_id: item for item in items}
    eligible = [
        item
        for item in items
        if item.status == "pending"
        and all(by_id[dependency].status == "done" for dependency in item.dependencies)
    ]
    return sorted(eligible, key=lambda item: (PRIORITY_ORDER[item.priority], item.order))


def validate(path: Path) -> int:
    items, errors = parse_backlog(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: {len(items)} work item(s) validated in {path}.")
    return 0


def next_item(path: Path) -> int:
    items, errors = parse_backlog(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    eligible = eligible_items(items)
    if not eligible:
        print("NONE: no eligible pending work items.")
        return 0

    item = eligible[0]
    dependencies = ", ".join(item.dependencies) if item.dependencies else "none"
    print(f"id={item.work_id}")
    print(f"title={item.title}")
    print(f"priority={item.priority}")
    print(f"depends_on={dependencies}")
    return 0


def get_item(path: Path, work_id: str) -> int:
    items, errors = parse_backlog(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    item = next((candidate for candidate in items if candidate.work_id == work_id), None)
    if item is None:
        print(f"ERROR: work item '{work_id}' not found.", file=sys.stderr)
        return 1

    lines = _read_lines(path)
    print("\n".join(lines[item.start : item.end]).rstrip())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("validate", "next"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("backlog", type=Path)

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("backlog", type=Path)
    get_parser.add_argument("work_id")

    args = parser.parse_args()
    if args.command == "validate":
        return validate(args.backlog)
    if args.command == "next":
        return next_item(args.backlog)
    return get_item(args.backlog, args.work_id)


if __name__ == "__main__":
    raise SystemExit(main())
