"""Live Claude Code and Codex CLI adapters for crew evals."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


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


def build_claude_command(*, model: str, effort: str) -> list[str]:
    return [
        "claude",
        "-p",
        "--safe-mode",
        "--no-session-persistence",
        "--tools",
        "",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(OUTPUT_SCHEMA, separators=(",", ":")),
        "--model",
        model,
        "--effort",
        effort,
    ]


def build_codex_command(
    *,
    model: str,
    effort: str,
    schema_path: Path,
    output_path: Path,
    cwd: Path,
) -> list[str]:
    return [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--cd",
        str(cwd),
        "--model",
        model,
        "--config",
        f'model_reasoning_effort="{effort}"',
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_path),
        "-",
    ]


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end < start:
            raise ValueError("provider output does not contain a JSON object")
        value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("provider output must be a JSON object")
    return value


def parse_claude_output(stdout: str) -> dict[str, Any]:
    wrapper = _parse_json_object(stdout)
    if isinstance(wrapper.get("structured_output"), dict):
        return wrapper["structured_output"]
    result = wrapper.get("result")
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return _parse_json_object(result)
    if "case_id" in wrapper:
        return wrapper
    raise ValueError("Claude output contains neither structured_output nor result")


def parse_codex_output(text: str) -> dict[str, Any]:
    return _parse_json_object(text)


def run_claude(prompt: str, *, model: str, effort: str, cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        build_claude_command(model=model, effort=effort),
        cwd=cwd,
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Claude CLI exited {completed.returncode}: {detail}")
    return parse_claude_output(completed.stdout)


def run_codex(prompt: str, *, model: str, effort: str, cwd: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="crew-eval-codex-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "schema.json"
        output_path = temp_path / "output.json"
        schema_path.write_text(json.dumps(OUTPUT_SCHEMA))
        completed = subprocess.run(
            build_codex_command(
                model=model,
                effort=effort,
                schema_path=schema_path,
                output_path=output_path,
                cwd=cwd,
            ),
            cwd=cwd,
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Codex CLI exited {completed.returncode}: {detail}")
        if not output_path.exists():
            raise RuntimeError("Codex CLI did not write the requested output file")
        return parse_codex_output(output_path.read_text())


def run_provider(
    provider: str,
    prompt: str,
    *,
    model: str,
    effort: str,
    cwd: Path,
) -> dict[str, Any]:
    if provider == "claude":
        return run_claude(prompt, model=model, effort=effort, cwd=cwd)
    if provider == "codex":
        return run_codex(prompt, model=model, effort=effort, cwd=cwd)
    raise ValueError(f"unsupported provider: {provider}")
