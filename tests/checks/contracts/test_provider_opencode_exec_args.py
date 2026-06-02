from __future__ import annotations

from pathlib import Path

from executor_request_test_support import role_request
from loopora.executor import build_opencode_exec_args
from loopora.providers import OPENCODE_DEFAULT_MODEL, executor_profile


def test_opencode_exec_args_use_variant_only_when_present(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="opencode", model="", reasoning_effort="")
    args = build_opencode_exec_args(request)

    assert args[:4] == ["opencode", "run", "--format", "json"]
    assert "--dangerously-skip-permissions" in args
    assert "--model" not in args
    assert "--variant" not in args


def test_opencode_preset_defaults_to_cli_model() -> None:
    profile = executor_profile("opencode")

    assert profile.default_model == OPENCODE_DEFAULT_MODEL
    assert profile.default_model == ""
    assert "--model" not in profile.command_args_template
    assert "{model}" not in profile.command_args_template


def test_opencode_exec_args_include_model_when_pinned(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="opencode", model="provider/model", reasoning_effort="")
    args = build_opencode_exec_args(request)

    assert "--model" in args
    assert args[args.index("--model") + 1] == "provider/model"
    assert "--variant" not in args


def test_opencode_exec_args_can_resume_session_and_append_extra_args(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="opencode", model="", reasoning_effort="")
    request.inherit_session = True
    request.resume_session_id = "open-session-42"
    request.extra_cli_args_text = "--share"

    args = build_opencode_exec_args(request)

    assert "--session" in args
    assert "open-session-42" in args
    assert "--share" in args
