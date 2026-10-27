# Shipright

**Ship it right, keep shipping.**

Shipright is a Claude Code plugin plus a small brain repo that make continuous delivery of AI-written software something a human can stand behind. AI drafts, humans sign, and tools can only say no: hooks, gates, CI and lint block bad moves but never approve anything. The human's job shrinks to the few decisions that matter.

See the picture: [docs/concept.html](docs/concept.html). Full design contract: [docs/DESIGN.md](docs/DESIGN.md).

Why it exists: [docs/STORY.md](docs/STORY.md).

## Five ideas

1. **Humans are the bottleneck**, so they only make the decisions that matter: what to build, approve the spec, approve the code, and write the why.
2. **Humans and AI supervise each other**: the AI grills the human before work starts; the human reviews what the AI produces.
3. **The brain fills the gaps in human memory**: decisions and their reasons live in a repo that outlasts any session.
4. **Everything goes up as a PR, reviewed twice**: first the spec, then the code. The plugin enforces the commit layer today; the GitHub layer is tier `github` (roadmap).
5. **Tools only have veto power**: a gate can refuse an edit, never approve one.

## Install

```
/plugin marketplace add agoopintsai/shipright
/plugin install shipright@shipright
/shipright:setup
```

The gates are Claude Code hooks. If you install Shipright from the Claude directory on claude.ai or Cowork, you get the skills (grill, where, modes) but not the gates.

## Your first 30 minutes

`/shipright:setup` asks one question at a time, with a default for each:

1. Where the brain lives (default `../brain`; it is created from the template if missing).
2. The product name (default: the project folder name).
3. Red zones: paths where edits are refused until a signed decision exists (defaults `**/migrations/**`, `**/payment/**`, `**/billing/**`).

It writes `shipright.yaml`, runs a self-check, then offers a 20-second **demo**: it tries to edit a red-zone file so you see one block, and tells you the two exits.

Then run your first **grill**: `/shipright:grill` on a real plan. Claude lays the plan out as a decision tree, questions you node by node, shows where its own answers might be wrong, and hands you a one-page sign-off sheet. When you sign, a consensus document is written to the brain with `branches: [<your branch>]`, and the gate opens for that branch.

## Levels

Shipright discloses itself gradually (DESIGN section 10).

- **Level 1**: `/shipright:setup`, `/shipright:grill`, the brain. This is all you need to start.
- **Level 2** (optional): `/shipright:mode chat|deep|delegate|off` and `/shipright:delegate`, plus the scout and executor agents. Setup asks once whether to show it.
- **Level 3**: governance of the brain and contributing questions back to the core bank (see [CONTRIBUTING.md](CONTRIBUTING.md)).

Lost at any point? `/shipright:where`.

## What's in the box

| Skill | What it does |
|---|---|
| `/shipright:setup` | Creates or connects the brain, picks red zones, writes `shipright.yaml`, shows the gate once |
| `/shipright:grill` | Reverse interrogation of a plan, ends in a signed consensus document or a recorded override |
| `/shipright:grilling` | The bare turn-by-turn questioning engine: no question bank, no document |
| `/shipright:where` | One sentence: your step, gates, brain, and whose move it is |
| `/shipright:mode` | Show or switch chat, deep, delegate, or off; enforced by hooks |
| `/shipright:chat` | Plain-text answers, 3 lookups per turn, no edits |
| `/shipright:deep` | Research mode, 10 lookups, read-only subagents only |
| `/shipright:delegate` | Judge in the main session, scouts read, executors write |

Also included: the `scout` and `executor` agents, the core question banks, the brain template, a `brain-lint` GitHub Action, and the hook engine.

## How a block looks

```
Blocked: migrations/0001_example.py is a red zone (**/migrations/**).
No consensus doc covers branch feat/example.
Exits: run /shipright:grill, or /shipright:grill --override "<reason>" (recorded in the brain log).
```

Every block says what was stopped, why, and how to get out.

## Gate tiers

Set `gate:` in `shipright.yaml`. The default is `commit`.

| Tier | Gate opens when | What the human does | Enforced in v0.1 |
|---|---|---|---|
| `file` | A consensus doc listing the branch exists in the brain | Signs in chat | Yes |
| `commit` | The doc exists, is committed and clean in the brain repo (and, if `ai_git_email` is set, was not committed by that identity) | Commits the doc in the brain, not the AI | Yes, default |
| `github` | The spec PR is approved on GitHub | Approves the PR | Roadmap, see [docs/github-gate.md](docs/github-gate.md) |

In `commit` tier the AI also cannot run `git commit` against the brain from Bash.

## Known limitations

- Bash edits (`sed`, `echo >`) are not intercepted; the gate watches Edit, Write and NotebookEdit.
- `cd brain && git commit` in a single Bash call is not caught.
- Hooks fail open on internal errors by design (the only deliberate denies are a broken config and the gate itself).

## The brain

The brain is a plain Markdown repo that sits beside your product. It holds signed decisions with their reasons, templates and question banks, and an append-only progress log. Governance, frontmatter rules and lint are described in [brain-template/GOVERNANCE.md](brain-template/GOVERNANCE.md).

## Roadmap

Not in v0.1 (DESIGN section 12):

- Automatic milestone write-back to the brain.
- A weekly gate report.
- `/why`.
- Task-tracker, chat and cloud-provider adapters.
- Non-English docs.
- Tier `github`: spec PR approval and merge interception ([docs/github-gate.md](docs/github-gate.md)).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), including the template for proposing a question for the core bank.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
