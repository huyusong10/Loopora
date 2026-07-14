from __future__ import annotations

from collections.abc import Mapping
import errno
from pathlib import Path
import shlex

from loopora import web_bind_preflight
from loopora.agent_adapter_command_prefix import rewrite_loopora_command_entry
from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.cli_agent_adapter_language import localized_agent_entry_command
from loopora.cli_serve_language import localized_serve_command
from loopora.first_use_same_agent_setup import first_use_same_agent_setup_action
from loopora.first_use_route_readiness import (
    first_use_web_readiness_blockers,
    first_use_web_recovery_actions,
)
from loopora.local_web_service import matching_configured_web_service
from loopora.fit_guidance import (
    FIT_FIRST_TASK_MESSAGE_STATUS,
    FIT_REVIEW_SETUP_GATE,
    normalize_fit_guidance_language,
)
from loopora.start_guidance_constants import (
    START_DOCTOR_COMMAND,
    START_WEB_COMMAND,
    START_WEB_HOST,
    START_WEB_PORT,
    START_WORKDIR_PLACEHOLDER,
)


def _start_route_actions(
    *,
    workdir_arg: str,
    language: str,
    cli_entry: str,
    web_route: Mapping[str, object],
    current_agent_host: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    fit_command = _start_fit_command(workdir_arg=workdir_arg, language=language)
    web_host = str(web_route.get("host") or START_WEB_HOST)
    web_port = int(web_route.get("port") or START_WEB_PORT)
    web_action = {
        "kind": "open_web_creation_choices",
        "command": localized_serve_command(
            _rewrite(
                START_WEB_COMMAND.format(workdir=workdir_arg, host=web_host, port=web_port),
                cli_entry=cli_entry,
            ),
            language=language,
        ),
        "route_contexts": ["web_conversation", "plan_file_import", "manual_expert"],
        "requires_agent_entry": False,
        "requires_doctor": False,
        "opens_browser": True,
        "host": web_host,
        "port": web_port,
        "requested_host": web_route["requested_host"],
        "requested_port": web_route["requested_port"],
        "suggested_port": web_route["suggested_port"],
        "preflight_checked": web_route["preflight_checked"],
        "preflight_status": web_route["preflight_status"],
        "start_blocked_reason": web_route["start_blocked_reason"],
        "readiness_blockers": list(web_route.get("readiness_blockers") or []),
        "note": _text(
            language,
            "Choose Web conversation, Plan File import, or manual expert creation; continue in Web after READY review.",
            "选择 Web 对话、Plan File 导入或手动专家创建；READY 审查后继续在 Web 中进行。",
        ),
    }
    recovery_actions = first_use_web_recovery_actions(
        web_action,
        workdir_arg=workdir_arg,
        cli_entry=cli_entry,
        language=language,
    )
    if recovery_actions:
        web_action["recovery_actions"] = recovery_actions
    return [
        {
            "kind": "check_fit_first",
            "command": _rewrite(fit_command, cli_entry=cli_entry),
            "note": _text(language, "Use before setup when fit is uncertain.", "不确定适配性时，在设置前先运行。"),
        },
        web_action,
        first_use_same_agent_setup_action(
            workdir_arg=workdir_arg,
            language=language,
            cli_entry=cli_entry,
            current_agent_host=current_agent_host,
        ),
        {
            "kind": "confirm_readiness",
            "command": localized_agent_entry_command(
                _rewrite(
                    _start_doctor_command(workdir_arg=workdir_arg, web_route=web_route),
                    cli_entry=cli_entry,
                ),
                language=language,
            ),
            "after_action": "install_agent_entry",
            "note": _text(
                language,
                "After installing the matching same-Agent project entry, confirm readiness before /loopora-plan.",
                "安装匹配的同一 Agent 项目入口后，在 /loopora-plan 前确认就绪。",
            ),
        },
        {
            "kind": "return_to_agent",
            "command": "/loopora-plan",
            "note": _text(
                language,
                "Bring the Loopora fit reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context.",
                "带上 Loopora 适配理由、任务目标、伪完成风险、必需证据、判断取舍和可选直接路径上下文。",
            ),
        },
        {"kind": "run_after_review", "command": "/loopora-run"},
        {
            "kind": "support",
            "command": _rewrite(
                _start_support_command(workdir_arg=workdir_arg, web_route=web_route, language=language),
                cli_entry=cli_entry,
            ),
        },
    ]


def _start_web_route_context(
    workdir_state: Mapping[str, object],
    *,
    workdir_arg: str,
    enabled: bool,
) -> dict[str, object]:
    context: dict[str, object] = {
        "requested_host": START_WEB_HOST,
        "requested_port": START_WEB_PORT,
        "host": START_WEB_HOST,
        "port": START_WEB_PORT,
        "suggested_port": None,
        "preflight_checked": False,
        "preflight_status": "not_checked",
        "start_blocked_reason": "",
        "readiness_blockers": [],
    }
    if (
        not enabled
        or workdir_arg == shlex.quote(START_WORKDIR_PLACEHOLDER)
        or not workdir_state
        or str(workdir_state.get("status") or "") != "ready"
    ):
        return context
    context["preflight_checked"] = True
    context["readiness_blockers"] = first_use_web_readiness_blockers(workdir_state)
    try:
        web_bind_preflight.probe_web_bind(START_WEB_HOST, START_WEB_PORT)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            context.update({"preflight_status": "bind_unavailable", "start_blocked_reason": "bind_failed"})
            return context
        if matching_configured_web_service(START_WEB_HOST, START_WEB_PORT):
            context["preflight_status"] = "matching_service_reusable"
            return context
        suggested_port = web_bind_preflight.next_available_web_port(host=START_WEB_HOST, port=START_WEB_PORT)
        if suggested_port is None:
            context.update(
                {
                    "preflight_status": "default_port_in_use_no_suggestion",
                    "start_blocked_reason": "port_in_use",
                }
            )
            return context
        context.update(
            {
                "port": suggested_port,
                "suggested_port": suggested_port,
                "preflight_status": "default_port_in_use_with_suggestion",
                "start_blocked_reason": "port_in_use",
            }
        )
        return context
    context["preflight_status"] = "available"
    return context


def _start_doctor_command(*, workdir_arg: str, web_route: Mapping[str, object]) -> str:
    command = START_DOCTOR_COMMAND.format(workdir=workdir_arg)
    if str(web_route.get("preflight_status") or "") == "default_port_in_use_with_suggestion":
        command = f"{command} --web-host {START_WEB_HOST} --web-port {int(web_route.get('port') or START_WEB_PORT)}"
    return command


def _start_support_command(*, workdir_arg: str, web_route: Mapping[str, object], language: str) -> str:
    language_arg = "" if language == "en" else f" --language {shlex.quote(language)}"
    command = f"loopora support{language_arg} --workdir {workdir_arg}"
    if str(web_route.get("preflight_status") or "") == "default_port_in_use_with_suggestion":
        command = f"{command} --web-host {START_WEB_HOST} --web-port {int(web_route.get('port') or START_WEB_PORT)}"
    return command


def _start_route_actions_for_review(
    route_actions: list[dict[str, object]],
    *,
    task_review_supplied: bool,
    fit_setup_allowed: bool,
) -> list[dict[str, object]]:
    if not task_review_supplied or not fit_setup_allowed:
        return route_actions
    return [action for action in route_actions if str(action.get("kind") or "") != "check_fit_first"]


def _start_fit_command(*, workdir_arg: str, language: str) -> str:
    parts = ["loopora", "fit"]
    if language != "en":
        parts.extend(["--language", language])
    if workdir_arg != shlex.quote(START_WORKDIR_PLACEHOLDER):
        parts.extend(["--workdir", workdir_arg])
    return " ".join(parts)


def _start_setup_command_blockers(
    *,
    fit_setup_allowed: bool,
    fit_setup_blocker: str,
    task_review_supplied: bool,
    route_commands_are_placeholders: bool,
    workdir_state: Mapping[str, object],
) -> list[str]:
    blockers: list[str] = []
    if task_review_supplied and not fit_setup_allowed:
        if fit_setup_blocker in {
            FIT_REVIEW_SETUP_GATE["direct_blocker"],
            FIT_REVIEW_SETUP_GATE["direct_input_blocker"],
        }:
            blockers.append(fit_setup_blocker)
            return blockers
        blockers.append("review_inputs_required")
    if route_commands_are_placeholders:
        blockers.append("target_project_required")
    elif workdir_state and str(workdir_state.get("status") or "") != "ready":
        blockers.append("target_project_unready")
    return blockers


def _start_fit_review_allows_setup_routes(summary: Mapping[str, object]) -> bool:
    fit_setup_blocker = str(summary.get("setup_blocker") or "")
    return bool(summary.get("ready_for_loopora_plan_message")) and not _fit_review_blocks_setup_routes(fit_setup_blocker)


def _fit_review_blocks_setup_routes(fit_setup_blocker: str) -> bool:
    return fit_setup_blocker in {
        FIT_REVIEW_SETUP_GATE["direct_blocker"],
        FIT_REVIEW_SETUP_GATE["direct_input_blocker"],
    }


def _payload_prefers_direct(payload: Mapping[str, object]) -> bool:
    state = payload.get("primary_first_task_message_state")
    return isinstance(state, Mapping) and str(state.get("status") or "") == FIT_FIRST_TASK_MESSAGE_STATUS["direct"]


def _payload_needs_direct_decision_input(payload: Mapping[str, object]) -> bool:
    state = payload.get("primary_first_task_message_state")
    return isinstance(state, Mapping) and str(state.get("status") or "") == FIT_FIRST_TASK_MESSAGE_STATUS["direct_input"]


def _copy_route_action(action: Mapping[str, object]) -> dict[str, object]:
    copied = dict(action)
    choices = copied.get("adapter_choices")
    if isinstance(choices, list):
        copied["adapter_choices"] = [dict(choice) for choice in choices if isinstance(choice, dict)]
    recovery_actions = copied.get("recovery_actions")
    if isinstance(recovery_actions, list):
        copied["recovery_actions"] = [dict(item) for item in recovery_actions if isinstance(item, dict)]
    return copied


def _start_workdir_state(workdir: Path | str | None) -> dict[str, object]:
    return adapter_workdir_state(workdir) if workdir is not None else {}


def _start_projected_workdir_state(workdir: Path | str | None) -> dict[str, object]:
    return adapter_workdir_state(workdir)


def _start_workdir_text(workdir: Path | str | None, workdir_state: Mapping[str, object]) -> str:
    if workdir is None:
        return ""
    normalized = str(workdir_state.get("workdir") or "").strip()
    return normalized or str(workdir).strip()


def _start_route_workdir_text(workdir_text: str, workdir_state: Mapping[str, object]) -> str:
    if not workdir_text.strip():
        return START_WORKDIR_PLACEHOLDER
    return START_WORKDIR_PLACEHOLDER if _start_workdir_needs_choice(workdir_state) else workdir_text


def _start_workdir_needs_choice(workdir_state: Mapping[str, object]) -> bool:
    if not workdir_state or str(workdir_state.get("status") or "") == "ready":
        return False
    commands = workdir_state.get("commands") if isinstance(workdir_state.get("commands"), Mapping) else {}
    return not str(commands.get("create") or "").strip()


def _start_workdir_arg(workdir: Path | str | None) -> str:
    normalized = str(workdir or "").strip()
    return shlex.quote(normalized) if normalized else '"$PWD"'


def _rewrite(command: str, *, cli_entry: str) -> str:
    return rewrite_loopora_command_entry(command, cli_entry=cli_entry)


def _payload_language(payload: Mapping[str, object]) -> str:
    try:
        return normalize_fit_guidance_language(str(payload.get("language") or "en"))
    except ValueError:
        return "en"


def _route_actions(payload: Mapping[str, object]) -> list[dict[str, object]]:
    return _actions(payload, "route_actions_after_strong_fit")


def _actions(payload: Mapping[str, object], key: str) -> list[dict[str, object]]:
    actions = payload.get(key)
    return [action for action in list(actions or []) if isinstance(action, dict)]


def _action_by_kind(actions: list[dict[str, object]], kind: str) -> dict[str, object]:
    for action in actions:
        if str(action.get("kind") or "").strip() == kind:
            return action
    return {}


def _action_command(actions: list[dict[str, object]], kind: str) -> str:
    return str(_action_by_kind(actions, kind).get("command") or "").strip()


def _action_command_template(actions: list[dict[str, object]], kind: str) -> str:
    return str(_action_by_kind(actions, kind).get("command_template") or "").strip()


def _action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english
