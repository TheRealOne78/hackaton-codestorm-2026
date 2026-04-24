#!/usr/bin/env python3
"""Fail when project Python files are missing a module-level docstring."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for rel in ("app", "scripts", "tests"):
        base = ROOT / rel
        if not base.exists():
            continue
        files.extend(sorted(base.rglob("*.py")))
    return files


def has_module_docstring(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    return ast.get_docstring(tree) is not None


def main() -> None:
    missing: list[Path] = []
    for file_path in iter_python_files():
        if not has_module_docstring(file_path):
            missing.append(file_path)

    if not missing:
        print("Docstring check passed")
        return

    print("Missing module docstrings:")
    for item in missing:
        print(f"- {item.relative_to(ROOT)}")
    sys.exit(1)


if __name__ == "__main__":
    main()
