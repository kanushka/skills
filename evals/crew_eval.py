#!/usr/bin/env python3
"""Render and grade portable eval cases for the crew-selection skills."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

if __package__:
    from .providers import run_provider
else:
    from providers import run_provider


GRADED_FIELDS = ("delegate", "lane", "model", "effort", "schedule")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_responses(path: Path) -> list[dict[str, Any]]:
    text = path.read_text().strip()
    if not text:
        return []
    if text.startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise ValueError("responses JSON must be an array or JSONL")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def grade_case(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if response.get("provider_error"):
        errors.append(f"provider_error: {response['provider_error']}")
    if response.get("case_id") != case["id"]:
        errors.append(f"case_id: expected {case['id']!r}, got {response.get('case_id')!r}")

    for field in GRADED_FIELDS:
        if field not in case.get("expected", {}):
            continue
        configured = case["expected"][field]
        allowed = configured if isinstance(configured, list) else [configured]
        actual = response.get(field)
        if actual not in allowed:
            errors.append(f"{field}: expected one of {allowed!r}, got {actual!r}")

    rationale = response.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("rationale: required non-empty string")

    runtime = case.get("runtime", {})
    model = response.get("model")
    if model is not None and model not in runtime.get("models", []):
        errors.append(f"model: {model!r} is not exposed by the runtime")
    effort = response.get("effort")
    if effort is not None and effort not in runtime.get("efforts", []):
        errors.append(f"effort: {effort!r} is not exposed by the runtime")
    return errors


def grade_suite(
    suite: dict[str, Any], responses: list[dict[str, Any]]
) -> dict[str, Any]:
    cases = {case["id"]: case for case in suite.get("cases", [])}
    response_map: dict[str, dict[str, Any]] = {}
    duplicate_case_ids: list[str] = []
    unknown_case_ids: list[str] = []

    for response in responses:
        case_id = response.get("case_id")
        if case_id in response_map:
            duplicate_case_ids.append(case_id)
            continue
        response_map[case_id] = response
        if case_id not in cases:
            unknown_case_ids.append(case_id)

    missing_case_ids = [case_id for case_id in cases if case_id not in response_map]
    results = []
    for case_id, case in cases.items():
        if case_id not in response_map:
            continue
        errors = grade_case(case, response_map[case_id])
        results.append({"case_id": case_id, "passed": not errors, "errors": errors})

    passed = (
        not missing_case_ids
        and not unknown_case_ids
        and not duplicate_case_ids
        and all(result["passed"] for result in results)
    )
    return {
        "skill": suite.get("skill"),
        "passed": passed,
        "passed_count": sum(result["passed"] for result in results),
        "case_count": len(cases),
        "missing_case_ids": missing_case_ids,
        "unknown_case_ids": unknown_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "results": results,
    }


def grade_repetitions(
    suite: dict[str, Any], runs: list[list[dict[str, Any]]]
) -> dict[str, Any]:
    run_results = [grade_suite(suite, responses) for responses in runs]
    case_ids = [case["id"] for case in suite.get("cases", [])]
    passed_by_case = {case_id: 0 for case_id in case_ids}
    for result in run_results:
        by_id = {item["case_id"]: item for item in result["results"]}
        for case_id in case_ids:
            if by_id.get(case_id, {}).get("passed"):
                passed_by_case[case_id] += 1
    repetitions = len(runs)
    return {
        "skill": suite.get("skill"),
        "repetitions": repetitions,
        "passed_repetitions": sum(result["passed"] for result in run_results),
        "case_pass_rates": {
            case_id: (passed_by_case[case_id] / repetitions if repetitions else 0.0)
            for case_id in case_ids
        },
        "runs": run_results,
    }


def render_prompt(
    suite: dict[str, Any],
    case: dict[str, Any],
    skill_text: str,
    *,
    mode: str,
) -> str:
    if mode not in {"control", "skill"}:
        raise ValueError("mode must be 'control' or 'skill'")

    sections = [
        "Choose the crew configuration for the task below.",
        f"Runtime constraints:\n{json.dumps(case.get('runtime', {}), indent=2)}",
        f"Task:\n{case['prompt']}",
    ]
    if mode == "skill":
        sections.append(f"Apply this skill exactly:\n\n{skill_text}")
    else:
        sections.append("Control run: make the decision without reading or invoking any skill.")

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
    return "\n\n".join(sections)


def run_suite(
    suite: dict[str, Any],
    skill_text: str,
    *,
    mode: str,
    repetitions: int,
    runner: Callable[[str], dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    runs: list[list[dict[str, Any]]] = []
    for repetition in range(1, repetitions + 1):
        responses = []
        for case in suite.get("cases", []):
            print(
                f"[{repetition}/{repetitions}] {case['id']}",
                file=sys.stderr,
                flush=True,
            )
            prompt = render_prompt(suite, case, skill_text, mode=mode)
            try:
                response = runner(prompt)
            except Exception as error:  # Preserve provider errors as gradable output.
                response = {
                    "case_id": case["id"],
                    "rationale": "",
                    "provider_error": str(error),
                }
            responses.append(response)
        runs.append(responses)
    return runs


def repo_root_for_cases(cases_path: Path) -> Path:
    return cases_path.resolve().parent.parent.parent


def render_command(args: argparse.Namespace) -> int:
    cases_path = Path(args.cases)
    suite = load_json(cases_path)
    skill_path = repo_root_for_cases(cases_path) / suite["skill_path"]
    skill_text = skill_path.read_text()
    rendered = [
        {
            "case_id": case["id"],
            "prompt": render_prompt(suite, case, skill_text, mode=args.mode),
        }
        for case in suite["cases"]
    ]
    output = "\n".join(json.dumps(item) for item in rendered) + "\n"
    if args.output:
        Path(args.output).write_text(output)
    else:
        sys.stdout.write(output)
    return 0


def grade_command(args: argparse.Namespace) -> int:
    result = grade_suite(load_json(Path(args.cases)), load_responses(Path(args.responses)))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def validated_output_dir(value: str, repo_root: Path) -> Path:
    output_dir = Path(value).resolve()
    results_root = (repo_root / "evals" / "results").resolve()
    if not output_dir.is_relative_to(results_root) or output_dir == results_root:
        raise ValueError(
            f"output directory must be a child of {results_root}, got {output_dir}"
        )
    return output_dir


def run_command(args: argparse.Namespace) -> int:
    cases_path = Path(args.cases)
    suite = load_json(cases_path)
    if args.case_id:
        requested = set(args.case_id)
        known = {case["id"] for case in suite.get("cases", [])}
        unknown = sorted(requested - known)
        if unknown:
            raise ValueError(f"unknown case ids: {unknown}")
        suite = {**suite, "cases": [case for case in suite["cases"] if case["id"] in requested]}

    repo_root = repo_root_for_cases(cases_path)
    output_dir = validated_output_dir(args.output_dir, repo_root)
    skill_text = (repo_root / suite["skill_path"]).read_text()
    runner = lambda prompt: run_provider(
        args.provider,
        prompt,
        model=args.model,
        effort=args.effort,
        cwd=repo_root,
    )
    runs = run_suite(
        suite,
        skill_text,
        mode=args.mode,
        repetitions=args.repetitions,
        runner=runner,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    for index, responses in enumerate(runs, start=1):
        (output_dir / f"rep-{index:03d}.responses.json").write_text(
            json.dumps(responses, indent=2) + "\n"
        )
        (output_dir / f"rep-{index:03d}.grade.json").write_text(
            json.dumps(grade_suite(suite, responses), indent=2) + "\n"
        )
    summary = grade_repetitions(suite, runs)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if not args.allow_fail and summary["passed_repetitions"] != summary["repetitions"]:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser("render", help="render control or skill prompts as JSONL")
    render.add_argument("--cases", required=True)
    render.add_argument("--mode", choices=("control", "skill"), required=True)
    render.add_argument("--output")
    render.set_defaults(func=render_command)

    grade = subparsers.add_parser("grade", help="grade JSON or JSONL responses")
    grade.add_argument("--cases", required=True)
    grade.add_argument("--responses", required=True)
    grade.set_defaults(func=grade_command)

    run = subparsers.add_parser("run", help="run cases through Claude Code or Codex CLI")
    run.add_argument("--provider", choices=("claude", "codex"), required=True)
    run.add_argument("--cases", required=True)
    run.add_argument("--mode", choices=("control", "skill"), required=True)
    run.add_argument("--model", required=True, help="model used to execute the eval")
    run.add_argument("--effort", default="medium", help="effort used to execute the eval")
    run.add_argument("--repetitions", type=positive_int, default=1)
    run.add_argument("--case-id", action="append")
    run.add_argument("--output-dir", required=True)
    run.add_argument(
        "--allow-fail",
        action="store_true",
        help="exit zero after writing results even when one or more repetitions fail",
    )
    run.set_defaults(func=run_command)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
