# Contributing

Thank you for helping. Everything in this repo is English and generic: no company, product, person or incident names.

## Getting started

Clone the repo and run the checks below. You need Python 3 only; there are no dependencies.

## Running the checks

```
python3 scripts/blacklist_check.py                 # must report 0 hits
python3 scripts/bank_lint.py banks/core            # validates question files
python3 -m unittest discover -s tests -v           # all tests pass
```

The blacklist check reads the public patterns in `scripts/blacklist.txt`. Maintainers may also keep private patterns in an optional, gitignored `scripts/blacklist.local.txt`; it is loaded when present and never committed.

## Contributing a question to the core bank

1. Copy this template to `banks/core/<category>-<nn>-<slug>.md`. Pick the next free `nn` in the category (`first-principles`, `boundaries` or `gatekeeping`). The schema is in `banks/SCHEMA.md`.

```markdown
---
id: <category>-<nn>-<slug>     # same as the file name without .md
category: <first-principles | boundaries | gatekeeping>
must_answer: false             # true only if skipping the question is dangerous
added: YYYY-MM-DD
---

## Question

One decision point, answerable with evidence.

## Why it matters

What goes wrong when nobody asks, in generic terms.

## Origin

(optional) Anonymised: a paper, or "found while reviewing a change to X".
```

2. Use generic wording only. No names of companies, products, people, tools, dates of incidents. Describe the pattern, not the story.
3. Run `python3 scripts/bank_lint.py banks/core` and the blacklist check, then open a pull request.

### The path from local to core: proven locally first

Questions should earn their place. Start in your own overlay bank, a folder listed in `banks:` in `shipright.yaml`; `/shipright:grill` offers to add a question there at the end of every session. Use it in real sessions. When a question has changed a decision, or caught something nobody had thought of, rewrite it generically and propose it to core. Say in the pull request how it was used. A question that has never been used in a real session is unlikely to be accepted into core.

### What reviewers check

- One question per file, one decision point per question.
- The wording is generic and the file passes the lint.
- It is not a near-duplicate of an existing question (if it sharpens one, propose the change to that file instead).
- It asks for evidence, not opinion, and could change a decision.
- `must_answer: true` is justified: skipping it would be dangerous in most plans.
- Local evidence of use, as described above.

## Pull request expectations

- Keep changes small and focused; one question or one fix per pull request.
- State what changed, why, and anything you decided on your own that the maintainers did not ask for.
- Checks above pass; CI runs the same ones.

## Code of conduct

Be kind, assume good faith, and critique ideas rather than people.

## License

Shipright is licensed under Apache-2.0. By submitting a contribution you agree that it is licensed under the same Apache-2.0 license.
