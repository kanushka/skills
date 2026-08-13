# Crew selection

Skills for choosing whether to delegate work, which subagent model and reasoning effort to use, and whether subagents can run in parallel.

Each skill selects the model and effort independently: model capacity clears the task's judgment floor, while effort clears its reasoning-depth floor. The resulting pair remains within the parent-session capability cap.

## Choose a skill

| Skill | Runs in | Dispatches to | Also requires | Status |
|---|---|---|---|---|
| `pick-claude-crew` | Claude Code | Claude subagents — Fable, Opus, Sonnet, Haiku | — | Stable |
| `pick-codex-crew` | Codex | Codex subagents — GPT-5.6 Sol, Terra, Luna | — | Stable |
| `pick-crew` | Claude Code | Claude **and** Codex subagents | Codex CLI, Codex plugin | **Experimental** |

`pick-crew` adds a lane choice ahead of the model and effort choice: cost-driven work routes to a Codex subagent, work needing session context or judgment above Sol stays on Claude. One plan mixes lanes freely, and the two lanes bill to separate budgets.

> **`pick-crew` is experimental.** I am still testing how well the lane choice holds up in real sessions, so its rules may change between versions. It has a [graded eval suite](../TESTING.md), but far less day-to-day mileage than the two single-lane skills. If you want something settled, install `pick-claude-crew` and keep dispatching to Codex by hand.

**On Claude Code, install `pick-claude-crew` or `pick-crew`, not both.** Their descriptions overlap, so both would load on every turn and either could claim the same decision. Pick `pick-crew` once the Codex CLI is set up; pick `pick-claude-crew` otherwise.

## Install

Claude Code:

```bash
npx skills add kanushka/skills \
  --skill pick-claude-crew \
  --agent claude-code \
  --global
```

Codex:

```bash
npx skills add kanushka/skills \
  --skill pick-codex-crew \
  --agent codex \
  --global
```

Claude Code driving both lanes:

```bash
npx skills add kanushka/skills \
  --skill pick-crew \
  --agent claude-code \
  --global
```

See the [root README](../README.md#install) for what `--global` and `--yes` do, and for manual copying from a clone.

## Requirements for `pick-crew`

`pick-crew` dispatches Codex subagents from inside Claude Code, so three things must be in place before installing it:

1. The [Codex CLI](https://developers.openai.com/codex/cli), authenticated — check with `codex login status`.
2. The [Codex plugin for Claude Code](https://github.com/openai/codex-plugin-cc#install), which supplies the `codex:codex-rescue` subagent the skill dispatches to.
3. A Claude Code restart or `/reload-plugins` after installing the plugin, so the subagent appears in the running session.

Without the plugin the Codex lane is simply unavailable, and the skill keeps every subtask on Claude.

## Testing

Unit tests, eval cases, and live CLI evals for these three skills are documented in [TESTING.md](../TESTING.md).
