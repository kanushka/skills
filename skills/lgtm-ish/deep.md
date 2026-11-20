# `--deep` review

Replaces the default reviewers in step 5. Also give each finder the step 4 summary.

Finders optimise for **recall**: report every suspected issue, including uncertain ones. Step 6 is the only filter. Each issue must be caused or exposed by the changed code. Budget about 20 tool calls per finder: read the diff once, then read outside it only to trace a specific suspicion (the other side of an API, a hook's `select`, a handler's error mapping). Prefer Read and Grep over Bash.

Each finder returns, per issue, a concrete failure scenario, plus a `checked` list of areas it cleared with the specific reason each is fine.

Launch in parallel:
- **Contracts (opus):** for each new or changed piece that talks to another layer (frontend and backend, service and upstream API, hook and component), check both sides agree on what is counted, filtered, returned and named.
- **Error paths (opus):** every error the change can raise or receive: status code mapping, which error wins when several checks fail, retries, what the user sees after a failure, whether retrying can ever succeed.
- **Logic & security (opus):** wrong conditions, unreachable branches, empty, single and missing cases, races, ordering; auth gates, input validation, privilege boundaries.
- **CLAUDE.md (sonnet):** only if CLAUDE.md files exist, using only those on the path of the changed file.

Then merge duplicates and launch one more opus agent ("what did they miss?") with the PR context and the merged `issues` and `checked` lists. Same budget. It looks only for issues not already listed and challenges thin `checked` reasons.

In step 6, cap validators at about 8 tool calls each.
