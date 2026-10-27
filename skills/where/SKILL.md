---
name: where
description: "One sentence on where you are: step, gates, brain, whose move"
---

# /shipright:where

Answer "where am I?" from evidence, not memory. Do not ask the user anything and do not change anything.

## Gather (read-only)

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" status` and read `shipright.yaml` in the project root. Missing file means "not configured". Unparsable file or missing brain path means broken: treat as "not configured" and say run `/shipright:setup`.
2. Current branch: `git branch --show-current`.
3. Consensus doc: any file under `<brain>/products/<product>/decisions/` or `<brain>/shared/decisions/` whose frontmatter `branches:` lists the current branch (the same scan the red-zone gate uses). Note its path, or none.
4. Pull request: if `gh` is available, run `gh pr view --json state,reviewDecision,url,isDraft`. If `gh` is missing or fails, skip and report "none".
5. Last line of `<brain>/products/<product>/log.md` (the last non-empty line), or "nothing yet".

## Pick the step by evidence

- **not configured**: no valid `shipright.yaml`.
- **planning (no consensus yet)**: configured, no consensus doc covers the branch, no PR.
- **spec review (PR open, awaiting approval)**: PR open, not approved, and the PR contains only the consensus doc or spec (no implementation yet).
- **implementing**: consensus doc covers the branch; no PR, or the PR is a draft.
- **code review (PR open after implementation)**: PR open, not approved, and it contains implementation changes.
- **ready to ship (approved)**: PR open and `reviewDecision` is APPROVED.

If evidence is mixed, pick the earliest plausible step and say what you could not verify.

## Answer in exactly this shape, nothing else

```
You are at <step>: <state>.
- Gates: <on|off> (<mode, or "no mode">), tier <file|commit> (from `gate:` in shipright.yaml, default commit)
- Consensus: <doc path or none>
- PR: <url + review state, or none>
- Brain last recorded: <log line or "nothing yet">
Next move: <whose> - <what>
```

`<state>` is one short clause (for example "branch feat/x has a signed decision, no PR yet"). Gates are "on" when the config is valid, "off" otherwise. "Next move" names the human or the AI and one action, for example "Human - run /shipright:grill" or "Human - approve the PR on GitHub".
