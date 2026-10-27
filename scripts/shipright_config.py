#!/usr/bin/env python3
"""Shipright config loader: reads <project>/shipright.yaml (see docs/DESIGN.md section 4).

No third-party YAML dependency: a tiny parser handles the flat schema we use
(scalars, inline or block lists of strings, and one level of nested maps).
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

UNCONFIGURED = "UNCONFIGURED"
BROKEN = "BROKEN"
OK = "OK"

CONFIG_NAME = "shipright.yaml"


class YamlError(ValueError):
    pass


def _strip_comment(line):
    """Drop a trailing '# comment' that is not inside quotes."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _scalar(text):
    t = text.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "'\"":
        return t[1:-1]
    if t in ("true", "True"):
        return True
    if t in ("false", "False"):
        return False
    return t


def _inline_list(text):
    t = text.strip()
    if not (t.startswith("[") and t.endswith("]")):
        raise YamlError(f"bad inline list: {text!r}")
    inner = t[1:-1].strip()
    if not inner:
        return []
    items, cur, quote = [], "", None
    for ch in inner:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            cur += ch
        elif ch == ",":
            items.append(_scalar(cur))
            cur = ""
        else:
            cur += ch
    if quote:
        raise YamlError(f"unterminated quote in list: {text!r}")
    if cur.strip():
        items.append(_scalar(cur))
    return items


def _split_key(text):
    """Split 'key: value' on the first colon outside quotes. Returns (key, value) or None."""
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == ":" and (i + 1 == len(text) or text[i + 1] in " \t"):
            return text[:i].strip(), text[i + 1:].strip()
    return None


def parse_yaml(text):
    """Parse the flat subset. Returns a dict; raises YamlError on anything it cannot read."""
    lines = []
    for raw in text.splitlines():
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError("tabs are not allowed for indentation")
        stripped = _strip_comment(raw).rstrip()
        if stripped.strip():
            lines.append((len(stripped) - len(stripped.lstrip()), stripped.strip()))
    result = {}
    i = 0
    while i < len(lines):
        indent, body = lines[i]
        if indent != 0:
            raise YamlError(f"unexpected indentation: {body!r}")
        kv = _split_key(body)
        if kv is None or not kv[0]:
            raise YamlError(f"expected 'key: value', got {body!r}")
        key, value = kv
        i += 1
        if value:
            result[key] = _inline_list(value) if value.startswith("[") else _scalar(value)
            continue
        # block value: list or nested map, determined by the first child
        if i >= len(lines) or lines[i][0] == 0:
            result[key] = None
            continue
        child_indent = lines[i][0]
        if lines[i][1].startswith("- ") or lines[i][1] == "-":
            items = []
            while i < len(lines) and lines[i][0] == child_indent and lines[i][1].startswith("-"):
                items.append(_scalar(lines[i][1][1:]))
                i += 1
            result[key] = items
        else:
            sub = {}
            while i < len(lines) and lines[i][0] == child_indent:
                skv = _split_key(lines[i][1])
                if skv is None or not skv[0]:
                    raise YamlError(f"expected 'key: value' under {key!r}, got {lines[i][1]!r}")
                sub[skv[0]] = _inline_list(skv[1]) if skv[1].startswith("[") else _scalar(skv[1])
                i += 1
            result[key] = sub
        if i < len(lines) and lines[i][0] != 0:
            raise YamlError(f"unexpected indentation: {lines[i][1]!r}")
    return result


def parse_frontmatter(text):
    """Return the parsed frontmatter dict of a Markdown file, or {} if none or unreadable."""
    if not text.startswith("---"):
        return {}
    m = re.match(r"---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)", text, re.S)
    if not m:
        return {}
    try:
        return parse_yaml(m.group(1))
    except YamlError:
        return {}


@dataclass
class ConfigResult:
    state: str
    reason: str = ""
    project_dir: str = ""
    brain_raw: str = ""
    brain: str = ""
    product: str = ""
    red_zones: list = field(default_factory=list)
    banks: list = field(default_factory=lambda: ["core"])
    models: dict = field(default_factory=dict)
    gate: str = "commit"
    ai_git_email: str = ""


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def load(project_dir):
    """Load <project_dir>/shipright.yaml and classify it as UNCONFIGURED, BROKEN or OK."""
    project_dir = str(project_dir)
    path = Path(project_dir) / CONFIG_NAME
    if not path.is_file():
        return ConfigResult(UNCONFIGURED, "no shipright.yaml", project_dir)
    try:
        data = parse_yaml(path.read_text(encoding="utf-8"))
    except (YamlError, OSError, UnicodeDecodeError) as e:
        return ConfigResult(BROKEN, f"shipright.yaml cannot be parsed ({e})", project_dir)
    for key in ("brain", "product"):
        v = data.get(key)
        if not isinstance(v, str) or not v.strip():
            return ConfigResult(BROKEN, f"required key '{key}' is missing in shipright.yaml", project_dir)
    brain_raw = data["brain"].strip()
    brain = Path(os.path.expanduser(brain_raw))
    if not brain.is_absolute():
        brain = Path(project_dir) / brain
    brain = Path(os.path.abspath(brain))
    if not brain.is_dir():
        return ConfigResult(BROKEN, f"brain directory does not exist: {brain_raw}", project_dir)
    gate = data.get("gate")
    gate = "commit" if gate is None else str(gate).strip()
    if gate == "github":
        return ConfigResult(BROKEN, "gate: github is not implemented in v0.1 (see docs/github-gate.md); "
                            "use file or commit", project_dir)
    if gate not in ("file", "commit"):
        return ConfigResult(BROKEN, f"unknown gate tier {gate!r} (use file or commit)", project_dir)
    email = data.get("ai_git_email")
    email = email.strip() if isinstance(email, str) else ""
    models = data.get("models") if isinstance(data.get("models"), dict) else {}
    banks = _as_list(data.get("banks")) or ["core"]
    return ConfigResult(
        OK, "", project_dir, brain_raw, str(brain), data["product"].strip(),
        _as_list(data.get("red_zones")), banks, {k: str(v) for k, v in models.items()},
        gate, email,
    )
