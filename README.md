# Crew Selection Skills

Provider-specific skills for choosing whether to delegate work, which subagent model and reasoning effort to use, and whether subagents can run in parallel.

## Skills

- `pick-claude-crew` — Claude Code: Fable, Opus, Sonnet, and Haiku.
- `pick-codex-crew` — Codex: GPT-5.6 Sol, Terra, and Luna.

Each skill selects the model and effort independently: model capacity clears the task's judgment floor, while effort clears its reasoning-depth floor. The resulting pair remains within the parent-session capability cap.

## Install

Install directly from GitHub with the [skills CLI](https://www.skills.sh/docs/cli). No repository clone is required.

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

`--global` makes the skill available across projects. Omit it to install into only the current project. Add `--yes` for a non-interactive install.

If you already cloned this repository, manual copying also works:

```bash
cp -R skills/pick-claude-crew ~/.claude/skills/
cp -R skills/pick-codex-crew ~/.codex/skills/
```

## Unit tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py
```

## Eval cases

Each provider's default suite has nine anchor cases covering:

- keeping tiny decisions in the parent session;
- deterministic, balanced, consequential, and exceptional work;
- unavailable-model fallback;
- parent-session cap enforcement; and
- parallel versus sequential scheduling.

The real-parent integration suites also cover independent model and effort choices:

- Claude: Sonnet/high, Opus/medium, and Opus/low.
- Codex: Terra/high, Sol/medium, and Sol/low.

These task definitions are saved in `evals/cases/pick-claude-crew-opus.json` and `evals/cases/pick-codex-crew-sol.json`.

Render prompts without calling a provider:

```bash
python3 evals/crew_eval.py render \
  --cases evals/cases/pick-codex-crew.json \
  --mode skill \
  --output /tmp/pick-codex-crew-prompts.jsonl
```

Grade captured JSON or JSONL responses:

```bash
python3 evals/crew_eval.py grade \
  --cases evals/cases/pick-codex-crew.json \
  --responses /tmp/pick-codex-crew-responses.json
```

## Live CLI evals

The live runner disables persisted sessions and streams prompts over stdin. It pastes the skill text into an isolated prompt; it does not test installed-skill discovery. Generated results must be written to a child directory under `evals/results/`, which Git ignores. A run exits nonzero if any repetition fails.

Codex:

```bash
python3 evals/crew_eval.py run \
  --provider codex \
  --cases evals/cases/pick-codex-crew.json \
  --mode skill \
  --model gpt-5.6-sol \
  --effort low \
  --repetitions 1 \
  --output-dir evals/results/codex-skill
```

Claude Code:

```bash
python3 evals/crew_eval.py run \
  --provider claude \
  --cases evals/cases/pick-claude-crew.json \
  --mode skill \
  --model fable \
  --effort low \
  --repetitions 1 \
  --output-dir evals/results/claude-skill
```

Run the same command with `--mode control` for a no-skill baseline. Add `--allow-fail` when intentionally collecting a failing baseline while requiring a zero exit status. Use several repetitions before drawing conclusions from stochastic results; additional repetitions increase provider usage and cost.

The default case files exercise several simulated parent caps. For a live integration check where the simulated parent matches the model executing the eval, use:

- `evals/cases/pick-claude-crew-opus.json` with `--model opus`
- `evals/cases/pick-codex-crew-sol.json` with `--model gpt-5.6-sol`

Check authentication before live runs:

```bash
codex login status
claude auth status
```
