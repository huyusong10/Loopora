from __future__ import annotations

import json
import re
from pathlib import Path

from loopora.executor_types import RoleRequest
from loopora.providers import (
    coerce_reasoning_setting,
    normalize_reasoning_setting,
)


import shlex

from loopora.providers import executor_profile






from loopora.executor_types import ExecutorError


def parse_structured_output_from_text(text: str) -> dict | None:
    candidate = str(text or "").strip()
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None

EXECUTOR_OUTPUT_MAX_BYTES = 1_000_000

def write_executor_schema_file(request: RoleRequest) -> Path:
    schema_path = request.run_dir / f"{request.role}_schema.json"
    schema_path.write_text(json.dumps(request.output_schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return schema_path

def write_executor_json_output(request: RoleRequest, payload: dict) -> None:
    request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def read_executor_json_object_output(
    request: RoleRequest,
    *,
    executor_label: str,
    invalid_json_message: str,
    non_object_message: str,
    allow_text_fallback: bool = False,
) -> dict:
    output_text = read_executor_output_text(request.output_path, role=request.role, executor_label=executor_label)
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        if allow_text_fallback:
            payload = parse_structured_output_from_text(output_text)
            if isinstance(payload, dict):
                return payload
        raise ExecutorError(invalid_json_message) from exc
    if not isinstance(payload, dict):
        raise ExecutorError(non_object_message)
    return payload

def read_executor_output_text(path: Path, *, role: str, executor_label: str) -> str:
    try:
        output_size = path.stat().st_size
    except OSError as exc:
        raise ExecutorError(f"{executor_label} output file is not readable for role={role}") from exc
    if output_size > EXECUTOR_OUTPUT_MAX_BYTES:
        raise ExecutorError(
            f"{executor_label} output file is too large for role={role}: "
            f"{output_size} bytes exceeds {EXECUTOR_OUTPUT_MAX_BYTES} bytes"
        )
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ExecutorError(f"role={role} produced non-UTF-8 output") from exc

COMMAND_EVENT_PREVIEW_LIMIT = 500

_SENSITIVE_ARG_NAMES = {
    "--api-key",
    "--auth-token",
    "--bearer-token",
    "--client-secret",
    "--cookie",
    "--password",
    "--private-key",
    "--proxy-authorization",
    "--secret",
    "--secret-token",
    "--set-cookie",
    "--token",
    "--x-api-key",
    "--x-loopora-token",
}

def build_command_event_payload(request: RoleRequest, args: list[str]) -> dict:
    schema_json = json.dumps(request.output_schema, ensure_ascii=False)
    prompt = str(request.prompt or "")
    sanitized_args: list[str] = []
    prompt_omitted = False
    json_schema_omitted = False
    token_omitted = False
    omit_next_value = False

    for raw_arg in args:
        arg = str(raw_arg)
        if omit_next_value:
            sanitized_args.append("<secret omitted>")
            token_omitted = True
            omit_next_value = False
            continue

        flag_name = arg.split("=", 1)[0].strip().lower().replace("_", "-")
        if flag_name in _SENSITIVE_ARG_NAMES:
            if "=" in arg:
                sanitized_args.append(f"{arg.split('=', 1)[0]}=<secret omitted>")
                token_omitted = True
            else:
                sanitized_args.append(arg)
                omit_next_value = True
            continue

        if prompt and prompt in arg:
            arg = arg.replace(prompt, "<prompt omitted>")
            prompt_omitted = True
        if schema_json and schema_json in arg:
            arg = arg.replace(schema_json, "<json schema omitted>")
            json_schema_omitted = True
        sanitized_args.append(arg)

    if omit_next_value:
        sanitized_args.append("<secret omitted>")
        token_omitted = True

    message = shlex.join(sanitized_args)
    command_truncated = len(message) > COMMAND_EVENT_PREVIEW_LIMIT
    if command_truncated:
        message = message[: COMMAND_EVENT_PREVIEW_LIMIT - 1].rstrip() + "…"

    return {
        "type": "command",
        "message": message,
        "prompt_omitted": prompt_omitted,
        "json_schema_omitted": json_schema_omitted,
        "token_omitted": token_omitted,
        "command_truncated": command_truncated,
        "arg_count": len(args),
    }

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


def normalize_reasoning_effort(value: str | None, executor_kind: str = "codex") -> str:
    return normalize_reasoning_setting(value, executor_kind=executor_kind)


def coerce_reasoning_effort(value: str | None, executor_kind: str = "codex") -> str:
    return coerce_reasoning_setting(value, executor_kind=executor_kind)


def build_codex_exec_args(request: RoleRequest, schema_path: Path) -> list[str]:
    reasoning_effort = coerce_reasoning_effort(request.reasoning_effort, request.executor_kind)
    extra_args = parse_extra_cli_args_text(request.extra_cli_args_text)
    resume_session_id = request.resume_session_id.strip()
    if request.inherit_session and resume_session_id:
        args = [
            "codex",
            "exec",
            "resume",
            "--json",
            "--skip-git-repo-check",
            "--output-last-message",
            str(request.output_path),
        ]
        if request.model.strip():
            args.extend(["--model", request.model.strip()])
        if reasoning_effort:
            args.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
        args.extend(extra_args)
        args.append(resume_session_id)
        args.append("-")
        return args

    args = [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--cd",
        str(request.workdir),
        "--sandbox",
        request.sandbox,
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(request.output_path),
    ]
    if request.model.strip():
        args.extend(["--model", request.model.strip()])
    if reasoning_effort:
        args.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
    args.extend(extra_args)
    args.append("-")
    return args


def build_claude_exec_args(request: RoleRequest) -> list[str]:
    extra_args = parse_extra_cli_args_text(request.extra_cli_args_text)
    args = ["claude", "--setting-sources", "user,project,local"]
    if request.inherit_session and request.resume_session_id.strip():
        args.extend(["--resume", request.resume_session_id.strip()])
    args.extend(["-p", "--output-format", "stream-json", "--include-partial-messages"])
    if not request.inherit_session:
        args.append("--no-session-persistence")
    args.extend(
        [
            "--permission-mode",
            "bypassPermissions",
            "--json-schema",
            json.dumps(request.output_schema, ensure_ascii=False),
        ]
    )
    if request.model.strip():
        args.extend(["--model", request.model.strip()])
    reasoning_effort = coerce_reasoning_effort(request.reasoning_effort, request.executor_kind)
    if reasoning_effort:
        args.extend(["--effort", reasoning_effort])
    args.extend(extra_args)
    args.append(request.prompt)
    return args


def build_opencode_exec_args(request: RoleRequest) -> list[str]:
    extra_args = parse_extra_cli_args_text(request.extra_cli_args_text)
    args = [
        "opencode",
        "run",
        "--format",
        "json",
        "--dir",
        str(request.workdir),
        "--dangerously-skip-permissions",
    ]
    resume_session_id = request.resume_session_id.strip()
    if request.inherit_session and resume_session_id:
        args.extend(["--session", resume_session_id])
    args.extend(extra_args)
    if request.model.strip():
        args.extend(["--model", request.model.strip()])
    variant = coerce_reasoning_effort(request.reasoning_effort, request.executor_kind)
    if variant:
        args.extend(["--variant", variant])
    args.append(request.prompt)
    return args


def build_custom_exec_args(request: RoleRequest, schema_path: Path) -> list[str]:
    cli_name = request.command_cli.strip()
    if not cli_name:
        raise ValueError("custom command executable is required in command mode")
    template_args = validate_command_args_text(request.command_args_text, executor_kind=request.executor_kind)
    extra_args = parse_extra_cli_args_text(request.extra_cli_args_text)
    replacements = {
        "{workdir}": str(request.workdir),
        "{schema_path}": str(schema_path),
        "{output_path}": str(request.output_path),
        "{prompt}": request.prompt,
        "{sandbox}": request.sandbox,
        "{json_schema}": json.dumps(request.output_schema, ensure_ascii=False),
        "{model}": request.model,
        "{reasoning_effort}": request.reasoning_effort,
        "{resume_session_id}": request.resume_session_id,
        "{alignment_session_id}": str(request.extra_context.get("alignment_session_id", "")),
        "{session_ref_json}": json.dumps(request.extra_context.get("session_ref") or {}, ensure_ascii=False),
    }
    placeholder_pattern = re.compile("|".join(re.escape(placeholder) for placeholder in replacements))
    resolved_args = []
    extra_args_consumed = False
    for template_arg in template_args:
        if template_arg.strip() == "{extra_cli_args}":
            resolved_args.extend(extra_args)
            extra_args_consumed = True
            continue
        if template_arg.strip() == "{prompt}" and extra_args and not extra_args_consumed:
            resolved_args.extend(extra_args)
            extra_args_consumed = True
        value = placeholder_pattern.sub(lambda match: replacements[match.group(0)], template_arg)
        if not value:
            if resolved_args and resolved_args[-1].startswith("-"):
                resolved_args.pop()
            continue
        resolved_args.append(value)
    if extra_args and not extra_args_consumed:
        resolved_args.extend(extra_args)
    return [cli_name, *resolved_args]
