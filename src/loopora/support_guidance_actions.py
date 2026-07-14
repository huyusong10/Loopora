from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
import shlex
from urllib.parse import urlencode

from loopora.agent_adapter_command_prefix import current_project_file_loopora_cli_entry, rewrite_loopora_command_entry
from loopora.support_guidance_constants import (
    SUPPORT_WORKDIR_PLACEHOLDER,
)
from loopora.support_guidance_routes import support_issue_route_actions
from loopora.web_origins import open_origin_for_bind_host
from loopora.workdir_inputs import workdir_path_state


def _support_next_actions(
    *,
    commands: Mapping[str, str],
    command_fields_executable: bool,
    target_project_required: bool,
    language: str,
    web_target_args: str,
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    command_field_blockers = ["target_project_required"] if target_project_required else []
    if target_project_required:
        actions.append(
            {
                "kind": "choose_workdir_for_public_report",
                "command": _public_support_target_project_command(language, web_target_args=web_target_args),
                "command_ready": True,
                "command_blockers": [],
                "local_only": True,
                "note": _support_text(
                    language,
                    "Run this from the target project to refresh support with ready preferred-bundle/fallback-report commands.",
                    "请先在目标项目中运行此命令，刷新出已就绪的优先支持包/兜底报告命令。",
                ),
            }
        )
    actions.extend(
        [
            {
                "kind": "run_public_issue_bundle",
                "command": commands["public_issue_bundle"],
                "command_ready": command_fields_executable,
                "command_blockers": list(command_field_blockers),
                "local_only": True,
                "public_output": "public_issue_bundle_output",
                "note": _support_text(
                    language,
                    "Run locally first when readiness evidence matters; paste the generated public issue bundle, not this command.",
                    "就绪证据相关时优先在本地运行；公开粘贴生成的公开 issue 支持包，不粘贴这条命令。",
                ),
            },
            {
                "kind": "run_public_doctor_report",
                "command": commands["public_doctor"],
                "command_ready": command_fields_executable,
                "command_blockers": list(command_field_blockers),
                "allows_nonzero_exit": True,
                "local_only": True,
                "public_output": "public_doctor_output",
                "note": _support_text(
                    language,
                    "Fallback: run locally only when maintainers request a separate readiness report; a blocked readiness report may exit nonzero, "
                    "but paste the redacted output, not this command.",
                    "兜底：只有维护者要求单独就绪报告时才在本地运行；就绪受阻时报告可能非零退出，"
                    "但公开粘贴脱敏输出，不粘贴这条命令。",
                ),
            },
            {
                "kind": "run_version_identity",
                "command": commands["version"],
                "command_ready": True,
                "command_blockers": [],
                "local_only": True,
                "public_output": "version_output",
                "public_outputs": ["version_output", "version_identity_json_output"],
                "structured_command": commands["version_json"],
                "structured_public_output": "version_identity_json_output",
                "note": _support_text(
                    language,
                    "Run locally and paste the compact identity output, or the structured JSON identity when tooling requests it.",
                    "在本地运行；报告问题时粘贴紧凑身份输出，工具需要时粘贴结构化 JSON 身份输出。",
                ),
            },
        ]
    )
    actions.extend(support_issue_route_actions(language=language))
    return actions


def _support_action_readiness_kinds(actions: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    ready: list[str] = []
    blocked: list[str] = []
    for action in actions:
        kind = str(action.get("kind") or "").strip()
        if not kind:
            continue
        blockers = [str(blocker).strip() for blocker in list(action.get("command_blockers") or []) if str(blocker).strip()]
        if action.get("command_ready") is False or blockers:
            blocked.append(kind)
        else:
            ready.append(kind)
    return ready, blocked


def _public_support_workdir_arg(workdir: Path | str | None) -> str:
    normalized = _public_support_workdir_value(workdir)
    return shlex.quote(normalized) if normalized else shlex.quote(SUPPORT_WORKDIR_PLACEHOLDER)


def _public_support_workdir_value(workdir: Path | str | None) -> str:
    normalized = str(workdir or "").strip()
    if not normalized:
        return ""
    with suppress(OSError, RuntimeError, ValueError):
        normalized = str(Path(normalized).expanduser().resolve(strict=False))
    return normalized


def _public_support_target_project_status(workdir: Path | str | None) -> str:
    if workdir is None or not str(workdir).strip():
        return "required"
    return str(workdir_path_state(workdir).get("status") or "unavailable")


def _public_support_command(command: str) -> str:
    return rewrite_loopora_command_entry(command, cli_entry=current_project_file_loopora_cli_entry())


def _public_support_web_target_args(*, web_host: str | None, web_port: int | str | None) -> str:
    requested_host = str(web_host or "").strip()
    requested_port = str(web_port or "").strip()
    if not requested_host and not requested_port:
        return ""
    host = requested_host or "127.0.0.1"
    port = requested_port or "8742"
    return f" --web-host {shlex.quote(host)} --web-port {shlex.quote(port)}"


def _public_support_web_support_url(*, web_host: str | None, web_port: int | str | None, workdir: Path | str | None) -> str:
    requested_host = str(web_host or "").strip()
    requested_port = str(web_port or "").strip()
    if not requested_host and not requested_port:
        return ""
    host = requested_host or "127.0.0.1"
    port_text = requested_port or "8742"
    with suppress(ValueError):
        url = f"{open_origin_for_bind_host(host, int(port_text)).rstrip('/')}/support"
        workdir_value = _public_support_workdir_value(workdir)
        return f"{url}?{urlencode({'workdir': workdir_value})}" if workdir_value else url
    return ""


def _public_support_target_project_command(language: str, *, web_target_args: str = "") -> str:
    language_arg = "" if language == "en" else f" --language {shlex.quote(language)}"
    return _public_support_command(f'loopora support{language_arg}{web_target_args} --workdir "$PWD"')


def _support_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english
