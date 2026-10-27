# Governance

Goal: the brain gets more trustworthy as it grows, not just bigger.

## 1. Single source of truth

Every fact has exactly one authoritative home. Everywhere else, link to it; never copy it. Copies drift, and drift creates two answers to one question. The `source` field of a doc says where the authority lives.

Do not store in the brain: moving state (todo lists, sprint boards), secret values (store only where they live), or details only one product cares about in `shared/`.

## 2. Append-only

Decision docs and logs are never rewritten. To update one, add a section at the end titled `## YYYY-MM-DD update: <title>` and refresh `last_verified`. To correct a wrong statement inline, strike it through and add a dated note, so the record shows what was once believed.

The one exception is `DIRECTION.md`, which is overwritten in place: it is a snapshot of now, not history.

## 3. Writing a decision

One file per decision, in `products/<product>/decisions/` (one product cares) or `shared/decisions/` (several do). Use `templates/decision.md`. Record the alternatives you rejected and the criteria you used, not only the conclusion, so the decision can be re-derived when things change.

AI can fill in the WHAT. The WHY (context, alternatives, criteria) must be written or confirmed by a human, with a date.

## 4. Flag and revalidate

Before proposing something that contradicts an active decision or the DIRECTION file, show that decision and its WHY and ask the owner: "Has the direction changed?" Never silently follow the old path and never silently break it. If the direction did change, write a new decision that supersedes the old one.

## 5. Status lifecycle

| status | meaning | handling |
|--------|---------|----------|
| `active` | currently valid | use normally |
| `deprecated` | no longer applies, no replacement | ignore as a current fact |
| `superseded-by:<id>` | replaced by a newer doc | read `<id>` instead |

## 6. Frontmatter

Required: `id`, `memory` (`episodic|semantic|procedural`), `source`, `status`, `last_verified`.
Optional: `relates_to`, `supersedes`, `branches`.

`branches` lists git branches covered by a consensus doc; the red-zone gate reads it.

## 7. Inbox and curation

Unsure where something belongs? Drop it in `inbox/` with a dated title. Curate regularly: lint with `brain_lint.py`, merge duplicates, re-verify docs older than 180 days, and move inbox items into proper docs.

## 8. Who commits a consensus doc

A human. The AI drafts the doc; a person commits it in the brain. Tier `commit` reads git for this: an uncommitted or dirty doc does not open the gate.
