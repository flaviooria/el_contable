#!/usr/bin/env python3
"""Validate the local structure of manually authored OpenSpec-style artifacts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

DELTA_SECTION_RE = re.compile(
    r"^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements\s*$", re.MULTILINE
)
REQUIREMENT_RE = re.compile(r"^### Requirement:\s+.+$", re.MULTILINE)
SCENARIO_RE = re.compile(r"^#### Scenario:\s+.+$", re.MULTILINE)
WHEN_RE = re.compile(r"^- \*\*WHEN\*\*\s+.+$", re.MULTILINE)
THEN_RE = re.compile(r"^- \*\*THEN\*\*\s+.+$", re.MULTILINE)
TASK_RE = re.compile(r"^- \[ \] \d+(?:\.\d+)*\s+.+$", re.MULTILINE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_change(change_dir: Path) -> list[str]:
    errors: list[str] = []

    if not change_dir.is_dir():
        return [f"Change directory does not exist: {change_dir}"]

    proposal = change_dir / "proposal.md"
    tasks = change_dir / "tasks.md"
    specs_dir = change_dir / "specs"

    if not proposal.is_file():
        errors.append("Missing proposal.md")
    else:
        proposal_text = read_text(proposal)
        for heading in ("## Why", "## What Changes", "## Impact"):
            if heading not in proposal_text:
                errors.append(f"proposal.md: missing '{heading}'")

    spec_files = sorted(specs_dir.glob("*/spec.md")) if specs_dir.is_dir() else []
    if not spec_files:
        errors.append("Missing delta spec at specs/<capability>/spec.md")

    for spec_file in spec_files:
        text = read_text(spec_file)
        if not DELTA_SECTION_RE.search(text):
            errors.append(f"{spec_file}: missing delta requirement section")
            continue

        has_added_or_modified = bool(
            re.search(r"^## (ADDED|MODIFIED) Requirements\s*$", text, re.MULTILINE)
        )
        if has_added_or_modified:
            requirements = REQUIREMENT_RE.findall(text)
            scenarios = SCENARIO_RE.findall(text)
            if not requirements:
                errors.append(f"{spec_file}: ADDED/MODIFIED delta has no Requirement headings")
            if not scenarios:
                errors.append(f"{spec_file}: ADDED/MODIFIED delta has no Scenario headings")
            if scenarios and not WHEN_RE.search(text):
                errors.append(f"{spec_file}: scenario missing '**WHEN**' step")
            if scenarios and not THEN_RE.search(text):
                errors.append(f"{spec_file}: scenario missing '**THEN**' step")

    if not tasks.is_file():
        errors.append("Missing tasks.md")
    else:
        tasks_text = read_text(tasks)
        if not TASK_RE.search(tasks_text):
            errors.append("tasks.md: no unchecked numbered tasks found")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_change.py <openspec/changes/change-id>", file=sys.stderr)
        return 2

    change_dir = Path(sys.argv[1])
    errors = validate_change(change_dir)

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    print(f"Validated manual OpenSpec artifacts in {change_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
