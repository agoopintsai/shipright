---
name: grilling
description: Round-based questioning engine. Turns a plan, decision or idea into a decision tree and questions you round by round until you and Claude share the same understanding. Use to stress-test your own thinking ("grill me", "question this plan"). Conversation only, no question banks, no documents. For banks, the red-zone gate and a consensus document use /shipright:grill.
argument-hint: "[plan or idea to question]"
---

# grilling: a round-based questioning engine

What will happen: Claude lays your topic out as a tree of decisions, then asks you questions in rounds. Each round holds every question that can be asked right now. You answer; your answers unlock the next round. It ends when no open question is left and you confirm "we understand each other". Nothing is written to disk.

## The topic is the root of the tree, not a given

Treat the user's statement as a hypothesis. The real problem may be a symptom, or the mirror image of a preselected solution. Make "what problem are we actually solving?" the root node.

**Re-root rule:** if questioning shows the real problem differs from the stated topic, replace the root with the restated problem and redo the affected subtrees.

## Rounds and the frontier

The **frontier** is every question whose prerequisite decisions are settled, so it can be asked now without guessing. Each round, ask the whole frontier at once. Number the questions and give a suggested answer for each, then stop and wait.

```
Q1 <title>: <question text, options if useful>
Suggested answer: <your answer plus one-sentence reason>
```

Answers reshape the tree. Recompute the frontier and ask the next round. A question that depends on another question in the same round belongs to the next round.

## Facts versus decisions

**Looking up facts is Claude's job, never the user's.** If a question needs facts from the codebase, files or documents, look them up (a read-only subagent is fine) rather than asking the user. Do not stall on it: a fact still being checked counts as an unsettled prerequisite, so only questions that depend on it wait. **Decisions always belong to the user**: put each one to them and wait; never answer your own question.

## Finishing

The session ends when the frontier is empty: every branch walked, nothing silently assumed. Do not act on the result until the user confirms they share the understanding.

## Relation to /shipright:grill

`/shipright:grill` is a separate skill with question banks, a hard gate for red-zone work and a consensus document. It deliberately asks one question at a time and lets Claude answer the low-risk nodes, because there the plan's author is Claude. Here the author is the user, so "Claude answers for you" does not apply. If you change tree mechanics (building the tree, frontier, re-rooting, facts versus decisions) in one skill, review the other.
