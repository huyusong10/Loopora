from __future__ import annotations

import json
import shlex

from loopora.executor_types import RoleRequest


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
