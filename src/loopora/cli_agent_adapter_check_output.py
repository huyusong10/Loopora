from __future__ import annotations

import shlex

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_agent_adapter_language import agent_entry_text, localized_agent_entry_command
from loopora.agent_native_v3 import AGENT_NATIVE_V3_SCHEMA_VERSION
from loopora.agent_native_v3 import agent_v3_envelope, agent_v3_legacy_raw
from loopora.first_use_web_guidance import open_web_creation_step


def adapter_check_json_payload(result: dict) -> dict:
    summary = adapter_check_summary(result)
    return agent_v3_envelope(
        kind="agent_check",
        status=str(result.get("check_status") or "fail"),
        summary=summary,
        extras={
            "diagnostics": {"legacy_summary_key": "agent_check_summary"},
            "raw": agent_v3_legacy_raw(summary_key="agent_check_summary", summary=summary, payload=result),
        },
    )


def adapter_check_summary(result: dict) -> dict:
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    summary: dict[str, object] = {
        "schema_version": AGENT_NATIVE_V3_SCHEMA_VERSION,
        "adapter": str(result.get("adapter") or "").strip(),
        "label": str(result.get("label") or "").strip(),
        "workdir": str(result.get("workdir") or "").strip(),
        "check_status": str(result.get("check_status") or "fail").strip(),
    }
    if recovery:
        summary["check_recovery"] = recovery
    next_steps = [str(item).strip() for item in list(result.get("next_steps") or []) if str(item).strip()]
    if next_steps:
        summary["next_steps"] = next_steps
    surface = result.get("native_surface") if isinstance(result.get("native_surface"), dict) else {}
    if surface:
        summary["agent_surface"] = surface
        capabilities = surface.get("experience_capabilities") if isinstance(surface.get("experience_capabilities"), dict) else {}
        if capabilities:
            summary["experience_capabilities"] = capabilities
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def print_adapter_check_recovery_summary(recovery: dict, *, language: str = "en") -> None:
    state = str(recovery.get("state") or "").strip()
    summary = str(recovery.get("summary") or "").strip()
    if state:
        state_text = _adapter_check_state_text(state, language=language)
        typer.echo(agent_entry_text(language, f"install state: {state_text}", f"安装状态：{state_text}"))
    if summary:
        summary_text = _adapter_check_summary_text(state, summary=summary, language=language)
        typer.echo(agent_entry_text(language, f"note: {summary_text}", f"说明：{summary_text}"))


def _plain_adapter_check_state(state: str) -> str:
    return state.replace("_", " ")


def _adapter_check_state_text(state: str, *, language: str) -> str:
    if language != "zh":
        return _plain_adapter_check_state(state)
    return {
        "installed": "已安装",
        "not_installed": "未安装",
        "installed_current": "已安装且为当前版本",
        "installed_needs_update": "已安装但需要更新",
        "installed_check_failed": "已安装但检查失败",
    }.get(state, state)


def _adapter_check_summary_text(state: str, *, summary: str, language: str) -> str:
    if language != "zh":
        return summary
    return {
        "installed": "同一 Agent 项目入口已安装并通过静态检查。",
        "not_installed": "该同一 Agent 项目入口尚未安装。",
        "installed_current": "托管项目入口为当前版本。",
        "installed_needs_update": "托管项目入口需要更新后才能继续。",
        "installed_check_failed": "项目入口检查失败；请审查失败项后再重装。",
    }.get(state, summary)


def print_adapter_check_recovery(result: dict, recovery: dict, *, language: str = "en") -> None:
    install_command = str(recovery.get("install_command") or "").strip()
    if not install_command:
        install_command = copyable_loopora_command(
            f"loopora init {result.get('adapter')} --workdir {shlex.quote(str(result.get('workdir')))}"
        )
    check_command = str(recovery.get("check_command") or "").strip()
    if not check_command:
        check_command = f"{install_command} --check"
    doctor_command = str(recovery.get("doctor_command") or "").strip()
    web_start_command = str(recovery.get("web_start_command") or "").strip()
    install_command = localized_agent_entry_command(install_command, language=language)
    check_command = localized_agent_entry_command(check_command, language=language)
    doctor_command = localized_agent_entry_command(doctor_command, language=language)
    typer.echo(agent_entry_text(language, "recovery:", "恢复："))
    if recovery.get("next_action_items"):
        _print_adapter_check_recovery_actions(
            recovery,
            install_command=install_command,
            check_command=check_command,
            doctor_command=doctor_command,
            web_start_command=web_start_command,
            language=language,
        )
        return
    typer.echo(agent_entry_text(language, f"- Run: {install_command}", f"- 运行：{install_command}"))
    typer.echo(agent_entry_text(language, f"- Then verify: {check_command}", f"- 然后验证：{check_command}"))
    if recovery.get("state") != "not_installed":
        typer.echo(
            agent_entry_text(
                language,
                "- If a file is unmanaged, inspect it before replacing or moving it.",
                "- 如果文件不受 Loopora 托管，请在替换或移动前先人工检查。",
            )
        )


def _print_adapter_check_recovery_actions(  # noqa: PLR0913 - renderer receives the stable recovery command set.
    recovery: dict,
    *,
    install_command: str,
    check_command: str,
    doctor_command: str,
    web_start_command: str,
    language: str,
) -> None:
    actions = recovery.get("next_action_items") if isinstance(recovery.get("next_action_items"), list) else []
    if not actions:
        actions = [
            {"kind": "install_agent_entry", "command": install_command},
            {"kind": "verify_agent_entry", "command": check_command},
            {"kind": "confirm_readiness", "command": doctor_command},
            {"kind": "return_to_agent"},
            {"kind": "confirm_agent_visibility"},
            {"kind": "run_loopora_plan", "command": "/loopora-plan"},
            {"kind": "review_ready_loop_preview"},
            {"kind": "run_loopora_run", "command": "/loopora-run"},
            {"kind": "start_web", "command": web_start_command},
        ]
    if _print_adapter_check_recovery_grouped_actions(actions, language=language):
        return
    for action in actions:
        if isinstance(action, dict):
            step = _adapter_check_recovery_action_step(action, language=language)
            if step:
                typer.echo(f"- {step}")


def _print_adapter_check_recovery_grouped_actions(actions: list[object], *, language: str) -> bool:
    typed_actions = [action for action in actions if isinstance(action, dict)]
    if not any(str(action.get("kind") or "").strip() == "start_web" for action in typed_actions):
        return False
    preflight_kinds = {"inspect_failed_checks", "install_agent_entry", "verify_agent_entry", "confirm_readiness"}
    agent_path_kinds = {"return_to_agent", "confirm_agent_visibility", "run_loopora_plan"}
    post_review_kinds = {"review_ready_loop_preview", "run_loopora_run"}
    grouped_kinds = preflight_kinds | agent_path_kinds | post_review_kinds | {"start_web"}
    by_kind = {str(action.get("kind") or "").strip(): action for action in typed_actions}
    _print_adapter_actions_for_kinds(
        by_kind,
        ("inspect_failed_checks", "install_agent_entry", "verify_agent_entry", "confirm_readiness"),
        language=language,
    )
    if any(kind in by_kind for kind in agent_path_kinds | {"start_web"}):
        typer.echo(agent_entry_text(language, "- After readiness passes, choose one path:", "- 就绪后，选择一条路径："))
    _print_adapter_actions_for_kinds(
        by_kind,
        ("return_to_agent", "confirm_agent_visibility", "run_loopora_plan"),
        prefix=agent_entry_text(language, "Same-Agent path: ", "同一 Agent 路径："),
        language=language,
    )
    _print_adapter_actions_for_kinds(by_kind, ("start_web",), language=language)
    if any(kind in by_kind for kind in agent_path_kinds | {"start_web"}):
        typer.echo(
            agent_entry_text(
                language,
                "- Plan-file/expert path: import a plan file or use manual expert mode in Web, then preview before creating or running.",
                "- 方案文件/专家路径：在 Web 中导入方案文件或使用手动专家模式，创建或运行前先预览。",
            )
        )
        typer.echo(
            agent_entry_text(
                language,
                "- Existing work path: inspect evidence, verdict state, residual risk, and next action in Web or loopora loops.",
                "- 现有工作路径：在 Web 或 loopora loops 中检查证据、裁决状态、残余风险和下一步动作。",
            )
        )
    _print_adapter_actions_for_kinds(
        by_kind,
        ("review_ready_loop_preview", "run_loopora_run"),
        language=language,
    )
    for action in typed_actions:
        if str(action.get("kind") or "").strip() in grouped_kinds:
            continue
        _print_adapter_action_step(action, language=language)
    return True


def _print_adapter_actions_for_kinds(
    actions_by_kind: dict[str, dict],
    kinds: tuple[str, ...],
    *,
    prefix: str = "",
    language: str,
) -> None:
    for kind in kinds:
        action = actions_by_kind.get(kind)
        if action:
            _print_adapter_action_step(action, prefix=prefix, language=language)


def _print_adapter_action_step(action: dict, *, prefix: str = "", language: str) -> None:
    step = _adapter_check_recovery_action_step(action, language=language)
    if step:
        typer.echo(f"- {prefix}{step}")


def _adapter_check_recovery_action_step(action: dict, *, language: str = "en") -> str:
    kind = str(action.get("kind") or "").strip()
    command = localized_agent_entry_command(str(action.get("command") or "").strip(), language=language)
    command_templates = {
        "install_agent_entry": ("Run: {command}", "Run loopora init for this Agent entry."),
        "verify_agent_entry": ("Then verify: {command}", "Then verify the Agent entry."),
        "confirm_readiness": (
            "Then confirm readiness: {command}",
            "Then confirm readiness with loopora doctor.",
        ),
        "start_web": (
            open_web_creation_step(target="{command}", sentence_case=False),
            open_web_creation_step(sentence_case=False),
        ),
    }
    fixed_steps = {
        "inspect_failed_checks": "Inspect failed checks before reinstalling; unmanaged files require manual review.",
        "confirm_agent_visibility": "If /loopora-plan or /loopora-run is not visible after install, refresh or restart the Agent.",
        "return_to_agent": (
            "Return to the Agent with the Loopora fit reason, task goal, fake-done risk, required evidence, "
            "judgment tradeoffs, and optional direct-path context."
        ),
        "run_loopora_plan": "Run /loopora-plan to prepare the Loop preview.",
        "review_ready_loop_preview": "Review whether the READY Loop preview matches the task judgment.",
        "run_loopora_run": "After the READY Loop preview matches the task judgment, run /loopora-run in the same Agent session.",
    }
    if language == "zh":
        command_templates = {
            "install_agent_entry": ("运行：{command}", "为此 Agent 项目入口运行 loopora init。"),
            "verify_agent_entry": ("然后验证：{command}", "然后验证该 Agent 项目入口。"),
            "confirm_readiness": ("然后确认就绪：{command}", "然后用 loopora doctor 确认就绪。"),
            "start_web": ("在 Web 中打开适用性判断/Web 选择：{command}", "在 Web 中打开适用性判断/Web 选择。"),
        }
        fixed_steps = {
            "inspect_failed_checks": "重装前先检查失败项；不受托管的文件需要人工审查。",
            "confirm_agent_visibility": "安装后若看不到 /loopora-plan 或 /loopora-run，请刷新或重启 Agent。",
            "return_to_agent": "带着 Loopora 适配理由、任务目标、伪完成风险、必需证据、判断取舍和可选直接路径上下文回到 Agent。",
            "run_loopora_plan": "运行 /loopora-plan 准备 Loop 预览。",
            "review_ready_loop_preview": "审查 READY Loop 预览是否符合任务判断。",
            "run_loopora_run": "READY Loop 预览符合任务判断后，在同一 Agent 会话中运行 /loopora-run。",
        }
    if kind in command_templates:
        with_command, fallback = command_templates[kind]
        return with_command.format(command=command) if command else fallback
    return fixed_steps.get(kind, "")
