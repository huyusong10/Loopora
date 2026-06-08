from __future__ import annotations

import json
import re
from pathlib import Path

from loopora.executor_command_events import (
    COMMAND_EVENT_PREVIEW_LIMIT as COMMAND_EVENT_PREVIEW_LIMIT,
    build_command_event_payload as build_command_event_payload,
)
from loopora.executor_command_validation import (
    COMMAND_PLACEHOLDER_PATTERN as COMMAND_PLACEHOLDER_PATTERN,
    COMMAND_PLACEHOLDERS as COMMAND_PLACEHOLDERS,
    parse_command_args_text as parse_command_args_text,
    parse_extra_cli_args_text as parse_extra_cli_args_text,
    validate_command_args_text as validate_command_args_text,
    validate_extra_cli_args_text as validate_extra_cli_args_text,
)
from loopora.executor_result_files import (
    EXECUTOR_OUTPUT_MAX_BYTES as EXECUTOR_OUTPUT_MAX_BYTES,
    read_executor_output_text as read_executor_output_text,
)
from loopora.executor_types import RoleRequest
from loopora.providers import (
    coerce_reasoning_setting,
    normalize_reasoning_setting,
)


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
