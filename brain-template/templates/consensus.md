---
id: <product>/decisions/<kebab-case-slug>
memory: episodic
source: ["grill session:YYYY-MM-DD", "<repo>:<path>"]
status: active
relates_to: []
branches: [<git branch this consensus covers>]
spec_pr:  # optional: number of the spec PR; only read by the future github gate tier
last_verified: YYYY-MM-DD
---

# Decision: <one sentence saying what was decided>

## One-page summary (signed YYYY-MM-DD)
- **In one sentence**: <what and why, 60 words at most>
- **Do / do not**: <what we do in 3 sentences or fewer; what we deliberately exclude>
- **Reasoning**: <5 bullets at most: choice, options, pick, because, where it is most likely wrong>
- **Decided silently on your behalf**: <implicit decisions, one line each>
- **May touch / must not touch**: <concrete names; empty means not ready to sign>
- **How it could break**: <5 rows at most: failure, how it is caught, severity, who accepts it>

## Status
<active, date, related PRs, deployed or not>

## Context
<Background and trigger.>

## Decision
1. <Numbered outcomes.>

## Alternatives considered
- **<Rejected option>**: rejected because <reason>.

## Criteria
<Criteria used at the time.>

## Safety premises
| Premise | Invariant or one-time check | How to verify mechanically | If it fails: open or closed | How failure is detected |
|---------|-----------------------------|----------------------------|-----------------------------|-------------------------|
| | | | | |

## Decision tree
<Indented list, one node per line: outcome plus a mark for each branch walked or skipped.>

## Consequences
- <Costs and residual risks, with who accepted them and why.>

## Review trigger
- <Events that force a re-review; always include "any safety premise above stops holding".>
