from __future__ import annotations

import shlex

import typer

from loopora.first_use_web_guidance import WEB_CREATION_CHOICE_LABEL, use_web_creation_step

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_check_utils import adapter_label as _adapter_label
from loopora import cli_agent_adapter_check_output as _adapter_check_output
from loopora import cli_agent_adapter_conflict_output as _adapter_conflict_output
from loopora.cli_agent_adapter_language import agent_entry_text, localized_agent_entry_command
from loopora.cli_first_task_handoff import FIRST_TASK_ORIENTATION_EXAMPLE_ZH, echo_first_task_handoff
from loopora.cli_serve_language import localized_serve_command
from loopora.cli_shared import echo_json

_adapter_check_json_payload = _adapter_check_output.adapter_check_json_payload
_adapter_check_summary = _adapter_check_output.adapter_check_summary
_print_adapter_check_recovery = _adapter_check_output.print_adapter_check_recovery
_print_adapter_check_recovery_summary = _adapter_check_output.print_adapter_check_recovery_summary
handle_adapter_install_conflict = _adapter_conflict_output.handle_adapter_install_conflict
is_adapter_install_conflict = _adapter_conflict_output.is_adapter_install_conflict
_adapter_conflict_paths = _adapter_conflict_output.adapter_conflict_paths


def print_adapter_mutation_result(result: dict, *, action: str, json_output: bool, language: str = "en") -> None:
    if json_output:
        echo_json(result)
        return
    label = str(result.get("label") or adapter_label(str(result.get("adapter") or "")))
    if action == "installed":
        typer.echo(agent_entry_text(language, f"{label} Loopora entry is installed", f"{label} Loopora 项目入口已安装"))
        typer.echo(agent_entry_text(language, f"target project: {result['workdir']}", f"目标项目：{result['workdir']}"))
        _print_adapter_next_steps(label, result.get("next_steps"), language=language)
        _print_adapter_first_task_message_example(result, language=language)
        _print_adapter_next_commands(result.get("next_commands"), language=language)
        _print_adapter_install_proof(result, language=language)
    elif action == "uninstall_preview":
        _print_adapter_uninstall_preview(label, result)
    elif action == "uninstalled":
        _print_adapter_uninstall_result(label, result)
    else:
        typer.echo(f"{label} Loopora entry {action}: {result['status']}")
        typer.echo(f"target project: {result['workdir']}")
        _print_adapter_file_details(result)


def print_adapter_check_result(result: dict, *, json_output: bool, language: str = "en") -> None:
    if json_output:
        echo_json(_adapter_check_json_payload(result))
        return
    label = str(result.get("label") or adapter_label(str(result.get("adapter") or "")))
    check_status = str(result.get("check_status") or "fail")
    status_text = {"pass": "通过", "fail": "失败"}.get(check_status, check_status) if language == "zh" else check_status
    typer.echo(
        agent_entry_text(
            language,
            f"{label} Loopora entry check: {check_status}",
            f"{label} Loopora 项目入口检查：{status_text}",
        )
    )
    typer.echo(agent_entry_text(language, f"target project: {result['workdir']}", f"目标项目：{result['workdir']}"))
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    _print_adapter_check_recovery_summary(recovery, language=language)
    if recovery.get("state") == "not_installed":
        _print_adapter_check_recovery(result, recovery, language=language)
        return
    checks = [item for item in list(result.get("checks") or []) if isinstance(item, dict)]
    failed_checks = [item for item in checks if item.get("status") != "pass"]
    if check_status == "pass":
        typer.echo(agent_entry_text(language, f"checks: pass ({len(checks)} checks)", f"检查：通过（共 {len(checks)} 项）"))
    elif checks:
        typer.echo(agent_entry_text(language, "checks:", "检查："))
        for item in checks:
            suffix = f" ({item.get('path')})" if item.get("path") else ""
            message = f": {item.get('message')}" if item.get("message") else ""
            typer.echo(f"- {item.get('status')}: {item.get('name')}{suffix}{message}")
    if check_status == "pass":
        _print_adapter_next_steps(label, result.get("next_steps"), language=language)
        _print_adapter_first_task_message_example(result, language=language)
        _print_adapter_next_commands(result.get("next_commands"), language=language)
        _print_adapter_install_proof(result, language=language)
    if check_status != "pass" or failed_checks:
        _print_adapter_check_recovery(result, recovery, language=language)


def adapter_label(adapter: str) -> str:
    return _adapter_label(adapter) or "Agent"


def _print_adapter_file_details(result: dict) -> None:
    managed_files = result.get("managed_files")
    if isinstance(managed_files, list):
        typer.echo("managed files:")
        for item in managed_files:
            if isinstance(item, dict):
                typer.echo(f"- {item.get('path')}: {item.get('state', 'managed')}")
    removed_files = result.get("removed_files")
    _print_adapter_plain_list("removed:", removed_files)
    removed_obsolete_files = result.get("removed_obsolete_files")
    _print_adapter_plain_list("removed obsolete managed files:", removed_obsolete_files)
    kept_files = result.get("kept_files")
    if isinstance(kept_files, list) and kept_files:
        typer.echo("kept:")
        for item in kept_files:
            if isinstance(item, dict):
                typer.echo(f"- {item.get('path')}: {item.get('reason')}")


def _print_adapter_plain_list(label: str, items: object) -> None:
    if not isinstance(items, list) or not items:
        return
    typer.echo(label)
    for item in items:
        typer.echo(f"- {item}")


def _print_adapter_uninstall_result(label: str, result: dict) -> None:
    removed_files = _string_items(result.get("removed_files"))
    kept_files = _kept_file_items(result.get("kept_files"))
    headline = "is already uninstalled" if not removed_files and not kept_files else "is uninstalled"
    typer.echo(f"{label} Loopora entry {headline}")
    typer.echo(f"target project: {result['workdir']}")
    typer.echo(f"removed files: {len(removed_files)} Loopora-managed files")
    if kept_files:
        typer.echo(f"kept files: {len(kept_files)} need manual review")
        typer.echo("manual review:")
        for item in kept_files[:5]:
            typer.echo(f"- {item['path']}: {item['reason']}")
        remaining = len(kept_files) - 5
        if remaining > 0:
            typer.echo(f"- ... {remaining} more kept files; use --json for the full list.")
    else:
        typer.echo("kept files: none")
    if result.get("manifest_error"):
        typer.echo("manifest warning: managed manifest was unreadable; only provably Loopora-managed files were removed.")
    _print_adapter_uninstall_next(label, result, kept_files=kept_files)
    typer.echo("details: pass --json when you need exact removed and kept paths for cleanup logs.")


def _print_adapter_uninstall_preview(label: str, result: dict) -> None:
    removed_files = _string_items(result.get("removed_files"))
    kept_files = _kept_file_items(result.get("kept_files"))
    typer.echo(f"{label} Loopora entry uninstall dry run")
    typer.echo(f"target project: {result['workdir']}")
    typer.echo(f"would remove: {len(removed_files)} Loopora-managed files")
    if kept_files:
        typer.echo(f"would keep: {len(kept_files)} files need manual review")
        typer.echo("manual review:")
        for item in kept_files[:5]:
            typer.echo(f"- {item['path']}: {item['reason']}")
        remaining = len(kept_files) - 5
        if remaining > 0:
            typer.echo(f"- ... {remaining} more kept files; use --json for the full list.")
    else:
        typer.echo("would keep: none")
    if result.get("manifest_error"):
        typer.echo("manifest warning: managed manifest was unreadable; only provably Loopora-managed files would be removed.")
    typer.echo("next:")
    adapter = str(result.get("adapter") or "").strip()
    workdir = str(result.get("workdir") or "").strip()
    if adapter and workdir:
        typer.echo(f"- After reviewing the dry-run scope: {copyable_loopora_command(f'loopora uninstall {adapter} --workdir {shlex.quote(workdir)}')}")
    typer.echo("details: pass --json with --dry-run when you need exact removed and kept paths before cleanup.")


def _print_adapter_uninstall_next(label: str, result: dict, *, kept_files: list[dict[str, str]]) -> None:
    reinstall_command = _adapter_reinstall_command(result)
    typer.echo("next:")
    if reinstall_command:
        typer.echo(f"- Reinstall later: {reinstall_command}")
    typer.echo(f"- If {label} still shows /loopora-plan or /loopora-run, refresh or restart {label}.")
    if kept_files:
        typer.echo("- Review kept files before assuming all project entries are gone.")


def _adapter_reinstall_command(result: dict) -> str:
    commands = result.get("next_commands") if isinstance(result.get("next_commands"), dict) else {}
    command = str(commands.get("reinstall") or "").strip()
    if command:
        return command
    adapter = str(result.get("adapter") or "").strip()
    workdir = str(result.get("workdir") or "").strip()
    if not adapter or not workdir:
        return ""
    workdir_arg = shlex.quote(workdir)
    return copyable_loopora_command(f"loopora init {adapter} --workdir {workdir_arg}")


def _string_items(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    return [text for text in (str(item or "").strip() for item in items) if text]


def _kept_file_items(items: object) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    kept: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        reason = str(item.get("reason") or "").strip() or "not_removed"
        if path:
            kept.append({"path": path, "reason": reason})
    return kept


def _print_adapter_next_steps(label: str, steps: object = None, *, language: str = "en") -> None:
    typer.echo(agent_entry_text(language, "next:", "下一步："))
    if language == "en" and isinstance(steps, list) and steps:
        for step in steps:
            text = str(step or "").strip()
            if text:
                typer.echo(f"- {text}")
        return
    if language == "zh":
        typer.echo(f"- 带着 Loopora 适配理由、任务目标、伪完成风险、必需证据、判断取舍和可选直接路径上下文回到本项目中的 {label}。")
        typer.echo("- 运行 /loopora-plan 准备 Loop 预览，再开始工作。")
        typer.echo("- 审查 READY Loop 预览，再在同一 Agent 会话中运行 /loopora-run。")
        typer.echo(f"- 如果 {label} 中看不到 /loopora-plan 或 /loopora-run，请重跑下方诊断并刷新或重启 {label}。")
        typer.echo("- 如果更适合在 Agent 会话外继续，请在 Web 中使用适用性判断/Web 选择。")
        return
    typer.echo(
        f"- Return to {label} in this project with the Loopora fit reason, task goal, fake-done risk, "
        "required evidence, judgment tradeoffs, and optional direct-path context."
    )
    typer.echo("- Run /loopora-plan to prepare the Loop preview before starting work.")
    typer.echo("- Review the READY Loop preview, then run /loopora-run in the same Agent session.")
    typer.echo(
        f"- If /loopora-plan or /loopora-run is not visible in {label}, "
        f"rerun the diagnostics below and refresh or restart {label}."
    )
    typer.echo(f"- {use_web_creation_step()}")


def _print_adapter_next_commands(commands: object, *, language: str = "en") -> None:
    if not isinstance(commands, dict):
        return
    web_start_command = str(commands.get("web_start") or "").strip()
    doctor_command = str(commands.get("doctor") or "").strip()
    check_command = str(commands.get("check") or "").strip()
    agent_check_command = str(commands.get("agent_check") or "").strip()
    support_command = str(commands.get("support") or "").strip()
    if not web_start_command and not doctor_command and not check_command and not agent_check_command and not support_command:
        return
    if doctor_command or check_command or agent_check_command or support_command:
        typer.echo(agent_entry_text(language, "diagnostics:", "诊断："))
        if doctor_command:
            command = localized_agent_entry_command(doctor_command, language=language)
            typer.echo(agent_entry_text(language, f"- readiness report: {command}", f"- 就绪报告：{command}"))
        if check_command:
            command = localized_agent_entry_command(check_command, language=language)
            typer.echo(agent_entry_text(language, f"- verify install: {command}", f"- 验证安装：{command}"))
        if agent_check_command:
            command = localized_agent_entry_command(agent_check_command, language=language)
            typer.echo(
                agent_entry_text(
                    language,
                    f"- agent-runtime check: {command}",
                    f"- Agent 运行时检查：{command}",
                )
            )
        if support_command:
            command = localized_agent_entry_command(support_command, language=language)
            typer.echo(agent_entry_text(language, f"- usage/setup help: {command}", f"- 使用/设置帮助：{command}"))
    if web_start_command:
        web_start_command = localized_serve_command(web_start_command, language=language)
        typer.echo(agent_entry_text(language, "web:", "Web："))
        typer.echo(
            agent_entry_text(
                language,
                f"- after readiness passes, open {WEB_CREATION_CHOICE_LABEL} in Web: {web_start_command}",
                f"- 就绪后，在 Web 中打开适用性判断/Web 选择：{web_start_command}",
            )
        )


def _print_adapter_install_proof(result: dict, *, language: str = "en") -> None:
    managed_files = [item for item in list(result.get("managed_files") or []) if isinstance(item, dict)]
    if managed_files:
        current_count = sum(1 for item in managed_files if item.get("state") == "current")
        typer.echo(
            agent_entry_text(
                language,
                f"installed files: {current_count}/{len(managed_files)} managed files current",
                f"已安装文件：{current_count}/{len(managed_files)} 个托管文件为当前版本",
            )
        )
    manifest_path = str(result.get("manifest_path") or "").strip()
    if manifest_path:
        typer.echo(agent_entry_text(language, f"manifest: {manifest_path}", f"清单：{manifest_path}"))
    typer.echo(
        agent_entry_text(
            language,
            "details: rerun with --json for managed file hashes and the Agent surface contract.",
            "详情：需要托管文件哈希和 Agent surface 契约时，请加 --json 重跑。",
        )
    )


def _print_adapter_first_task_message_example(result: dict, *, language: str = "en") -> None:
    echo_first_task_handoff(
        result,
        example=FIRST_TASK_ORIENTATION_EXAMPLE_ZH if language == "zh" else None,
        copy_rule_transform=_adapter_plain_copy_rule,
        language=language,
    )


def _adapter_plain_copy_rule(policy: dict[str, object], copy_rule: str) -> str:
    raw_fit_command = str(policy.get("fit_command") or "loopora fit").strip()
    fit_command = copyable_loopora_command(raw_fit_command)
    return copy_rule.replace(raw_fit_command, fit_command)
