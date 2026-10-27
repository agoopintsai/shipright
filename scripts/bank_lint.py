#!/usr/bin/env python3
"""Validate a question bank folder against banks/SCHEMA.md. Stdlib only."""
import re
import sys
from datetime import date
from pathlib import Path

CATEGORIES = {"first-principles", "boundaries", "gatekeeping"}
REQUIRED_FIELDS = ("id", "category", "must_answer", "added")
REQUIRED_SECTIONS = ("## Question", "## Why it matters")
NAME_RE = re.compile(r"^(first-principles|boundaries|gatekeeping)-\d{2}-[a-z0-9]+(-[a-z0-9]+)*$")


def parse(text):
    """Return (fields, body) or (None, text) when frontmatter is missing."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fields = {}
            for raw in lines[1:i]:
                if ":" in raw:
                    k, v = raw.split(":", 1)
                    fields[k.strip()] = v.split(" #")[0].strip()
            return fields, "\n".join(lines[i + 1:])
    return None, text


def lint_file(path):
    errs = []
    fields, body = parse(path.read_text(encoding="utf-8"))
    if fields is None:
        return ["missing or unterminated frontmatter"]
    if not NAME_RE.match(path.stem):
        errs.append(f"file name '{path.stem}' does not match <category>-<nn>-<slug>")
    for f in REQUIRED_FIELDS:
        if f not in fields or fields[f] == "":
            errs.append(f"missing field '{f}'")
    if fields.get("id") and fields["id"] != path.stem:
        errs.append(f"id '{fields['id']}' does not match file name '{path.stem}'")
    if fields.get("category") and fields["category"] not in CATEGORIES:
        errs.append(f"invalid category '{fields['category']}'")
    if fields.get("must_answer") and fields["must_answer"] not in ("true", "false"):
        errs.append(f"must_answer must be true or false, got '{fields['must_answer']}'")
    if fields.get("added"):
        try:
            date.fromisoformat(fields["added"])
        except ValueError:
            errs.append(f"added must be YYYY-MM-DD, got '{fields['added']}'")
    heads = {ln.strip() for ln in body.splitlines()}
    for s in REQUIRED_SECTIONS:
        if s not in heads:
            errs.append(f"missing section '{s}'")
    return errs


def main(argv):
    if len(argv) != 2:
        print("usage: bank_lint.py <folder>", file=sys.stderr)
        return 2
    folder = Path(argv[1])
    if not folder.is_dir():
        print(f"not a folder: {folder}", file=sys.stderr)
        return 2
    files = sorted(folder.glob("*.md"))
    bad = 0
    seen = {}
    for p in files:
        for e in lint_file(p):
            print(f"{p}: {e}")
            bad += 1
        seen.setdefault(p.stem, []).append(p)
    if not files:
        print(f"{folder}: no .md files found")
        bad += 1
    print(f"{len(files)} files checked, {bad} errors")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
