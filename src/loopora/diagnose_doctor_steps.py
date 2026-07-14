from __future__ import annotations

from typing import Any

from loopora.cli_diagnose_doctor_language import doctor_localized_action_command
from loopora.first_use_web_guidance import open_web_creation_step


def doctor_action_step(action: dict[str, Any], *, language: str = "en") -> str:
    if language == "zh":
        return _doctor_action_step_zh(action)
    command_blockers = [
        str(blocker).strip() for blocker in list(action.get("command_blockers") or []) if str(blocker).strip()
    ]
    step = _agent_doctor_action_step(action, command_blockers=command_blockers)
    if step:
        return step
    return _environment_doctor_action_step(action, command_blockers=command_blockers)


def _agent_doctor_action_step(action: dict[str, Any], *, command_blockers: list[str]) -> str:
    kind = str(action.get("kind") or "").strip()
    label = str(action.get("label") or "Agent").strip() or "Agent"
    command = str(action.get("command") or "").strip()
    after_action = str(action.get("after_action") or "").strip()
    selection_required = action.get("selection_required") is True
    if kind == "check_fit_first":
        step = f"If you are not sure this task needs a Loop, run this before installing same-Agent project entries: {command}" if command else (
            "If you are not sure this task needs a Loop, run the fit guide before installing same-Agent project entries."
        )
    elif kind in {"return_to_agent", "return_to_ready_agent"}:
        step = _return_to_agent_doctor_action_step(label, selection_required=selection_required)
    elif kind == "install_agent_entry":
        step = (
            "Choose the same-Agent project entry that matches your current host, then install it."
            if command
            else "Choose the same-Agent project entry that matches your current host."
        )
    elif kind == "confirm_readiness":
        step = _confirm_readiness_doctor_action_step(command=command, after_action=after_action)
    elif kind == "refresh_agent_host":
        step = _refresh_agent_host_doctor_action_step(selection_required=selection_required)
    elif kind == "confirm_agent_visibility":
        step = f"If /loopora-plan or /loopora-run is not visible in {label}, refresh or restart {label}."
    else:
        step = _agent_slash_command_step(kind=kind, command_blockers=command_blockers) or {
            "review_ready_loop_preview": "Review whether the READY Loop preview matches the task judgment.",
        }.get(kind, "")
    return step


def _agent_slash_command_step(*, kind: str, command_blockers: list[str]) -> str:
    if kind == "run_loopora_plan":
        blocker_text = _doctor_command_blocker_text(command_blockers)
        return (
            f"After {blocker_text}, run /loopora-plan to prepare the Loop preview."
            if blocker_text
            else "Run /loopora-plan to prepare the Loop preview."
        )
    if kind != "run_loopora_run":
        return ""
    if "ready_review_required" in command_blockers:
        return "After the READY preview matches the task judgment, run /loopora-run in the same Agent session."
    blocker_text = _doctor_command_blocker_text(command_blockers)
    return (
        f"After {blocker_text}, run /loopora-run in the same Agent session."
        if blocker_text
        else "Run /loopora-run in the same Agent session."
    )


def _doctor_command_blocker_text(blockers: list[str]) -> str:
    labels: list[str] = []
    for blocker in blockers:
        label = _doctor_command_blocker_label(str(blocker or "").strip())
        if label and label not in labels:
            labels.append(label)
    if not labels:
        return ""
    return f"{_doctor_join_command_blocker_labels(labels)} {'is' if len(labels) == 1 else 'are'} ready"


def _doctor_join_command_blocker_labels(labels: list[str]) -> str:
    if len(labels) <= 1:
        return labels[0] if labels else ""
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _doctor_command_blocker_label(blocker: str) -> str:
    labels = {
        "target_project_required": "usable target project",
        "target_project_unready": "usable target project",
        "same_agent_entry_required": "same-Agent project entry",
        "app_state_not_ready": "local App state",
        "first_task_message_not_ready": "copyable /loopora-plan task message",
    }
    return labels.get(blocker, blocker.replace("_", " "))


def _refresh_agent_host_doctor_action_step(*, selection_required: bool) -> str:
    if selection_required:
        return "After installing the matching same-Agent project entry, refresh or restart that Agent so the entry is visible."
    return "Refresh or restart the Agent so the new same-Agent project entry is visible."


def _return_to_agent_doctor_action_step(label: str, *, selection_required: bool = False) -> str:
    if selection_required:
        return (
            "After installing the matching same-Agent project entry, return to that Agent with the Loopora fit "
            "reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context."
        )
    if label == "Agent":
        return (
            "Return to the same Agent you installed with the Loopora fit reason, task goal, fake-done risk, "
            "required evidence, judgment tradeoffs, and optional direct-path context."
        )
    return (
        f"Return to {label} with the Loopora fit reason, task goal, fake-done risk, required evidence, "
        "judgment tradeoffs, and optional direct-path context."
    )


def _confirm_readiness_doctor_action_step(*, command: str, after_action: str) -> str:
    install_prefix = "After installing the matching same-Agent project entry, confirm readiness before returning to Agent"
    messages = {
        "create_workdir": (
            f"After creating the project directory, re-run doctor to continue readiness checks: {command}",
            "After creating the project directory, re-run doctor to continue readiness checks.",
        ),
        "choose_workdir": (
            "After choosing a usable project directory, re-run doctor to continue readiness checks.",
            "After choosing a usable project directory, re-run doctor to continue readiness checks.",
        ),
        "preview_app_database_reset": (
            f"After applying an acceptable App reset, re-run doctor to confirm App/Web readiness: {command}",
            "After applying an acceptable App reset, re-run doctor to confirm App/Web readiness.",
        ),
        "use_matching_loopora_version_or_reset": (
            f"After using a matching/newer Loopora version or applying an acceptable App reset, re-run doctor to confirm App/Web readiness: {command}",
            "After using a matching/newer Loopora version or applying an acceptable App reset, re-run doctor to confirm App/Web readiness.",
        ),
        "inspect_or_reset_app_state": (
            f"After inspecting or resetting local App state, re-run doctor to confirm App/Web readiness: {command}",
            "After inspecting or resetting local App state, re-run doctor to confirm App/Web readiness.",
        ),
        "install_agent_entry": (f"{install_prefix}: {command}", f"{install_prefix}."),
    }
    with_command, without_command = messages.get(
        after_action,
        (f"Confirm readiness before returning to Agent: {command}", "Confirm readiness before returning to Agent."),
    )
    return with_command if command else without_command


def _environment_doctor_action_step(action: dict[str, Any], *, command_blockers: list[str]) -> str:
    kind = str(action.get("kind") or "").strip()
    command = str(action.get("command") or "").strip()
    origin = str(action.get("origin") or "").strip()
    note = str(action.get("note") or "").strip()
    operation = str(action.get("operation") or "").strip()
    app_state_blocked = "app_state_not_ready" in command_blockers
    if kind == "create_workdir":
        step = _targeted_sentence(
            "Create the target project directory before installing same-Agent project entries",
            command,
        )
    elif kind == "choose_workdir":
        step = "Choose a project directory path; the configured workdir is not usable or is not a directory."
    elif kind == "support":
        step = _targeted_sentence("Usage/setup help", command)
    elif kind == "start_web":
        step = (
            _targeted_sentence("Open the existing Loopora Web service", command or origin)
            if operation == "open_existing"
            else open_web_creation_step(target=command or origin)
        )
    else:
        step = _web_environment_doctor_action_step(kind, target=command or origin, app_state_blocked=app_state_blocked)
        step = step or _app_state_doctor_action_step(
            kind,
            command=command,
            note=note,
            after_action=str(action.get("after_action") or "").strip(),
        )
        if not step and kind == "use_temporary_app_home":
            step = _targeted_sentence(
                "To preview Web without changing blocked App state, start a temporary empty App home",
                command,
            )
    return step


def _web_environment_doctor_action_step(kind: str, *, target: str, app_state_blocked: bool) -> str:
    prefixes = {
        "configure_web_auth": (
            "After App state is ready, set a Web auth token before starting network Web",
            "Set a Web auth token before starting network Web",
        ),
        "resolve_web_port": (
            "After App state is ready, choose a free Web port or stop the service using the configured port",
            "Choose a free Web port or stop the service using the configured port",
        ),
        "resolve_web_bind": (
            "After App state is ready, choose a different Web bind host or port",
            "Choose a different Web bind host or port",
        ),
    }
    prefix_pair = prefixes.get(kind)
    if not prefix_pair:
        return ""
    return _targeted_sentence(prefix_pair[0] if app_state_blocked else prefix_pair[1], target)


def _app_state_doctor_action_step(kind: str, *, command: str, note: str, after_action: str) -> str:
    archive_first = after_action == "create_recovery_archive"
    if kind == "create_recovery_archive":
        detail = note or "Create and inspect a private recovery archive before resetting local App state"
        return _targeted_sentence(detail.removesuffix("."), command)
    if kind == "preview_app_database_reset":
        detail = note or "preview the App database reset scope"
    elif kind == "use_matching_loopora_version_or_reset":
        detail = note or "Use a matching or newer Loopora version if available; otherwise preview the App database reset scope"
    elif kind == "inspect_or_reset_app_state":
        detail = note or "inspect local App state first; if choosing reset, preview the App database reset scope"
    else:
        return ""
    if archive_first:
        detail = f"After the private recovery archive succeeds, {detail[0].lower()}{detail[1:]}"
        return _targeted_sentence(detail, command)
    if note and kind == "preview_app_database_reset":
        return _targeted_sentence(note.removesuffix("."), command)
    return _targeted_sentence(f"Before /loopora-plan or Web review, {detail}", command)


def _targeted_sentence(prefix: str, target: str) -> str:
    return f"{prefix}: {target}" if target else f"{prefix}."


def _doctor_action_step_zh(action: dict[str, Any]) -> str:
    step = _doctor_agent_action_step_zh(action)
    if step:
        return step
    command = doctor_localized_action_command(action, language="zh")
    blockers = [str(item).strip() for item in list(action.get("command_blockers") or []) if str(item).strip()]
    return _doctor_environment_action_step_zh(action, command=command, blockers=blockers)


def _doctor_agent_action_step_zh(action: dict[str, Any]) -> str:
    kind = str(action.get("kind") or "").strip()
    command = doctor_localized_action_command(action, language="zh")
    blockers = [str(item).strip() for item in list(action.get("command_blockers") or []) if str(item).strip()]
    label = str(action.get("label") or "Agent").strip() or "Agent"
    if kind == "check_fit_first":
        step = _targeted_sentence_zh("如果不确定这个任务是否需要 Loop，请在安装同一 Agent 项目入口前先运行 fit", command)
    elif kind == "install_agent_entry":
        step = "选择与你当前宿主匹配的同一 Agent 项目入口。"
    elif kind in {"return_to_agent", "return_to_ready_agent"}:
        step = f"带着 Loopora 适配理由、任务目标、伪完成风险、必需证据和判断取舍返回 {label}。"
    elif kind == "confirm_agent_visibility":
        step = f"如果 {label} 中看不到 /loopora-plan 或 /loopora-run，请刷新或重启 {label}。"
    elif kind == "refresh_agent_host":
        step = "刷新或重启 Agent，让新的同一 Agent 项目入口可见。"
    elif kind == "confirm_readiness":
        step = _doctor_confirm_readiness_step_zh(command, after_action=str(action.get("after_action") or "").strip())
    elif kind == "run_loopora_plan":
        blocker_text = _doctor_blocker_text_zh(blockers)
        step = f"等待{blocker_text}就绪后，运行 /loopora-plan 准备 Loop 预览。" if blocker_text else "运行 /loopora-plan 准备 Loop 预览。"
    elif kind == "review_ready_loop_preview":
        step = "审查 READY Loop 预览是否符合任务判断。"
    elif kind == "run_loopora_run":
        step = "READY 预览符合任务判断后，在同一 Agent 会话运行 /loopora-run。"
    else:
        step = ""
    return step


def _doctor_confirm_readiness_step_zh(command: str, *, after_action: str) -> str:
    prefixes = {
        "create_workdir": "创建项目目录后，重跑 Doctor 继续就绪检查",
        "choose_workdir": "选择可用项目目录后，重跑 Doctor 继续就绪检查",
        "preview_app_database_reset": "应用可接受的 App 重置后，重跑 Doctor 确认 App/Web 就绪状态",
        "use_matching_loopora_version_or_reset": "使用匹配/更新版本或应用可接受的 App 重置后，重跑 Doctor",
        "inspect_or_reset_app_state": "检查或重置本地 App 状态后，重跑 Doctor",
        "install_agent_entry": "安装匹配的同一 Agent 项目入口后，重跑 Doctor，再返回 Agent",
    }
    return _targeted_sentence_zh(prefixes.get(after_action, "重跑 Doctor 确认就绪状态"), command)


def _doctor_environment_action_step_zh(action: dict[str, Any], *, command: str, blockers: list[str]) -> str:
    kind = str(action.get("kind") or "").strip()
    origin = str(action.get("origin") or "").strip()
    target = command or origin
    app_blocked = "app_state_not_ready" in blockers
    if kind == "create_workdir":
        step = _targeted_sentence_zh("安装同一 Agent 项目入口前，先创建目标项目目录", command)
    elif kind == "choose_workdir":
        step = "选择可用项目目录；当前目标不可用或不是目录。"
    elif kind == "support":
        step = _targeted_sentence_zh("使用/设置帮助", command)
    elif kind == "start_web":
        prefix = "打开现有 Loopora Web 服务" if action.get("operation") == "open_existing" else "打开 Fit Guide/Web 创建选择"
        step = _targeted_sentence_zh(prefix, target)
    elif kind == "create_recovery_archive":
        step = _targeted_sentence_zh("删除有价值的本地历史前，先创建并审查私有精确路径恢复归档", command)
    elif kind in {"preview_app_database_reset", "use_matching_loopora_version_or_reset", "inspect_or_reset_app_state"}:
        step = _doctor_app_recovery_step_zh(kind, command=command, after_action=str(action.get("after_action") or ""))
    elif kind == "use_temporary_app_home":
        step = _targeted_sentence_zh("不改动被阻止的 App 状态，使用临时空 App Home 预览 Web", command)
    else:
        prefixes = {
            "configure_web_auth": "App 状态就绪后，设置 Web 认证 token 再启动网络 Web" if app_blocked else "设置 Web 认证 token 再启动网络 Web",
            "resolve_web_port": "App 状态就绪后，选择空闲 Web 端口或停止占用服务" if app_blocked else "选择空闲 Web 端口或停止占用服务",
            "resolve_web_bind": "App 状态就绪后，选择其他 Web 绑定 host 或端口" if app_blocked else "选择其他 Web 绑定 host 或端口",
        }
        step = _targeted_sentence_zh(prefixes[kind], target) if kind in prefixes else ""
    return step


def _doctor_app_recovery_step_zh(kind: str, *, command: str, after_action: str) -> str:
    details = {
        "preview_app_database_reset": "预览 App 数据库重置范围",
        "use_matching_loopora_version_or_reset": "优先使用匹配或更新的 Loopora；否则预览 App 数据库重置范围",
        "inspect_or_reset_app_state": "先检查本地 App 状态；如果选择重置，再预览重置范围",
    }
    detail = details[kind]
    if after_action == "create_recovery_archive":
        detail = f"私有恢复归档成功后，{detail}"
    return _targeted_sentence_zh(detail, command)


def _doctor_blocker_text_zh(blockers: list[str]) -> str:
    labels = {
        "target_project_required": "可用目标项目",
        "target_project_unready": "可用目标项目",
        "same_agent_entry_required": "同一 Agent 项目入口",
        "app_state_not_ready": "本地 App 状态",
        "first_task_message_not_ready": "可复制的 /loopora-plan 任务消息",
        "ready_review_required": "READY 预览审查",
    }
    return "、".join(dict.fromkeys(labels.get(item, item.replace("_", " ")) for item in blockers))


def _targeted_sentence_zh(prefix: str, target: str) -> str:
    return f"{prefix}：{target}" if target else f"{prefix}。"


def next_steps_from_actions(actions: list[dict[str, Any]], *, language: str = "en") -> list[str]:
    return [step for step in (doctor_action_step(action, language=language) for action in actions) if step]
