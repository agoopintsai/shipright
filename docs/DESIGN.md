# Shipright Design Contract

This document is the contract later work follows. If code and this file disagree, fix one of them in the same change.

## 1. Purpose

Shipright enables continuous delivery of software a human can stand behind. AI drafts, humans sign, and tools can only say no.

## 2. Three layers, one spine

- **Human decides.** Says what to build, approves the spec and the code, and writes the WHY.
- **AI judge** (expensive model). Grills the human, writes the spec, delegates, reviews.
- **AI hands** (cheap models). Read, search, write, test.
- **Brain repo** beside them (the spine). It holds decisions plus WHY (human-signed), templates plus question banks, and an append-only progress log.
- **Tools** (hooks, gates, CI, lint) only have veto power. They block; they never approve.

## 3. Repo layout

```
.claude-plugin/{plugin.json,marketplace.json}
hooks/hooks.json
scripts/{shipright_hooks.py,blacklist_check.py,blacklist.txt}
.github/workflows/ci.yml
docs/DESIGN.md
skills/ agents/ banks/core/ brain-template/ tests/
```

Steps 4-7 add:

```
skills/{setup,grill,grilling,mode,chat,deep,delegate,where}/SKILL.md
agents/{scout,executor}.md
banks/core/*.md
banks/SCHEMA.md
brain-template/
.github/actions/brain-lint/
scripts/brain_lint.py
scripts/bank_lint.py
docs/concept.html
LICENSE NOTICE README.md CONTRIBUTING.md
```

## 4. Config: `shipright.yaml`

The ONLY config file, at the project root.

```yaml
brain: ../brain            # path to the brain repo, relative to project root or absolute
product: my-app            # folder name under <brain>/products/
red_zones:                 # globs; editing these requires a consensus doc
  - "**/migrations/**"
  - "**/payment/**"
  - "**/billing/**"
banks: [core]              # question banks to load, in order; later entries override same ids. "core" = plugin banks/core; other entries are paths relative to project root
models:
  judge: inherit
  executor: sonnet
  scout: haiku
```

## 5. Config states and hook behaviour

Fail semantics are decided by the owner:

- **(a) No `shipright.yaml`:** hooks are INERT. UserPromptSubmit adds a one-line banner: `Shipright: not configured for this project. Run /shipright:setup`.
- **(b) `shipright.yaml` exists but is unparsable, or the `brain` path does not exist:** BROKEN. PreToolUse denies Edit/Write/NotebookEdit with reason `Shipright config is broken: <reason>. Run /shipright:setup to repair.`
- **(c) Configured:** modes and the red-zone gate are active.

## 6. Red-zone gate

PreToolUse on Edit/Write/NotebookEdit. If the target path matches any `red_zones` glob AND no consensus doc exists for the current git branch, deny. The message states what was blocked, which rule matched, and two exits:

1. run `/shipright:grill`
2. override with a reason via `/shipright:grill --override '<reason>'` (overrides are appended to `<brain>/products/<product>/log.md`)

Consensus doc detection: any file under `<brain>/products/<product>/decisions/` or `<brain>/shared/decisions/` whose frontmatter has `branches:` containing the current branch name.

### 6.1 Gate tiers

`gate:` in `shipright.yaml` selects how much the doc must prove. Missing means `commit`.

- `file`: the doc exists (the behaviour above).
- `commit` (default): the doc must also be committed and clean in the brain repo, so the AI cannot open the gate by writing the doc itself. Checks, in order: the brain is inside a git work tree; `git log -1 -- <doc>` is non-empty; `git status --porcelain -- <doc>` is empty; and if `ai_git_email` is set, the last commit author differs from it (case-insensitive). Any failure, including a git error, denies; this tier never fails open on git problems. PreToolUse on Bash also denies `git [-C <path>] commit` commands that mention the brain path. Known limit: `cd brain && git commit` in one call is not caught.
- `github`: not implemented in v0.1; config is BROKEN with a pointer to [github-gate.md](github-gate.md).

## 7. Modes (Level 2, optional)

- `chat`: 3 lookups per turn, no writes, short replies.
- `deep`: 10 lookups, read-only subagents allowed, no writes.
- `delegate`: 5 personal lookups, writes ask first, subagents monitored.

State is a flag file per session at `${CLAUDE_PLUGIN_DATA}/modes/<session_id>.json`. No mode set means no quota. Deny messages must be human-readable and name the exit.

## 8. Brain template

Pure Markdown plus one workflow file that calls `agoopintsai/shipright/.github/actions/brain-lint@v0.1`.

```
README.md  GOVERNANCE.md  INDEX.md
products/<product>/{DIRECTION.md,MAP.md,decisions/,log.md}
shared/decisions/
inbox/
templates/{decision.md,consensus.md,spec.md}
```

- Required frontmatter on decision docs: `id`, `memory` (`episodic|semantic|procedural`), `source`, `status` (`active|deprecated|superseded-by:<id>`), `last_verified`.
- Optional frontmatter: `relates_to`, `supersedes`, `branches`.
- Products are discovered by scanning `products/*/`. A product dir without `DIRECTION.md` is a lint WARNING.
- `last_verified` older than 180 days is a WARNING.
- Append-only: updates go in dated `## YYYY-MM-DD update:` sections at the end of the file.

## 9. Question banks

One question per file: `banks/core/<category>-<nn>-<slug>.md`.

- Frontmatter: `id`, `category` (`first-principles|boundaries|gatekeeping`), `must_answer` (bool), `added` (date).
- Body sections: `## Question`, `## Why it matters` (generic wording only, no company incidents), `## Origin` (optional, anonymised).
- Local overlay: project `banks:` entries pointing to a folder of the same shape; the same `id` overrides.
- Growth path: grill's closing question "Should any question from this session join the bank?" writes to the local overlay. Proven questions are PR'd to core using CONTRIBUTING.md's template. `scripts/bank_lint.py` validates the schema in CI.

## 10. Progressive disclosure

- **Level 1:** `/shipright:setup`, `/shipright:grill`, the brain.
- **Level 2:** `/shipright:mode`, `/shipright:delegate`, agents.
- **Level 3:** governance, bank contribution.

`/shipright:setup` enables Level 1 only and asks once whether to show Level 2.

## 11. Confidence devices (v1)

- `/shipright:where`: one sentence saying which step you are at, which gates are on, what the brain last recorded, and whose move it is.
- Every deny says what was blocked, why, and the exit.
- `/shipright:setup` ends with a demo that deliberately edits a red-zone file so the user sees a block once.

## 12. Out of scope for v0.1

- Automatic milestone write-back to the brain (roadmap #1).
- Weekly gate report.
- `/why`.
- Any task-tracker, chat, or cloud-provider adapters.
- Non-English docs.
- Gate tier `github` (spec PR approval, merge interception): see github-gate.md.
