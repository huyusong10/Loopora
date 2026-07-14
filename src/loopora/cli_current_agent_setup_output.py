from __future__ import annotations

from collections.abc import Mapping

import typer

from loopora.cli_agent_adapter_language import agent_entry_text, localized_agent_entry_command
from loopora.cli_shared import echo_json
from loopora.diagnose_doctor import doctor_json_payload

CURRENT_AGENT_SETUP_SCHEMA_VERSION = 1
SETUP_RECOVERY_LABELS = {
    "preview_app_database_reset": "Preview the App-state reset scope",
    "inspect_or_reset_app_state": "Inspect App state and preview reset if needed",
    "use_matching_loopora_version_or_reset": "Use a matching Loopora version or preview reset",
    "confirm_readiness": "Confirm readiness after recovery",
}
SETUP_RECOVERY_LABELS_ZH = {
    "preview_app_database_reset": "预览 App 状态重置范围",
    "inspect_or_reset_app_state": "检查 App 状态，并在需要时预览重置",
    "use_matching_loopora_version_or_reset": "使用匹配的 Loopora 版本，或预览重置",
    "confirm_readiness": "恢复后确认就绪",
}


def current_agent_setup_ready(report: Mapping[str, object]) -> bool:
    return report.get("first_task_handoff_executable") is True


def current_agent_setup_payload(
    *,
    detection: Mapping[str, object],
    install_result: Mapping[str, object],
    doctor_report: Mapping[str, object],
) -> dict[str, object]:
    ready = current_agent_setup_ready(doctor_report)
    return {
        **install_result,
        "schema_version": CURRENT_AGENT_SETUP_SCHEMA_VERSION,
        "kind": "same_agent_setup",
        "current_agent_host": dict(detection),
        "setup_status": "ready" if ready else "needs_attention",
        "setup_ready": ready,
        "readiness": doctor_json_payload(dict(doctor_report)),
    }


def print_current_agent_setup(
    *,
    detection: Mapping[str, object],
    install_result: Mapping[str, object],
    doctor_report: Mapping[str, object],
    language: str = "en",
    json_output: bool,
) -> None:
    if json_output:
        echo_json(
            current_agent_setup_payload(
                detection=detection,
                install_result=install_result,
                doctor_report=doctor_report,
            )
        )
        return
    ready = current_agent_setup_ready(doctor_report)
    label = str(install_result.get("label") or detection.get("adapter") or "Agent")
    managed_files = [item for item in list(install_result.get("managed_files") or []) if isinstance(item, Mapping)]
    current_files = sum(1 for item in managed_files if item.get("state") == "current")
    blockers = [
        _setup_blocker_text(str(item), language=language)
        for item in list(doctor_report.get("first_task_handoff_blockers") or [])
        if str(item).strip()
    ]
    typer.echo(
        agent_entry_text(
            language,
            f"Loopora same-Agent setup: {'ready' if ready else 'needs attention'}",
            f"Loopora 同一 Agent 设置：{'就绪' if ready else '需要处理'}",
        )
    )
    typer.echo(agent_entry_text(language, f"current host: {label}", f"当前宿主：{label}"))
    typer.echo(
        agent_entry_text(
            language,
            f"target project: {install_result.get('workdir')}",
            f"目标项目：{install_result.get('workdir')}",
        )
    )
    typer.echo(
        agent_entry_text(
            language,
            f"project entry: {install_result.get('status')} ({current_files}/{len(managed_files)} managed files current)",
            f"项目入口：{_setup_install_status_zh(install_result.get('status'))}（{current_files}/{len(managed_files)} 个托管文件为当前版本）",
        )
    )
    if ready:
        typer.echo(agent_entry_text(language, "plan handoff: ready for /loopora-plan", "计划交接：可运行 /loopora-plan"))
        _print_ready_next_steps(label, language=language)
    else:
        heading = agent_entry_text(language, "plan handoff: blocked", "计划交接：受阻")
        typer.echo(heading + (f" ({', '.join(blockers)})" if blockers else ""))
        _print_blocked_next_steps(doctor_report, language=language)
    raw_doctor_command = _next_command(install_result, "doctor")
    doctor_command = localized_agent_entry_command(raw_doctor_command, language=language)
    if doctor_command and (ready or not _recovery_command_is_visible(doctor_report, raw_doctor_command)):
        typer.echo(agent_entry_text(language, f"readiness details: {doctor_command}", f"就绪详情：{doctor_command}"))


def _print_ready_next_steps(label: str, *, language: str) -> None:
    typer.echo(agent_entry_text(language, "next:", "下一步："))
    typer.echo(
        agent_entry_text(
            language,
            f"- Refresh or restart {label} if /loopora-plan is not visible.",
            f"- 如果看不到 /loopora-plan，请刷新或重启 {label}。",
        )
    )
    typer.echo(
        agent_entry_text(
            language,
            f"- Return to {label} with the reviewed task judgment and run /loopora-plan.",
            f"- 带着已审查的任务判断回到 {label}，运行 /loopora-plan。",
        )
    )
    typer.echo(
        agent_entry_text(
            language,
            "- Review the READY Loop preview, then run /loopora-run in the same Agent session.",
            "- 审查 READY Loop 预览，再在同一 Agent 会话中运行 /loopora-run。",
        )
    )


def _print_blocked_next_steps(report: Mapping[str, object], *, language: str) -> None:
    typer.echo(agent_entry_text(language, "next:", "下一步："))
    labels = SETUP_RECOVERY_LABELS_ZH if language == "zh" else SETUP_RECOVERY_LABELS
    actions = [item for item in list(report.get("next_action_items") or []) if isinstance(item, Mapping)]
    relevant = [
        (
            labels.get(str(item.get("kind") or "")),
            localized_agent_entry_command(str(item.get("command") or "").strip(), language=language),
        )
        for item in actions
        if item.get("command_ready") is not False and str(item.get("kind") or "") in SETUP_RECOVERY_LABELS
    ]
    relevant = [(label, command) for label, command in relevant if label and command]
    if not relevant:
        typer.echo(
            agent_entry_text(
                language,
                "- Run the readiness details command and resolve its blocking actions before /loopora-plan.",
                "- 运行就绪详情命令，并在 /loopora-plan 前解决其中的阻塞动作。",
            )
        )
        return
    for label, command in relevant[:3]:
        typer.echo(f"- {label}: {command}")


def _next_command(result: Mapping[str, object], key: str) -> str:
    commands = result.get("next_commands") if isinstance(result.get("next_commands"), Mapping) else {}
    return str(commands.get(key) or "").strip()


def _recovery_command_is_visible(report: Mapping[str, object], command: str) -> bool:
    return any(
        isinstance(item, Mapping)
        and str(item.get("kind") or "") in SETUP_RECOVERY_LABELS
        and str(item.get("command") or "").strip() == command
        and item.get("command_ready") is not False
        for item in list(report.get("next_action_items") or [])
    )


def _setup_blocker_text(blocker: str, *, language: str) -> str:
    if language != "zh":
        return blocker
    return {
        "target_project_required": "需要可用目标项目",
        "target_project_unready": "目标项目未就绪",
        "same_agent_entry_required": "同一 Agent 项目入口未就绪",
        "app_state_not_ready": "本地 App 状态未就绪",
    }.get(blocker, blocker)


def _setup_install_status_zh(status: object) -> str:
    value = str(status or "unknown")
    return {
        "installed": "已安装",
        "current": "当前版本",
        "not_installed": "未安装",
    }.get(value, value)


__all__ = ["current_agent_setup_payload", "current_agent_setup_ready", "print_current_agent_setup"]
