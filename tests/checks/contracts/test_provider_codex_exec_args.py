from __future__ import annotations

from pathlib import Path

from executor_request_test_support import role_request
from loopora.executor import build_codex_exec_args
from loopora.providers import executor_profile


def test_codex_exec_args_include_output_schema_and_reasoning(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="codex", model="gpt-5.4", reasoning_effort="high")
    args = build_codex_exec_args(request, request.run_dir / "schema.json")

    assert args[:3] == ["codex", "exec", "--json"]
    assert args[-1] == "-"
    assert request.prompt not in args
    assert "--output-schema" in args
    assert "--output-last-message" in args
    assert "--model" in args
    assert args[args.index("--model") + 1] == "gpt-5.4"
    assert 'model_reasoning_effort="high"' in args


def test_codex_preset_defaults_to_cli_model() -> None:
    profile = executor_profile("codex")

    assert profile.default_model == ""
    assert profile.effort_default == ""
    assert "--model" not in profile.command_args_template
    assert "{model}" not in profile.command_args_template
    assert 'model_reasoning_effort="medium"' not in profile.command_args_template


def test_codex_exec_args_omit_model_and_reasoning_when_blank(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="codex", model="", reasoning_effort="")
    args = build_codex_exec_args(request, request.run_dir / "schema.json")

    assert args[:3] == ["codex", "exec", "--json"]
    assert args[-1] == "-"
    assert request.prompt not in args
    assert "--output-schema" in args
    assert "--output-last-message" in args
    assert "--model" not in args
    assert not any("model_reasoning_effort" in arg for arg in args)


def test_codex_exec_args_start_fresh_session_when_resume_id_is_missing(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="codex", model="gpt-5.4", reasoning_effort="medium")
    request.inherit_session = True
    request.resume_session_id = ""

    args = build_codex_exec_args(request, request.run_dir / "schema.json")

    assert args[:3] == ["codex", "exec", "--json"]
    assert "resume" not in args
    assert "--last" not in args
    assert "--cd" in args


def test_codex_exec_args_can_resume_previous_session_and_append_extra_args(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="codex", model="gpt-5.4", reasoning_effort="medium")
    request.inherit_session = True
    request.resume_session_id = "codex-session-123"
    request.extra_cli_args_text = "--search --verbose"

    args = build_codex_exec_args(request, request.run_dir / "schema.json")

    assert args[:3] == ["codex", "exec", "resume"]
    assert "codex-session-123" in args
    assert "--cd" not in args
    assert "--sandbox" not in args
    assert "--output-schema" not in args
    assert "--output-last-message" in args
    assert "--search" in args
    assert "--verbose" in args
    assert request.prompt not in args
    assert args[-1] == "-"
