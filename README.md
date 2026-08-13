# Everyday Agent Skills

[![skills.sh](https://skills.sh/b/kanushka/skills)](https://skills.sh/kanushka/skills)

Skills I use day to day with coding agents, shared for other developers to pick up and improve.

Each one encodes a decision I kept making by hand — how to delegate a task, how to take a pull request through review.

## Categories

| Category | For | Skills |
|---|---|---|
| [Crew selection](docs/crew-selection.md) | Choosing whether to delegate, which subagent model and reasoning effort to use, and whether subagents can run in parallel. | `pick-claude-crew`, `pick-codex-crew`, `pick-crew` *(experimental)* |
| [Pull requests](docs/pull-requests.md) | Getting a pull request from opened to merged. | `babysit-pr` |

Each category page covers what its skills do, which agent they run in, what they require, and how to install them.

## Install

Install directly from GitHub with the [skills CLI](https://www.skills.sh/docs/cli). No repository clone is required.

```bash
npx skills add kanushka/skills --skill <skill-name>
```

Without `--agent`, the CLI detects the coding agents you have installed and prompts if it finds none. Add `--global` to make the skill available across projects — the default is the current project only. Add `--yes` to skip prompts.

The crew-selection skills only work in the agent they dispatch from, so name it explicitly: `--agent claude-code` for `pick-crew` and `pick-claude-crew`, `--agent codex` for `pick-codex-crew`. `babysit-pr` runs in any agent with skills support, so let the CLI detect.

If you already cloned this repository, manual copying also works — `babysit-pr` goes wherever your agent keeps its skills:

```bash
cp -R skills/pick-claude-crew ~/.claude/skills/
cp -R skills/pick-codex-crew ~/.codex/skills/
cp -R skills/pick-crew ~/.claude/skills/
cp -R skills/babysit-pr ~/.claude/skills/     # or ~/.codex/skills/, etc.
```

**On Claude Code, install `pick-claude-crew` or `pick-crew`, not both** — their descriptions overlap, so both would load on every turn and either could claim the same decision. See [Crew selection](docs/crew-selection.md) for which to pick.

## Testing

Every skill here is graded by one shared harness — unit tests, eval cases, and live CLI evals are documented in [TESTING.md](TESTING.md).
