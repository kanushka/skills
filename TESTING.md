# Testing

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

`evals/cases/pick-crew.json` grades the two-lane skill. Seven cases anchor the lane choice — cost-driven work to Codex, trivial mechanical work and unwritten session context to Claude, a judgment floor above Sol to Claude, an independent second pass to Codex, and a pinned tier the crew must honour while reporting the floor it overshoots. Three more mirror the parent cap and the two scheduling anchors, which behave differently here because the cap constrains only the Claude lane. The suite grades selection only: the harness renders a prompt and grades a JSON verdict, so the dispatch contract in `CODEX-DISPATCH.md` is out of its reach.

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

`pick-crew` on Claude Code:

```bash
python3 evals/crew_eval.py run \
  --provider claude \
  --cases evals/cases/pick-crew.json \
  --mode skill \
  --model opus \
  --effort medium \
  --repetitions 3 \
  --output-dir evals/results/pick-crew-skill
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
