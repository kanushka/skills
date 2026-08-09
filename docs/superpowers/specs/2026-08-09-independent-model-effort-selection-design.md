# Independent Model and Effort Selection

## Goal

Pick the cheapest subagent configuration that clears the task's quality needs without coupling a model tier to a fixed effort. Model capacity should pay for judgment; effort should pay for reasoning depth.

## Selection model

Each provider skill evaluates two independent floors:

1. **Judgment floor:** ambiguity, novelty, domain judgment, failure cost, and blast radius select the cheapest capable model within the parent-session cap.
2. **Depth floor:** context size, search breadth, step count, and interacting constraints select the cheapest available effort.

The final pair may combine any feasible model and effort. Verification and better-scoped context can lower a floor when they reduce the corresponding risk. Delegation and scheduling remain separate decisions.

Security and failure-cost signals affect the model floor only. They do not raise effort unless the task also has broader context, search, steps, or interactions.

## Provider mappings

Claude maps increasing judgment to Haiku, Sonnet, Opus, and Fable. Codex maps it to Luna, Terra, and Sol. Both skills inspect the active tool schema and use only exposed effort values instead of assuming a provider-wide fixed list.

The effort guidance uses task signals rather than model names:

- low: narrow supplied context, few steps, and little search;
- medium: multi-step or bounded analysis, exhaustive sweeps, or moderately interacting constraints;
- high: broad or unfamiliar search, large context, many interactions, or incomplete evidence;
- highest exposed: exceptional depth beyond reliable high-effort coverage.

## Routing coverage

The real-parent suites add task-shaped cases for pairings hidden by the former coupled ladder:

- broad, precedented cross-module implementation: Sonnet/high or Terra/high;
- bounded security diagnosis with three interacting flows: Opus/medium or Sol/medium;
- supplied-evidence security adjudication with a brief decision: Opus/low or Sol/low.

The deterministic rename remains Haiku/medium or Luna/medium because the exhaustive reference sweep adds depth without adding judgment.

## Validation

Unit tests require both integration suites to contain the independent-axis pairings and require deterministic exhaustive work to use medium effort. Live provider checks compare the old and revised skill wording. Generated provider responses remain under the ignored `evals/results/` directory.

The initial Claude baseline coupled both consequential cases to Opus/high; revised wording selected all eight expected routes. The initial Codex baseline coupled the bounded security case to Sol/high and selected low effort for the deterministic sweep; revised wording selected Luna/medium, Terra/high, Sol/medium, and Sol/low in targeted checks.
