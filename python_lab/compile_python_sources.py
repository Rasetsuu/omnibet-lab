#!/usr/bin/env python3
from __future__ import annotations

import py_compile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    files = sorted(root.glob("*.py")) + sorted((root / "adapters").glob("*.py"))
    if not files:
        raise SystemExit("no Python files found")
    for path in files:
        py_compile.compile(str(path), doraise=True)
    print(f"compiled {len(files)} Python files")


if __name__ == "__main__":
    main()
