# `pick-crew` Eval Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `pick-crew` a graded eval suite that exercises its lane choice and its pin-reporting rule, without disturbing the two suites that already pass.

**Architecture:** Three additive changes to `evals/crew_eval.py` — a `lane` graded field, a `pin_conflict` graded field, and a runtime check that a `codex` lane is only claimed when the case exposes it — followed by a new 10-case file at `evals/cases/pick-crew.json`. `grade_case` skips any field a case does not declare in `expected`, so widening `GRADED_FIELDS` cannot affect `pick-claude-crew` or `pick-codex-crew`. Every change is test-first against the existing 25-test `unittest` suite.

**Tech Stack:** Python 3 standard library only (`unittest`, `json`, `argparse`). No dependencies are added.

## Global Constraints

- Model names in case files are **capitalized**: `Fable`, `Opus`, `Sonnet`, `Haiku`, `Sol`, `Terra`, `Luna`. This matches `evals/cases/pick-codex-crew.json` and matters because `grade_case` does an exact `in` match, not a case-insensitive one. (The handoff table wrote them lowercase; the skill's Model Floor table capitalizes them. Case files follow the existing files.)
- Valid Codex effort values are `none, minimal, low, medium, high, xhigh`. `light` is not one.
- `expected` values are **lists of allowed values**, except booleans (`delegate`, `pin_conflict`), which `grade_case` wraps automatically via `allowed = configured if isinstance(configured, list) else [configured]`.
- Each case declares its own `runtime`; efforts are per-case, not per-file (`exceptional-architecture` in `pick-codex-crew.json` declares `xhigh` where its siblings do not).
- Run the unit tests with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py` from the repo root.
- Live runs must write under `evals/results/`, which is gitignored, and `validated_output_dir` rejects anything else.
- Commits go straight to `main`. This repo has zero branches and zero merges in its history; do not create one.
- The suite grades **selection only**. The harness renders a prompt and grades a JSON verdict; it never dispatches a subagent, so the dispatch contract, the flag-drop workaround, `--wait`, and the step-8 label are out of scope. Do not add cases that pretend to cover them.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `evals/crew_eval.py` | Modify | `GRADED_FIELDS` gains two entries; `render_prompt` gains two JSON schema lines; `grade_case` gains one runtime check |
| `evals/test_crew_eval.py` | Modify | Unit coverage for the three harness changes plus integration assertions over the new case file |
| `evals/cases/pick-crew.json` | Create | The 10-case suite |
| `TESTING.md` | Modify | Line 24 currently says `pick-crew` has no suite; replace with the suite's coverage and its run command |

Note: `README.md` does **not** claim `pick-crew` lacks an eval suite — the handoff attributed that line to the README, but it lives at `TESTING.md:24`. README needs no change.

---

### Task 1: Grade the `lane` field

**Files:**
- Modify: `evals/crew_eval.py:18` (`GRADED_FIELDS`), `evals/crew_eval.py:154-164` (`render_prompt` schema block)
- Test: `evals/test_crew_eval.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `GRADED_FIELDS` containing `"lane"`; a rendered prompt whose JSON schema includes a `"lane"` line. Tasks 2 and 4 extend both.

- [ ] **Step 1: Write the failing tests**

Add to `evals/test_crew_eval.py`, inside `GradeCaseTests`:

```python
    def test_lane_mismatch_is_an_error(self):
        case = {
            "id": "case-1",
            "runtime": {"models": ["Terra"], "efforts": ["medium"]},
            "expected": {"lane": ["codex"]},
        }
        response = {
            "case_id": "case-1",
            "lane": "claude",
            "rationale": "picked claude",
        }
        errors = grade_case(case, response)
        self.assertIn("lane: expected one of ['codex'], got 'claude'", errors)

    def test_lane_is_skipped_when_a_case_omits_it(self):
        case = {
            "id": "case-1",
            "runtime": {"models": ["Terra"], "efforts": ["medium"]},
            "expected": {"delegate": True},
        }
        response = {
            "case_id": "case-1",
            "delegate": True,
            "lane": "whatever",
            "rationale": "no lane declared",
        }
        self.assertEqual([], grade_case(case, response))
```

And inside `RenderPromptTests`:

```python
    def test_skill_mode_asks_for_lane(self):
        suite = {"skill": "pick-crew"}
        case = {"id": "case-1", "prompt": "Choose a crew.", "runtime": {}}
        prompt = render_prompt(suite, case, "# Skill body", mode="skill")
        self.assertIn('"lane"', prompt)
        self.assertIn('"claude" or "codex"', prompt)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: `test_lane_mismatch_is_an_error` FAILs (the error string is absent because `lane` is not graded) and `test_skill_mode_asks_for_lane` FAILs on the missing `"lane"` substring. `test_lane_is_skipped_when_a_case_omits_it` already passes — it is the backward-compatibility guard, and it must stay green through every later step.

- [ ] **Step 3: Widen `GRADED_FIELDS`**

In `evals/crew_eval.py`, replace line 18:

```python
GRADED_FIELDS = ("delegate", "lane", "model", "effort", "schedule")
```

- [ ] **Step 4: Add `lane` to the rendered schema**

In `render_prompt`, insert the lane line after `"delegate"` so the schema block reads:

```python
    sections.append(
        "Return one JSON object and no surrounding prose with these fields:\n"
        "{\n"
        f'  "case_id": {json.dumps(case["id"])},\n'
        '  "delegate": true or false,\n'
        '  "lane": "claude" or "codex",\n'
        '  "model": "runtime model name" or null,\n'
        '  "effort": "runtime effort name" or null,\n'
        '  "schedule": "parent", "single", "parallel", or "sequential",\n'
        '  "rationale": "one concise sentence"\n'
        "}"
    )
```

- [ ] **Step 5: Run the full test suite**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: PASS, all tests, including the 25 that existed before.

- [ ] **Step 6: Commit**

```bash
git add evals/crew_eval.py evals/test_crew_eval.py
git commit -m "feat: grade the lane field in crew evals"
```

---

### Task 2: Grade the `pin_conflict` field

**Files:**
- Modify: `evals/crew_eval.py:18` (`GRADED_FIELDS`), `evals/crew_eval.py` (`render_prompt` schema block)
- Test: `evals/test_crew_eval.py`

**Interfaces:**
- Consumes: `GRADED_FIELDS` and the schema block as Task 1 left them.
- Produces: `GRADED_FIELDS` containing `"pin_conflict"`; a schema line `"pin_conflict": true or false`. Task 4's `pinned-tier-overshoot` case declares `"pin_conflict": true`.

Why a boolean: step 6 of the skill says to honour a pin *and report the floor it overshoots*. Honouring a pin is easy; reporting the overshoot unprompted is the behaviour that either exists or does not. A boolean makes that gradeable without substring-matching free-text rationale.

- [ ] **Step 1: Write the failing tests**

Add to `GradeCaseTests`:

```python
    def test_pin_conflict_must_be_reported_when_expected(self):
        case = {
            "id": "case-1",
            "runtime": {"models": ["Sol"], "efforts": ["low"]},
            "expected": {"pin_conflict": True},
        }
        response = {
            "case_id": "case-1",
            "pin_conflict": False,
            "rationale": "complied silently",
        }
        errors = grade_case(case, response)
        self.assertIn("pin_conflict: expected one of [True], got False", errors)

    def test_pin_conflict_absent_from_response_is_an_error_when_expected(self):
        case = {
            "id": "case-1",
            "runtime": {"models": ["Sol"], "efforts": ["low"]},
            "expected": {"pin_conflict": True},
        }
        response = {"case_id": "case-1", "rationale": "said nothing about the pin"}
        errors = grade_case(case, response)
        self.assertIn("pin_conflict: expected one of [True], got None", errors)
```

Add to `RenderPromptTests`:

```python
    def test_skill_mode_asks_for_pin_conflict(self):
        suite = {"skill": "pick-crew"}
        case = {"id": "case-1", "prompt": "Choose a crew.", "runtime": {}}
        prompt = render_prompt(suite, case, "# Skill body", mode="skill")
        self.assertIn('"pin_conflict"', prompt)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: all three new tests FAIL — the two grading tests because `pin_conflict` is not in `GRADED_FIELDS` so `grade_case` returns no such error, and the render test on the missing substring.

- [ ] **Step 3: Widen `GRADED_FIELDS` again**

```python
GRADED_FIELDS = ("delegate", "lane", "model", "effort", "schedule", "pin_conflict")
```

- [ ] **Step 4: Add `pin_conflict` to the rendered schema**

Insert after the `"schedule"` line, and extend the rationale line's wording so the field has a defined meaning:

```python
        '  "schedule": "parent", "single", "parallel", or "sequential",\n'
        '  "pin_conflict": true or false,\n'
        '  "rationale": "one concise sentence"\n'
        "}\n"
        "Set \"pin_conflict\" true when the task pins a lane, model, or effort "
        "that overshoots or misses the floor you would otherwise pick, and name "
        "that floor in the rationale. Set it false otherwise."
```

- [ ] **Step 5: Run the full test suite**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: PASS, all tests.

- [ ] **Step 6: Commit**

```bash
git add evals/crew_eval.py evals/test_crew_eval.py
git commit -m "feat: grade pin-conflict reporting in crew evals"
```

---

### Task 3: Reject a Codex lane the runtime does not expose

**Files:**
- Modify: `evals/crew_eval.py:57-63` (the runtime-exposure block at the end of `grade_case`)
- Test: `evals/test_crew_eval.py`

**Interfaces:**
- Consumes: `grade_case` as Tasks 1 and 2 left it.
- Produces: an error string of the form `lane: 'codex' is not exposed by the runtime`, mirroring the existing `model:` and `effort:` exposure errors. Task 4's `codex-unavailable-fallback` case relies on this.

Why: this makes the availability constraint structural rather than resting on one case's `expected` list. It is a fourth harness change beyond the three the handoff agreed; it is backward compatible because a case with no `codex_available` key is unconstrained, and the two existing suites have no such key.

- [ ] **Step 1: Write the failing tests**

Add to `GradeCaseTests`:

```python
    def test_codex_lane_is_rejected_when_the_runtime_withholds_it(self):
        case = {
            "id": "case-1",
            "runtime": {
                "models": ["Sonnet"],
                "efforts": ["medium"],
                "codex_available": False,
            },
            "expected": {"lane": ["claude"]},
        }
        response = {
            "case_id": "case-1",
            "lane": "codex",
            "rationale": "reached for a lane that is not there",
        }
        errors = grade_case(case, response)
        self.assertIn("lane: 'codex' is not exposed by the runtime", errors)

    def test_codex_lane_is_allowed_when_the_runtime_exposes_it(self):
        case = {
            "id": "case-1",
            "runtime": {
                "models": ["Terra"],
                "efforts": ["medium"],
                "codex_available": True,
            },
            "expected": {"lane": ["codex"]},
        }
        response = {
            "case_id": "case-1",
            "lane": "codex",
            "model": "Terra",
            "effort": "medium",
            "rationale": "cost-driven build",
        }
        self.assertEqual([], grade_case(case, response))

    def test_lane_exposure_is_unconstrained_when_the_key_is_absent(self):
        case = {
            "id": "case-1",
            "runtime": {"models": ["Terra"], "efforts": ["medium"]},
            "expected": {},
        }
        response = {
            "case_id": "case-1",
            "lane": "codex",
            "rationale": "legacy suite with no codex_available key",
        }
        self.assertEqual([], grade_case(case, response))
```

- [ ] **Step 2: Run the tests to verify the first fails**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: `test_codex_lane_is_rejected_when_the_runtime_withholds_it` FAILs on the missing error string. The other two already pass and are the backward-compatibility guards.

- [ ] **Step 3: Add the exposure check**

In `grade_case`, after the existing `effort` exposure check and before `return errors`:

```python
    lane = response.get("lane")
    if lane == "codex" and runtime.get("codex_available") is False:
        errors.append("lane: 'codex' is not exposed by the runtime")
    return errors
```

- [ ] **Step 4: Run the full test suite**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add evals/crew_eval.py evals/test_crew_eval.py
git commit -m "feat: reject a codex lane the eval runtime withholds"
```

---

### Task 4: Add the `pick-crew` case file

**Files:**
- Create: `evals/cases/pick-crew.json`
- Test: `evals/test_crew_eval.py` (`IntegrationCaseFileTests`)

**Interfaces:**
- Consumes: `GRADED_FIELDS` including `lane` and `pin_conflict` (Tasks 1–2), and the lane exposure check (Task 3).
- Produces: a suite at `evals/cases/pick-crew.json` with `skill: "pick-crew"` and `skill_path: "skills/pick-crew/SKILL.md"`, holding case ids `cost-driven-implementation`, `trivial-mechanical-stays-claude`, `session-context-stays-claude`, `judgment-above-sol`, `codex-unavailable-fallback`, `independent-second-pass`, `pinned-tier-overshoot`, `parent-cap-claude-lane`, `independent-parallel-work`, `dependent-sequential-work`. Task 5 documents it.

Seven cases are lane-specific anchors. Three are mirrored from `pick-claude-crew.json` — the parent cap and the two scheduling cases, which are where `pick-crew`'s text genuinely differs, since the cap now sits inside a two-lane step 2. The other six `pick-claude-crew` anchors are deliberately not mirrored: their text is near-identical and already passing.

`parent-cap-claude-lane` is **not** a verbatim mirror. In `pick-claude-crew` the cap binds unconditionally; in `pick-crew` the cap constrains only the Claude lane, so a bare security-review prompt could legitimately answer `codex`/`Sol` and grade nothing. The prompt below adds unwritten session context and structured output feeding parent reasoning — two Claude lane signals — so the lane is settled and the cap is what is being tested.

- [ ] **Step 1: Write the failing integration tests**

Add to `IntegrationCaseFileTests` in `evals/test_crew_eval.py`:

```python
    def test_pick_crew_suite_covers_both_lanes(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-crew.json").read_text()
        )
        self.assertEqual("pick-crew", suite["skill"])
        self.assertEqual("skills/pick-crew/SKILL.md", suite["skill_path"])
        lanes = {
            lane
            for case in suite["cases"]
            for lane in case["expected"].get("lane", [])
        }
        self.assertEqual({"claude", "codex"}, lanes)

    def test_pick_crew_suite_grades_a_pin_conflict(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-crew.json").read_text()
        )
        pinned = next(
            case for case in suite["cases"] if case["id"] == "pinned-tier-overshoot"
        )
        self.assertTrue(pinned["expected"]["pin_conflict"])

    def test_pick_crew_suite_declares_codex_availability_on_every_case(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-crew.json").read_text()
        )
        self.assertTrue(suite["cases"])
        for case in suite["cases"]:
            self.assertIn("codex_available", case["runtime"], case["id"])

    def test_pick_crew_expected_models_are_exposed_by_their_runtime(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-crew.json").read_text()
        )
        for case in suite["cases"]:
            for model in case["expected"].get("model", []):
                if model is not None:
                    self.assertIn(model, case["runtime"]["models"], case["id"])
            for effort in case["expected"].get("effort", []):
                if effort is not None:
                    self.assertIn(effort, case["runtime"]["efforts"], case["id"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: all four new tests ERROR with `FileNotFoundError` — `evals/cases/pick-crew.json` does not exist yet.

- [ ] **Step 3: Write the case file**

Create `evals/cases/pick-crew.json`:

```json
{
  "skill": "pick-crew",
  "skill_path": "skills/pick-crew/SKILL.md",
  "cases": [
    {
      "id": "cost-driven-implementation",
      "prompt": "The parent has already established this as a distinct subtask worth delegating: port an existing auth handler to a second service by following the handler and its tests, a substantial and fully precedented build whose whole specification fits in the prompt. Token cost dominates the choice. Choose its configuration.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "lane": ["codex"], "model": ["Terra"], "effort": ["medium"], "schedule": ["single"], "pin_conflict": false}
    },
    {
      "id": "trivial-mechanical-stays-claude",
      "prompt": "The parent has already established this as a distinct subtask worth delegating: rename one private helper in a single file and update its three references. Choose its configuration.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "lane": ["claude"], "model": ["Haiku"], "schedule": ["single"], "pin_conflict": false}
    },
    {
      "id": "session-context-stays-claude",
      "prompt": "The parent has already established this as a distinct subtask worth delegating: implement the caching approach this session settled on across four verbal revisions. The reasoning behind the approach was never written to a file. Choose its configuration.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "lane": ["claude"], "pin_conflict": false}
    },
    {
      "id": "judgment-above-sol",
      "prompt": "Design an irreversible, novel migration spanning storage, identity, and billing with incomplete requirements and no precedent. Choose its configuration.",
      "runtime": {"parent_model": "Fable", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "lane": ["claude"], "model": ["Fable"], "effort": ["high"], "schedule": ["single", "parallel"], "pin_conflict": false}
    },
    {
      "id": "codex-unavailable-fallback",
      "prompt": "The parent has already established this as a distinct subtask worth delegating: port an existing auth handler to a second service by following the handler and its tests, a substantial and fully precedented build whose whole specification fits in the prompt. Token cost dominates the choice. Choose its configuration.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku"], "efforts": ["low", "medium", "high"], "codex_available": false},
      "expected": {"delegate": true, "lane": ["claude"], "model": ["Sonnet"], "effort": ["medium"], "schedule": ["single"], "pin_conflict": false}
    },
    {
      "id": "independent-second-pass",
      "prompt": "The parent designed a lock-ordering fix, applied it twice, and the deadlock still reproduces under load. The parent has established that an independent diagnosis pass on the same code is required, with the whole failing scenario written down in the prompt. Choose its configuration.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "lane": ["codex"], "model": ["Sol"], "schedule": ["single"], "pin_conflict": false}
    },
    {
      "id": "pinned-tier-overshoot",
      "prompt": "The parent has already established this as a distinct subtask worth delegating: delete a deprecated feature flag and every reference to it, a mechanical sweep with a clear completion check. The user has pinned the subagent to Sol. Choose its configuration.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "lane": ["codex"], "model": ["Sol"], "schedule": ["single"], "pin_conflict": true}
    },
    {
      "id": "parent-cap-claude-lane",
      "prompt": "The parent has already established that an independent delegated review is required: review the authorization redesign for security flaws. The reviewer must use the trust-boundary decisions this session made verbally and return a structured finding list the parent will reason over directly. Choose the strongest configuration permitted by the parent-session cap.",
      "runtime": {"parent_model": "Sonnet", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "lane": ["claude"], "model": ["Sonnet"], "effort": ["high"], "schedule": ["single"], "pin_conflict": false}
    },
    {
      "id": "independent-parallel-work",
      "prompt": "Map frontend conventions and database conventions. The workstreams are read-only and neither needs the other's output. Choose the crew schedule.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "schedule": ["parallel"], "pin_conflict": false}
    },
    {
      "id": "dependent-sequential-work",
      "prompt": "First derive the API contract, then implement a client that requires that contract. Choose the crew schedule.",
      "runtime": {"parent_model": "Opus", "models": ["Fable", "Opus", "Sonnet", "Haiku", "Sol", "Terra", "Luna"], "efforts": ["low", "medium", "high", "xhigh"], "codex_available": true},
      "expected": {"delegate": true, "schedule": ["sequential"], "pin_conflict": false}
    }
  ]
}
```

Notes on deliberate omissions, so a later reader does not "fix" them:

- `trivial-mechanical-stays-claude`, `session-context-stays-claude`, and `independent-second-pass` omit `effort`. The lane and model are what those cases test; pinning effort would fail them for a defensible depth call.
- `session-context-stays-claude` omits `model` too. Haiku through Opus are all defensible for a four-revision caching change; only the lane is being graded.
- The two scheduling cases omit `lane` and `model`. Either lane can schedule correctly, and forcing one would grade the lane table twice instead of the schedule.
- `codex-unavailable-fallback` grades the skill's reasoning about an availability flag, not a genuinely unregistered subagent — the harness cannot create that condition. It is kept because it is the only case touching step 2's feasible-set gate, and because the failure it catches (naming Terra when the lane is not exposed) fails a real dispatch outright.

- [ ] **Step 4: Run the full test suite**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: PASS, all tests.

- [ ] **Step 5: Verify the suite renders**

Run:

```bash
python3 evals/crew_eval.py render \
  --cases evals/cases/pick-crew.json \
  --mode skill | python3 -c "import sys,json; [json.loads(l) for l in sys.stdin]; print('10 prompts parsed')"
```

Expected: `10 prompts parsed`, with no traceback. This confirms `skill_path` resolves and every case renders.

- [ ] **Step 6: Commit**

```bash
git add evals/cases/pick-crew.json evals/test_crew_eval.py
git commit -m "test: add the pick-crew eval suite"
```

---

### Task 5: Document the suite

**Files:**
- Modify: `TESTING.md:24`

**Interfaces:**
- Consumes: the case file from Task 4.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Replace the stale claim**

`TESTING.md:24` currently reads:

> These task definitions are saved in `evals/cases/pick-claude-crew-opus.json` and `evals/cases/pick-codex-crew-sol.json`. `pick-crew` has no suite yet; its lane choice needs grading the harness does not currently do.

Replace it with:

> These task definitions are saved in `evals/cases/pick-claude-crew-opus.json` and `evals/cases/pick-codex-crew-sol.json`.
>
> `evals/cases/pick-crew.json` grades the two-lane skill. Seven cases anchor the lane choice — cost-driven work to Codex, trivial mechanical work and unwritten session context to Claude, a judgment floor above Sol to Claude, an independent second pass to Codex, and a pinned tier the crew must honour while reporting the floor it overshoots. Three more mirror the parent cap and the two scheduling anchors, which behave differently here because the cap constrains only the Claude lane. The suite grades selection only: the harness renders a prompt and grades a JSON verdict, so the dispatch contract in `CODEX-DISPATCH.md` is out of its reach.

- [ ] **Step 2: Add the run command**

Append to the "Live CLI evals" section of `TESTING.md`, after the existing Claude example:

````markdown
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
````

- [ ] **Step 3: Verify the referenced paths exist**

Run: `ls evals/cases/pick-crew.json skills/pick-crew/CODEX-DISPATCH.md`
Expected: both paths listed, no `No such file` error.

- [ ] **Step 4: Commit**

```bash
git add TESTING.md
git commit -m "docs: document the pick-crew eval suite"
```

---

### Task 6: Run the suite live and record the baseline

**Files:**
- Writes to: `evals/results/pick-crew-skill/` and `evals/results/pick-crew-control/` (both gitignored)

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces: a pass rate per case. Nothing downstream depends on it in code.

This task is verification, not construction. It is where the suite either earns its keep or exposes a bad case. Do not skip it and do not report the suite as working before it has run — the prior session's real defects came from running Codex, not from reasoning about it.

- [ ] **Step 1: Run the skill arm**

```bash
python3 evals/crew_eval.py run \
  --provider claude \
  --cases evals/cases/pick-crew.json \
  --mode skill \
  --model opus \
  --effort medium \
  --repetitions 3 \
  --allow-fail \
  --output-dir evals/results/pick-crew-skill
```

`--allow-fail` is deliberate: this is a baseline measurement, so results must be written even when cases fail.

- [ ] **Step 2: Run the control arm**

```bash
python3 evals/crew_eval.py run \
  --provider claude \
  --cases evals/cases/pick-crew.json \
  --mode control \
  --model opus \
  --effort medium \
  --repetitions 3 \
  --allow-fail \
  --output-dir evals/results/pick-crew-control
```

The control arm is what shows the skill is doing work. A case both arms pass is measuring the model, not the skill.

- [ ] **Step 3: Compare the two arms**

```bash
python3 -c "
import json
skill = json.load(open('evals/results/pick-crew-skill/summary.json'))['case_pass_rates']
control = json.load(open('evals/results/pick-crew-control/summary.json'))['case_pass_rates']
for case_id in skill:
    print(f'{case_id:34} skill {skill[case_id]:.2f}  control {control[case_id]:.2f}')
"
```

- [ ] **Step 4: Report, do not silently repair**

Write the per-case skill and control rates into the session's response. Then classify each case:

- **Skill high, control low** — the case works. This is the target.
- **Both high** — the case grades the model, not the skill. Report it as low-value; do not delete it without asking.
- **Skill low** — either the skill has a real defect or the case's `expected` is wrong. Read three failing rationales from `evals/results/pick-crew-skill/rep-001.responses.json` before deciding which. Loosening `expected` to make a case pass is only correct when the rationale shows defensible reasoning the case wrongly excluded; say explicitly which of the two it was.

Do not edit `skills/pick-crew/SKILL.md` in this task. A skill defect found here is a finding to report, not a fix to fold in silently.

- [ ] **Step 5: Commit any case-file corrections**

Only if Step 4 concluded a case's `expected` was wrong:

```bash
git add evals/cases/pick-crew.json
git commit -m "test: correct pick-crew case expectations against live rationales"
```

---

### Task 7: Let the new fields survive the provider, and correct three cases

**Files:**
- Modify: `evals/providers.py:12-27` (`OUTPUT_SCHEMA`)
- Modify: `evals/cases/pick-crew.json` (three cases)
- Test: `evals/test_crew_eval.py`

**Interfaces:**
- Consumes: `GRADED_FIELDS` and the rendered schema from Tasks 1–2; the case file from Task 4.
- Produces: an `OUTPUT_SCHEMA` whose `properties` and `required` both cover `lane` and `pin_conflict`. Task 6's re-run depends on it.

Why this task exists: Task 6's first live run scored 0/3 on every case. `evals/providers.py` carries a second output schema, independent of `render_prompt`'s, and passes it to the CLI as a hard `--json-schema` with `"additionalProperties": False`. The CLI stripped `lane` and `pin_conflict` from every response before grading — the models had reasoned about both (a rep-001 rationale opens "Codex lane (no pin conflict)"), but the grader saw `None`. Tasks 1–4 were correct against their briefs; the plan simply never touched `providers.py`.

The three case corrections come from the same run, on the four fields that did survive:

- `cost-driven-implementation` and `codex-unavailable-fallback` expected `effort: ["medium"]`; both arms returned `high` all three times, reasoning that the port needs a broad read of the handler plus its tests. The skill's own Effort Floor section says "broad precedented implementation can use Sonnet/high or Terra/high" — the expectation contradicted the skill's worked example. Widening to `["medium", "high"]` admits reasoning the case wrongly excluded; it is not a skill defect.
- `judgment-above-sol` expected `delegate: true`; both arms returned `delegate: false, schedule: "parent"`, reasoning that a Fable parent keeps novel connecting work in-session — a correct read of step 1. The prompt was copied from `pick-claude-crew` without the established-delegation preamble its nine siblings all carry. The prompt is what is wrong.

- [ ] **Step 1: Write the failing tests**

Add a new class to `evals/test_crew_eval.py`, after `ProviderAdapterTests`:

```python
class OutputSchemaTests(unittest.TestCase):
    def test_schema_carries_every_graded_field(self):
        for field in GRADED_FIELDS:
            self.assertIn(field, OUTPUT_SCHEMA["properties"], field)

    def test_schema_requires_lane_and_pin_conflict(self):
        self.assertIn("lane", OUTPUT_SCHEMA["required"])
        self.assertIn("pin_conflict", OUTPUT_SCHEMA["required"])

    def test_lane_is_constrained_to_the_two_lanes(self):
        self.assertEqual(
            ["claude", "codex"], OUTPUT_SCHEMA["properties"]["lane"]["enum"]
        )

    def test_schema_still_forbids_unknown_properties(self):
        self.assertFalse(OUTPUT_SCHEMA["additionalProperties"])
```

`test_schema_carries_every_graded_field` is the guard that would have caught this defect: it ties the provider's schema to `GRADED_FIELDS`, so widening one without the other now fails a test.

Add `GRADED_FIELDS` to the existing `from evals.crew_eval import (...)` block and `OUTPUT_SCHEMA` to the existing `from evals.providers import (...)` block.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: `test_schema_carries_every_graded_field`, `test_schema_requires_lane_and_pin_conflict`, and `test_lane_is_constrained_to_the_two_lanes` FAIL. `test_schema_still_forbids_unknown_properties` passes already — it is the guard that keeps the fix from being "delete `additionalProperties`".

- [ ] **Step 3: Widen the provider schema**

In `evals/providers.py`, replace `OUTPUT_SCHEMA` with:

```python
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "case_id": {"type": "string"},
        "delegate": {"type": "boolean"},
        "lane": {"type": "string", "enum": ["claude", "codex"]},
        "model": {"type": ["string", "null"]},
        "effort": {"type": ["string", "null"]},
        "schedule": {
            "type": "string",
            "enum": ["parent", "single", "parallel", "sequential"],
        },
        "pin_conflict": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
    "required": [
        "case_id",
        "delegate",
        "lane",
        "model",
        "effort",
        "schedule",
        "pin_conflict",
        "rationale",
    ],
    "additionalProperties": False,
}
```

Both fields are `required` because `render_prompt` asks every suite for them, not just `pick-crew`. A `pick-codex-crew` run will now emit a `lane` its case file does not grade; `grade_case` skips undeclared fields, so that is inert.

- [ ] **Step 4: Run the full test suite**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py`
Expected: PASS, all tests.

- [ ] **Step 5: Commit the harness fix**

```bash
git add evals/providers.py evals/test_crew_eval.py
git commit -m "fix: let lane and pin-conflict survive the eval provider schema"
```

- [ ] **Step 6: Correct the two effort expectations**

In `evals/cases/pick-crew.json`, in the case with `"id": "cost-driven-implementation"`, change its `expected` `effort` from `["medium"]` to `["medium", "high"]`. Make the identical change to the case with `"id": "codex-unavailable-fallback"`. Change nothing else in either case.

- [ ] **Step 7: Correct the `judgment-above-sol` prompt**

In the same file, in the case with `"id": "judgment-above-sol"`, replace the `prompt` value with exactly:

```
The parent has already established this as a distinct subtask worth delegating: design an irreversible, novel migration spanning storage, identity, and billing with incomplete requirements and no precedent. Choose its configuration.
```

Leave that case's `runtime` and `expected` untouched.

- [ ] **Step 8: Verify the file still parses and still passes its integration tests**

Run:

```bash
python3 -c "import json; d=json.load(open('evals/cases/pick-crew.json')); print(len(d['cases']), 'cases')"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v evals/test_crew_eval.py
```

Expected: `10 cases`, then PASS on all tests.

- [ ] **Step 9: Commit the case corrections**

```bash
git add evals/cases/pick-crew.json
git commit -m "test: correct pick-crew case expectations against live rationales"
```

---

## Self-Review

**Spec coverage.** The three agreed harness changes are Tasks 1–2 (`lane`, `pin_conflict`, both in `GRADED_FIELDS` and in the rendered schema). The agreed runtime block — flat seven-model `models` plus `codex_available` — is in every case in Task 4. All seven agreed lane anchors appear, with the ids the handoff named. Open call 1 resolved: `codex-unavailable-fallback` is kept, with its limit written into the case file notes. Open call 2 resolved: three mirrors, not nine. The `README.md` line the handoff asked to update does not exist; the equivalent claim at `TESTING.md:24` is updated in Task 5, and the discrepancy is called out in the File Structure table.

**Additions beyond the agreed design.** Task 3 (lane exposure check) is a fourth harness change. It is separable — dropping it costs only the structural guarantee, since `codex-unavailable-fallback`'s `expected` already catches that case. Task 6 (live baseline with a control arm) is not in the handoff either; the suite is unverified without it.

**Type consistency.** `GRADED_FIELDS` is a tuple of strings throughout. `expected` values are lists everywhere except `delegate` and `pin_conflict`, which are bare booleans that `grade_case` wraps. Model names are capitalized in every case file entry and in every test assertion. Error strings asserted in tests match the f-strings in `grade_case` exactly, including the `!r` repr quoting.

**Known scope limit, restated.** The harness never dispatches a subagent. The flag-drop workaround, `--wait`, and the step-8 label are ungraded by every task here, by design.
