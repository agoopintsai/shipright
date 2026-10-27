---
name: setup
description: Set up Shipright for this project - create or connect the brain repo, choose red zones, write shipright.yaml, and show the gate once. Run it when Shipright says it is not configured or its config is broken.
argument-hint: "[--check]"
---

# /shipright:setup

You are guiding the user through setup in a conversation. Ask one question at a time, offer a default for each, and wait for the answer. Plain English; gloss any term once ("red zone = a path where edits need a signed decision first").

## Step 0: check mode

If `shipright.yaml` exists in the project root (or the user passed `--check`), do NOT run setup. Instead check and print a checklist with a tick or cross per line, then stop:

- Config parses and has `brain`, `product`, `red_zones`, `banks`, `models`.
- The `brain` path exists and contains `GOVERNANCE.md`.
- `products/<product>/` exists in the brain and has `DIRECTION.md`.
- Lint passes: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brain_lint.py" <brain>` (errors are crosses, warnings are notes).
- Hooks are loaded: the Shipright banner or gate message appeared this session. If you cannot tell, say so.

For each cross, say in one line how to fix it. If the config is broken, offer to rerun setup from Step 1.

## Step 1: where the brain lives

Ask: "Where should the brain (your project's memory repo) live? Default: `../brain`, next to this project."

- Folder does not exist: copy `${CLAUDE_PLUGIN_ROOT}/brain-template/` there, run `git init` inside it, and continue. Do not commit yet (Step 2 renames things first).
- Folder exists and has `GOVERNANCE.md`: it is a brain. Reuse it and say so.
- Folder exists but is not a brain: stop and ask for a different path.

## Step 2: product name

Ask: "What is this product called? Default: the project folder name." Use lowercase letters, digits and dashes.

If you just created the brain: rename `products/example-product` to `products/<product>`, replace `example-product` in `INDEX.md` and in the `DIRECTION.md`, `MAP.md` and `log.md` headings, and set the first log entry's date to today. Then commit with the message "Brain created by Shipright".

If you reused a brain and `products/<product>/` is missing: copy the template's `products/example-product/` in as `products/<product>`, add a row to `INDEX.md`, and commit "Add <product>".

## Step 3: red zones

Say: "Red zones are paths where I will refuse to edit until a signed decision exists for the current branch. Defaults:"

```
**/migrations/**
**/payment/**
**/billing/**
```

Ask: "Use these? (yes, or tell me what to add or remove)". One "yes" accepts all three. Turn plain-language answers ("anything touching invoices") into globs and read them back for confirmation.

## Step 4: write shipright.yaml

Write it at the project root, exactly this shape (fill in the answers):

```yaml
brain: <brain path>        # relative to project root or absolute
product: <product>
red_zones:
  - "<glob>"
gate: commit
banks: [core]
models:
  judge: inherit
  executor: sonnet
  scout: haiku
```

Then say one sentence: "`gate: commit` means a consensus doc only opens the gate once a human has committed it in the brain; set `gate: file` to relax that." Do not ask a question about it.

## Step 5: self-check

Run the Step 0 checks against what you just wrote (skip the hooks line: they load on the next session start). Print the checklist. If any line fails, fix it before moving on.

## Step 6: demo (ask first)

Ask: "Want a 20-second demo of the gate? I will try to edit a red-zone file so you see a block once."

If yes:
1. Create a scratch file whose path matches a red zone, for example `migrations/0001_shipright_demo.py`, containing a one-line comment.
2. Try to edit it with the Edit tool. Expect a block message. If it is not blocked, tell the user the hooks are not active yet and that restarting the session may be needed.
3. Show the block message and delete the scratch file (and the folder if you created it).
4. Explain in two sentences: the gate stops edits to risky paths until a signed decision exists for the current branch, and it can only say no, never approve. There are two exits (in the default commit tier the decision doc must also be committed by a human in the brain): run `/shipright:grill` to produce the signed decision, or override with a recorded reason via `/shipright:grill --override '<reason>'`.

## Step 7: finish

Ask once: "Want to see Level 2 (modes and delegation)?" If yes, describe `/shipright:mode` and `/shipright:delegate` in two sentences each and stop. If no, end with exactly:

"You're set. Next: /shipright:grill before any red-zone change; /shipright:where whenever you're lost."

## Rules

- Never edit or delete anything outside the brain folder and `shipright.yaml`, except the demo scratch file.
- Never push anywhere. The brain stays local until the user adds a remote.
- If the user is unsure at any step, take the default and say what you chose.
