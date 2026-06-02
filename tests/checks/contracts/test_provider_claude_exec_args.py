from __future__ import annotations

from pathlib import Path

from executor_request_test_support import role_request
from loopora.executor import build_claude_exec_args
from loopora.providers import CLAUDE_DEFAULT_MODEL, executor_profile


def test_claude_exec_args_map_xhigh_to_max(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="claude", model="sonnet", reasoning_effort="xhigh")
    args = build_claude_exec_args(request)

    assert args[:6] == ["claude", "--setting-sources", "user,project,local", "-p", "--output-format", "stream-json"]
    assert "--json-schema" in args
    assert "--model" in args
    assert "--effort" in args
    assert "max" in args
    assert "xhigh" not in args


def test_claude_exec_args_resume_session_and_drop_no_persistence(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="claude", model="sonnet", reasoning_effort="high")
    request.inherit_session = True
    request.resume_session_id = "claude-session-abc"
    request.extra_cli_args_text = "--verbose"

    args = build_claude_exec_args(request)

    assert "--resume" in args
    assert "claude-session-abc" in args
    assert "--no-session-persistence" not in args
    assert "--verbose" in args


def test_claude_preset_defaults_to_cli_model() -> None:
    profile = executor_profile("claude")

    assert profile.default_model == CLAUDE_DEFAULT_MODEL
    assert profile.default_model == ""
    assert profile.effort_default == ""
    assert "--model" not in profile.command_args_template
    assert "{model}" not in profile.command_args_template
    assert "--effort" not in profile.command_args_template


def test_claude_exec_args_omit_model_and_effort_when_blank(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="claude", model="", reasoning_effort="")
    args = build_claude_exec_args(request)

    assert args[:6] == ["claude", "--setting-sources", "user,project,local", "-p", "--output-format", "stream-json"]
    assert "--json-schema" in args
    assert "--model" not in args
    assert "--effort" not in args
