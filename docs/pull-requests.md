# Pull requests

Skills for reviewing a pull request and getting it from opened to merged.

| Skill | Runs in | Purpose |
|---|---|---|
| `babysit-pr` | Any agent with skills support | Takes every open review thread on a PR to answered — from a human, CodeRabbit, or Copilot. |
| `lgtm-ish` | Claude Code | Reviews a PR with parallel subagents and writes the verified findings as short, plain comments a busy human would leave. |

## `babysit-pr`

A thread is answered when the **last word is yours**. That single test drives both what the skill works on and when it stops, and it holds whoever spoke — a human, `coderabbitai`, `copilot-pull-request-reviewer`, or an earlier run of the skill.

Each pass:

1. Reads all three places findings live — inline review threads, review bodies, and PR conversation comments.
2. Picks the threads still needing an answer: unresolved, last comment not yours, and carrying a finding rather than an acknowledgement.
3. Verifies each finding against the code before acting. A reviewer bot states intent confidently and is sometimes wrong.
4. Batches the fixes into as few commits as they group into, runs the project's test gate **once**, then pushes — so every sha it quotes back has passed the gate.
5. Replies inside the thread the reviewer opened, not at PR level.

Pushing moves the head, which triggers a fresh bot review, so the skill is a loop: it runs until a pass produces no commit and no reply.

### Invoking

`/babysit-pr #4` names the PR. Bare `/babysit-pr` infers it from the current branch and asks when that comes back empty. Pass `repo:owner/name` or a full PR URL to target another repo — in a fork the PR usually lives on the upstream, and the skill confirms when upstream and `origin` disagree.

### Requirements

The [`gh` CLI](https://cli.github.com/), authenticated against the repo the PR lives in. The skill reads and replies entirely through `gh api`, so it is not tied to any one coding agent — anything that loads skills and can run `gh`, commit, and push will do.

### Install

```bash
npx skills add kanushka/skills --skill babysit-pr
```

The CLI detects your installed agents and prompts if it finds none. Add `--global` to install across projects rather than just the current one, or `--agent <name>` to skip detection. See the [root README](../README.md#install) for the full set.

### A branch that cannot merge

Once every finding is answered and pushed, the skill checks whether the branch
can still land. A conflicting branch is resolved at that point — after the
replies, so the resolution is done once against final content — and by merge
rather than rebase, so the shas quoted in the replies still exist.

The resolution itself is delegated to the
[`resolving-merge-conflicts`](https://github.com/mattpocock/skills/blob/main/skills/engineering/resolving-merge-conflicts/SKILL.md)
skill by Matt Pocock, invoked automatically when it is installed — no
confirmation step. Install it alongside `babysit-pr` if you want conflicts
handled; without it the skill still answers the whole review and names the
conflict in its report, but leaves the branch untouched.

### Testing

Thirteen graded cases in `evals/cases/babysit-pr.json`, run through the shared
harness. See [TESTING.md](../TESTING.md).

## `lgtm-ish`

A PR review that reads like a teammate wrote it. Subagents find and verify the
issues; the comments come out as one or two plain sentences each, with no fix
suggestions, no summary, and uncertain issues asked as questions.

Adapted from Anthropic's
[`code-review`](https://github.com/anthropics/claude-code/tree/main/plugins/code-review)
plugin (Apache-2.0). The review pipeline is the same by default; the output
style, the `--deep` mode, and the gate (skip a PR you already reviewed) are new.

### Modes

- **Default:** the original pipeline. A gate check, a summary, two CLAUDE.md
  reviewers and two Opus bug reviewers in parallel, then a validator per issue.
- **`--deep`:** focused Opus finders — cross-layer contracts, error paths, and
  logic and security — that report every suspicion, then a "what did they
  miss?" pass. Validators are the only filter. Slower, catches more.

Results come back in chat as a numbered list (🐛 confirmed, ❓ plausible) so you
can follow up on any one. Without `--comment` nothing touches GitHub. With it,
each comment is posted inline on its line, emoji-free, or the PR is approved if
nothing survived.

Issues someone else (a human or a bot like CodeRabbit) already raised are not
posted again; they show in chat as 💬 already flagged. The PR is only approved
when nobody has open findings.

### Re-review

If you've reviewed the PR before, the run becomes a re-review: it reviews only
the PR's own commits since your last review, checks each of your earlier
threads against the current code (solved or open), and approves only when there
are no new issues, every earlier thread is solved, and your approval isn't
already active.

### Invoking

```
/lgtm-ish 123
/lgtm-ish https://github.com/owner/repo/pull/123 --deep --comment
```

It only runs when invoked; the model never starts it on its own. In the Claude desktop app it also renames the session to `🔍 #<PR> <short title>`, so reviews are easy to find in the sidebar.

### Requirements

Claude Code, for its subagents and per-agent model choice, and the
[`gh` CLI](https://cli.github.com/) authenticated against the PR's repo.

### Install

```bash
npx skills add kanushka/skills --skill lgtm-ish --agent claude-code
```

### Testing

Twenty-five graded cases in `evals/cases/lgtm-ish.json`, run through the shared
harness. They grade the orchestration rules (gate, dedupe, approval, re-review),
not review recall. See [TESTING.md](../TESTING.md).
