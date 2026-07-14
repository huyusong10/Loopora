from __future__ import annotations

import typer

from loopora.cli_fit_output_common import (
    fit_action_adapter_choices as _fit_action_adapter_choices,
    fit_action_alternative_commands as _fit_action_alternative_commands,
    fit_text as _fit_text,
    fit_web_route_preflight_notes as _fit_web_route_preflight_notes,
    localized_fit_action_note as _localized_fit_action_note,
    payload_dict_list as _payload_dict_list,
)
from loopora.first_use_route_terminal import (
    first_use_route_action_status_lines,
    first_use_route_preview_status_line,
)


def print_fit_ready_next_actions(payload: dict[str, object], *, language: str) -> None:
    actions = _payload_dict_list(payload, "next_actions")
    route_source = _payload_dict_list(payload, "route_actions_after_strong_fit") or actions
    if not actions and not route_source:
        return
    recovery_actions = _fit_recovery_actions_before_route(actions)
    route_actions = _fit_route_actions_for_print(route_source)
    action_by_kind = {str(action.get("kind") or "").strip(): action for action in route_actions}
    _print_fit_target_recovery(payload, recovery_actions=recovery_actions, language=language)
    if _fit_targetless_route_preview_hidden(payload):
        _print_fit_targetless_route_preview_hidden(language=language)
        return
    typer.echo(_fit_ready_heading(payload, recovery_actions=recovery_actions, language=language))
    _print_fit_route_action_status(payload, language=language)
    _print_fit_route_preview_status(payload, language=language)
    web_action = action_by_kind.get("open_web_creation_choices")
    agent_action = action_by_kind.get("return_to_agent")
    install_action = action_by_kind.get("install_agent_entry")
    doctor_action = action_by_kind.get("confirm_readiness")
    support_already_printed = any(str(action.get("kind") or "").strip() == "support" for action in recovery_actions)
    support_action = None if support_already_printed else action_by_kind.get("support")
    if web_action or agent_action:
        typer.echo(_fit_text(language, "Choose the route that matches where you are:", "选择符合当前上下文的路线:"))
    if web_action:
        _print_fit_choice_action(
            web_action,
            label=_fit_text(language, "Fit Guide/Web choices", "适用性判断/Web 选择"),
            language=language,
        )
    if agent_action:
        typer.echo(_fit_text(language, "- Same-Agent path:", "- 同一 Agent 路径:"))
        _print_fit_numbered_action(install_action, index=1, language=language)
        _print_fit_numbered_action(doctor_action, index=2, language=language)
        _print_fit_numbered_action(agent_action, index=3, language=language)
    run_action = action_by_kind.get("run_after_review")
    if run_action:
        typer.echo(_fit_text(language, "After the READY preview matches the task judgment:", "READY 预览符合任务判断后:"))
        if web_action:
            typer.echo(
                _fit_text(
                    language,
                    "- Fit Guide/Web choices: create or run from Web, then review evidence, verdict state, residual risk, and next action there.",
                    "- 适用性判断/Web 选择：从 Web 创建或运行，然后在那里审查证据、裁决状态、残余风险和下一步动作。",
                )
            )
        _print_fit_choice_action(
            run_action,
            label=_fit_text(language, "Same-Agent path", "同一 Agent 路径"),
            language=language,
        )
    if support_action:
        _print_fit_choice_action(
            support_action,
            label=_fit_text(language, "Usage/setup help", "使用/设置帮助"),
            language=language,
        )


def _print_fit_target_recovery(
    payload: dict[str, object],
    *,
    recovery_actions: list[dict[str, object]],
    language: str,
) -> None:
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), dict) else {}
    if not recovery_actions:
        return
    workdir = str(payload.get("workdir") or "").strip()
    if workdir:
        typer.echo(_fit_text(language, f"Target project: {workdir}", f"目标项目：{workdir}"))
    status = str(workdir_state.get("status") or "").strip()
    summary = str(workdir_state.get("summary") or "").strip()
    if status:
        typer.echo(_fit_text(language, f"Target project state: {status}", f"目标项目状态：{status}"))
    if summary:
        typer.echo(_fit_text(language, f"Note: {summary}", f"说明：{summary}"))
    typer.echo(_fit_text(language, "Next before route commands:", "运行路线命令前下一步:"))
    for index, action in enumerate(recovery_actions, start=1):
        _print_fit_numbered_action(action, index=index, language=language)


def _fit_targetless_route_preview_hidden(payload: dict[str, object]) -> bool:
    route_blockers = {str(item) for item in list(payload.get("route_preview_blockers") or [])}
    return (
        bool(payload.get("route_commands_are_placeholders"))
        and not str(payload.get("workdir") or "").strip()
        and bool(route_blockers & {"target_project_required", "target_project_unready"})
    )


def _print_fit_targetless_route_preview_hidden(*, language: str) -> None:
    typer.echo(
        _fit_text(
            language,
            "Target project: not supplied; rerun fit from the target project before copying route commands.",
            "目标项目：尚未提供；请先从目标项目重跑 fit，再复制路线命令。",
        )
    )
    typer.echo(
        _fit_text(
            language,
            "Route preview: hidden until you choose a usable target project; rerun fit from that project before copying Web/init/doctor commands.",
            "路线预览：选择可用目标项目之前先隐藏；请从该项目重跑 fit 后再复制 Web/init/doctor 命令。",
        )
    )


def _fit_ready_heading(
    payload: dict[str, object],
    *,
    recovery_actions: list[dict[str, object]],
    language: str,
) -> str:
    if bool(payload.get("route_commands_are_placeholders")):
        typer.echo(
            _fit_text(
                language,
                "Target project: not supplied; rerun fit from the target project before copying route commands.",
                "目标项目：尚未提供；请先从目标项目重跑 fit，再复制路线命令。",
            )
        )
        return _fit_text(language, "Route shape if fit is strong:", "适配度很强时的路线形状:")
    if recovery_actions:
        if not _fit_recovery_actions_include_target_recovery(recovery_actions):
            return _fit_text(language, "Route preview after completed fit review:", "补齐适配审查后的路线预览:")
        return _fit_text(language, "Route preview after the target project is usable:", "目标项目可用后的入口预览:")
    return _fit_text(language, "Next if fit is strong:", "如果适配度很强，下一步:")


def _fit_recovery_actions_include_target_recovery(actions: list[dict[str, object]]) -> bool:
    return any(str(action.get("kind") or "").strip() in {"choose_workdir", "create_workdir", "confirm_readiness"} for action in actions)


def _print_fit_route_preview_status(payload: dict[str, object], *, language: str) -> None:
    if bool(payload.get("route_preview_executable")):
        if bool(payload.get("fit_review_recommended_before_setup")):
            typer.echo(
                _fit_text(
                    language,
                    "- Route commands are concrete because the target project is ready; they do not prove a completed fit review.",
                    "- 路线命令已经具体化，是因为目标项目已就绪；这并不代表适配审查已经完成。",
                )
            )
        return
    line = first_use_route_preview_status_line(payload, language=language)
    if line:
        typer.echo(line)


def _print_fit_route_action_status(payload: dict[str, object], *, language: str) -> None:
    lines = first_use_route_action_status_lines(
        payload,
        route_actions=_payload_dict_list(payload, "route_actions_after_strong_fit"),
        language=language,
    )
    for line in lines:
        typer.echo(line)


def _fit_recovery_actions_before_route(actions: list[dict[str, object]]) -> list[dict[str, object]]:
    recovery: list[dict[str, object]] = []
    for action in actions:
        kind = str(action.get("kind") or "").strip()
        if kind == "open_web_creation_choices":
            break
        if kind in {"complete_review_inputs", "create_workdir", "choose_workdir", "support"} or (kind == "confirm_readiness" and recovery):
            recovery.append(action)
    return recovery


def _fit_route_actions_for_print(actions: list[dict[str, object]]) -> list[dict[str, object]]:
    for index, action in enumerate(actions):
        if str(action.get("kind") or "").strip() == "open_web_creation_choices":
            return actions[index:]
    return actions


def _print_fit_numbered_action(action: dict[str, object] | None, *, index: int, language: str) -> None:
    if not action:
        return
    command = str(action.get("command") or "").strip()
    command_template = str(action.get("command_template") or "").strip()
    note = _localized_fit_action_note(action, language=language)
    suffix = f" ({note})" if note else ""
    alternatives = _fit_action_adapter_choices(action)
    if not command and command_template:
        label = _fit_numbered_action_label(action, language=language)
        typer.echo(f"  {index}. {label}: {command_template}{suffix}")
        return
    if not command and alternatives:
        label = _fit_text(language, "choose one matching same-Agent project entry", "选择一个匹配的同一 Agent 项目入口")
        typer.echo(f"  {index}. {label}{suffix}")
        for choice in alternatives:
            adapter = str(choice.get("adapter") or "").strip()
            choice_command = str(choice.get("command") or "").strip()
            if adapter and choice_command:
                typer.echo(f"     - {adapter}: {choice_command}")
        return
    if not command:
        if note:
            typer.echo(f"  {index}. {note}")
        return
    typer.echo(f"  {index}. {command}{suffix}")
    alternatives = _fit_action_alternative_commands(action)
    if alternatives:
        label = _fit_text(language, "alternatives", "可选入口")
        typer.echo(f"     {label}: {'; '.join(alternatives)}")


def _fit_numbered_action_label(action: dict[str, object], *, language: str) -> str:
    kind = str(action.get("kind") or "").strip()
    labels = {
        "complete_review_inputs": _fit_text(language, "Complete review inputs", "补齐判断输入"),
    }
    return labels.get(kind, kind.replace("_", " "))


def _print_fit_choice_action(action: dict[str, object], *, label: str, language: str) -> None:
    command = str(action.get("command") or "").strip()
    if not command:
        return
    note = _localized_fit_action_note(action, language=language)
    suffix = f" ({note})" if note else ""
    prefix = f"- {label}: " if label else "- "
    if _fit_web_command_is_unavailable(action):
        typer.echo(f"{prefix}{_fit_web_route_blocked_until(action, language=language)}.")
        command_label = _fit_web_blocked_command_label(action, language=language)
        typer.echo(
            _fit_text(
                language,
                f"  - {command_label}: {command}",
                f"  - {command_label}: {command}",
            )
        )
        for route_note in _fit_web_blocked_route_notes(action, language=language):
            typer.echo(f"  - {route_note}")
        for recovery_action in _fit_web_recovery_actions(action):
            recovery_note = _localized_fit_action_note(recovery_action, language=language)
            recovery_suffix = f" ({recovery_note})" if recovery_note else ""
            recovery_label = _fit_recovery_action_label(recovery_action, language=language)
            recovery_command = str(recovery_action.get("command") or "").strip()
            typer.echo(f"  - {recovery_label}: {recovery_command}{recovery_suffix}")
        return
    typer.echo(f"{prefix}{command}{suffix}")
    for recovery_action in _fit_web_recovery_actions(action):
        recovery_note = _localized_fit_action_note(recovery_action, language=language)
        recovery_suffix = f" ({recovery_note})" if recovery_note else ""
        recovery_label = _fit_recovery_action_label(recovery_action, language=language)
        recovery_command = str(recovery_action.get("command") or "").strip()
        typer.echo(f"  - {recovery_label}: {recovery_command}{recovery_suffix}")


def _fit_web_blocked_route_notes(action: dict[str, object], *, language: str) -> list[str]:
    notes = _fit_web_route_preflight_notes(action, language=language)
    action_note = str(action.get("note") or "").strip()
    if language == "zh" and str(action.get("kind") or "").strip() == "open_web_creation_choices":
        action_note = (
            "不在 Agent 会话中时，先选择适用性判断/Web 选择；READY 审查后 Web/导入/手动工作继续在 Web 中进行，"
            "只有当前已经在 Agent 宿主中时才选择同一 Agent 设置"
        )
    if action_note:
        notes.append(action_note)
    return notes


def _fit_web_recovery_actions(action: dict[str, object]) -> list[dict[str, object]]:
    if str(action.get("kind") or "") != "open_web_creation_choices":
        return []
    return [item for item in list(action.get("recovery_actions") or []) if isinstance(item, dict) and str(item.get("command") or "").strip()]


def _fit_web_command_is_unavailable(action: dict[str, object]) -> bool:
    if str(action.get("kind") or "") != "open_web_creation_choices" or action.get("command_ready") is not False:
        return False
    blockers = {str(item) for item in list(action.get("command_blockers") or [])}
    return bool(blockers & {"app_state_not_ready", "web_port_unavailable"})


def _fit_web_blocked_command_label(action: dict[str, object], *, language: str) -> str:
    blockers = {str(item) for item in list(action.get("command_blockers") or [])}
    if "web_port_unavailable" in blockers:
        return _fit_text(language, "Requested Web command, currently unavailable", "请求的 Web 命令当前不可用")
    return _fit_text(language, "Web command after blockers are resolved", "前置条件处理后的 Web 命令")


def _fit_web_route_blocked_until(action: dict[str, object], *, language: str) -> str:
    blockers = {str(item) for item in list(action.get("command_blockers") or [])}
    if "app_state_not_ready" in blockers and "web_port_unavailable" in blockers:
        return _fit_text(
            language,
            "blocked until App/Web readiness and a usable local Web port are resolved",
            "处理好 App/Web 就绪状态并选择可用本地 Web 端口前保持阻止",
        )
    if "app_state_not_ready" in blockers:
        return _fit_text(language, "blocked until App/Web readiness is resolved", "处理好 App/Web 就绪状态前保持阻止")
    if "web_port_unavailable" in blockers:
        return _fit_text(language, "blocked until a usable local Web port is chosen", "选择可用本地 Web 端口前保持阻止")
    return _fit_text(language, "blocked until route prerequisites are resolved", "处理好路线前置条件前保持阻止")


def _fit_recovery_action_label(action: dict[str, object], *, language: str) -> str:
    kind = str(action.get("kind") or "").strip()
    labels = {
        "create_recovery_archive": _fit_text(language, "Create private recovery archive", "创建私有恢复归档"),
        "preview_app_database_reset": _fit_text(language, "Preview App database reset", "预览 App 数据库 reset"),
        "use_temporary_app_home": _fit_text(language, "Temporary Web preview", "临时 Web 预览"),
        "use_matching_loopora_version_or_reset": _fit_text(
            language,
            "Use matching Loopora version or preview reset",
            "使用匹配 Loopora 版本或预览 reset",
        ),
        "inspect_or_reset_app_state": _fit_text(language, "Inspect or reset App state", "检查或 reset App 状态"),
        "inspect_app_state": _fit_text(language, "Inspect App state", "检查 App 状态"),
    }
    return labels.get(kind, kind.replace("_", " "))
