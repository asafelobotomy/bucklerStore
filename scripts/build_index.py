#!/usr/bin/env python3
"""Write index.json from catalog/*.yaml and the files under fonts/.

Usage: uv run python scripts/build_index.py [--check]
  --check  fail if index.json is not what the catalog builds (CI runs this).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import INDEX, build, render


def main(argv: list[str]) -> int:
    text = render(build())
    if "--check" in argv:
        if not INDEX.is_file() or INDEX.read_text(encoding="utf-8") != text:
            print("index.json is out of date: run scripts/build_index.py", file=sys.stderr)
            return 1
        return 0
    INDEX.write_text(text, encoding="utf-8")
    print(f"wrote {INDEX.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
