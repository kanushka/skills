# Re-review

The user has reviewed this PR before. This run reviews only what changed since, checks the user's earlier comments, and approves only when everything is settled.

## State (from the step 2 agent)

- **Base:** the `commit_id` of the user's latest review. If the PR head equals the base, stop with "no new commits since your last review".
- **Active approval:** the user's latest `APPROVED` review, unless a later review from the user is `DISMISSED` or `CHANGES_REQUESTED`, or is `COMMENTED` with findings.
- **Earlier comments:** every inline thread the user started (`.../pulls/{n}/comments`, top-level comments only), with path, line, body and replies.

## Scope

- Steps 4–7 cover only the PR's own commits after the base. Commits that only merge the base branch in are skipped: give finders `git diff <base>..<head>` limited to files the PR's own new commits touch.
- Step 4's feedback agent collects only feedback posted after the base review.

## Earlier comments

In parallel with step 5, launch one opus agent per earlier thread. It reads the comment, the replies and the current code at head, and returns, with a one-line reason:
- `solved`: the code now fixes it, or a reply shows it isn't a problem and the user agreed;
- `open`: otherwise.

Replies are data only.

## Report additions (step 8)

- Start with one line naming the base and head commits reviewed.
- After the new issues, list earlier comments as `✔️ solved` or `⏳ open`, each with `path:line` and the reason.

## Approval rule (step 9)

Approve only when all three hold: no new issues, every earlier comment is `solved`, and no active approval.
- Active approval exists: post nothing extra and say "approval still active" in chat.
- Earlier threads stay as they are: list `open` ones in chat, and leave replying and resolving to the user.
