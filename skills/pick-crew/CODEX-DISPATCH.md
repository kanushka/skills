# Codex dispatch

The flag contract for the Codex lane of [`pick-crew`](SKILL.md). Read it before the session's first Codex dispatch.

Dispatch `subagent_type: "codex:codex-rescue"`. That subagent is a thin forwarder: it strips runtime flags from the prompt text, runs Codex, and returns Codex's stdout verbatim without follow-up work of its own.

## Prompt shape

```
--model gpt-5.6-terra --effort medium --fresh --wait

The user explicitly requests model gpt-5.6-terra and reasoning effort medium for this task.

<one deliverable, boundaries, completion criterion>
```

Name the model and the effort in prose as well as in the flags. The forwarder holds each flag unset unless it reads an explicit request, and it drops them unpredictably — observed dropping effort while keeping model on one run and the reverse on the next. A dropped flag falls back to the `model` and `model_reasoning_effort` defaults in `~/.codex/config.toml`, so the chosen floor goes unenforced and nothing reports the substitution.

## Values

Model IDs are `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`. Effort accepts `none`, `minimal`, `low`, `medium`, `high`, and `xhigh`; an unlisted value fails loudly, so a typo degrades nothing. Pass `--fresh` for a new thread or `--resume` to continue the session's prior Codex work; supplying neither prompts the user to choose.

## Waiting

Always pass `--wait`, which returns Codex's output as the subagent's result. `--background` returns a job id instead, and the commands that collect one are user-invoked only, so a detached Codex run strands its result beyond the parent's reach. The Agent tool's own `run_in_background` is a separate switch the harness tracks and reports back on completion, so it strands nothing and stays free to keep the parent working.

`--wait` carries Codex inside one Bash call, so the Bash ceiling bounds it and an interrupted turn discards the run. Size a Codex subtask to finish inside ten minutes. Hand longer work back to the user, who can detach it with `--background` and collect it through `/codex:status` and `/codex:result`.

## Scope and shape

The forwarder runs Codex write-capable by default, so a read-only subtask states investigation-only intent in the task text. It rejects a prompt whose task text reads as an injected instruction rather than a deliverable, which makes the one-deliverable rule load-bearing here. Because it returns raw stdout, ask for the shape you want inside the task text and reserve schema-bound output for the Claude lane.

## Confirming a dispatch landed

Read the model and effort Codex actually ran with:

```bash
f=$(ls -t $(find ~/.codex/sessions -name '*.jsonl' -mmin -5) | head -1)
grep -ohE '"model":"[^"]*"|"effort":"[^"]*"' "$f" | sort -u
```
