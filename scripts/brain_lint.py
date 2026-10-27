#!/usr/bin/env python3
"""brain_lint: validate a Shipright brain repo.

Usage: python3 brain_lint.py <brain_path> [--graph out.json]

Errors (exit 1): missing or invalid frontmatter, missing required field, bad
`memory` or `status`, duplicate id, dangling relates_to/supersedes/superseded-by.
Warnings (exit 0): last_verified older than 180 days, product dir without
DIRECTION.md, orphan doc (no edges in or out).

Pure standard library. Frontmatter parser handles flat keys, inline lists
([a, b]) and block lists ("- a").
"""
import datetime
import json
import re
import sys
from pathlib import Path

REQUIRED = ("id", "memory", "source", "status", "last_verified")
MEMORY = {"episodic", "semantic", "procedural"}
STATUS_RE = re.compile(r"^(active|deprecated|superseded-by:\S+)$")
EDGE_KEYS = ("relates_to", "supersedes")
SKIP_NAMES = {"MAP.md", "DIRECTION.md", "log.md", "README.md", "INDEX.md"}
STALE_DAYS = 180


def _scalar(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _inline_list(s):
    inner = s.strip()[1:-1].strip()
    if not inner:
        return []
    return [_scalar(x) for x in inner.split(",") if x.strip()]


def parse_frontmatter(text):
    """Return (data, key_lines, error). data maps key -> str | list[str]."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, {}, "missing frontmatter (file must start with '---')"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, {}, "frontmatter is not closed with '---'"
    data, key_lines, cur = {}, {}, None
    for i in range(1, end):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if m and not raw[0].isspace():
            cur, val = m.group(1), re.sub(r"\s+#.*$", "", m.group(2)).strip()
            key_lines[cur] = i + 1
            if val == "":
                data[cur] = []  # may be filled by a block list below
            elif val.startswith("["):
                if not val.endswith("]"):
                    return None, key_lines, f"line {i + 1}: unterminated list"
                data[cur] = _inline_list(val)
            else:
                data[cur] = _scalar(val)
        elif raw.lstrip().startswith("- ") and cur is not None and isinstance(data.get(cur), list):
            data[cur].append(_scalar(raw.lstrip()[2:]))
        else:
            return None, key_lines, f"line {i + 1}: cannot parse '{raw.strip()}'"
    return data, key_lines, None


def as_list(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def iter_docs(root):
    for sub in ("products", "shared"):
        base = root / sub
        if base.is_dir():
            for p in sorted(base.rglob("*.md")):
                if p.name not in SKIP_NAMES:
                    yield p


def lint(root, today=None):
    today = today or datetime.date.today()
    errors, warnings = [], []  # (relpath, line, message)
    docs = {}  # id -> dict(path, fm)
    count = 0

    def rel(p):
        return p.relative_to(root).as_posix()

    for p in iter_docs(root):
        count += 1
        r = rel(p)
        fm, kl, err = parse_frontmatter(p.read_text(encoding="utf-8"))
        if err:
            errors.append((r, 1, err))
            continue
        for k in REQUIRED:
            if fm.get(k) in (None, "", []):
                errors.append((r, 1, f"missing required field '{k}'"))
        if fm.get("memory") and fm["memory"] not in MEMORY:
            errors.append((r, kl.get("memory", 1),
                           f"bad memory '{fm['memory']}' (use episodic|semantic|procedural)"))
        st = fm.get("status")
        if st and (isinstance(st, list) or not STATUS_RE.match(st)):
            errors.append((r, kl.get("status", 1),
                           f"bad status '{st}' (use active|deprecated|superseded-by:<id>)"))
        lv = fm.get("last_verified")
        if lv and not isinstance(lv, list):
            try:
                d = datetime.date.fromisoformat(lv)
                if (today - d).days > STALE_DAYS:
                    warnings.append((r, kl.get("last_verified", 1),
                                     f"last_verified {lv} is older than {STALE_DAYS} days"))
            except ValueError:
                errors.append((r, kl.get("last_verified", 1),
                               f"last_verified '{lv}' is not a YYYY-MM-DD date"))
        did = fm.get("id")
        if did and not isinstance(did, list):
            if did in docs:
                errors.append((r, kl.get("id", 1),
                               f"duplicate id '{did}' (also in {docs[did]['path']})"))
            else:
                docs[did] = {"path": r, "fm": fm, "kl": kl}

    out, inc = {i: [] for i in docs}, {i: [] for i in docs}
    for did, info in docs.items():
        fm, kl, r = info["fm"], info["kl"], info["path"]
        targets = [(k, t) for k in EDGE_KEYS for t in as_list(fm.get(k))]
        st = fm.get("status", "")
        if isinstance(st, str) and st.startswith("superseded-by:"):
            targets.append(("superseded-by", st.split(":", 1)[1].strip()))
        for key, t in targets:
            line = kl.get("status" if key == "superseded-by" else key, 1)
            if t not in docs:
                errors.append((r, line, f"dangling {key} target '{t}'"))
            else:
                out[did].append(t)
                inc[t].append(did)
    for did, info in docs.items():
        if not out[did] and not inc[did]:
            warnings.append((info["path"], 1, "orphan doc: no relates_to/supersedes edges in or out"))

    pdir = root / "products"
    if pdir.is_dir():
        for d in sorted(x for x in pdir.iterdir() if x.is_dir()):
            if not (d / "DIRECTION.md").is_file():
                warnings.append((rel(d), 1, "product has no DIRECTION.md"))

    graph = {
        "nodes": {i: {"path": v["path"], "status": v["fm"].get("status")} for i, v in docs.items()},
        "edges": out,
        "backlinks": inc,
    }
    return errors, warnings, count, graph


def main(argv):
    args = argv[1:]
    graph_path = None
    if "--graph" in args:
        i = args.index("--graph")
        if i + 1 >= len(args):
            print("usage: brain_lint.py <brain_path> [--graph out.json]", file=sys.stderr)
            return 2
        graph_path = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print("usage: brain_lint.py <brain_path> [--graph out.json]", file=sys.stderr)
        return 2
    root = Path(args[0]).resolve()
    if not root.is_dir():
        print(f"{args[0]}: ERROR: brain path does not exist", file=sys.stderr)
        return 2
    errors, warnings, count, graph = lint(root)
    for r, ln, m in errors:
        print(f"{r}:{ln}: ERROR: {m}")
    for r, ln, m in warnings:
        print(f"{r}:{ln}: WARN: {m}")
    if graph_path:
        Path(graph_path).write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"brain-lint: {count} docs, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
