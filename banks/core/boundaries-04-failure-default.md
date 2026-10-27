---
id: boundaries-04-failure-default
category: boundaries
must_answer: false
added: 2026-10-23
---

## Question

If the premise silently fails, does the logic that depends on it fail closed (stop and report) or fail open (carry on as if it held)?

## Why it matters

Fail-open failures have no symptoms. A missing key treated as "no duplicate found, proceed" is a classic example: everything looks fine until the numbers do not add up.
