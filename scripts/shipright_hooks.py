#!/usr/bin/env python3
"""Shipright hook engine (see docs/DESIGN.md sections 5-7).

Hook events: session-start, user-prompt-submit, pre-tool-use, stop, subagent-start, subagent-stop.
CLI for skills: `set <mode> [chat word limit]`, `clear`, `status`.

Tools can only say no: this engine denies or asks, it never approves. Always exits 0 for hook
events; internal errors fail open (logged), except the deliberate BROKEN-config deny.
"""
import glob as _glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shipright_config as cfg  # noqa: E402

EXEMPT_EXACT = {"Skill", "AskUserQuestion", "ToolSearch", "SendMessage", "ListAgents", "ScheduleWakeup"}
EXEMPT_PREFIX = ("mcp__ccd_",)
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
LOOKUP_TOOLS = {"Read", "Grep", "Glob", "Bash", "WebFetch", "WebSearch"}
DEEP_LOOKUP_TOOLS = LOOKUP_TOOLS | {"Agent"}
DEEP_OK_AGENTS = {"shipright:scout", "scout", "Explore", "Plan", "claude-code-guide"}
DEFAULT_CHAT_WORDS = 300

MAX_CONCURRENT = 4
MAX_PER_TURN = 8
MAX_DURATION = 600
MAX_AGENTS_KEPT = 50
NOTIFY_MODES = ("delegate", "deep")

# Output-producing tools blocked in chat mode (artifacts, docs, widgets, connector writes).
OUTPUT_TOOL_RE = re.compile(
    r"^(Artifact|SendUserFile)$|show_widget$"
    r"|^mcp__.*(__create|__batch|__update|__export|create_pages|notion-create-pages)$"
)

MODES = {
    "chat": {"quota": 3, "model": "a fast, cheap model", "effort": "low",
             "summary": "chat mode: plain text replies of at most {limit} words; up to 3 lookups per turn; "
                        "no subagents, edits or artifacts; mark answers confirmed or guessed; "
                        "when the quota is spent say the question needs /shipright:deep."},
    "deep": {"quota": 10, "model": "your strongest model", "effort": "high",
             "summary": "deep mode: up to 10 lookups per turn (Agent included); only read-only subagents "
                        "(scout, Explore, Plan, claude-code-guide); no edits (use /shipright:delegate to build)."},
    "delegate": {"quota": 5, "model": "your strongest model", "effort": "high",
                 "summary": "delegate mode: writes go to executor, lookups to scout; up to 5 personal lookups "
                            "per turn; edits ask first; subagents are monitored (more than 4 at once, more than 8 "
                            "per turn, or one over 10 minutes raises an alert and a 'Subagent status:' line)."},
}


# ---------------------------------------------------------------- paths and state

def data_dir():
    d = os.environ.get("CLAUDE_PLUGIN_DATA")
    return Path(d) if d else Path.home() / ".shipright"


def modes_dir():
    return data_dir() / "modes"


def log_error(event):
    try:
        data_dir().mkdir(parents=True, exist_ok=True)
        with open(data_dir() / "hooks.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {event}\n{traceback.format_exc()}\n")
    except Exception:
        pass


def safe_sid(sid):
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(sid)) if sid else None


def flag_path(sid):
    return modes_dir() / f"{safe_sid(sid)}.json"


def read_flag(sid):
    if not sid:
        return None
    try:
        return json.loads(flag_path(sid).read_text())
    except Exception:
        return None


def write_flag(sid, data):
    modes_dir().mkdir(parents=True, exist_ok=True)
    flag_path(sid).write_text(json.dumps(data))


def clear_flag(sid):
    try:
        flag_path(sid).unlink()
    except (FileNotFoundError, TypeError):
        pass


def read_stdin():
    try:
        d = json.loads(sys.stdin.read() or "{}")
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def project_dir_for(d):
    return os.environ.get("CLAUDE_PROJECT_DIR") or d.get("cwd") or os.getcwd()


def emit(obj):
    print(json.dumps(obj))


def pretool(kind, reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": kind, "permissionDecisionReason": reason}})


def message(what, why, exit_):
    """Every deny/ask: what was blocked, why (the rule), and the exit."""
    return f"Blocked: {what}\nWhy: {why}\nExit: {exit_}"


# ---------------------------------------------------------------- red-zone gate

def glob_to_regex(pattern):
    """Translate a glob with ** support into an anchored regex over '/'-separated paths."""
    p = pattern.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    out, i = "", 0
    while i < len(p):
        if p.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif p.startswith("**", i):
            out += ".*"
            i += 2
        elif p[i] == "*":
            out += "[^/]*"
            i += 1
        elif p[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(p[i])
            i += 1
    return re.compile("^" + out + "$")


def match_red_zone(rel_path, zones):
    """Return the first matching glob, or None. A trailing '/**' also matches the directory itself."""
    rel = rel_path.replace(os.sep, "/")
    for z in zones:
        if glob_to_regex(z).match(rel):
            return z
    return None


def target_path(tool_input):
    return tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")


def relative_to_project(path, project_dir):
    """Path relative to the project root, or None when outside the project."""
    base = os.path.realpath(project_dir)
    full = path if os.path.isabs(path) else os.path.join(project_dir, path)
    # realpath on the parent: the target file may not exist yet
    parent, name = os.path.split(os.path.abspath(full))
    full_real = os.path.join(os.path.realpath(parent), name)
    rel = os.path.relpath(full_real, base)
    if rel == ".." or rel.startswith(".." + os.sep):
        return None
    return rel


def current_branch(project_dir):
    # rev-parse fails on a repo with no commits yet; symbolic-ref covers that case.
    for cmd in (["git", "rev-parse", "--abbrev-ref", "HEAD"], ["git", "symbolic-ref", "--short", "HEAD"]):
        try:
            r = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, timeout=5)
            b = r.stdout.strip()
            if r.returncode == 0 and b and b != "HEAD":
                return b
        except Exception:
            pass
    return "(no branch)"


def consensus_doc_for(conf, branch):
    """Path of a decision doc whose frontmatter `branches:` lists this branch, else None."""
    if branch == "(no branch)":
        return None
    dirs = [Path(conf.brain) / "products" / conf.product / "decisions", Path(conf.brain) / "shared" / "decisions"]
    for d in dirs:
        for f in sorted(_glob.glob(str(d / "*.md"))):
            try:
                fm = cfg.parse_frontmatter(Path(f).read_text(encoding="utf-8"))
            except Exception:
                continue
            branches = fm.get("branches")
            if isinstance(branches, str):
                branches = [branches]
            if isinstance(branches, list) and branch in branches:
                return f
    return None


def red_zone_check(conf, tool_input, project_dir):
    path = target_path(tool_input)
    if not path or not conf.red_zones:
        return None
    rel = relative_to_project(str(path), project_dir)
    if rel is None:
        return None
    zone = match_red_zone(rel, conf.red_zones)
    if not zone:
        return None
    branch = current_branch(project_dir)
    doc = consensus_doc_for(conf, branch)
    if doc:
        return None
    return (f"Blocked: {rel} is a red zone ({zone}).\n"
            f"No consensus doc covers branch {branch}.\n"
            f"Gate tier: {conf.gate}.\n"
            "Exits: run /shipright:grill, or /shipright:grill --override \"<reason>\" "
            "(recorded in the brain log).")


def _git_brain(conf, *args):
    r = subprocess.run(["git", "-C", conf.brain, *args], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "git failed")
    return r.stdout.strip()


def commit_tier_problem(conf, doc, rel, zone, branch):
    """Deny text when the consensus doc fails the commit-tier checks, else None. Git errors deny."""
    head = f"Blocked: {rel} is a red zone ({zone}).\n"
    try:
        _git_brain(conf, "rev-parse", "--show-toplevel")
    except Exception:
        return (head + f"Gate tier is commit but the brain at {conf.brain} is not a git repository.\n"
                "Exits: git init the brain and commit the consensus doc, or set gate: file in shipright.yaml.")
    not_committed = (head + f"Consensus doc {doc} covers branch {branch} but is not committed (gate tier: commit).\n"
                     "Exits: a human commits the doc in the brain repo, or set gate: file.")
    try:
        if not _git_brain(conf, "log", "-1", "--format=%H", "--", doc):
            return not_committed
        if _git_brain(conf, "status", "--porcelain", "--", doc):
            return not_committed
        if conf.ai_git_email:
            author = _git_brain(conf, "log", "-1", "--format=%ae", "--", doc)
            if author.lower() == conf.ai_git_email.lower():
                return (head + f"Consensus doc {doc} was committed by the AI identity {author} "
                        "(gate tier: commit).\n"
                        "Exits: a human commits the doc in the brain repo, or set gate: file.")
    except Exception:
        return not_committed
    return None


BRAIN_COMMIT_RE = re.compile(r"git\s+(-C\s+\S+\s+)?commit\b")


def brain_commit_check(conf, tool_input):
    cmd = tool_input.get("command")
    if not isinstance(cmd, str) or not BRAIN_COMMIT_RE.search(cmd):
        return None
    refs = {conf.brain, conf.brain_raw.rstrip("/")}
    refs.discard("")
    if any(r in cmd for r in refs):
        return ("Blocked: committing to the brain is a human action (gate tier: commit).\n"
                "Exit: run the commit yourself in a terminal.")
    return None


def gate_check(conf, tool_input, project_dir, tool="Edit"):
    """Red-zone gate for the configured tier. Returns None or a deny string."""
    if conf.gate == "commit" and tool == "Bash":
        return brain_commit_check(conf, tool_input)
    reason = red_zone_check(conf, tool_input, project_dir)
    if reason is not None or conf.gate != "commit":
        return reason
    path = target_path(tool_input)
    if not path or not conf.red_zones:
        return None
    rel = relative_to_project(str(path), project_dir)
    zone = match_red_zone(rel, conf.red_zones) if rel else None
    if not zone:
        return None
    branch = current_branch(project_dir)
    return commit_tier_problem(conf, consensus_doc_for(conf, branch), rel, zone, branch)


# ---------------------------------------------------------------- Workflow guard

STRONG_RE = re.compile(r"opus|fable|mythos", re.I)
CALL_RE = re.compile(r"(?<![\w.$])agent\s*\(")
KEY_RE = re.compile(r"\bmodel\s*:")
SHORT_RE = re.compile(r"[{,]\s*model\s*(?=[,}])")


def mask_js(src):
    """Blank out string contents and comments (keeping quotes, newlines and length)."""
    out = list(src)
    n = len(src)

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    def scan(i, stop_at_brace):
        depth = 0
        while i < n:
            c = src[i]
            if c == "/" and src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                i = j
            elif c == "/" and src.startswith("/*", i):
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                blank(i, j)
                i = j
            elif c in "'\"":
                j = i + 1
                while j < n and src[j] != c and src[j] != "\n":
                    j += 2 if src[j] == "\\" else 1
                blank(i + 1, min(j, n))
                i = j + 1
            elif c == "`":
                i = template(i)
            elif c == "{":
                depth += 1
                i += 1
            elif c == "}":
                if stop_at_brace and depth == 0:
                    return i
                depth -= 1
                i += 1
            else:
                i += 1
        return i

    def template(i):
        j = i + 1
        start = j
        while j < n and src[j] != "`":
            if src[j] == "\\":
                j += 2
            elif src.startswith("${", j):
                blank(start, j)
                end = scan(j + 2, True)
                j = end + 1
                start = j
            else:
                j += 1
        blank(start, min(j, n))
        return j + 1

    scan(0, False)
    return "".join(out)


def match_paren(masked, open_idx):
    depth = 0
    for k in range(open_idx, len(masked)):
        ch = masked[k]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return k
    return len(masked) - 1


def model_value(masked, src, start, end):
    """('lit', text), ('dyn', None), or None when the call has no model key."""
    seg = masked[start:end]
    m = KEY_RE.search(seg)
    if m:
        vs = start + m.end()
        depth, k = 0, vs
        while k < end:
            ch = masked[k]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif ch == "," and depth == 0:
                break
            k += 1
        mv = masked[vs:k].strip()
        if len(mv) >= 2 and mv[0] == mv[-1] and mv[0] in "'\"`" and mv[1:-1].strip() == "":
            body = src[vs:k].strip()[1:-1]
            return ("dyn", None) if (mv[0] == "`" and "${" in body) else ("lit", body)
        return ("dyn", None)
    if SHORT_RE.search(seg):
        return ("dyn", None)
    return None


def workflow_decision(src):
    """Return (kind, reason) for a Workflow script, or None to allow."""
    masked = mask_js(src)
    calls = []
    for m in CALL_RE.finditer(masked):
        open_idx = m.end() - 1
        end = match_paren(masked, open_idx)
        calls.append((src.count("\n", 0, m.start()) + 1, model_value(masked, src, open_idx, end)))
    if not calls:
        return None
    missing = [ln for ln, v in calls if v is None]
    if missing:
        lines = ", ".join(f"L{x}" for x in missing[:10])
        return ("deny", message(
            "this Workflow script",
            f"Every agent() in a Workflow must set model. Found {len(missing)} without (lines: {lines}). "
            "An agent() with no model silently runs on the main session's model.",
            "add model: 'sonnet' or model: 'haiku' to each agent() call"))
    risky = [ln for ln, v in calls if v[0] == "dyn" or STRONG_RE.search(v[1])]
    if risky:
        lines = ", ".join(f"L{x}" for x in risky[:10])
        return ("ask", f"{len(risky)} of {len(calls)} agent() calls use a strong model (opus/fable) or a model "
                       f"value that cannot be checked statically (lines: {lines}). Confirm how many are needed and why.")
    return None


def workflow_source(tool_input):
    if tool_input.get("script"):
        return tool_input["script"]
    sp = tool_input.get("scriptPath")
    if sp:
        with open(os.path.expanduser(sp), encoding="utf-8") as f:
            return f.read()
    return None


# ---------------------------------------------------------------- subagent monitoring

def is_subagent(d):
    if d.get("agent_id") or d.get("agent_type"):
        return True
    return "/subagents/" in str(d.get("transcript_path") or "")


def is_exempt(tool):
    return tool in EXEMPT_EXACT or tool.startswith(EXEMPT_PREFIX)


def notify(flag, msg):
    """Record an alert in the flag (caller writes it) and raise a macOS notification when possible."""
    flag.setdefault("alerts", []).append(msg)
    if os.environ.get("SHIPRIGHT_NO_NOTIFY"):
        return
    if sys.platform == "darwin" and shutil.which("osascript"):
        try:
            safe = msg.replace("\\", " ").replace('"', "'")
            subprocess.run(["osascript", "-e", f'display notification "{safe}" with title "Shipright"'],
                           timeout=3, capture_output=True)
        except Exception:
            pass


def scan_long_running(flag):
    changed, now = False, time.time()
    for aid, a in (flag.get("agents") or {}).items():
        if a.get("end") is None and not a.get("alerted") and now - a.get("start", now) > MAX_DURATION:
            a["alerted"] = True
            notify(flag, f"{a.get('type') or 'subagent'} ({aid}) has run {int((now - a['start']) // 60)} minutes")
            changed = True
    return changed


def prune_agents(flag):
    ag = flag.get("agents") or {}
    if len(ag) > MAX_AGENTS_KEPT:
        keep = sorted(ag.items(), key=lambda kv: kv[1].get("start", 0))[-MAX_AGENTS_KEPT:]
        flag["agents"] = dict(keep)


def on_subagent_start(d, conf):
    sid, aid = d.get("session_id"), d.get("agent_id")
    flag = read_flag(sid)
    if not flag or not aid:
        return
    flag.setdefault("agents", {})[aid] = {"type": d.get("agent_type"), "start": time.time(), "end": None}
    flag["turn_agents"] = int(flag.get("turn_agents", 0)) + 1
    prune_agents(flag)
    if flag.get("mode") in NOTIFY_MODES:
        running = sum(1 for a in flag["agents"].values() if a.get("end") is None)
        if running > MAX_CONCURRENT:
            notify(flag, f"{running} subagents running at once (limit {MAX_CONCURRENT})")
        if flag["turn_agents"] > MAX_PER_TURN:
            notify(flag, f"{flag['turn_agents']} subagents started this turn (limit {MAX_PER_TURN})")
    write_flag(sid, flag)


def on_subagent_stop(d, conf):
    sid, aid = d.get("session_id"), d.get("agent_id")
    flag = read_flag(sid)
    if not flag or not aid:
        return
    now = time.time()
    a = flag.setdefault("agents", {}).setdefault(aid, {"type": d.get("agent_type"), "start": now})
    a["end"] = now
    dur = d.get("duration_seconds")
    a["duration"] = float(dur) if isinstance(dur, (int, float)) else now - a.get("start", now)
    prune_agents(flag)
    if flag.get("mode") in NOTIFY_MODES and a["duration"] > MAX_DURATION and not a.get("alerted"):
        a["alerted"] = True
        notify(flag, f"{a.get('type') or 'subagent'} ({aid}) ran {int(a['duration'] // 60)} minutes")
    write_flag(sid, flag)


# ---------------------------------------------------------------- prompt parsing and banner

def parse_prompt(prompt):
    """('set', mode[, limit]) / ('clear',) / None, from a typed /shipright:... command."""
    p = (prompt or "").strip()
    m = re.fullmatch(r"/shipright:chat(?:\s+(\d+))?", p)
    if m:
        return ("set", "chat", int(m.group(1))) if m.group(1) and int(m.group(1)) > 0 else ("set", "chat")
    if p == "/shipright:deep":
        return ("set", "deep")
    if p == "/shipright:delegate":
        return ("set", "delegate")
    m = re.fullmatch(r"/shipright:mode\s+(\S+)(?:\s+(\d+))?", p)
    if m:
        if m.group(1) == "off":
            return ("clear",)
        if m.group(1) in MODES:
            if m.group(1) == "chat" and m.group(2) and int(m.group(2)) > 0:
                return ("set", "chat", int(m.group(2)))
            return ("set", m.group(1))
    return None


def new_flag(mode, limit=None, old=None):
    nf = {"mode": mode, "set_at": time.time(), "used": 0, "turn_agents": 0}
    for k in ("agents", "alerts"):
        if old and old.get(k):
            nf[k] = old[k]
    if mode == "chat":
        nf["limit"] = limit or DEFAULT_CHAT_WORDS
    return nf


def banner(conf, flag):
    gate = "on" if conf.red_zones else "off (no red zones)"
    if flag and flag.get("mode") in MODES:
        mode = flag["mode"]
        q = MODES[mode]["quota"]
        head = f"mode: {mode} ({int(flag.get('used', 0))}/{q} lookups)"
    else:
        head = "mode: off"
    return f"Shipright · {head} · gate: {gate} · brain: {conf.brain_raw}"


# ---------------------------------------------------------------- event handlers

def on_session_start(d, conf):
    sid = d.get("session_id")
    if sid:
        modes_dir().mkdir(parents=True, exist_ok=True)
        (modes_dir() / "current").write_text(str(sid))
        env_file = os.environ.get("CLAUDE_ENV_FILE")
        if env_file:
            with open(env_file, "a") as f:
                f.write(f"export SHIPRIGHT_SESSION={safe_sid(sid)}\n")
    try:
        cutoff = time.time() - 7 * 86400
        for p in modes_dir().glob("*.json"):
            if p.stat().st_mtime < cutoff:
                p.unlink()
    except Exception:
        pass


def context(text):
    emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}})


def on_user_prompt(d, conf):
    sid = d.get("session_id")
    if conf.state == cfg.UNCONFIGURED:
        return context("Shipright: not configured for this project. Run /shipright:setup")
    if conf.state == cfg.BROKEN:
        return context(f"Shipright config is broken: {conf.reason}. Run /shipright:setup to repair.")
    if not sid:
        return
    modes_dir().mkdir(parents=True, exist_ok=True)
    (modes_dir() / "current").write_text(str(sid))
    act = parse_prompt(d.get("prompt"))
    if act:
        if act[0] == "set":
            write_flag(sid, new_flag(act[1], act[2] if len(act) > 2 else None, read_flag(sid)))
        else:
            clear_flag(sid)
    flag = read_flag(sid)
    if flag and flag.get("mode") in MODES:
        flag["used"] = 0
        flag["turn_agents"] = 0
        if flag["mode"] in NOTIFY_MODES:
            scan_long_running(flag)
        write_flag(sid, flag)
        rules = MODES[flag["mode"]]["summary"].format(limit=flag.get("limit") or DEFAULT_CHAT_WORDS)
        tag = f"End your reply with the marker [{flag['mode']}]."
        return context(f"{banner(conf, flag)}\nMode rules: {rules} {tag}")
    context(banner(conf, None))


def on_pre_tool_use(d, conf):
    tool = d.get("tool_name") or ""
    ti = d.get("tool_input") or {}
    if conf.state == cfg.UNCONFIGURED:
        return
    if conf.state == cfg.BROKEN:
        if tool in EDIT_TOOLS:
            pretool("deny", f"Shipright config is broken: {conf.reason}. Run /shipright:setup to repair.")
        return

    if tool in EDIT_TOOLS or tool == "Bash":
        reason = gate_check(conf, ti, conf.project_dir, tool)
        if reason:
            return pretool("deny", reason)

    sid = d.get("session_id")
    flag = read_flag(sid)
    mode = flag.get("mode") if flag else None
    if mode not in MODES:
        mode = None

    if tool == "Workflow" and mode not in ("chat", "deep"):
        res = workflow_decision(workflow_source(ti) or "")
        if res:
            return pretool(*res)

    if not mode:
        return
    sub = is_subagent(d)
    if sub:  # subagent calls are not counted; edits are still denied in chat/deep
        if mode in ("chat", "deep") and tool in EDIT_TOOLS:
            return pretool("deny", message(
                f"{tool} from a subagent",
                f"{mode} mode never edits, and subagents inherit that rule",
                "switch with /shipright:delegate (or /shipright:mode off) to allow edits"))
        return
    if is_exempt(tool):
        return
    if mode in NOTIFY_MODES and scan_long_running(flag):
        write_flag(sid, flag)
    used, quota = int(flag.get("used", 0)), MODES[mode]["quota"]

    if mode == "chat":
        if tool in ("Agent", "Workflow"):
            return pretool("deny", message(f"{tool} call", "chat mode does not run subagents",
                                           "ask for /shipright:deep to research with subagents"))
        if tool in EDIT_TOOLS or OUTPUT_TOOL_RE.search(tool):
            return pretool("deny", message(f"{tool} call", "chat mode replies in plain text only: no edits, "
                                           "artifacts or documents", "switch with /shipright:delegate to build, "
                                           "or /shipright:mode off"))
        if tool in LOOKUP_TOOLS:
            if used >= quota:
                return pretool("deny", message(
                    f"{tool} lookup", f"chat mode allows {quota} lookups per turn and {quota}/{quota} are used",
                    "answer from what you found and mark guesses as guesses; the user can say /shipright:deep "
                    "for more research"))
            flag["used"] = used + 1
            write_flag(sid, flag)
        return

    if mode == "deep":
        if tool == "Workflow":
            return pretool("deny", message("Workflow call", "deep mode only allows read-only subagents",
                                           "use /shipright:delegate to run a Workflow"))
        if tool in EDIT_TOOLS:
            return pretool("deny", message(f"{tool} call", "deep mode never edits",
                                           "switch with /shipright:delegate to build"))
        if tool == "Agent" and ti.get("subagent_type") not in DEEP_OK_AGENTS:
            return pretool("deny", message(
                f"Agent of type {ti.get('subagent_type')!r}",
                "deep mode only allows read-only subagents (scout, Explore, Plan, claude-code-guide)",
                "dispatch shipright:scout instead, or switch with /shipright:delegate"))
        if tool in DEEP_LOOKUP_TOOLS:
            if used >= quota:
                return pretool("deny", message(
                    f"{tool} lookup", f"deep mode allows {quota} lookups per turn and {quota}/{quota} are used",
                    "answer with what you have; the next user message resets the count"))
            flag["used"] = used + 1
            write_flag(sid, flag)
        return

    if mode == "delegate":
        if tool in EDIT_TOOLS:
            return pretool("ask", f"delegate mode: {tool} should normally go to the executor subagent. "
                                  "Approve only for a trivial one-file edit.")
        if tool in LOOKUP_TOOLS:
            if used >= quota:
                return pretool("deny", message(
                    f"{tool} lookup",
                    f"delegate mode allows {quota} personal lookups per turn and {quota}/{quota} are used",
                    "write a brief and dispatch shipright:scout (batch the queries), or /shipright:deep to look yourself"))
            flag["used"] = used + 1
            write_flag(sid, flag)
        return  # Agent: unlimited, monitored by SubagentStart/Stop


def last_assistant_text(path):
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if isinstance(o, dict) and o.get("type") == "assistant":
                last = o
    if last is None:
        return None
    content = (last.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    return "".join(b.get("text", "") for b in content
                   if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))


def on_stop(d, conf):
    if conf.state != cfg.OK or d.get("stop_hook_active") is True:
        return
    sid = d.get("session_id")
    flag = read_flag(sid)
    if not flag:
        return
    if flag.get("alerts") and flag.get("mode") in NOTIFY_MODES:
        alerts = flag["alerts"]
        longest = int(max([a.get("duration") or 0 for a in (flag.get("agents") or {}).values()] or [0]))
        flag["alerts"] = []
        write_flag(sid, flag)
        return emit({"decision": "block", "reason":
                     "Subagent alert. Append one line to your reply starting with \"Subagent status:\" covering: "
                     + "; ".join(alerts)
                     + f"; {int(flag.get('turn_agents', 0))} started this turn, longest {longest}s."})
    if flag.get("mode") != "chat":
        return
    path = d.get("transcript_path")
    if not path:
        return
    text = last_assistant_text(path)
    if text is None:
        return
    limit = int(flag.get("limit") or DEFAULT_CHAT_WORDS)
    n = len(text.split())
    if n > limit:
        emit({"decision": "block", "reason":
              f"chat mode limits replies to {limit} words (this one is {n}). Rewrite it shorter: "
              "conclusion first, then only the reasons that matter."})


HANDLERS = {
    "session-start": on_session_start,
    "user-prompt-submit": on_user_prompt,
    "pre-tool-use": on_pre_tool_use,
    "stop": on_stop,
    "subagent-start": on_subagent_start,
    "subagent-stop": on_subagent_stop,
}


# ---------------------------------------------------------------- CLI for skills

def cli_session():
    sid = os.environ.get("SHIPRIGHT_SESSION")
    if sid:
        return sid
    try:
        return (modes_dir() / "current").read_text().strip() or None
    except Exception:
        return None


def cli(cmd, args):
    sid = cli_session()
    if cmd == "set":
        if not args or args[0] not in MODES:
            print(f"usage: shipright_hooks.py set <{'|'.join(MODES)}> [chat word limit]", file=sys.stderr)
            return 2
        if not sid:
            print("No session found (no SHIPRIGHT_SESSION and no modes/current). Send any prompt first.",
                  file=sys.stderr)
            return 1
        limit = None
        if args[0] == "chat" and len(args) > 1:
            if not args[1].isdigit() or int(args[1]) <= 0:
                print("word limit must be a positive integer", file=sys.stderr)
                return 2
            limit = int(args[1])
        write_flag(sid, new_flag(args[0], limit, read_flag(sid)))
        r = MODES[args[0]]
        print(f"Mode set to {args[0]} (stays until you switch or the session ends). "
              f"Switch the model menu to {r['model']} with {r['effort']} effort.")
        return 0
    if cmd == "clear":
        clear_flag(sid)
        print("Mode cleared.")
        return 0
    if cmd == "status":
        flag = read_flag(sid)
        if not flag:
            print(f"No mode set (session {sid or 'unknown'}).")
        else:
            print(f"Mode: {flag.get('mode')}, {flag.get('used', 0)}/{MODES[flag['mode']]['quota']} lookups "
                  f"used this turn (session {sid}).")
        return 0
    print(f"unknown command {cmd}", file=sys.stderr)
    return 2


def main(argv):
    if len(argv) < 2:
        print("usage: shipright_hooks.py <event|set|clear|status>", file=sys.stderr)
        return 2
    cmd = argv[1]
    if cmd in ("set", "clear", "status"):
        return cli(cmd, argv[2:])
    handler = HANDLERS.get(cmd)
    if not handler:
        return 0
    d = read_stdin()
    try:
        conf = cfg.load(project_dir_for(d))
        handler(d, conf)
    except Exception:  # fail open
        log_error(cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
