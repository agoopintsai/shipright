---
id: gatekeeping-01-author-reviewer-identity
category: gatekeeping
must_answer: true
added: 2026-10-23
---

## Question

For every place the plan has A review, approve, or release B: in the system that actually enforces the review (code host, cloud IAM, admin accounts), are A and B two different identities? Check which identity the mechanism recognises and which one the reviewed party actually uses.

## Why it matters

If author and reviewer share an identity, the review is physically impossible or trivially bypassed. A gate like this looks healthy until the first day someone really needs it to stop something. Many platforms forbid self-approval, so a policy written as if it were possible fails on day one.
