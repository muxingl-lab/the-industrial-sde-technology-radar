#!/usr/bin/env python3
"""Validate the repository's service-volume and Markdown navigation contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


LINK_RE = re.compile(r"\[[^]]+\]\((?!https?://)([^)#]+\.md)(?:#([^)]*))?\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
LEVEL_FILES = (
    "level-1-philosophy.md",
    "level-2-internals.md",
    "level-3-code-labs.md",
)
PATTERN_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MEMBER_RE = re.compile(r"^([a-z0-9-]+):q([1-9][0-9]*)$")


def slug(text: str) -> str:
    text = re.sub(r"[`*_~]", "", text.strip().lower())
    text = re.sub(r"[^\w\- ]", "", text)
    return re.sub(r"\s+", "-", text)


def headings(path: Path) -> set[str]:
    result: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line)
        if match:
            result.add(slug(match.group(1)))
    return result


def question_numbers(path: Path) -> list[int]:
    numbers = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^## Q(\d+)\.", line)
        if match:
            numbers.append(int(match.group(1)))
    return numbers


def question_anchor(path: Path, number: int) -> str | None:
    prefix = f"## Q{number}."
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return slug(line.removeprefix("## "))
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []

    for required in (
        "README.md",
        "CONTRIBUTING.md",
        "library/README.md",
        "library/patterns.json",
        "library/schema.md",
        "library/comparisons/README.md",
    ):
        if not (root / required).exists():
            errors.append(f"missing required project file: {required}")

    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        for target, anchor in LINK_RE.findall(path.read_text(encoding="utf-8")):
            destination = (path.parent / target).resolve()
            if not destination.exists():
                errors.append(f"{path.relative_to(root)}: missing {target}")
            elif anchor and anchor not in headings(destination):
                errors.append(
                    f"{path.relative_to(root)}: missing anchor {target}#{anchor}"
                )

    ignored = {"references", "agents", "scripts", "library", ".git"}
    for service in root.iterdir():
        if not service.is_dir() or service.name in ignored:
            continue
        present = [service / name for name in LEVEL_FILES if (service / name).exists()]
        if present and len(present) != len(LEVEL_FILES):
            missing = [name for name in LEVEL_FILES if not (service / name).exists()]
            errors.append(f"{service.name}: incomplete level set: {', '.join(missing)}")
        if len(present) == len(LEVEL_FILES):
            sequences = [question_numbers(path) for path in present]
            if not all(sequence == sequences[0] for sequence in sequences[1:]):
                errors.append(f"{service.name}: question numbers differ across levels")

    library_text = (root / "library/README.md").read_text(encoding="utf-8") if (root / "library/README.md").exists() else ""
    for level_one in root.glob("*/level-1-philosophy.md"):
        service = level_one.parent.name
        for line in level_one.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^## Q\d+\.\s+(.+?)\s*$", line)
            if not match:
                continue
            anchor = slug(line.removeprefix("## "))
            expected = f"../{service}/level-1-philosophy.md#{anchor}"
            if expected not in library_text:
                errors.append(f"library: missing {service} question #{anchor}")

    comparisons_dir = root / "library/comparisons"
    comparisons_index = (comparisons_dir / "README.md").read_text(encoding="utf-8") if comparisons_dir.exists() else ""
    if comparisons_dir.exists():
        for comparison in comparisons_dir.glob("*.md"):
            if comparison.name != "README.md" and f"({comparison.name})" not in comparisons_index:
                errors.append(f"comparison index: missing {comparison.name}")

    registry_path = root / "library/patterns.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"pattern registry: cannot read JSON: {exc}")
            registry = {}

        if not isinstance(registry, dict):
            errors.append("pattern registry: top level must be an object")
            registry = {}

        patterns = registry.get("patterns", [])
        if registry.get("schema_version") != 1:
            errors.append("pattern registry: schema_version must be 1")
        if not isinstance(patterns, list):
            errors.append("pattern registry: patterns must be a list")
            patterns = []

        pattern_ids: set[str] = set()
        comparison_paths: set[str] = set()
        for pattern in patterns:
            if not isinstance(pattern, dict):
                errors.append("pattern registry: every pattern must be an object")
                continue
            pattern_id = pattern.get("id", "")
            if not isinstance(pattern_id, str) or not PATTERN_ID_RE.fullmatch(pattern_id):
                errors.append(f"pattern registry: invalid pattern id {pattern_id!r}")
            elif pattern_id in pattern_ids:
                errors.append(f"pattern registry: duplicate pattern id {pattern_id}")
            pattern_ids.add(pattern_id)

            for field in ("title", "summary"):
                if not isinstance(pattern.get(field), str) or not pattern[field].strip():
                    errors.append(f"pattern {pattern_id}: missing non-empty {field}")
            dimensions = pattern.get("dimensions")
            if (
                not isinstance(dimensions, list)
                or not dimensions
                or not all(isinstance(item, str) and item for item in dimensions)
                or len(dimensions) != len(set(dimensions))
            ):
                errors.append(f"pattern {pattern_id}: dimensions must be a non-empty unique list")

            comparison = pattern.get("comparison", "")
            if not isinstance(comparison, str) or not comparison.startswith("comparisons/"):
                errors.append(f"pattern {pattern_id}: invalid comparison path")
            else:
                if comparison in comparison_paths:
                    errors.append(f"pattern {pattern_id}: comparison path is already registered")
                comparison_paths.add(comparison)
                comparison_file = root / "library" / comparison
                if not comparison_file.exists():
                    errors.append(f"pattern {pattern_id}: missing {comparison}")
                elif f"({Path(comparison).name})" not in comparisons_index:
                    errors.append(f"pattern {pattern_id}: comparison is not indexed")

            members = pattern.get("members")
            if not isinstance(members, list) or len(members) < 2:
                errors.append(f"pattern {pattern_id}: comparison requires at least two members")
                continue
            if len(members) != len(set(members)):
                errors.append(f"pattern {pattern_id}: duplicate members")
            for member in members:
                match = MEMBER_RE.fullmatch(member) if isinstance(member, str) else None
                if not match:
                    errors.append(f"pattern {pattern_id}: invalid member {member!r}")
                    continue
                service, question = match.group(1), int(match.group(2))
                level_one = root / service / "level-1-philosophy.md"
                if not level_one.exists():
                    errors.append(f"pattern {pattern_id}: unknown service in {member}")
                elif question not in question_numbers(level_one):
                    errors.append(f"pattern {pattern_id}: unknown question in {member}")
                elif isinstance(comparison, str):
                    anchor = question_anchor(level_one, question)
                    expected = f"../../{service}/level-1-philosophy.md#{anchor}"
                    comparison_file = root / "library" / comparison
                    if comparison_file.exists() and expected not in comparison_file.read_text(encoding="utf-8"):
                        errors.append(f"pattern {pattern_id}: comparison does not link to {member}")

        registered_pages = {Path(path).name for path in comparison_paths}
        if comparisons_dir.exists():
            for comparison in comparisons_dir.glob("*.md"):
                if comparison.name != "README.md" and comparison.name not in registered_pages:
                    errors.append(f"pattern registry: missing comparison {comparison.name}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Radar validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
