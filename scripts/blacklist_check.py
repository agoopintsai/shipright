#!/usr/bin/env python3
"""Fail if any repo text file matches a pattern in scripts/blacklist.txt (and the optional scripts/blacklist.local.txt)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "scripts" / "blacklist.txt"
LOCAL_LIST = ROOT / "scripts" / "blacklist.local.txt"  # optional, gitignored
LISTS = {LIST, LOCAL_LIST}
SKIP_DIRS = {".git"}


def load_list(path):
    pats = []
    if not path.exists():
        return pats
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            pats.append((line, re.compile(line)))
    return pats


def load_patterns():
    public = load_list(LIST)
    local = load_list(LOCAL_LIST)
    print(f"loaded {len(public)} public + {len(local)} local patterns")
    return public + local


def iter_files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.is_file() and p not in LISTS:
            yield p, rel


def main() -> int:
    pats = load_patterns()
    hits = 0
    for p, rel in iter_files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable
        for n, line in enumerate(text.splitlines(), 1):
            for src, rx in pats:
                if rx.search(line):
                    print(f"{rel}:{n}: {src}")
                    hits += 1
    if hits:
        print(f"blacklist check FAILED: {hits} hit(s)")
        return 1
    print("blacklist check passed: 0 hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
