# Question bank schema

A question bank is a folder of Markdown files. Each file holds exactly one question.

## File name

`<category>-<nn>-<slug>.md`, for example `gatekeeping-01-author-reviewer-identity.md`.

- `category`: one of `first-principles`, `boundaries`, `gatekeeping`.
- `nn`: two-digit number, unique within the category.
- `slug`: lowercase words joined by hyphens.

## Frontmatter

```yaml
---
id: gatekeeping-01-author-reviewer-identity   # must equal the file name without .md
category: gatekeeping                          # first-principles | boundaries | gatekeeping
must_answer: true                              # true | false
added: 2026-10-23                              # YYYY-MM-DD
---
```

`must_answer: true` means `/shipright:grill` may never skip the question or end it with "no answer" silently. An unanswered must-answer question becomes a blocker.

## Body

```markdown
## Question
The question, one decision point, answerable with evidence.

## Why it matters
Generic wording only. No company, product, person or incident names.

## Origin
(optional) Anonymised source, such as a paper citation or "found in a review of a billing change".
```

`## Question` and `## Why it matters` are required. `## Origin` is optional. Keep each file under 25 lines.

## Overlay rule

`banks:` in `shipright.yaml` lists banks in load order. `core` is the plugin's `banks/core`; every other entry is a folder, relative to the project root, with files of the same shape.

- Same `id` in a later bank overrides the earlier one.
- New ids are added.
- Load order is list order.

Validate a folder with `python3 scripts/bank_lint.py <folder>`. The command exits 1 on any error.
