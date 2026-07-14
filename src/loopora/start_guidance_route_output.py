from __future__ import annotations

from collections.abc import Mapping

from loopora.first_use_web_recovery import first_use_web_readiness_note
from loopora.fit_review_guidance import FIT_FIRST_TASK_MESSAGE_STATUS
from loopora.first_use_route_terminal import (
    first_use_route_action_status_lines,
    first_use_route_preview_status_line,
)
from loopora.start_guidance_action_output import _action_label, _action_line
from loopora.start_guidance_actions import (
    _action_by_kind,
    _action_command,
    _actions,
    _route_actions,
    _start_workdir_needs_choice,
    _text,
)
from loopora.start_guidance_constants import START_WEB_HOST, START_WEB_PORT


def blocked_setup_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    lines = [_text(language, "Next before setup:", "设置前下一步:")]
    lines.extend(_action_line(action, language=language) for action in _actions(payload, "next_actions"))
    if _review_inputs_block_setup(payload):
        lines.append(_hidden_route_preview_line(payload, language=language))
        return lines
    if _cold_start_hides_route_preview(payload):
        lines.append(_targetless_cold_start_route_preview_line(payload, language=language))
        return lines
    heading = _blocked_route_preview_heading(payload, language=language)
    lines.extend(route_lines(payload, language=language, heading=heading))
    return lines


def route_lines(payload: Mapping[str, object], *, language: str, heading: str) -> list[str]:
    route_actions = _route_actions(payload)
    lines = [heading]
    lines.extend(first_use_route_action_status_lines(payload, route_actions=route_actions, language=language))
    _append_route_preview_status(lines, payload, language=language)
    web_action = _action_by_kind(route_actions, "open_web_creation_choices")
    web_command = str(web_action.get("command") or "").strip() if web_action else ""
    if web_command:
        lines.extend(_web_route_lines(web_action, web_command=web_command, language=language))
    install_action = _action_by_kind(route_actions, "install_agent_entry")
    if install_action:
        lines.extend(
            _same_agent_route_lines(
                install_action,
                route_actions=route_actions,
                language=language,
            )
        )
    support_already_printed = (not bool(payload.get("setup_allowed"))) and _action_by_kind(_actions(payload, "next_actions"), "support")
    support_command = "" if support_already_printed else _action_command(route_actions, "support")
    if support_command:
        lines.append(_text(language, f"- Usage/setup help: {support_command}", f"- 使用/设置帮助：{support_command}"))
    return lines


def _same_agent_route_lines(
    install_action: Mapping[str, object],
    *,
    route_actions: list[dict[str, object]],
    language: str,
) -> list[str]:
    lines: list[str] = []
    confirm_action = _action_by_kind(route_actions, "confirm_readiness")
    doctor_command = str(confirm_action.get("command") or "").strip() if confirm_action else ""
    plan_command = _action_command(route_actions, "return_to_agent")
    run_command = _action_command(route_actions, "run_after_review")
    install_command = str(install_action.get("command") or "").strip()
    selection_required = install_action.get("selection_required") is True
    if install_command and not selection_required:
        lines.append(
            _text(
                language,
                f"- Same-Agent path (detected current host): {install_command}",
                f"- 同一 Agent 路径（已检测到当前宿主）：{install_command}",
            )
        )
    elif selection_required:
        lines.append(
            _text(
                language,
                "- Same-Agent path: current host detection needs an explicit adapter choice; continue only when already inside that host.",
                "- 同一 Agent 路径：当前宿主检测需要明确选择 adapter；只有已经在该宿主中时才继续。",
            )
        )
        for choice in list(install_action.get("adapter_choices") or []):
            if isinstance(choice, Mapping) and choice.get("fallback_applicable") is True:
                adapter = str(choice.get("adapter") or "").strip()
                command = str(choice.get("command") or "").strip()
                if adapter and command:
                    lines.append(f"  - {adapter}: {command}")
    if not lines:
        return []
    if doctor_command:
        lines.append(_confirm_readiness_route_line(confirm_action, command=doctor_command, language=language))
    if plan_command:
        lines.append(
            _text(
                language,
                f"  - Return to that same Agent for {plan_command} with the reviewed task judgment.",
                f"  - 回到同一 Agent，带着已审查任务判断运行 {plan_command}。",
            )
        )
    if run_command:
        lines.append(_text(language, f"  - After READY preview review in that Agent: {run_command}", f"  - 在该 Agent 中审查 READY 预览后：{run_command}"))
    return lines


def _review_inputs_block_setup(payload: Mapping[str, object]) -> bool:
    return "review_inputs_required" in {str(item) for item in list(payload.get("setup_command_blockers") or [])}


def _cold_start_hides_route_preview(payload: Mapping[str, object]) -> bool:
    task_review_status = str(payload.get("task_review_status") or "").strip()
    return (
        task_review_status in {"", FIT_FIRST_TASK_MESSAGE_STATUS["example"]}
        and not str(payload.get("workdir") or "").strip()
        and _workdir_needs_choice(payload)
    )


def _targetless_cold_start_route_preview_line(payload: Mapping[str, object], *, language: str) -> str:
    route_blockers = {str(item) for item in list(payload.get("route_preview_blockers") or [])}
    if route_blockers & {"target_project_required", "target_project_unready"}:
        return _text(
            language,
            "Route preview: hidden until you choose a usable target project; rerun start from that project before copying Web/init/doctor commands.",
            "路线预览：选择可用目标项目之前先隐藏；请从该项目重跑 start 后再复制 Web/init/doctor 命令。",
        )
    return _text(
        language,
        "Route preview: hidden until you choose a target project.",
        "路线预览：选择目标项目之前先隐藏。",
    )


def _hidden_route_preview_line(payload: Mapping[str, object], *, language: str) -> str:
    route_blockers = {str(item) for item in list(payload.get("route_preview_blockers") or [])}
    if _workdir_needs_choice(payload) or route_blockers & {"target_project_required", "target_project_unready"}:
        return _text(
            language,
            "Route preview: hidden until review inputs are complete and a usable target project is chosen.",
            "路线预览：补齐判断输入并选择可用目标项目前先隐藏。",
        )
    return _text(
        language,
        "Route preview: hidden until review inputs are complete; rerun the completion command above to get route commands.",
        "路线预览：补齐判断输入前先隐藏；重新运行上方补全命令后再获取路线命令。",
    )


def _blocked_route_preview_heading(payload: Mapping[str, object], *, language: str) -> str:
    fit_blocked = str(payload.get("task_review_status") or "") == FIT_FIRST_TASK_MESSAGE_STATUS["preview"]
    workdir_blocked = _workdir_blocked(payload)
    workdir_needs_choice = _workdir_needs_choice(payload)
    if fit_blocked and workdir_needs_choice:
        return _text(
            language,
            "Route shape after choosing a usable target project and completing a strong-fit review:",
            "选择可用目标项目且补全强适配审查后的路线形状:",
        )
    if workdir_needs_choice:
        return _text(language, "Route shape after choosing a usable target project:", "选择可用目标项目后的路线形状:")
    if fit_blocked and workdir_blocked:
        return _text(
            language,
            "Route preview after the target project is usable and the completed review is still a strong fit:",
            "目标项目可用且补全审查仍为强适配后的入口预览:",
        )
    if workdir_blocked:
        return _text(language, "Route preview after the target project is usable:", "目标项目可用后的入口预览:")
    return _text(
        language,
        "Route preview after the completed review is still a strong fit:",
        "补全审查且仍为强适配后的入口预览:",
    )


def _workdir_blocked(payload: Mapping[str, object]) -> bool:
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), Mapping) else {}
    return bool(workdir_state) and str(workdir_state.get("status") or "") != "ready"


def _workdir_needs_choice(payload: Mapping[str, object]) -> bool:
    if bool(payload.get("target_project_required")):
        return True
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), Mapping) else {}
    return _start_workdir_needs_choice(workdir_state)


def _confirm_readiness_route_line(action: Mapping[str, object], *, command: str, language: str) -> str:
    if str(action.get("after_action") or "") == "install_agent_entry":
        return _text(
            language,
            f"  - After installing the matching same-Agent project entry, confirm readiness before /loopora-plan: {command}",
            f"  - 安装匹配的同一 Agent 项目入口后，在 /loopora-plan 前确认就绪：{command}",
        )
    return _text(language, f"  - Confirm readiness before /loopora-plan: {command}", f"  - /loopora-plan 前确认就绪：{command}")


def _web_route_lines(web_action: Mapping[str, object], *, web_command: str, language: str) -> list[str]:
    command_ready = bool(web_action.get("command_ready", True))
    if command_ready:
        lines = [
            _text(
                language,
                f"- Fit Guide/Web choices (outside an Agent session, import, or manual expert path): {web_command}",
                f"- 适用性判断/Web 选择（不在 Agent 会话中、导入或手动专家路径）：{web_command}",
            )
        ]
    else:
        blocked_command_label = _web_route_blocked_command_label(web_action, language=language)
        lines = [
            _text(
                language,
                f"- Fit Guide/Web choices (outside an Agent session, import, or manual expert path): blocked until {_web_route_blocked_until(web_action, language=language)}.",
                f"- 适用性判断/Web 选择（不在 Agent 会话中、导入或手动专家路径）：{_web_route_blocked_until(web_action, language=language)}前保持阻止。",
            ),
            f"  - {blocked_command_label}: {web_command}",
        ]
    preflight_note = _web_route_preflight_note(web_action, language=language)
    if preflight_note:
        lines.append(f"  - {preflight_note}")
    readiness_note = _web_route_readiness_note(web_action, language=language)
    if readiness_note:
        lines.append(f"  - {readiness_note}")
    for recovery_action in _web_route_recovery_actions(web_action):
        lines.append(_web_route_recovery_line(recovery_action, language=language))
    lines.append(
        _text(
            language,
            "  - Choose Web conversation, Plan File import, or manual expert creation; continue in Web after READY review.",
            "  - 选择 Web 对话、Plan File 导入或手动专家创建；READY 审查后继续在 Web 中进行。",
        )
    )
    lines.append(
        _text(
            language,
            "  - These Web paths do not require a same-Agent project entry or doctor check; use same-Agent setup only when you are already in an Agent session.",
            "  - 这些 Web 路径不需要同一 Agent 项目入口或 doctor 检查；只有已经在 Agent 会话中时才使用同一 Agent 设置。",
        )
    )
    return lines


def _append_route_preview_status(lines: list[str], payload: Mapping[str, object], *, language: str) -> None:
    preview_status = first_use_route_preview_status_line(payload, language=language)
    if preview_status:
        lines.append(preview_status)


def _web_route_preflight_note(action: Mapping[str, object], *, language: str) -> str:
    status = str(action.get("preflight_status") or "")
    requested_port = int(action.get("requested_port") or START_WEB_PORT)
    port = int(action.get("port") or START_WEB_PORT)
    if status == "matching_service_reusable":
        return _text(
            language,
            f"A matching Loopora Web service is already running on port {requested_port}; this route reuses it.",
            f"端口 {requested_port} 上已有匹配的 Loopora Web 服务；此路线会直接复用。",
        )
    if status == "default_port_in_use_with_suggestion" and port != requested_port:
        return _text(
            language,
            f"Default Web port {requested_port} is already in use; this route uses available port {port}.",
            f"默认 Web 端口 {requested_port} 已被占用；此路线改用可用端口 {port}。",
        )
    if status == "default_port_in_use_no_suggestion":
        return _text(
            language,
            f"Default Web port {requested_port} is already in use; run doctor or choose another --port before starting Web.",
            f"默认 Web 端口 {requested_port} 已被占用；启动 Web 前请运行 doctor 或选择其他 --port。",
        )
    if status == "bind_unavailable":
        return _text(
            language,
            f"Web bind preflight could not use {START_WEB_HOST}:{requested_port}; run doctor before starting Web.",
            f"Web 绑定预检无法使用 {START_WEB_HOST}:{requested_port}；启动 Web 前请先运行 doctor。",
        )
    return ""


def _web_route_blocked_until(action: Mapping[str, object], *, language: str) -> str:
    blockers = {str(item) for item in list(action.get("command_blockers") or [])}
    if "app_state_not_ready" in blockers and "web_port_unavailable" in blockers:
        return _text(
            language,
            "App/Web readiness and a usable local Web port are resolved",
            "处理好 App/Web 就绪状态并选择可用本地 Web 端口",
        )
    if "app_state_not_ready" in blockers:
        return _text(language, "App/Web readiness is resolved", "处理好 App/Web 就绪状态")
    if "web_port_unavailable" in blockers:
        return _text(language, "a usable local Web port is chosen", "选择可用本地 Web 端口")
    return _text(language, "route prerequisites are resolved", "处理好路线前置条件")


def _web_route_blocked_command_label(action: Mapping[str, object], *, language: str) -> str:
    blockers = {str(item) for item in list(action.get("command_blockers") or [])}
    if "web_port_unavailable" in blockers:
        return _text(language, "Requested Web command, currently unavailable", "请求的 Web 命令当前不可用")
    return _text(language, "Web command after blockers are resolved", "前置条件处理后的 Web 命令")


def _web_route_readiness_note(action: Mapping[str, object], *, language: str) -> str:
    return first_use_web_readiness_note(action, language=language)


def _web_route_recovery_actions(action: Mapping[str, object]) -> list[dict[str, object]]:
    return [item for item in list(action.get("recovery_actions") or []) if isinstance(item, dict) and str(item.get("command") or "").strip()]


def _web_route_recovery_line(action: Mapping[str, object], *, language: str) -> str:
    label = _action_label(str(action.get("kind") or "").strip(), language=language)
    command = str(action.get("command") or "").strip()
    note = str(action.get("note") or "").strip()
    suffix = f" ({note})" if note else ""
    return _text(language, f"  - Recovery: {label}: {command}{suffix}", f"  - 恢复动作：{label}：{command}{suffix}")
