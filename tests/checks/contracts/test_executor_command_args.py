from __future__ import annotations

from pathlib import Path

import pytest

from executor_request_test_support import role_request
from loopora.executor import build_custom_exec_args, validate_command_args_text, validate_extra_cli_args_text

CODEX_JSON_COMMAND_ARGS = [
    "exec",
    "--json",
    "--output-schema",
    "{schema_path}",
    "--output-last-message",
    "{output_path}",
    "{prompt}",
]
CLAUDE_STREAM_COMMAND_ARGS = [
    "-p",
    "--output-format",
    "stream-json",
    "--json-schema",
    "{json_schema}",
    "{prompt}",
]


def test_custom_exec_args_require_runtime_placeholders() -> None:
    with pytest.raises(ValueError, match="missing required placeholders"):
        validate_command_args_text("--model\ngpt-5.4\n{prompt}\n", executor_kind="codex")


def test_claude_command_args_require_json_schema_placeholder() -> None:
    with pytest.raises(ValueError, match="\\{json_schema\\}"):
        validate_command_args_text("-p\n--output-format\nstream-json\n{prompt}\n", executor_kind="claude")


def test_custom_command_args_require_output_path_placeholder() -> None:
    with pytest.raises(ValueError, match="\\{output_path\\}"):
        validate_command_args_text("--prompt\n{prompt}\n", executor_kind="custom")


def test_custom_command_args_reject_unknown_placeholders() -> None:
    with pytest.raises(ValueError, match="unsupported placeholders: \\{outpt_path\\}"):
        validate_command_args_text(
            "exec\n--output-schema\n{schema_path}\n--output-last-message\n{output_path}\n{outpt_path}\n{prompt}\n",
            executor_kind="codex",
        )


def test_custom_command_args_allow_json_literals() -> None:
    args = validate_command_args_text(
        '--config\n{"mode":"strict"}\n--output\n{output_path}\n{prompt}\n',
        executor_kind="custom",
    )

    assert '{"mode":"strict"}' in args


def test_extra_cli_args_placeholder_must_be_its_own_argument() -> None:
    with pytest.raises(ValueError, match="\\{extra_cli_args\\} must be its own argument"):
        validate_command_args_text(
            "--output\n{output_path}\n--flags={extra_cli_args}\n{prompt}\n",
            executor_kind="custom",
        )


def test_custom_exec_args_resolve_runtime_values(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="claude", model="sonnet", reasoning_effort="medium")
    _set_command_mode(request, "claude", CLAUDE_STREAM_COMMAND_ARGS)

    args = build_custom_exec_args(request, request.run_dir / "schema.json")

    assert args[0] == "claude"
    assert "--json-schema" in args
    assert "Return JSON only." in args
    schema_arg = args[args.index("--json-schema") + 1]
    assert schema_arg.startswith("{")


def test_custom_exec_args_insert_extra_cli_args_before_prompt_when_possible(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="codex", model="gpt-5.4", reasoning_effort="medium")
    _set_command_mode(request, "codex", CODEX_JSON_COMMAND_ARGS)
    request.extra_cli_args_text = "--verbose --search"

    args = build_custom_exec_args(request, request.run_dir / "schema.json")

    prompt_index = args.index("Return JSON only.")
    assert args[prompt_index - 2 : prompt_index] == ["--verbose", "--search"]


def test_custom_exec_args_drop_empty_placeholder_lines(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="opencode", model="", reasoning_effort="")
    _set_command_mode(request, "opencode", ["run", "--model", "{model}", "{prompt}"])

    args = build_custom_exec_args(request, request.run_dir / "schema.json")

    assert args == ["opencode", "run", "Return JSON only."]


def test_custom_exec_args_do_not_expand_placeholders_inside_prompt_value(tmp_path: Path) -> None:
    request = role_request(tmp_path, executor_kind="codex", model="gpt-5.4", reasoning_effort="medium")
    request.prompt = "Keep the literal token {workdir} in the final prompt."
    _set_command_mode(request, "codex", CODEX_JSON_COMMAND_ARGS)

    args = build_custom_exec_args(request, request.run_dir / "schema.json")

    assert args[-1] == "Keep the literal token {workdir} in the final prompt."


def test_extra_cli_args_validation_rejects_unbalanced_quotes() -> None:
    with pytest.raises(ValueError, match="invalid extra CLI args"):
        validate_extra_cli_args_text('--verbose "unterminated')


def _set_command_mode(request, command_cli: str, command_args: list[str]) -> None:
    request.executor_mode = "command"
    request.command_cli = command_cli
    request.command_args_text = "\n".join(command_args)
