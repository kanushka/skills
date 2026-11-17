---
name: lgtm-ish
description: Review a GitHub pull request with parallel subagents and verified, high-signal findings, then write them as short, plain, human-style inline comments. Use when the user runs /lgtm-ish with a PR number or URL.
argument-hint: <PR number or URL> [--comment] [--deep]
disable-model-invocation: true
allowed-tools: Bash(gh issue view:*), Bash(gh search:*), Bash(gh issue list:*), Bash(gh pr comment:*), Bash(gh pr review:*), Bash(gh pr diff:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh api:*), Bash(git rev-parse:*), mcp__github_inline_comment__create_inline_comment
---

Review the pull request: $ARGUMENTS

Adapted from Anthropic's [`code-review`](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) plugin (v1.0.1, Apache-2.0). Changes: a `--deep` review mode, human-style comments without fix suggestions, and a user-review gate in place of the Claude-comment gate.

Flags:
- `--comment`: post the comments on the PR, or approve it if nothing is found. Without it, print only.
- `--deep`: replace the default reviewers (step 4) with focused finders and a missed-issue pass. Slower, catches more.

**Agent assumptions (applies to all agents and subagents):**
- All tools are functional and will work without error. Do not test tools or make exploratory calls. Make sure this is clear to every subagent that is launched.
- Only call a tool if it is required to complete the task. Every tool call should have a clear purpose.

The orchestrator does not read code itself. All code reading happens inside subagents.

## Review pipeline

1. Launch a haiku agent to check if any of the following are true:
   - The pull request is closed
   - The pull request is a draft
   - The pull request does not need code review (e.g. automated PR, trivial change that is obviously correct)
   - The user has already left review comments on this PR (check `gh pr view <PR> --comments`)

   If any condition is true, stop and say why in one line.

2. Launch a haiku agent to return a list of file paths (not their contents) for all relevant CLAUDE.md files:
   - The root CLAUDE.md file, if it exists
   - Any CLAUDE.md files in directories containing files modified by the pull request

3. Launch a sonnet agent to view the pull request and return a summary of the changes.

4. Review. Give every agent the PR title and description. Each returns a list of issues, each with a description, file:line, and the reason it was flagged (e.g. "CLAUDE.md adherence", "bug").

   **Default (no `--deep`):** launch 4 agents in parallel.
   - Agents 1 + 2 (sonnet): audit CLAUDE.md compliance. Only consider CLAUDE.md files that share a path with the file or its parents. Skip both if no CLAUDE.md exists.
   - Agent 3 (opus): scan for obvious bugs in the diff only, without extra context. Flag only significant bugs. Do not flag what can't be validated from the diff.
   - Agent 4 (opus): look for problems in the introduced code: security issues, incorrect logic, etc. Only issues within the changed code.

   **HIGH SIGNAL ONLY.** Flag issues where:
   - The code will fail to compile or parse
   - The code will definitely produce wrong results (clear logic errors)
   - Clear CLAUDE.md violations where the exact rule can be quoted

   Do NOT flag style, quality, input-dependent maybes, or subjective improvements. If unsure, don't flag.

   **With `--deep`:** launch these finders in parallel instead. Also give each the step 3 summary.

   Finders optimize for **recall**: report every suspected issue, including uncertain ones; step 5 is the only filter. Each issue must be caused or exposed by the changed code. Budget ~20 tool calls per finder: read the diff once, then read outside it only to trace a specific suspicion (the other side of an API, a hook's `select`, a handler's error mapping). Prefer Read/Grep over Bash.

   Each finder also returns a concrete failure scenario per issue, and a `checked` list of areas it cleared with the specific reason each is fine.

   - **Contracts (opus):** for each new/changed piece that talks to another layer (frontend↔backend, service↔upstream API, hook↔component), check both sides agree on what is counted, filtered, returned, and named.
   - **Error paths (opus):** every error the change can raise or receive: status code mapping, which error wins when several checks fail, retries, what the user sees after a failure, whether retrying can ever succeed.
   - **Logic & security (opus):** wrong conditions, unreachable branches, empty/single/missing cases, races, ordering; auth gates, input validation, privilege boundaries.
   - **CLAUDE.md (sonnet):** only if CLAUDE.md files exist, same scoping rule as the default.

   Then merge duplicates and launch one more opus agent ("what did they miss?") with the PR context and the merged `issues` and `checked` lists. Same budget. It looks only for issues not already listed and challenges thin `checked` reasons.

5. Merge duplicates (same root cause). For each issue, launch a parallel validator (opus for bugs/logic, sonnet for CLAUDE.md) with the PR title, description, and the issue. It checks the issue in the real code and returns `confirmed`, `plausible`, or `rejected` with the reason. In `--deep`, cap validators at ~8 tool calls.

   Only keep issues where the code fails to compile/parse, definitely produces wrong results or broken user flows, or clearly violates a quotable CLAUDE.md rule.

6. Drop `rejected` issues.

False positives (always rejected):
- Pre-existing issues
- Things that look like bugs but are correct
- Pedantic nitpicks a senior engineer wouldn't flag
- Anything a linter catches
- General quality concerns (test coverage etc.) unless CLAUDE.md requires it
- CLAUDE.md issues explicitly silenced in code

## Comment style: a busy human, in plain words

Each comment is a quick note from a busy teammate. Keep it simple enough to understand in one read:
- 1–2 short sentences. Say what breaks and when, in everyday words.
- Plain text, plus inline code (backticks) for names of functions, files, variables, and values. No arrows, symbols, headers, bullets, bold, emoji, labels, or fenced code blocks.
- No fix suggestions, no suggestion blocks, no "consider…", no "you could…".
- Avoid internal jargon when a simple word works. Name a function or file only if it helps the reader find the problem.
- No summary comment, no intro, no sign-off.
- `plausible` issues are asked as a question.
- One comment per issue, on the line where the problem is.
- Vary the wording between comments. Don't start them all the same way.

Examples (note the different shapes):
> archived items are filtered out by `onlyActive`, so they never show in this dialog. the server still counts them though, so a folder with only archived items can't be deleted and the user won't see why.

> if the order is already gone, `fetchOrder` returns a plain error instead of `ErrNotFound`. so the user sometimes gets 503 "try again later" and retrying never works.

> the server skips draft invoices but this list includes them. could that block a delete the server would allow?

## Report

7. Reply in chat with the results, numbered so the user can follow up ("fix 2", "is 3 real?"). Emoji go in this chat reply only, never in anything posted to GitHub.

   - No issues: `✅ lgtm, no issues found.`
   - Issues: one line of header (`🔍 found N issues`), then per issue:

     ```
     🐛 1. `path/to/file.ts:157`
     <comment text exactly as it would be posted>
     ```

     Use 🐛 for confirmed and ❓ for plausible.
   - End with one line saying what was posted (with `--comment`) or that nothing was posted.

   Without `--comment`, stop here. Do not post anything to GitHub.

8. With `--comment`:
   - No issues: approve the PR with `gh pr review <PR> --approve` (no body) and stop. If GitHub refuses (e.g. it's the user's own PR), say so in chat and post nothing else.
   - Issues: post each as an inline comment on its line, using `mcp__github_inline_comment__create_inline_comment` with `confirmed: true` if available, otherwise `gh api repos/{owner}/{repo}/pulls/{n}/comments` with the head commit SHA, `path`, `line`, and `side: RIGHT`. One comment per unique issue, no duplicates. Do not approve.

Notes:
- Use gh CLI for GitHub. Do not use web fetch.
- Create a todo list before starting.
