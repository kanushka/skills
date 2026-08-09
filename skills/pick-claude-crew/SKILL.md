---
name: pick-claude-crew
description: Use before spawning Claude Code subagents when deciding whether to delegate, whether work can run in parallel, or which Claude model and effort to assign.
---

# Pick Claude Crew

Choose the cheapest crew that clears two independent floors: **judgment** and **depth**. Model buys judgment; effort buys depth. Verification buys deterministic confidence more cheaply than either.

## Select the Crew

1. **Decide whether to delegate.** Spawn for bounded isolation, parallelism, or independent review; keep connecting decisions in the parent. Done when each subtask has a distinct deliverable.
2. **Build the feasible set.** Read the Agent/Task schema and retain accepted values within the session cap: `Fable > Opus > Sonnet > Haiku`. Done when every candidate is exposed and at or below the parent tier.
3. **Choose model.** Use ambiguity, novelty, domain judgment, failure cost, and blast radius. Done when the cheapest feasible model clears the judgment signals below.
4. **Choose effort independently.** Use depth, search breadth, context size, step count, and interacting constraints. Done when the cheapest exposed effort clears the depth signals below.
5. **Check the pair.** Improve context or verification when cheaper. Choose the cheapest pairing that independently clears both floors. Done when lowering either axis would miss its floor.
6. **Schedule.** Parallelize independent work; sequence shared files and output dependencies. Done when each dependency is ordered and each parallel pair is independent.

## Model Floor: Judgment

| Model | Judgment signals |
|---|---|
| Haiku | Mechanical rule execution with clear completion checks and strong verification |
| Sonnet | Routine engineering or review, including precedented implementation, with bounded ambiguity |
| Opus | Security, architecture, conflicting evidence, or high failure cost and blast radius |
| Fable | Novel, cross-domain, irreversible work where exceptional judgment dominates cost |

## Effort Floor: Depth

| Effort | Depth signals |
|---|---|
| low | Small supplied context, few steps, narrow deliverable, and little search |
| medium | Multi-step or bounded analysis, an exhaustive repository sweep, or moderately interacting constraints |
| high | Broad or unfamiliar search, large context, many interactions, or incomplete evidence |
| highest exposed | Exceptional depth that high effort cannot cover reliably |

Route security and failure-cost signals to model; route effort solely by depth signals, including for security and architecture work. Bounded security adjudication can use Opus/low; broad precedented implementation can use Sonnet/high. An exhaustive mechanical rename uses Haiku/medium: the sweep adds depth, not judgment.

## Escalation

When output misses a floor, repair context and scope, strengthen verification, then raise effort for depth or model for judgment.

If the feasible set cannot clear both floors, keep the critical reasoning in the parent session or ask the user to raise the session tier.

## Dispatch Contract

Give each subagent one deliverable, minimal context, boundaries, and a checkable completion criterion. Pass model and effort through actual tool fields. Parallel agents get disjoint files or read-only scopes.
