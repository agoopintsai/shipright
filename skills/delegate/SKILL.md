---
name: delegate
description: Delegate mode. The main session judges, scouts read and search, executors write and run; saves the expensive model's quota. Use for "/shipright:delegate", "delegate mode", or when about to do large read or write work by hand.
---

# /shipright:delegate

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" set delegate` and relay the one-line output (switch the model menu to your strongest model). End every reply with the marker `[delegate]`.

## What the hooks enforce

1. Edit, Write, NotebookEdit: ask first. Writes belong to an executor.
2. More than 5 personal lookups (Read, Grep, Glob, Bash, WebFetch, WebSearch) in one turn: denied. Dispatch a scout.
3. Agent is neither blocked nor counted, but monitored: more than 4 concurrent, more than 8 this turn, or one over 10 minutes raises an alert, and your reply must end with a line `Subagent status: ...`.

## Who does what

| Role | Does | Model |
|---|---|---|
| Judge (this session) | Clarify, decompose, decide, review, synthesise, answer the human | the strong model |
| `shipright:scout` | Read files, search code, check docs and the web, read-only commands | haiku |
| `shipright:executor` | Write code, edit files, run commands and tests | sonnet |

Trivial work stays inline: a one or two line, single-file change that needs no research, or one short file you must read line by line to decide. A spawn has fixed overhead.

## Brief format (every dispatch)

```
OBJECTIVE: one sentence, what is wanted
SCOPE: exact paths, globs or URLs (executors may touch only these)
CONTEXT: facts you already know, pasted in so the worker does not re-discover them
REPORT: the shape of the answer and a line limit
DON'T: rabbit holes to avoid
```

## Doctrine

- Never spawn without a written brief. Merge related small queries into one scout.
- At most 4 workers in parallel; a Workflow's agents count too. Prefer few large briefs.
- Every `agent()` in a Workflow must set `model` ('sonnet' or 'haiku'). Missing is denied by the hook; opus or fable asks first. Say how many and why before using a strong model.
- Reports are at most 40 lines. Anything longer goes to a scratch file and the report names the path.
- Trust but spot-check: verify load-bearing claims by pointer (`path:line`); do not re-read whole files.
- Retry a failed worker once with a fixed brief, then escalate the model or take over, and say so.
- Local heavy work (test suites, browsers, containers) runs one worker at a time.
- Executors never merge and never open PRs unless the brief says so. Review the diff yourself before telling the human it is done.
- Judgement, design trade-offs and grilling stay in this session; do not delegate them.
