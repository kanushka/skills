# Pick Crew End-to-End Benchmark Design

## Objective

Measure whether `pick-claude-crew` and `pick-codex-crew` lower total cost per successful real task while preserving quality. The benchmark must execute actual repository work, observe whether the parent delegates, associate every child trace with its parent, and include parent coordination and rework in the total.

The pilot is exploratory. One repetition can validate the harness and reveal large effects, but it cannot establish a stable cost-effectiveness claim.

## Decision Rule

The skill arm is cost-effective only when it meets the control arm's quality floor and lowers median cost per successful task, or preserves cost while materially reducing latency.

Primary metrics:

- task success and rubric score;
- total cost per successful task;
- paired cost delta between control and skill arms.

Secondary metrics:

- wall time;
- parent and child token usage;
- child count, model, and effort;
- retries, failed calls, and provider errors;
- whether delegation occurred and whether child output returned to the parent;
- verification and rework tokens.

## Pilot Matrix

The primary pilot contains 24 paid parent runs:

```text
3 tasks × 2 context sizes × 2 arms × 2 providers × 1 repetition
```

Providers and fixed parents:

- Claude: Opus parent at medium effort;
- Codex: GPT-5.6 Sol parent at medium reasoning effort.

Arms:

- `control`: the parent completes the task without the skill or subagents;
- `skill`: the same parent receives the provider skill and may delegate naturally.

Two additional forced-delegation diagnostics run the balanced task once per provider. They verify child execution and accounting but remain excluded from primary control-versus-skill statistics.

Run order is randomized with a recorded seed. Every run starts from an identical fixture hash in a fresh isolated directory.

## Context Variants

Both variants describe the same deliverable and use the same fixture.

- `small`: 300–800 prompt tokens containing the task, constraints, and completion command.
- `medium`: 5,000–8,000 prompt tokens adding relevant repository context already discoverable from the fixture. It must not contain hidden tests, the completed solution, or facts unavailable to the small arm through repository inspection.

Context templates are versioned and their rendered hashes and measured token counts are stored in each run manifest.

## Task Corpus

All fixtures use Python's standard library and `unittest` to avoid dependency and network variance. Public tests help agents work; hidden graders remain outside the editable fixture.

### Deterministic Config Rename

Rename the configuration key `legacy_timeout_ms` to `request_timeout_ms` across the package, examples, and public tests. Preserve its documented default and validation behavior. The old key must not remain in executable code, tests, or examples.

The hidden grader checks:

- all tests pass;
- the new key loads, defaults, and validates correctly;
- the old key is rejected;
- no disallowed old-key references remain.

### Balanced Audit Pagination

Implement cursor pagination for tenant-scoped audit events using an adjacent paginated listing as precedent. Results use descending `(created_at, id)` order, an opaque cursor, and a limit from 1 through 100. Pages must not duplicate or skip events, including equal timestamps, and must not cross tenant boundaries.

The hidden grader checks:

- first, middle, final, and empty pages;
- invalid cursor and invalid limit handling;
- stable ordering with timestamp ties;
- tenant isolation;
- preservation of existing behavior.

### Consequential Tenant Authorization

Repair a cross-tenant authorization flaw in a bounded resource service. A caller may access a resource only when the caller and resource share a tenant and the caller has the required role. A global administrator exception exists only where the supplied policy explicitly grants it. The fixture contains misleading proximity between identity and resource identifiers so an identifier-only fix fails.

The hidden grader checks:

- same-tenant permitted and denied paths;
- cross-tenant denial for matching and nonmatching identifiers;
- administrator policy boundaries;
- malformed or missing tenant context;
- no regressions in unrelated resource operations.

## Repository Layout

```text
benchmarks/
  DESIGN.md
  tasks/
    deterministic-config-rename/
    balanced-audit-pagination/
    consequential-tenant-authorization/
  graders/
  schemas/
  pricing/
  reports/
  runner/
  tests/
  results/                 # generated and Git-ignored
```

Task fixtures, prompt templates, graders, schemas, pricing metadata, runner code, and aggregate reports are committed. Raw prompts containing rendered repository context, model transcripts, temporary worktrees, and per-run traces stay under ignored `benchmarks/results/`.

## Execution Flow

For every matrix cell, the runner:

1. validates provider authentication and telemetry capability before paid work;
2. copies the immutable task fixture into a fresh temporary directory and records its hash;
3. renders the chosen context and arm prompt;
4. launches the fixed parent with identical permissions and timeout policy;
5. captures structured parent events and any linked child traces;
6. runs the hidden grader after the provider exits or times out;
7. normalizes usage, cost, delegation, timing, and quality into a run record;
8. preserves raw traces under the ignored results directory;
9. verifies that the fixture source remains unchanged.

The skill arm instructs the parent to use the supplied Pick Crew skill before any spawn. It does not require delegation. A run counts as delegated only when a linked child trace actually executes.

The control arm omits the skill and disables subagent use while preserving all other task context, permissions, parent model, and effort.

## Delegation Evidence

Recommendation text is not evidence of delegation.

Claude child traces are associated using the provider's parent tool-use linkage. Codex child rollouts are associated using the recorded parent thread identifier. Before the first paid matrix run, a telemetry preflight must confirm the current CLI schemas still expose these links.

Each skill-arm record includes:

- `delegated`;
- child count;
- child thread or trace identifiers;
- child model and effort when exposed;
- parallel or sequential schedule when observable;
- whether the child returned a result to the parent;
- provider errors and retry count.

## Usage and Pricing

Usage is normalized per parent and child session, then summed once. Forwarded child messages in parent traces are not counted as new model usage.

Token fields retain all provider-exposed categories:

- uncached input;
- cached input or cache reads;
- cache writes when exposed;
- output;
- reasoning tokens as an output subset when exposed;
- total tokens.

Claude uses provider-reported monetary cost when available and also stores per-model usage. Codex records actual tokens and an API-equivalent estimate because subscription sessions may not expose a per-call charge. Pricing metadata includes provider, model, token category, rate, currency, effective date, retrieval date, and primary-source URL. Rates are verified immediately before execution.

`total_cost` includes the parent, every child, retries, integration, and verification calls made by the provider. Local deterministic grader execution has zero model cost.

## Grading

Deterministic hidden tests run first. Each task also produces a rubric score with task-specific dimensions such as correctness, completeness, security invariants, and regression safety. Graders receive only the final working tree and run metadata needed for diagnostics; they do not receive the experimental arm.

A run is successful only when all mandatory hidden tests pass. Partial rubric scores remain useful for diagnosing failures but do not convert a failed task into a saving.

## Schemas and Reports

Versioned JSON Schemas cover:

- benchmark manifest;
- task definition;
- normalized run record;
- provider usage and child linkage;
- grader result;
- aggregate report.

The aggregate report includes paired rows per task, context, and provider; success rates; median cost per success; wall-time deltas; delegation rates; child configurations; and explicit exclusions. Forced-delegation diagnostics appear in a separate section.

The report must state that one repetition is a harness pilot, not a statistically reliable product claim.

## Error Handling and Paid-Run Gates

The runner stops before paid work when authentication, fixture hashes, schemas, pricing metadata, or output-directory validation fails.

Provider timeouts, quota errors, malformed telemetry, missing child linkage, grader crashes, and task failures are distinct statuses. A missing usage component blocks cost comparison for that run rather than silently treating the value as zero.

Before launching all 26 runs, dry runs and telemetry preflights must prove:

- fixture reset and hidden grading work;
- control mode cannot delegate;
- skill mode can execute a real child;
- parent and child usage are linked without double-counting;
- normalized records validate against their schemas;
- a failed grade produces a failed benchmark status.

## Completion Criteria

The pilot is complete when:

- all three fixtures and hidden graders pass against known-good solutions and fail against their untouched baselines;
- runner and accounting tests pass;
- both provider telemetry preflights pass;
- all 24 primary cells and two diagnostics have terminal records;
- every successful cost comparison has complete parent and child accounting;
- an aggregate report clearly separates quality, cost, latency, and delegation outcomes;
- committed artifacts contain no raw provider transcripts or temporary task worktrees.
