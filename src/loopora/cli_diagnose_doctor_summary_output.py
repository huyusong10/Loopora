from __future__ import annotations

import typer

from loopora.cli_diagnose_doctor_next_steps_output import doctor_action_items
from loopora.cli_diagnose_doctor_language import doctor_text
from loopora.diagnose_doctor_identity import package_source_label
from loopora.diagnose_doctor_projection import doctor_action_step


def print_doctor_readiness_summary(report: dict, *, language: str = "en") -> None:
    summary = _doctor_readiness_summary(report, language=language)
    if summary:
        typer.echo(doctor_text(language, f"readiness summary: {summary}", f"就绪摘要：{summary}"))
    primary_action = _doctor_primary_next_action(report, language=language)
    if primary_action:
        typer.echo(doctor_text(language, f"primary next action: {primary_action}", f"首要下一步：{primary_action}"))


def print_doctor_package(report: dict, *, language: str = "en") -> None:
    package = report.get("package") if isinstance(report.get("package"), dict) else {}
    if package:
        source = package_source_label(package)
        if language == "zh":
            source_note = f"；{source.replace('source ', '源码 ', 1)}" if source else ""
            typer.echo(f"包：loopora {package.get('version')}（Python {package.get('python')}{source_note}）")
        else:
            source_note = f"; {source}" if source else ""
            typer.echo(f"package: loopora {package.get('version')} (Python {package.get('python')}{source_note})")


def print_doctor_workdir_state(report: dict, *, language: str = "en") -> None:
    workdir_state = report.get("workdir_state") if isinstance(report.get("workdir_state"), dict) else {}
    if not workdir_state or workdir_state.get("needs_attention") is not True:
        return
    status = str(workdir_state.get("status") or "unknown")
    status_text = _doctor_workdir_status_zh(status) if language == "zh" else status
    typer.echo(doctor_text(language, f"project directory state: {status_text}", f"项目目录状态：{status_text}（{status}）"))
    summary = str(workdir_state.get("summary") or "").strip()
    if summary:
        localized_summary = _doctor_workdir_summary_zh(status) if language == "zh" else summary
        typer.echo(doctor_text(language, f"  note: {localized_summary}", f"  说明：{localized_summary}"))
    commands = workdir_state.get("commands") if isinstance(workdir_state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "").strip()
    if create_command:
        typer.echo(doctor_text(language, f"  create directory: {create_command}", f"  创建目录：{create_command}"))


def doctor_workdir_usable(report: dict) -> bool:
    workdir_state = report.get("workdir_state") if isinstance(report.get("workdir_state"), dict) else {}
    if not workdir_state:
        return True
    return workdir_state.get("usable_for_agent_entries") is True


def _doctor_readiness_summary(report: dict, *, language: str = "en") -> str:
    blockers = _doctor_readiness_blockers(report, language=language)
    if report.get("strict_ready") is True:
        web = report.get("web") if isinstance(report.get("web"), dict) else {}
        if web.get("already_running") is True:
            return doctor_text(language, "same-Agent project entry and App state are ready; Web is running.", "同一 Agent 项目入口和 App 状态已就绪；Web 正在运行。")
        return doctor_text(language, "same-Agent project entry, App state, and Web start are ready.", "同一 Agent 项目入口、App 状态和 Web 启动都已就绪。")
    if report.get("agent_entry_ready", report.get("ready")) is True:
        if blockers:
            joined = _doctor_join_labels(blockers, language=language)
            return doctor_text(language, f"same-Agent project entry is ready; strict readiness is blocked by {joined}.", f"同一 Agent 项目入口已就绪；严格就绪仍被{joined}阻止。")
        return doctor_text(language, "same-Agent project entry is ready; inspect warnings before strict automation.", "同一 Agent 项目入口已就绪；用于严格自动化前请检查警告。")
    if blockers:
        joined = _doctor_join_labels(blockers, language=language)
        return doctor_text(language, f"blocked until {joined} {_doctor_ready_verb(blockers)} ready.", f"需要先让{joined}就绪。")
    return doctor_text(language, "blocked until a same-Agent project entry is ready.", "需要先让一个同一 Agent 项目入口就绪。")


def _doctor_readiness_blockers(report: dict, *, language: str = "en") -> list[str]:
    blockers: list[str] = []
    workdir_state = report.get("workdir_state") if isinstance(report.get("workdir_state"), dict) else {}
    if workdir_state.get("needs_attention") is True:
        blockers.append(doctor_text(language, "target project directory", "目标项目目录"))
    if report.get("agent_entry_ready", report.get("ready")) is not True:
        blockers.append(doctor_text(language, "same-Agent project entry", "同一 Agent 项目入口"))
    if doctor_workdir_usable(report):
        app_state = report.get("app_state") if isinstance(report.get("app_state"), dict) else {}
        if app_state.get("needs_attention") is True:
            blockers.append(doctor_text(language, "App state", "App 状态"))
        web = report.get("web") if isinstance(report.get("web"), dict) else {}
        if web.get("start_available") is False:
            blockers.append(doctor_text(language, "Web start", "Web 启动"))
    if report.get("agent_entry_ready", report.get("ready")) is True and int(report.get("attention_adapter_count") or 0) > 0:
        blockers.append(doctor_text(language, "installed same-Agent entry warnings", "已安装同一 Agent 入口的警告"))
    return _doctor_unique_labels(blockers)


def _doctor_primary_next_action(report: dict, *, language: str = "en") -> str:
    actions = doctor_action_items(report)
    primary_kind = str(report.get("primary_next_action_kind") or "").strip()
    if primary_kind:
        primary = next((action for action in actions if str(action.get("kind") or "").strip() == primary_kind), None)
        step = doctor_action_step(primary, language=language) if primary else ""
        if step:
            return step
    for action in actions:
        step = doctor_action_step(action, language=language)
        if step:
            return step
    for step in [str(item).strip() for item in list(report.get("next_steps") or [])]:
        if step:
            return step
    return ""


def _doctor_unique_labels(labels: list[str]) -> list[str]:
    unique_labels: list[str] = []
    for label in labels:
        if label and label not in unique_labels:
            unique_labels.append(label)
    return unique_labels


def _doctor_join_labels(labels: list[str], *, language: str = "en") -> str:
    if language == "zh":
        return "、".join(labels)
    if len(labels) <= 1:
        return labels[0] if labels else ""
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _doctor_ready_verb(labels: list[str]) -> str:
    return "is" if len(labels) == 1 else "are"


def _doctor_workdir_status_zh(status: str) -> str:
    return {
        "required": "需要选择",
        "missing": "不存在",
        "not_directory": "不是目录",
        "unavailable": "不可用",
        "ready": "可用",
    }.get(status, "未知")


def _doctor_workdir_summary_zh(status: str) -> str:
    return {
        "required": "检查同一 Agent 就绪状态前，需要明确目标项目目录。",
        "missing": "目标项目目录不存在；创建后再继续设置。",
        "not_directory": "目标路径不是目录；请选择可用项目目录。",
        "unavailable": "目标项目目录当前不可访问。",
    }.get(status, "目标项目目录需要处理。")
