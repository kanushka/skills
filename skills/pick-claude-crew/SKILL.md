---
name: pick-claude-crew
description: Use before spawning Claude Code subagents when deciding whether to delegate, whether work can run in parallel, or which Claude model and effort to assign.
---

# Pick Claude Crew

Choose the cheapest crew configuration that clears the task's **quality floor**. Model buys judgment; effort buys depth. Verification buys confidence on deterministic work more cheaply than either.

## Select the Crew

1. **Decide whether to delegate.** Spawn when a bounded workstream benefits from isolation, parallelism, or an independent review. Do small connecting decisions in the parent session. This step is complete when every proposed subtask has a distinct deliverable.
2. **Build the feasible set.** Read the active Agent/Task tool schema and keep only models and effort levels it accepts. Apply the session cap: `Fable > Opus > Sonnet > Haiku`; a child stays at or below the parent session's tier. This step is complete when every candidate is both available and within the cap.
3. **Set the quality floor.** Judge ambiguity, novelty, domain depth, failure cost, blast radius, and strength of available verification. This step is complete when the floor maps to one row below.
4. **Choose model, then effort.** Start at the balanced row. Move the model for judgment; move effort for reasoning depth, search breadth, or interacting constraints. Change one axis at a time. This step is complete when no cheaper candidate still clears the quality floor.
5. **Schedule the work.** Run independent workstreams in parallel. Sequence work that shares files or consumes another task's output. This step is complete when every dependency has an order and every parallel pair is independent.

## Claude Ladder

| Quality floor | Model | Effort | Typical work |
|---|---|---|---|
| Deterministic | Haiku | medium | Renames, formatting, exhaustive searches; require tests or a sweep |
| Balanced | Sonnet | medium | Precedented implementation, repository mapping, routine review |
| Consequential | Opus | high | Ambiguous design, security analysis, high-blast-radius changes |
| Exceptional | Fable | high or highest available | Novel, cross-domain, irreversible work where failure cost dominates |

Use the nearest available row within the cap. For a deterministic task, strengthen its test, search, or checklist before buying more reasoning.

## Escalation

When an output misses the quality floor:

1. Repair missing context, scope, or completion criteria.
2. Strengthen verification.
3. Raise effort one level when the model has enough judgment but needs more depth.
4. Raise model one tier when the task needs better judgment.

If the feasible set cannot clear the quality floor, keep the critical reasoning in the parent session or ask the user to raise the session tier.

## Dispatch Contract

Give each subagent one deliverable, the minimum relevant context, explicit boundaries, and a checkable completion criterion. Pass the selected model and effort through the tool's actual fields. For parallel agents, assign disjoint files or read-only scopes.
