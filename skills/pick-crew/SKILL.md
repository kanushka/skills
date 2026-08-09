---
name: pick-crew
description: Use before spawning subagents when deciding whether to delegate, whether to route work to Claude or Codex, which model and effort to assign, or whether work can run in parallel.
---

# Pick Crew

Choose the cheapest crew that clears two independent floors: **judgment** and **depth**. Model buys judgment; reasoning effort buys depth. Verification buys deterministic confidence more cheaply than either.

Each subtask also picks a **lane** — Claude or Codex. The lanes bill to separate budgets, so a Codex subtask preserves Claude session capacity. One plan mixes lanes freely.

## Select the Crew

1. **Decide whether to delegate.** Spawn for bounded isolation, parallelism, or independent review; keep connecting decisions in the parent. Done when each subtask has a distinct deliverable.
2. **Build the feasible set.** Retain the models and effort values the active Agent schema accepts. Keep the Claude lane at or below the parent session tier: `Fable > Opus > Sonnet > Haiku`. Keep the Codex lane only when the Agent tool exposes `codex:codex-rescue`. Done when every candidate is exposed and within its cap.
3. **Choose the lane per subtask.** Match the lane signals below. Done when each subtask names one lane.
4. **Choose model.** Use ambiguity, novelty, domain judgment, failure cost, and blast radius. Done when the cheapest feasible model clears the judgment signals below.
5. **Choose effort independently.** Use depth, search breadth, context size, step count, and interacting constraints. Done when the cheapest exposed effort clears the depth signals below.
6. **Check the pair.** Improve context or verification when cheaper than either axis. Honour a lane, model, or effort the user pinned, and report the floor that pin overshoots or misses. Done when every axis sits at its cheapest clearing value or carries a reported pin.
7. **Schedule.** Parallelize independent work; sequence shared files and output dependencies. Done when each dependency is ordered and each parallel pair is independent.
8. **Label every dispatch.** Prefix the Agent tool's `description`, or a workflow `agent()` call's `label`, with `model·effort: task_description` — `opus·high: trace render regression`, `terra·medium: port the auth handler`, `haiku: rename test fixtures` where nothing set effort. Resolve each part against what the agent actually runs with, stopping at the first match: model from the call, else the agent definition's frontmatter, else the session model; effort from the call, else that frontmatter, else omitted. A Codex dispatch instead takes both parts from its own `--model` and `--effort` flags and names the bare tier, `luna`, `terra`, or `sol`; the forwarder's frontmatter reports Sonnet and would hide the crew member actually running. Say which part is ambiguous rather than guessing it. Done when every dispatch carries its resolved prefix.

## Lane

| Lane | Signals |
|---|---|
| Codex | Substantial precedented implementation where cost dominates; a self-contained deliverable fully describable in prompt text; an independent pass on work Claude itself designed or got stuck on |
| Claude | Conversation context the parent already holds; a judgment floor above Sol; structured output feeding parent reasoning; an enforced read-only scope |

Codex **cold-starts**: it reads the repository fresh and receives only the prompt text, so a subtask carrying unwritten session context belongs to Claude. That start-up also costs wall-clock a small task never repays — a one-call Codex lookup measured 53s against 32s for a nine-call Claude sweep — so trivial mechanical work stays on Claude whatever its token price.

## Model Floor: Judgment

| Judgment signals | Claude | Codex |
|---|---|---|
| Mechanical rule execution with clear completion checks and strong verification | Haiku | Luna |
| Routine engineering or review, including precedented implementation, with bounded ambiguity | Sonnet | Terra |
| Security, architecture, conflicting evidence, or high failure cost and blast radius | Opus | Sol |
| Novel, cross-domain, irreversible work where exceptional judgment dominates cost | Fable | route to Claude |

Sol is the Codex ceiling, so a judgment floor above it belongs to Claude in the first place and re-runs there when a Codex dispatch misses it.

## Effort Floor: Depth

| Effort | Depth signals |
|---|---|
| low | Small supplied context, few steps, narrow deliverable, and little search |
| medium | Multi-step or bounded analysis, an exhaustive repository sweep, or moderately interacting constraints |
| high | Broad or unfamiliar search, large context, many interactions, or incomplete evidence |
| highest exposed | Exceptional depth that high effort cannot cover reliably; Codex exposes `xhigh` |

Route security and failure-cost signals to model; route effort solely by depth signals, including for security and architecture work. Bounded security adjudication can use Opus/low or Sol/low; broad precedented implementation can use Sonnet/high or Terra/high. An exhaustive mechanical rename uses Haiku/medium or Luna/medium: the sweep adds depth, not judgment.

## Escalation

When output misses a floor, repair context and scope, strengthen verification, then raise effort for depth or model for judgment.

If the feasible set cannot clear both floors, keep the critical reasoning in the parent session or ask the user to raise the session tier.

## Dispatch Contract

Give each subagent one deliverable, minimal context, boundaries, and a checkable completion criterion. Parallel agents get disjoint files or read-only scopes. Dispatch independent subtasks in a single message so they run concurrently, and set `run_in_background` true to keep the parent working through a long run. The label from step 8 travels with each dispatch, so a running fleet reads back as the crew this skill picked.

**Claude lane.** Pass model and effort through the Agent tool's own fields.

**Codex lane.** Dispatch `subagent_type: "codex:codex-rescue"` under the flag contract in [`CODEX-DISPATCH.md`](CODEX-DISPATCH.md). Read it first: the forwarder silently discards model and effort flags that the contract's wording leaves unprotected, and a discarded flag runs the subtask at the Codex config default instead of the chosen floor.
