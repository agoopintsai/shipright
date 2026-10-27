# Tier `github` (design, not implemented)

Status: not implemented. A v0.2 candidate. `gate: github` is rejected by the config loader in v0.1.

## Goal

Make GitHub approval the hard gate, so a signature means a named reviewer clicked Approve, not that a file exists or was committed.

## Spec stage

- The consensus doc frontmatter carries `spec_pr: <number>`, the pull request that holds the spec.
- Before any red-zone edit, the hook runs `gh pr view <n> --json reviewDecision`.
- The gate opens only when `reviewDecision` is `APPROVED`. Any other value (REVIEW_REQUIRED, CHANGES_REQUESTED, empty) denies.

## Code stage

- PreToolUse on Bash denies `gh pr merge` and `git push` to the default branch unless the implementation PR is `APPROVED`.
- Because the spec and the code travel in the same pull request, a single PR can carry both reviews.

## Failure behaviour

- `gh` missing, unauthenticated, offline or erroring: deny, not fail-open. This tier exists to be strict; the exit message says how to fix `gh` or fall back to `gate: commit`.

## Identity

- GitHub does not allow approving your own PR. The AI and the human reviewer must therefore use different accounts, which is the point: the author cannot sign for the reviewer.

## Open questions

- Matching a branch to its PR when several exist.
- Enterprise setups where `reviewDecision` is empty without a branch-protection rule.
- Pushes made through tools other than `git push` or `gh` (same limit as every Bash-level check).
