import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.crew_eval import (
    grade_case,
    grade_repetitions,
    grade_suite,
    positive_int,
    render_prompt,
    run_command,
    run_suite,
    validated_output_dir,
)
from evals.providers import (
    build_claude_command,
    build_codex_command,
    parse_claude_output,
    parse_codex_output,
    run_codex,
)


class GradeCaseTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "id": "deterministic",
            "prompt": "Rename a private helper and update all references.",
            "runtime": {
                "parent_model": "Sol",
                "models": ["Sol", "Terra"],
                "efforts": ["low", "medium", "high"],
            },
            "expected": {
                "delegate": True,
                "model": ["Terra"],
                "effort": ["medium"],
                "schedule": ["single"],
            },
        }

    def test_accepts_expected_selection(self):
        response = {
            "case_id": "deterministic",
            "delegate": True,
            "model": "Terra",
            "effort": "medium",
            "schedule": "single",
            "rationale": "Verification carries confidence for deterministic work.",
        }
        self.assertEqual([], grade_case(self.case, response))

    def test_rejects_overpowered_selection(self):
        response = {
            "case_id": "deterministic",
            "delegate": True,
            "model": "Sol",
            "effort": "high",
            "schedule": "single",
            "rationale": "Use the strongest configuration to be safe.",
        }
        errors = grade_case(self.case, response)
        self.assertIn("model: expected one of ['Terra'], got 'Sol'", errors)
        self.assertIn("effort: expected one of ['medium'], got 'high'", errors)

    def test_requires_a_rationale(self):
        response = {
            "case_id": "deterministic",
            "delegate": True,
            "model": "Terra",
            "effort": "medium",
            "schedule": "single",
            "rationale": "",
        }
        self.assertIn("rationale: required non-empty string", grade_case(self.case, response))

    def test_surfaces_provider_errors(self):
        response = {
            "case_id": "deterministic",
            "rationale": "",
            "provider_error": "CLI exited 1: not authenticated",
        }
        self.assertIn(
            "provider_error: CLI exited 1: not authenticated",
            grade_case(self.case, response),
        )

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


class GradeSuiteTests(unittest.TestCase):
    def test_reports_missing_and_unknown_responses(self):
        suite = {"cases": [{"id": "known", "expected": {}}]}
        responses = [{"case_id": "unknown", "rationale": "present"}]
        result = grade_suite(suite, responses)
        self.assertFalse(result["passed"])
        self.assertEqual(["known"], result["missing_case_ids"])
        self.assertEqual(["unknown"], result["unknown_case_ids"])

    def test_aggregates_repetition_pass_rates(self):
        suite = {
            "skill": "pick-codex-crew",
            "cases": [
                {
                    "id": "known",
                    "runtime": {"models": ["Terra"], "efforts": ["low"]},
                    "expected": {
                        "delegate": True,
                        "model": ["Terra"],
                        "effort": ["low"],
                        "schedule": ["single"],
                    },
                }
            ],
        }
        passing = {
            "case_id": "known",
            "delegate": True,
            "model": "Terra",
            "effort": "low",
            "schedule": "single",
            "rationale": "bounded",
        }
        failing = {**passing, "model": "Sol"}
        summary = grade_repetitions(suite, [[passing], [failing]])
        self.assertEqual(2, summary["repetitions"])
        self.assertEqual(1, summary["passed_repetitions"])
        self.assertEqual(0.5, summary["case_pass_rates"]["known"])


class IntegrationCaseFileTests(unittest.TestCase):
    @staticmethod
    def selections(suite):
        return {
            (model, effort)
            for case in suite["cases"]
            for model in case["expected"]["model"]
            for effort in case["expected"]["effort"]
            if model is not None and effort is not None
        }

    def test_claude_opus_suite_uses_the_real_parent_cap(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-claude-crew-opus.json").read_text()
        )
        self.assertTrue(suite["cases"])
        self.assertTrue(
            all(case["runtime"]["parent_model"] == "Opus" for case in suite["cases"])
        )
        self.assertTrue(all("Fable" not in case["expected"]["model"] for case in suite["cases"]))

    def test_codex_sol_suite_uses_the_real_parent_cap(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-codex-crew-sol.json").read_text()
        )
        self.assertTrue(suite["cases"])
        self.assertTrue(
            all(case["runtime"]["parent_model"] == "Sol" for case in suite["cases"])
        )

    def test_claude_suite_covers_model_and_effort_as_independent_axes(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-claude-crew-opus.json").read_text()
        )
        self.assertTrue(
            {("Sonnet", "high"), ("Opus", "medium"), ("Opus", "low")}
            <= self.selections(suite)
        )

    def test_codex_suite_covers_model_and_effort_as_independent_axes(self):
        suite = json.loads(
            (Path(__file__).parent / "cases" / "pick-codex-crew-sol.json").read_text()
        )
        self.assertTrue(
            {("Terra", "high"), ("Sol", "medium"), ("Sol", "low")}
            <= self.selections(suite)
        )

    def test_exhaustive_deterministic_tasks_use_medium_effort(self):
        for filename in ("pick-claude-crew-opus.json", "pick-codex-crew-sol.json"):
            suite = json.loads((Path(__file__).parent / "cases" / filename).read_text())
            deterministic = next(
                case for case in suite["cases"] if case["id"].endswith("deterministic")
            )
            self.assertEqual(["medium"], deterministic["expected"]["effort"])


class RenderPromptTests(unittest.TestCase):
    def test_skill_mode_embeds_skill_and_output_contract(self):
        suite = {"skill": "pick-codex-crew"}
        case = {
            "id": "case-1",
            "prompt": "Choose a crew.",
            "runtime": {"parent_model": "Sol"},
        }
        prompt = render_prompt(suite, case, "# Skill body", mode="skill")
        self.assertIn("# Skill body", prompt)
        self.assertIn('"case_id"', prompt)
        self.assertIn('"schedule"', prompt)

    def test_control_mode_omits_skill(self):
        suite = {"skill": "pick-codex-crew"}
        case = {"id": "case-1", "prompt": "Choose a crew.", "runtime": {}}
        prompt = render_prompt(suite, case, "SECRET SKILL", mode="control")
        self.assertNotIn("SECRET SKILL", prompt)

    def test_skill_mode_asks_for_lane(self):
        suite = {"skill": "pick-crew"}
        case = {"id": "case-1", "prompt": "Choose a crew.", "runtime": {}}
        prompt = render_prompt(suite, case, "# Skill body", mode="skill")
        self.assertIn('"lane"', prompt)
        self.assertIn('"claude" or "codex"', prompt)

    def test_skill_mode_asks_for_pin_conflict(self):
        suite = {"skill": "pick-crew"}
        case = {"id": "case-1", "prompt": "Choose a crew.", "runtime": {}}
        prompt = render_prompt(suite, case, "# Skill body", mode="skill")
        self.assertIn('"pin_conflict"', prompt)


class RunSuiteTests(unittest.TestCase):
    def test_runs_every_case_for_every_repetition(self):
        suite = {
            "skill": "pick-codex-crew",
            "cases": [
                {"id": "a", "prompt": "A", "runtime": {}},
                {"id": "b", "prompt": "B", "runtime": {}},
            ],
        }
        calls = []

        def fake_runner(prompt):
            case_id = "a" if '"a"' in prompt else "b"
            calls.append(case_id)
            return {"case_id": case_id, "rationale": "chosen"}

        runs = run_suite(
            suite,
            "# Skill",
            mode="skill",
            repetitions=2,
            runner=fake_runner,
        )
        self.assertEqual(["a", "b", "a", "b"], calls)
        self.assertEqual(2, len(runs))
        self.assertEqual(["a", "b"], [item["case_id"] for item in runs[0]])

    def test_direct_cli_entry_point_runs_from_repo_root(self):
        repo_root = Path(__file__).resolve().parent.parent
        completed = subprocess.run(
            [sys.executable, "evals/crew_eval.py", "run", "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_repetitions_must_be_positive(self):
        self.assertEqual(2, positive_int("2"))
        with self.assertRaisesRegex(Exception, "at least 1"):
            positive_int("0")

    def test_output_directory_must_be_under_ignored_results_root(self):
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            accepted = repo_root / "evals" / "results" / "codex-skill"
            self.assertEqual(accepted.resolve(), validated_output_dir(str(accepted), repo_root))
            with self.assertRaisesRegex(ValueError, "must be a child"):
                validated_output_dir(str(repo_root / "untracked-results"), repo_root)

    def test_live_run_fails_by_default_and_allow_fail_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            cases_dir = repo_root / "evals" / "cases"
            skill_dir = repo_root / "skills" / "pick-codex-crew"
            cases_dir.mkdir(parents=True)
            skill_dir.mkdir(parents=True)
            cases_path = cases_dir / "pick-codex-crew.json"
            cases_path.write_text(json.dumps({
                "skill": "pick-codex-crew",
                "skill_path": "skills/pick-codex-crew/SKILL.md",
                "cases": [{
                    "id": "case-1",
                    "prompt": "Choose.",
                    "runtime": {},
                    "expected": {"delegate": True},
                }],
            }))
            (skill_dir / "SKILL.md").write_text("# Skill\n")

            def arguments(allow_fail):
                return type("Args", (), {
                    "cases": str(cases_path),
                    "case_id": None,
                    "provider": "codex",
                    "model": "gpt-5.6-sol",
                    "effort": "low",
                    "mode": "skill",
                    "repetitions": 1,
                    "output_dir": str(repo_root / "evals" / "results" / "run"),
                    "allow_fail": allow_fail,
                })()

            failing_response = {"case_id": "case-1", "delegate": False, "rationale": "no"}
            with patch("evals.crew_eval.run_provider", return_value=failing_response):
                self.assertEqual(1, run_command(arguments(False)))
                self.assertEqual(0, run_command(arguments(True)))

    def test_invalid_output_directory_prevents_provider_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            cases_dir = repo_root / "evals" / "cases"
            skill_dir = repo_root / "skills" / "pick-codex-crew"
            cases_dir.mkdir(parents=True)
            skill_dir.mkdir(parents=True)
            cases_path = cases_dir / "pick-codex-crew.json"
            cases_path.write_text(json.dumps({
                "skill": "pick-codex-crew",
                "skill_path": "skills/pick-codex-crew/SKILL.md",
                "cases": [{"id": "case-1", "prompt": "Choose.", "runtime": {}}],
            }))
            (skill_dir / "SKILL.md").write_text("# Skill\n")
            args = type("Args", (), {
                "cases": str(cases_path),
                "case_id": None,
                "provider": "codex",
                "model": "gpt-5.6-sol",
                "effort": "low",
                "mode": "skill",
                "repetitions": 1,
                "output_dir": str(repo_root / "not-ignored"),
                "allow_fail": False,
            })()

            with patch("evals.crew_eval.run_provider") as provider:
                with self.assertRaisesRegex(ValueError, "must be a child"):
                    run_command(args)
                provider.assert_not_called()


class ProviderAdapterTests(unittest.TestCase):
    def test_builds_isolated_claude_command(self):
        command = build_claude_command(model="sonnet", effort="medium")
        self.assertEqual("claude", command[0])
        self.assertIn("--safe-mode", command)
        self.assertIn("--no-session-persistence", command)
        self.assertEqual("sonnet", command[command.index("--model") + 1])
        self.assertEqual("medium", command[command.index("--effort") + 1])
        self.assertIn("--json-schema", command)

    def test_parses_claude_structured_output(self):
        response = {"case_id": "x", "delegate": False, "rationale": "tiny"}
        wrapped = json.dumps({"structured_output": response})
        self.assertEqual(response, parse_claude_output(wrapped))

    def test_parses_claude_result_string(self):
        response = {"case_id": "x", "delegate": False, "rationale": "tiny"}
        wrapped = json.dumps({"result": json.dumps(response)})
        self.assertEqual(response, parse_claude_output(wrapped))

    def test_builds_isolated_codex_command(self):
        command = build_codex_command(
            model="gpt-5.6-terra",
            effort="medium",
            schema_path=Path("/tmp/schema.json"),
            output_path=Path("/tmp/output.json"),
            cwd=Path("/tmp/work"),
        )
        self.assertEqual(["codex", "exec"], command[:2])
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ephemeral", command)
        self.assertEqual("read-only", command[command.index("--sandbox") + 1])
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertEqual("-", command[-1])

    def test_parses_codex_output(self):
        response = {"case_id": "x", "delegate": False, "rationale": "tiny"}
        self.assertEqual(response, parse_codex_output(json.dumps(response)))

    def test_codex_runner_streams_prompt_over_stdin(self):
        response = {"case_id": "x", "delegate": False, "rationale": "tiny"}

        def complete(command, **kwargs):
            output_path = Path(command[command.index("--output-last-message") + 1])
            output_path.write_text(json.dumps(response))
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch("evals.providers.subprocess.run", side_effect=complete) as mocked:
            self.assertEqual(
                response,
                run_codex("prompt", model="gpt-5.6-sol", effort="low", cwd=Path("/tmp")),
            )
        self.assertEqual("prompt", mocked.call_args.kwargs["input"])
        self.assertNotIn("stdin", mocked.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
