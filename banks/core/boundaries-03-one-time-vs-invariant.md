---
id: boundaries-03-one-time-vs-invariant
category: boundaries
must_answer: false
added: 2026-10-23
---

## Question

Is the premise verified once by hand at launch, or turned into a continuing mechanical guarantee (constraint, monitor, pre-deploy probe, CI check)? If it is only checked once, why is that enough?

## Why it matters

A one-time check is valid only until the next out-of-band operation. Mechanical invariants keep working when people forget.
