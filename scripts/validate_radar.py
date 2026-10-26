#!/usr/bin/env python3
"""Validate the repository's service-volume and Markdown navigation contract."""

from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []

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

    ignored = {"references", "agents", "scripts", ".git"}
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

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Radar validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
