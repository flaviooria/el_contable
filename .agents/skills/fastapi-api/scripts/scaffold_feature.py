#!/usr/bin/env python3
"""Create missing modules for an El Contable feature without overwriting files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FEATURE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
DEFAULT_FEATURES_ROOT = Path("src/el_contable/features")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Scaffold missing feature modules without overwriting existing files."
    )
    parser.add_argument("feature", help="Feature package name in snake_case.")
    parser.add_argument(
        "--features-root",
        type=Path,
        default=DEFAULT_FEATURES_ROOT,
        help="Feature root directory. Defaults to src/el_contable/features.",
    )
    parser.add_argument(
        "--with-use-case",
        action="store_true",
        help="Also create use_case.py for multi-aggregate orchestration.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned files without writing them.",
    )
    return parser.parse_args()


def module_contents(feature: str, module: str) -> str:
    """Return minimal module contents for a scaffolded feature file."""
    readable_feature = feature.replace("_", " ")

    if module == "__init__.py":
        return f'"""{readable_feature.title()} feature."""\n'

    if module == "router.py":
        return (
            f'"""HTTP routes for the {readable_feature} feature."""\n\n'
            "from fastapi import APIRouter\n\n"
            "router = APIRouter()\n"
        )

    descriptions = {
        "schemas.py": "Pydantic schemas",
        "models.py": "SQLAlchemy models",
        "service.py": "Single-aggregate application operations",
        "use_case.py": "Multi-aggregate application use cases",
    }
    return f'"""{descriptions[module]} for the {readable_feature} feature."""\n'


def scaffold_feature(
    feature: str,
    features_root: Path,
    *,
    with_use_case: bool,
    dry_run: bool,
) -> list[Path]:
    """Create missing feature modules and return the files that would be created."""
    if not FEATURE_RE.fullmatch(feature):
        raise ValueError(
            "Feature name must be snake_case, start with a letter, and contain only "
            "lowercase letters, digits, and underscores."
        )

    feature_dir = features_root / feature
    modules = ["__init__.py", "router.py", "schemas.py", "models.py", "service.py"]
    if with_use_case:
        modules.append("use_case.py")

    planned: list[Path] = []
    for module in modules:
        path = feature_dir / module
        if path.exists():
            print(f"SKIP {path}")
            continue
        planned.append(path)
        print(f"CREATE {path}")

    if dry_run:
        return planned

    feature_dir.mkdir(parents=True, exist_ok=True)
    for path in planned:
        path.write_text(module_contents(feature, path.name), encoding="utf-8")

    return planned


def main() -> int:
    """Run the feature scaffolder."""
    args = parse_args()
    try:
        scaffold_feature(
            args.feature,
            args.features_root,
            with_use_case=args.with_use_case,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
