---
name: babysit-pr
description: Use when the user asks to babysit, shepherd, or nurse a pull request's review feedback, or invokes /babysit-pr — a PR has open review threads from a human reviewer, CodeRabbit, Copilot, or any other review bot sitting unanswered.
---

# Babysit PR

Take every open review thread on a pull request to answered: read it, decide
whether it is right, fix what is right, reply to all of it.

**Core principle:** a thread is answered when the **last word is yours**. That
one test drives both what to work on and when to stop, and it holds whoever
spoke — a human reviewer, a review bot, or an earlier run of this skill. A
reviewer answering back is a thread with the last word theirs again, so this
skill is a loop: run it until a pass makes no commit and no reply.

## Arguments

`/babysit-pr #4` names the PR. Bare `/babysit-pr` infers it from the current
branch with `gh pr view --repo <o/r> --json number,url`, and asks the user when
that comes back empty.

**Repo:** an explicit `repo:owner/name`, else the repo in a full PR URL, else
`gh repo view --json nameWithOwner`. In a fork the PR usually lives on the
**upstream**; confirm when upstream and `origin` disagree.

## Read everything

Findings live in three places. Read all three, then `gh api user --jq .login`
for the last-word test.

```sh
# Inline threads — the primary unit of work
gh api graphql -f query='
{ repository(owner:"<owner>", name:"<repo>") { pullRequest(number:<n>) {
    reviewThreads(first:100) { nodes { isResolved isOutdated path line
      comments(first:50) { nodes { databaseId author{login} body } } } } } } }'

# Review bodies — a human's "changes requested" prose, a bot's summary or nitpicks
gh api repos/<o/r>/pulls/<n>/reviews --jq '.[] | {id, state, user: .user.login, body}'

# PR conversation — findings a human dropped outside any review
gh api repos/<o/r>/issues/<n>/comments --paginate --jq '.[] | {user: .user.login, body}'
```

**The two APIs spell bot logins differently.** REST suffixes every bot login
with `[bot]` and GraphQL returns it bare — `coderabbitai[bot]` against
`coderabbitai`. Match on the prefix — a suffixed filter against GraphQL matches
nothing, and every guard below then quietly passes.

## Reviewer quirks

Every rule in this skill is the same whoever reviewed. Only these details
differ, and a reviewer missing from this table is read by the same two
questions: where do its findings land, and how does it say it agrees.

| Reviewer | Where its findings land | An acknowledgement reads as |
|---|---|---|
| `coderabbitai` | Inline threads, **plus nitpicks in the review body** that never become threads | "confirmed" and a `<!-- <review_comment_addressed> -->` marker |
| `copilot-pull-request-reviewer` | Inline threads. Its review body is a "Pull request overview" summary — read it, but a summary is not a finding | No marker; judge the prose |
| A human | Anywhere: threads, a "changes requested" body, a loose PR comment | Prose — "looks good", "fair enough", or a reaction |

## Pick the threads to answer

Work a thread when all of these hold:

- `isResolved` is false;
- the **last** comment's author is not you;
- that comment carries a **finding**, not an **acknowledgement**. A reviewer
  agreeing with your fix has answered the thread, not reopened it — see Reviewer
  quirks for how each one says so.

`isOutdated` qualifies a thread like any other: the lines moved, so judge the
finding against the code as it stands. Still live, answer it; already fixed by a
later commit, say so and name that commit.

## Answer each one

**Verify the finding against the code first.** A reviewer bot states intent
confidently and is sometimes wrong, and the repo may document the opposite.
Decide on what the code says.

- **Valid** → fix it, then reply `Fixed in <short-sha>.`, plus at most one clause
  when the diff does not speak for itself.
- **Invalid** → one or two lines on why not. Keep the reasoning out of the
  thread; put it in your response to the user.

Batch the fixes into as few commits as they naturally group into, run the
project's test gate **once** at the end, then **push** — and reply after that, so
every sha you quote passed the gate and the reader can fetch it.

Reply to the thread, not the PR, and pass the body by file so backticks and
newlines survive:

```sh
gh api -X POST repos/<o/r>/pulls/<n>/comments/<ROOT_ID>/replies -F body=@reply.md
```

`ROOT_ID` is the **first** comment's `databaseId` in that thread.

## Findings with no thread

A finding in a **review body** or a loose PR comment has no thread, and nothing
else answers it. CodeRabbit's nitpicks arrive this way on most reviews and a
human's "changes requested" prose lands the same, so this is routine rather than
rare. Answer them all in one PR-level comment:

```sh
gh pr comment <n> --repo <o/r> -F body=@reply.md
```

Its body is an opening line naming the sha, one bullet per finding you acted on,
and a closing line for any finding you are pushing back on:

```md
Addressed the review-body findings in 607c17e1:

- dropped the DOM-position and computed-style assertions, keeping the
  consumer-visible label and chip-tone ones;
- trimmed the external-spec URL and content payloads;
- reset the mutable mock readiness state in teardown.

The 80% docstring warning is a CodeRabbit heuristic, not a repository gate.
```

Three parts: the sha line, the bullets, the pushback line. A comment with a
fourth part is reporting the pass, and the pass is reported to the user.

## Then the branch itself

Every finding answered, check whether the branch can still land:

```sh
gh pr view <n> --repo <o/r> --json mergeable,mergeStateStatus
```

`CONFLICTING` means the review is answered onto a branch that cannot merge.
Resolve it without asking — but only now, after the replies. Your fixes land
first, so the resolution is done once against final content instead of being
redone underneath them.

**If `resolving-merge-conflicts` is installed, invoke it** for the resolution
itself: it reads both sides' intent from their commits and PRs, resolves each
hunk, runs the project's checks, and finishes the merge. If it is not installed,
leave the branch alone and name the conflict in your report to the user —
improvising a resolution is how a merge quietly drops someone's change.

Prefer a merge over a rebase while the review is open. A rebase rewrites the
shas you just quoted in your replies, and a reviewer following `Fixed in <sha>`
then lands on a commit that no longer exists.

## What a pass leaves on the PR

Exactly these artifacts, and nothing besides:

1. **Commits** — as few as the fixes naturally group into.
2. **One push**, once the test gate has passed.
3. **One threaded reply per thread you worked**, quoting the sha that fixed it.
4. **One PR-level comment**, if any finding arrived outside a thread.
5. **The merge that clears a conflicting branch**, when there was one.

The first four answer a reviewer; the fifth lets the answered PR land.

## Report the pass to the user

The account of the pass has its own home, and it is not the PR. Tell the user:

- **what you fixed**, and the sha carrying it;
- **what you pushed back on**, with the reasoning you kept out of the thread;
- **which gate you ran and what it returned** — a green gate belongs here, not
  in a comment: it answers no finding, and no reviewer asked for it;
- **what is still open** — threads waiting on a human, findings you deferred, and
  any conflict hunk whose resolution was a judgement call worth a second look.

Pushing moves the head and the bots re-review it. A reply invites an answer even
when nothing was pushed — a reviewer you pushed back on may push back in turn.
Either way the last word can become theirs again, so start over: fresh threads
are ordinary work, acknowledgements are answered threads, and the loop ends only
on a pass that makes **no commit and no reply**.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Filtering GraphQL results for a `[bot]`-suffixed login | GraphQL returns bot logins bare (`coderabbitai`); REST suffixes them (`coderabbitai[bot]`). Match on prefix, or the filter silently matches nothing. |
| Reading a reviewer's summary as a finding | Copilot's review body is an overview of the PR; CodeRabbit's carries real nitpicks. Check whether the prose actually asks for a change before answering it. |
| Stopping after fixing everything you saw | A push triggers a fresh bot review. Re-fetch threads after pushing — the loop isn't done until a pass produces no commit and no reply. |
| Replying to the PR instead of the thread | `gh pr comment` posts at PR level; only `.../pulls/<n>/comments/<ROOT_ID>/replies` lands inside the thread the reviewer opened. Use PR-level comments only for findings that arrived outside any thread. |
| Reporting the pass inside the PR-level comment | Green gates and a roll-call of the threads you already replied to answer nobody — the reviewer reads that comment for the review-body findings alone. Match the example in Findings with no thread, and report the pass to the user. |
| Resolving the conflict before answering the threads | Your fixes land after it, so the resolution gets redone underneath them. Answer, push, then resolve — and prefer a merge, so the shas your replies quote still exist. |
| Treating a bot's finding as automatically correct | Bots state intent confidently and are sometimes wrong. Check the finding against the code (and the repo's own docs) before fixing anything. |
| Pushing per-commit and replying immediately | Replies should quote a sha that already passed the test gate. Batch fixes, run the gate once, push, then reply. |
