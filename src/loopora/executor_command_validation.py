from __future__ import annotations

import re
import shlex

from loopora.providers import executor_profile

COMMAND_PLACEHOLDER_PATTERN = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
COMMAND_PLACEHOLDERS = frozenset(
    {
        "{workdir}",
        "{schema_path}",
        "{output_path}",
        "{prompt}",
        "{sandbox}",
        "{json_schema}",
        "{model}",
        "{reasoning_effort}",
        "{resume_session_id}",
        "{alignment_session_id}",
        "{session_ref_json}",
        "{extra_cli_args}",
    }
)


def parse_command_args_text(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def parse_extra_cli_args_text(value: str | None) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    try:
        return shlex.split(text)
    except ValueError as exc:
        raise ValueError(f"invalid extra CLI args: {exc}") from exc


def validate_extra_cli_args_text(value: str | None) -> list[str]:
    return parse_extra_cli_args_text(value)


def validate_command_args_text(command_args_text: str | None, *, executor_kind: str) -> list[str]:
    args = parse_command_args_text(command_args_text)
    if not args:
        raise ValueError("custom command arguments are required in command mode")
    joined = "\n".join(args)
    unsupported_placeholders = sorted(set(COMMAND_PLACEHOLDER_PATTERN.findall(joined)) - COMMAND_PLACEHOLDERS)
    if unsupported_placeholders:
        joined_unsupported = ", ".join(unsupported_placeholders)
        raise ValueError(f"custom command has unsupported placeholders: {joined_unsupported}")
    invalid_extra_args_placeholder = [
        arg for arg in args if "{extra_cli_args}" in arg and arg.strip() != "{extra_cli_args}"
    ]
    if invalid_extra_args_placeholder:
        raise ValueError("custom command placeholder {extra_cli_args} must be its own argument")
    profile = executor_profile(executor_kind)
    required_placeholders = profile.command_required_placeholders
    missing = [placeholder for placeholder in required_placeholders if placeholder not in joined]
    if missing:
        joined_missing = ", ".join(missing)
        raise ValueError(f"custom command is missing required placeholders: {joined_missing}")
    return args
