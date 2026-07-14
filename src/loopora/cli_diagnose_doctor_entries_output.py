from __future__ import annotations

import typer

from loopora.cli_agent_adapter_language import localized_agent_entry_command
from loopora.cli_diagnose_doctor_language import doctor_text


def print_doctor_entries(report: dict, *, language: str = "en") -> None:
    entries = [entry for entry in list(report.get("agent_entries") or []) if isinstance(entry, dict)]
    if not entries:
        return
    setup_states = {"not_installed"}
    ready_entries = [entry for entry in entries if entry.get("ready") is True]
    blocked_entries = [entry for entry in entries if entry.get("ready") is not True and str(entry.get("install_state") or "") == "blocked_by_workdir"]
    attention_entries = [
        entry for entry in entries if entry.get("ready") is not True and str(entry.get("install_state") or "") not in setup_states | {"blocked_by_workdir"}
    ]
    setup_options = [entry for entry in entries if entry.get("ready") is not True and str(entry.get("install_state") or "") in setup_states]
    typer.echo(doctor_text(language, "same-Agent project entries:", "同一 Agent 项目入口："))
    for entry in ready_entries:
        _print_doctor_entry_line(entry, state_label=doctor_text(language, "ready", "已就绪"), command_key="install_check", language=language)
    for entry in attention_entries:
        _print_doctor_entry_line(entry, state_label=doctor_text(language, "needs attention", "需要处理"), command_key="install_check", language=language)
    if not ready_entries and not attention_entries:
        if blocked_entries:
            blocked_entries = entries
        else:
            setup_options = setup_options or entries
    if setup_options:
        typer.echo(doctor_text(language, f"- setup options: {_entry_labels(setup_options)}", f"- 可设置选项：{_entry_labels(setup_options)}"))
    if blocked_entries:
        typer.echo(doctor_text(language, f"- blocked options: {_entry_labels(blocked_entries)}", f"- 被阻止选项：{_entry_labels(blocked_entries)}"))


def _print_doctor_entry_line(entry: dict, *, state_label: str, command_key: str, language: str) -> None:
    label = str(entry.get("label") or entry.get("adapter") or "Agent")
    adapter = str(entry.get("adapter") or "")
    title = f"{label} ({adapter})" if adapter else label
    detail = _doctor_entry_detail(entry, language=language)
    typer.echo(f"- {state_label}: {title}; {detail}" if detail else f"- {state_label}: {title}")
    summary = str(entry.get("summary") or "").strip()
    if summary:
        localized_summary = _doctor_entry_summary(entry, summary=summary, language=language)
        typer.echo(doctor_text(language, f"  note: {localized_summary}", f"  说明：{localized_summary}"))
    commands = entry.get("commands") if isinstance(entry.get("commands"), dict) else {}
    command = ""
    if command_key:
        command = str(commands.get(command_key) or commands.get("agent_check") or commands.get("install") or "").strip()
    if command:
        command = localized_agent_entry_command(command, language=language)
        typer.echo(doctor_text(language, f"  command: {command}", f"  命令：{command}"))


def _doctor_entry_detail(entry: dict, *, language: str) -> str:
    parts = [_doctor_entry_state_text(entry, language=language), _doctor_entry_next_action_text(entry, language=language)]
    return doctor_text(language, "; ".join(part for part in parts if part), "；".join(part for part in parts if part))


def _doctor_entry_state_text(entry: dict, *, language: str) -> str:
    if entry.get("ready") is True:
        return doctor_text(language, "adapter check passes", "adapter 检查通过")
    install_state = str(entry.get("install_state") or "unknown")
    if install_state == "not_installed":
        return doctor_text(language, "not installed yet", "尚未安装")
    if install_state == "blocked_by_workdir":
        return doctor_text(language, "waiting for a usable project directory", "等待可用项目目录")
    if install_state == "installed":
        return doctor_text(language, "installed entry needs attention", "已安装入口需要处理")
    if install_state == "unknown":
        return doctor_text(language, "state needs attention", "状态需要处理")
    return doctor_text(language, f"{install_state.replace('_', ' ')} needs attention", f"{install_state} 需要处理")


def _doctor_entry_next_action_text(entry: dict, *, language: str) -> str:
    next_action = str(entry.get("next_action") or "").strip()
    if not next_action:
        return ""
    labels = {
        "return_to_agent": doctor_text(language, "return to Agent", "返回 Agent"),
        "install_agent_entry": doctor_text(language, "install same-Agent project entry", "安装同一 Agent 项目入口"),
        "inspect_or_repair_agent_entry": doctor_text(language, "inspect or repair same-Agent project entry", "检查或修复同一 Agent 项目入口"),
        "create_workdir": doctor_text(language, "create project directory", "创建项目目录"),
        "choose_workdir": doctor_text(language, "choose project directory", "选择项目目录"),
    }
    label = labels.get(next_action, next_action.replace("_", " "))
    return doctor_text(language, f"next: {label}", f"下一步：{label}")


def _entry_labels(entries: list[dict]) -> str:
    labels = [str(entry.get("label") or entry.get("adapter") or "Agent").strip() for entry in entries]
    return ", ".join(label for label in labels if label)


def _doctor_entry_summary(entry: dict, *, summary: str, language: str) -> str:
    if language != "zh":
        return summary
    install_state = str(entry.get("install_state") or "unknown")
    if entry.get("ready") is True:
        return "托管项目入口检查通过。"
    if install_state == "not_installed":
        return "尚未安装；首次安装前缺少托管文件属于预期状态。"
    if install_state == "blocked_by_workdir":
        return "需要先选择可用目标项目目录。"
    return summary
