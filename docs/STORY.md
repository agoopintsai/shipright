# Shipping software a human can stand behind

*A responsible vibe coding workflow*

## Purpose

The goal was never "ship faster." It was to keep shipping products that a named human can be accountable for. AI made output cheap. It did not make accountability cheap. If anything, it made it harder: more changes landed than anyone could read, and the person signing off was signing for things they had never seen.

## The difficulties

Several product lines shared data and contracts. A change in one quietly reached another. The same small team had to keep the old systems running and build the new ones, with one set of eyes. Decisions lived in chat threads, task cards and people's heads. Three months later nobody could say why a thing had been decided, only that it had.

## The bottleneck

The first instinct was to add more checks. Every AI step got a human gate. The result was an AI that got slower and more hesitant with each layer, and humans who could not keep up. When people cannot keep up, they start accepting verbal reports as verification. "It's handled" replaces "show me."

A payment-related incident made this visible. Looking back at the two days before it, the pattern was plain: the decision had run ahead of the evidence, and the gate had been a person who was already out of attention.

So the chain broke at the human. But the only one who can answer "should this exist at all" and "where does it stop" is also the human. The problem was not too many humans or too few. It was human attention spent in the wrong places.

## The method: keep humans at the decision points, release everything else

**Release memory.** Decisions and the reasons behind them go into a separate GitHub repository, the brain. Progress is appended automatically; decisions are signed by a person. Every grilled plan, every override, every reason lands there with a date. The thicker the brain, the fewer questions climb up to a human, because the AI reads what was already settled before it asks.

**Release the scope of judgement.** Before anything touches money, data or a shared contract, the AI grills the plan. It lays the plan out as a decision tree and asks the human only the questions that belong to a human: is the need real, who named it, what does it cost to not do it, where is the boundary. Implementation-level decisions are answered by the AI, symmetrically, with a line on where each answer is most likely wrong. The human overturns what they disagree with and signs a one-page sheet. Nothing is built before the signature.

**Release the hands.** When a problem arrives, a triage skill picks it up, asks the brain, and solves it if the brain already knows how. Only what the brain cannot answer is escalated. Implementation goes to cheap executor models within the boundary the signed spec drew. The human reviews exactly twice: once on the spec, once on the code, in the same pull request. (Shipright v0.1 enforces this up to the commit layer; the GitHub layer is next.)

**Tools can refuse, never approve.** Hooks, gates, CI and lint have veto power and nothing else. They block an edit in a red zone, refuse a workflow that forgot to pin a model, fail a build that lost a link. They never approve. This is what keeps the AI from becoming the boss: the only way to get a "yes" is a human signature.

Two footnotes from building it. Designing "the human approves on GitHub" revealed, halfway through, that the AI and the reviewer were using the same account, and GitHub does not allow self-approval. A rule that cannot physically be pressed is not a rule. And one afternoon a single session spawned sixty-five subagents, most of them on the most expensive model, despite a written guideline saying not to. The guideline moved into a hook the same week. Rules in documents do not hold. Rules in tools do.

## Shipright

All of this is now a Claude Code plugin called Shipright: a setup that walks you through in minutes, a grill with a small core question bank you can grow, a brain template, and a hook engine whose every refusal tells you what was blocked, why, and how to get out. If you are letting AI write code that moves money or touches data, the gates may be worth more to you than any single line of code.

→ https://github.com/agoopintsai/shipright
