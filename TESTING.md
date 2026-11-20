# Testing

One harness serves every skill in this repository. A suite declares what it
grades, so `evals/skill_eval.py` is not limited to the crew-selection fields it started with:

| Suite key | Purpose | Default when omitted |
|---|---|---|
| `graded_fields` | Response fields the grader compares against `expected` | The crew-selection set |
| `instruction` | Opening line of the rendered prompt | "Choose the crew configuration…" |
| `response_fields` | Field lines in the requested JSON contract | The crew-selection contract |
| `response_note` | Trailing clarification after the contract | The pin-conflict note |
| `response_schema` | JSON schema enforced on the provider's output | The crew-selection schema |

A case that omits `runtime` renders without a runtime block, so suites that have
no model or effort constraints stay clean.

## Unit tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_skill_eval.py
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

`evals/cases/babysit-pr.json` grades the PR-review skill on thirteen cases. Six
anchor which findings get answered and where: CodeRabbit's review-body nitpicks
answered at PR level alongside its threads, Copilot's overview body recognised
as a summary rather than a finding, a human's loose PR comment and prose review
body answered at PR level, and both outdated-thread readings. Three anchor
stopping: acknowledged threads, your own last word, and a finding you reject
without touching code — the last of these caught a real defect on its first run,
where a reply-only pass read as terminal because the loop was explained through
pushing alone. One holds the PR-level comment to its three parts under the
pressure of a green test gate. Three cover a conflicting branch: resolved
without asking but only after the replies are posted, and only when
`resolving-merge-conflicts` is installed — the third case withholds that skill
and expects the branch left alone. The suite grades the shape of a pass, not the
`gh` calls that carry it out.

`evals/cases/lgtm-ish.json` grades the PR review skill on twenty-five cases. The
suite sets `skill_extra_paths`, so `deep.md` and `re-review.md` are pasted in
after `SKILL.md`. Six cases anchor the gate (closed, draft, a Dependabot bump,
a Renovate bump that also edits code, docs only, a lockfile only). Seven cover a first review: approving a clean PR only with
`--comment`, printing without posting, skipping an issue another reviewer
already raised for the same root cause but not one that only shares a line,
asking a plausible issue as a question, dropping a vague maybe, and
rejecting a confirmed bug that is pre-existing or that a linter catches. Nine cover a
re-review: no new commits, an approval still active, an approval superseded by a
later review, an earlier thread still open, an author's "won't fix" the user
never accepted, everything solved, a new bug after a change request, a merge of
main that brings in unrelated code, and feedback older than the last review that
must not count as already flagged. Like the others,
the suite grades the outcome of a run from given subagent results, not the
subagents themselves, so it measures the orchestration rules, not recall.

Render prompts without calling a provider:

```bash
python3 evals/skill_eval.py render \
  --cases evals/cases/pick-codex-crew.json \
  --mode skill \
  --output /tmp/pick-codex-crew-prompts.jsonl
```

Grade captured JSON or JSONL responses:

```bash
python3 evals/skill_eval.py grade \
  --cases evals/cases/pick-codex-crew.json \
  --responses /tmp/pick-codex-crew-responses.json
```

## Live CLI evals

The live runner disables persisted sessions and streams prompts over stdin. It pastes the skill text into an isolated prompt; it does not test installed-skill discovery. Generated results must be written to a child directory under `evals/results/`, which Git ignores. A run exits nonzero if any repetition fails.

Codex:

```bash
python3 evals/skill_eval.py run \
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
python3 evals/skill_eval.py run \
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
python3 evals/skill_eval.py run \
  --provider claude \
  --cases evals/cases/pick-crew.json \
  --mode skill \
  --model opus \
  --effort medium \
  --repetitions 3 \
  --output-dir evals/results/pick-crew-skill
```

`babysit-pr` on Claude Code:

```bash
python3 evals/skill_eval.py run \
  --provider claude \
  --cases evals/cases/babysit-pr.json \
  --mode skill \
  --model sonnet \
  --effort medium \
  --repetitions 3 \
  --output-dir evals/results/babysit-pr-skill
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

## Running every suite

`evals/run.sh` runs the unit tests, then each Claude suite, and prints a pass
rate per suite with any case below 1.0. Results land in
`evals/results/<suite>-<mode>/`.

```bash
evals/run.sh                                  # all Claude suites, skill mode, sonnet/medium, x1
evals/run.sh lgtm-ish skill sonnet medium 3   # one suite, three repetitions
evals/run.sh lgtm-ish control                 # no-skill baseline
```

Arguments are positional: suite (or `all`), mode, model, effort, repetitions.
The Codex suites need `--provider codex` and are not part of `all`.

## GitHub Actions

`.github/workflows/evals.yml` runs `evals/run.sh` on demand only (Actions →
Evals → Run workflow, from `main`), never on push or pull requests. Pick the
suite, mode, model, effort and repetitions in the form. Results are uploaded as
an artifact.

It authenticates with
[Workload Identity Federation](https://platform.claude.com/docs/en/manage-claude/wif-providers/github-actions),
not an API key. Before every `claude -p` call, `evals/wif_token.sh` fetches a
fresh GitHub OIDC token, exchanges it for a short-lived Anthropic token, and the
harness passes that as `ANTHROPIC_AUTH_TOKEN`. A fresh token per call matters:
each OIDC token is single-use, and a minted token lives at most ten minutes.

Setup:

1. In the Claude Console, Settings → Workload identity → Connect workload →
   GitHub Actions. Scope the rule to `repo:kanushka/skills:ref:refs/heads/main`
   with `repository_owner: kanushka`.
2. Add these as repository variables (not secrets; they are IDs):
   `ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`,
   `ANTHROPIC_SERVICE_ACCOUNT_ID`, and `ANTHROPIC_WORKSPACE_ID` (needed when the
   rule covers more than one workspace).
3. Don't add an `ANTHROPIC_API_KEY` secret.

Locally, `ANTHROPIC_TOKEN_COMMAND` is unset, so runs use your own `claude` login.
