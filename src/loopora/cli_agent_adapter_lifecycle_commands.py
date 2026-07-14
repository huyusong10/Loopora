from __future__ import annotations

from pathlib import Path
import shlex
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command, rewrite_loopora_help_commands
from loopora.agent_adapter_current_host import current_agent_host_detection
from loopora.agent_adapter_check_utils import adapter_label
from loopora.agent_adapter_workdir_recovery import (
    AdapterWorkdirRetryPolicy,
    adapter_workdir_recovery_payload,
    adapter_workdir_state,
)
from loopora.cli_agent_adapter_output import (
    handle_adapter_install_conflict as _handle_adapter_install_conflict,
    is_adapter_install_conflict as _is_adapter_install_conflict,
    print_adapter_check_result as _print_adapter_check_result,
    print_adapter_mutation_result as _print_adapter_mutation_result,
)
from loopora.cli_agent_adapter_language import agent_entry_text, localized_agent_entry_command
from loopora.cli_agent_command_options import AdapterEntryWorkdirOption, CheckOption, effective_adapter_workdir
from loopora.cli_group_help import LooporaHelpCommand
from loopora.cli_shared import JsonOutputOption, echo_json, handle_error
from loopora.cli_current_agent_setup_output import print_current_agent_setup
from loopora.diagnose_doctor import build_doctor_report
from loopora.agent_adapters import (
    check_agent_adapter,
    install_agent_adapter,
    preview_agent_adapter_uninstall,
    uninstall_agent_adapter,
)
from loopora.first_use_web_guidance import WEB_CREATION_CHOICE_LABEL, WEB_CREATION_CHOICE_SUMMARY
from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.service import LooporaError
from loopora.service_types import LooporaConflictError

AGENT_ENTRY_CHECK_HELP_EPILOG = (
    "Check is read-only: it inspects the Loopora-managed project entry, reports install/drift/readiness recovery, "
    "and does not install, repair, overwrite, or refresh the host Agent. If the entry is ready, run "
    '`loopora doctor --workdir "$PWD"` before `/loopora-plan`; if it is missing or drifted, use the printed '
    "`loopora init {adapter} --workdir ...` recovery."
)
AGENT_ENTRY_UNINSTALL_HELP_EPILOG = (
    "Uninstall removes only files proven Loopora-managed for this project entry. User-owned host configuration is "
    "preserved; kept files are reported for manual review. Use --dry-run to preview removed and kept file counts "
    "before deleting anything. This is not a state reset: reinstall with "
    '`loopora init {adapter} --workdir "$PWD"` when needed, then refresh or restart the host Agent.'
)
InitLanguageOption = Annotated[
    str,
    typer.Option(
        "--language",
        help="Plain setup/check language: en or zh; common aliases like en-US and zh-CN are normalized.",
    ),
]


def _agent_entry_init_help(agent_label: str, adapter: str) -> str:
    return rewrite_loopora_help_commands(
        f"Install or update the {agent_label} project entry for task-judgment first use.\n\n"
        "First-use path:\n"
        "If you are not sure this task needs a Loop, run `loopora fit` before installing.\n"
        "When fit is strong:\n"
        f'1. Run `loopora init {adapter} --workdir "$PWD"`.\n'
        '2. Run `loopora doctor --workdir "$PWD"` to confirm readiness.\n'
        "3. After readiness passes, or when you already have reviewed material, choose one path:\n"
        f"Same-Agent path: return to {agent_label} with the Loopora fit reason, task goal, fake-done risk, required evidence,\n"
        "judgment tradeoffs, and optional direct-path context\n"
        "and run /loopora-plan.\n"
        f'{WEB_CREATION_CHOICE_LABEL}: use `loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` for {WEB_CREATION_CHOICE_SUMMARY}.\n'
        "Plan-file/expert path: import a plan file or use manual expert mode in Web, then preview before creating or running.\n"
        "Existing work path: inspect evidence, verdict state, residual risk, and next action in Web or `loopora loops`.\n"
        "4. After the READY Loop preview matches the task judgment:\n"
        "Fit Guide/Web choices create or run from Web, then review evidence, verdict state, residual risk, and next action there.\n"
        "Same-Agent path: run /loopora-run in the same Agent session."
    )


def register_agent_adapter_lifecycle_commands(init_app: typer.Typer, uninstall_app: typer.Typer) -> None:
    _register_init_commands(init_app)
    _register_uninstall_commands(uninstall_app)


def _register_init_commands(init_app: typer.Typer) -> None:
    @init_app.command(
        "current",
        cls=LooporaHelpCommand,
        help=rewrite_loopora_help_commands(
            "Set up the uniquely detected current Codex, Claude Code, or OpenCode host and confirm plan readiness.\n\n"
            "This command detects host session presence without printing session identifiers. It fails closed and prints explicit "
            "adapter commands when no host or multiple hosts are detected. After installing the project entry, it runs the same "
            "read-only readiness check as doctor and exits non-zero when /loopora-plan handoff is blocked. Use "
            "`loopora init <agent> --workdir \"$PWD\"` followed by doctor when running outside the target Agent session."
        ),
    )
    def init_current(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        check: CheckOption = False,
        language: InitLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Install or check the uniquely detected current Agent entry."""
        workdir = _effective_parent_workdir(ctx, workdir)
        language = _normalize_init_language(language, workdir=workdir, json_output=json_output)
        detection = current_agent_host_detection()
        adapter = str(detection.get("adapter") or "")
        if not adapter:
            _print_current_host_recovery(
                workdir=workdir,
                detection=detection,
                check=check,
                language=language,
                json_output=json_output,
            )
            raise typer.Exit(code=1)
        if check:
            _install_adapter(adapter, workdir=workdir, check=True, language=language, json_output=json_output)
            return
        _setup_current_adapter(
            adapter,
            workdir=workdir,
            detection=detection,
            language=language,
            json_output=json_output,
        )

    @init_app.command("codex", cls=LooporaHelpCommand, help=_agent_entry_init_help("Codex", "codex"))
    def init_codex(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        check: CheckOption = False,
        language: InitLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Install or update the Codex project entry."""
        workdir = _effective_parent_workdir(ctx, workdir)
        language = _normalize_init_language(language, workdir=workdir, json_output=json_output)
        _install_adapter("codex", workdir=workdir, check=check, language=language, json_output=json_output)

    @init_app.command("claude", cls=LooporaHelpCommand, help=_agent_entry_init_help("Claude Code", "claude"))
    def init_claude(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        check: CheckOption = False,
        language: InitLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Install or update the Claude Code project entry."""
        workdir = _effective_parent_workdir(ctx, workdir)
        language = _normalize_init_language(language, workdir=workdir, json_output=json_output)
        _install_adapter("claude", workdir=workdir, check=check, language=language, json_output=json_output)

    @init_app.command("opencode", cls=LooporaHelpCommand, help=_agent_entry_init_help("OpenCode", "opencode"))
    def init_opencode(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        check: CheckOption = False,
        language: InitLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Install or update the OpenCode project entry."""
        workdir = _effective_parent_workdir(ctx, workdir)
        language = _normalize_init_language(language, workdir=workdir, json_output=json_output)
        _install_adapter("opencode", workdir=workdir, check=check, language=language, json_output=json_output)


def _effective_parent_workdir(ctx: typer.Context, workdir: Path) -> Path:
    return effective_adapter_workdir(ctx, workdir)


def _normalize_init_language(language: str, *, workdir: Path, json_output: bool) -> str:
    try:
        return normalize_fit_guidance_language(language)
    except ValueError as exc:
        if json_output:
            handle_error(ValueError(f"invalid --language: {exc}"), json_output=True, recovery_workdir=workdir)
            return "en"
        typer.echo(f"invalid --language: {exc}", err=True)
        raise typer.Exit(code=2) from exc


def _install_adapter(adapter: str, *, workdir: Path, check: bool, language: str, json_output: bool) -> None:
    if _handle_unusable_adapter_workdir(
        adapter,
        workdir=workdir,
        action="check" if check else "install",
        language=language,
        json_output=json_output,
    ):
        raise typer.Exit(code=1)
    try:
        if check:
            _check_adapter(adapter, workdir=workdir, language=language, json_output=json_output)
            return
        result = install_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="installed", language=language, json_output=json_output)
    except LooporaConflictError as exc:
        if _is_adapter_install_conflict(exc):
            _handle_adapter_install_conflict(
                adapter,
                workdir=workdir,
                exc=exc,
                language=language,
                json_output=json_output,
            )
        else:
            handle_error(exc, json_output=json_output)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)


def _setup_current_adapter(
    adapter: str,
    *,
    workdir: Path,
    detection: dict[str, object],
    language: str,
    json_output: bool,
) -> None:
    if _handle_unusable_adapter_workdir(
        adapter,
        workdir=workdir,
        action="install",
        language=language,
        json_output=json_output,
    ):
        raise typer.Exit(code=1)
    try:
        install_result = install_agent_adapter(adapter, workdir=workdir)
        doctor_report = build_doctor_report(workdir=workdir)
        print_current_agent_setup(
            detection=detection,
            install_result=install_result,
            doctor_report=doctor_report,
            language=language,
            json_output=json_output,
        )
        if doctor_report.get("first_task_handoff_executable") is not True:
            raise typer.Exit(code=1)
    except LooporaConflictError as exc:
        if _is_adapter_install_conflict(exc):
            _handle_adapter_install_conflict(
                adapter,
                workdir=workdir,
                exc=exc,
                language=language,
                json_output=json_output,
            )
        else:
            handle_error(exc, json_output=json_output)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)


def _check_adapter(adapter: str, *, workdir: Path, language: str, json_output: bool) -> None:
    if _handle_unusable_adapter_workdir(
        adapter,
        workdir=workdir,
        action="check",
        language=language,
        json_output=json_output,
    ):
        raise typer.Exit(code=1)
    try:
        result = check_agent_adapter(adapter, workdir=workdir)
        _print_adapter_check_result(result, language=language, json_output=json_output)
        if result.get("check_status") != "pass":
            raise typer.Exit(code=1)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)


def _register_uninstall_commands(uninstall_app: typer.Typer) -> None:
    @uninstall_app.command(
        "codex",
        cls=LooporaHelpCommand,
        epilog=rewrite_loopora_help_commands(AGENT_ENTRY_UNINSTALL_HELP_EPILOG.format(adapter="codex")),
    )
    def uninstall_codex(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        dry_run: bool = typer.Option(default=False, help="Preview cleanup scope without removing files."),
        json_output: JsonOutputOption = False,
    ) -> None:
        """Remove the Loopora-managed Codex project entry."""
        workdir = effective_adapter_workdir(ctx, workdir)
        _uninstall_adapter("codex", workdir=workdir, dry_run=dry_run, json_output=json_output)

    @uninstall_app.command(
        "claude",
        cls=LooporaHelpCommand,
        epilog=rewrite_loopora_help_commands(AGENT_ENTRY_UNINSTALL_HELP_EPILOG.format(adapter="claude")),
    )
    def uninstall_claude(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        dry_run: bool = typer.Option(default=False, help="Preview cleanup scope without removing files."),
        json_output: JsonOutputOption = False,
    ) -> None:
        """Remove the Loopora-managed Claude Code project entry."""
        workdir = effective_adapter_workdir(ctx, workdir)
        _uninstall_adapter("claude", workdir=workdir, dry_run=dry_run, json_output=json_output)

    @uninstall_app.command(
        "opencode",
        cls=LooporaHelpCommand,
        epilog=rewrite_loopora_help_commands(AGENT_ENTRY_UNINSTALL_HELP_EPILOG.format(adapter="opencode")),
    )
    def uninstall_opencode(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        dry_run: bool = typer.Option(default=False, help="Preview cleanup scope without removing files."),
        json_output: JsonOutputOption = False,
    ) -> None:
        """Remove the Loopora-managed OpenCode project entry."""
        workdir = effective_adapter_workdir(ctx, workdir)
        _uninstall_adapter("opencode", workdir=workdir, dry_run=dry_run, json_output=json_output)


def _uninstall_adapter(adapter: str, *, workdir: Path, dry_run: bool, json_output: bool) -> None:
    if _handle_unusable_adapter_workdir(
        adapter,
        workdir=workdir,
        action="uninstall",
        language="en",
        json_output=json_output,
    ):
        raise typer.Exit(code=1)
    try:
        if dry_run:
            result = preview_agent_adapter_uninstall(adapter, workdir=workdir)
            _print_adapter_mutation_result(result, action="uninstall_preview", json_output=json_output)
            return
        result = uninstall_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="uninstalled", json_output=json_output)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)


def register_agent_check_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    @adapter_app.command(
        "check",
        cls=LooporaHelpCommand,
        epilog=rewrite_loopora_help_commands(AGENT_ENTRY_CHECK_HELP_EPILOG.format(adapter=adapter)),
    )
    def agent_check(
        ctx: typer.Context,
        workdir: AdapterEntryWorkdirOption = Path(),
        *,
        language: InitLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Check the Loopora-managed project entry."""
        workdir = effective_adapter_workdir(ctx, workdir)
        language = _normalize_init_language(language, workdir=workdir, json_output=json_output)
        _check_adapter(adapter, workdir=workdir, language=language, json_output=json_output)


def _handle_unusable_adapter_workdir(
    adapter: str,
    *,
    workdir: Path,
    action: str,
    language: str,
    json_output: bool,
) -> bool:
    state = adapter_workdir_state(workdir)
    if state["status"] == "ready":
        return False
    payload = adapter_workdir_recovery_payload(
        adapter,
        action=action,
        workdir_state=state,
        retry_policy=AdapterWorkdirRetryPolicy(before_readiness=True),
    )
    if json_output:
        echo_json(payload)
    else:
        _print_adapter_workdir_recovery(payload, language=language)
    return True


def _print_current_host_recovery(
    *,
    workdir: Path,
    detection: dict[str, object],
    check: bool,
    language: str,
    json_output: bool,
) -> None:
    root = workdir.expanduser().resolve(strict=False)
    action = "check" if check else "install"
    suffix = " --check" if check else ""
    choices = [
        {
            "adapter": adapter,
            "command": copyable_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))}{suffix}"),
        }
        for adapter in ("codex", "claude", "opencode")
    ]
    state = str(detection.get("state") or "unavailable")
    payload = {
        "status": "blocked",
        "action": action,
        "workdir": str(root),
        "current_agent_host": detection,
        "selection_required": True,
        "adapter_choices": choices,
    }
    if json_output:
        echo_json(payload)
        return
    state_text = {"unavailable": "不可用", "ambiguous": "存在冲突", "detected": "已检测"}.get(state, state)
    typer.echo(agent_entry_text(language, f"Current Agent host detection: {state}", f"当前 Agent 宿主检测：{state_text}"))
    if state == "ambiguous":
        labels = ", ".join(adapter_label(str(item)) for item in list(detection.get("detected_adapters") or []))
        typer.echo(
            agent_entry_text(
                language,
                f"Multiple Agent hosts are present in this environment: {labels}.",
                f"当前环境中存在多个 Agent 宿主：{labels}。",
            )
        )
    else:
        typer.echo(
            agent_entry_text(
                language,
                "No supported Agent host session was detected in this environment.",
                "当前环境中未检测到受支持的 Agent 宿主会话。",
            )
        )
    typer.echo(
        agent_entry_text(
            language,
            "Choose the Agent that will continue this task; no project entry was changed:",
            "请选择将继续此任务的 Agent；项目入口尚未改动：",
        )
    )
    for choice in choices:
        command = localized_agent_entry_command(str(choice["command"]), language=language)
        typer.echo(f"- {adapter_label(str(choice['adapter']))}: {command}")


def _print_adapter_workdir_recovery(payload: dict[str, object], *, language: str) -> None:
    label = str(payload.get("label") or "Agent")
    action = str(payload.get("action") or "manage")
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), dict) else {}
    workdir = str(payload.get("workdir") or "")
    heading = {
        "install": "was not installed",
        "check": "check is blocked",
        "uninstall": "was not uninstalled",
    }.get(action, "is blocked")
    typer.echo(
        agent_entry_text(
            language,
            f"{label} Loopora entry {heading}",
            f"{label} Loopora 项目入口{_workdir_heading_zh(action)}",
        )
    )
    typer.echo(agent_entry_text(language, f"target project: {workdir}", f"目标项目：{workdir}"))
    typer.echo(
        agent_entry_text(
            language,
            f"project directory state: {workdir_state.get('status')}",
            f"项目目录状态：{_workdir_state_zh(workdir_state.get('status'))}",
        )
    )
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(agent_entry_text(language, f"note: {summary}", f"说明：{_workdir_summary_zh(summary)}"))
    typer.echo(agent_entry_text(language, "next:", "下一步："))
    next_actions = payload.get("next_actions") if isinstance(payload.get("next_actions"), list) else []
    for item in next_actions:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        command = str(item.get("command") or "").strip()
        label_text = {
            "create_workdir": "Create the target project directory",
            "choose_workdir": "Choose an existing project directory",
            "confirm_readiness": "Confirm readiness after retrying the requested same-Agent project entry action",
            "retry_install": "Retry install after the target exists",
            "retry_check": "Retry check after the target exists",
            "retry_uninstall": "Retry uninstall after the target exists",
        }.get(kind, kind)
        if language == "zh":
            label_text = {
                "create_workdir": "创建目标项目目录",
                "choose_workdir": "选择现有项目目录",
                "confirm_readiness": "重试同一 Agent 项目入口操作后确认就绪",
                "retry_install": "目标存在后重试安装",
                "retry_check": "目标存在后重试检查",
                "retry_uninstall": "目标存在后重试卸载",
            }.get(kind, kind)
        command = localized_agent_entry_command(command, language=language)
        separator = "：" if language == "zh" else ": "
        typer.echo(f"- {label_text}{separator}{command}" if command else f"- {label_text}")


def _workdir_summary_zh(summary: str) -> str:
    if "does not exist" in summary:
        return "目标项目目录尚不存在；在修改同一 Agent 项目入口前先创建或选择目录。"
    if "not a directory" in summary:
        return "目标项目路径不是目录；请先选择现有项目目录。"
    if "could not be inspected" in summary:
        return "无法检查目标项目目录；请先选择可访问的项目目录。"
    return summary


def _workdir_heading_zh(action: str) -> str:
    return {
        "install": "未安装",
        "check": "检查受阻",
        "uninstall": "未卸载",
    }.get(action, "受阻")


def _workdir_state_zh(status: object) -> str:
    value = str(status or "unknown")
    return {
        "missing": "不存在",
        "not_directory": "不是目录",
        "uninspectable": "无法检查",
        "ready": "就绪",
    }.get(value, value)
