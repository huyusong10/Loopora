from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.branding import app_home_path
from loopora.cli_shared import JsonOutputOption, echo_json, get_service, handle_error
from loopora.existing_work_status import existing_work_status_payload
from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.service_types import LooporaError
from loopora.workdir_inputs import normalize_existing_workdir

STATUS_HELP_EPILOG = (
    "Status is read-only by default. It combines planning conversations, active Runs, "
    "recoverable failures, evidence gaps, recent results, and saved Loops that have not run yet. By default it "
    "scopes to the current directory; use --workdir for another target or --all for a cross-project scan. It never "
    "starts, retries, stops, or rewrites work. If it detects records whose local workers are gone, review the result "
    "and explicitly pass --reconcile to move only that scope into recoverable terminal states."
)

StatusWorkdirOption = Annotated[
    Path | None,
    typer.Option(
        "--workdir",
        file_okay=True,
        dir_okay=True,
        exists=False,
        help="Target project to inspect; defaults to the current directory.",
    ),
]
StatusAllProjectsOption = Annotated[
    bool,
    typer.Option("--all", help="Inspect existing work across all target projects instead of one workdir."),
]
StatusLanguageOption = Annotated[
    str,
    typer.Option("--language", help="Plain output language: en or zh; common locale aliases are accepted."),
]
StatusReconcileOption = Annotated[
    bool,
    typer.Option(
        "--reconcile",
        help="Explicitly reconcile orphaned local Run/planning records in the selected scope before reporting.",
    ),
]


def register_status_command(app: typer.Typer) -> None:
    @app.command("status", epilog=rewrite_loopora_help_commands(STATUS_HELP_EPILOG))
    def status(
        workdir: StatusWorkdirOption = None,
        *,
        all_projects: StatusAllProjectsOption = False,
        language: StatusLanguageOption = "en",
        reconcile: StatusReconcileOption = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Show the next action for existing Loopora work."""
        try:
            if all_projects and workdir is not None:
                raise LooporaError("choose either --workdir or --all, not both")
            normalized_workdir = None if all_projects else normalize_existing_workdir(workdir or Path.cwd())
            normalized_language = normalize_fit_guidance_language(language)
            database = app_home_path() / "app.db"
            service = (
                get_service(
                    apply_startup_repairs=False,
                    storage_read_only=not reconcile,
                )
                if database.is_file()
                else None
            )
            payload = existing_work_status_payload(
                service,
                workdir=normalized_workdir,
                all_projects=all_projects,
                language=normalized_language,
                reconcile_runtime_state=reconcile,
            )
            if json_output:
                echo_json(payload)
                return
            print_existing_work_status(payload)
        except (LooporaError, ValueError) as exc:
            handle_error(exc, json_output=json_output, recovery_workdir=workdir)


def print_existing_work_status(payload: dict[str, object]) -> None:
    language = str(payload.get("language") or "en")
    all_projects = payload.get("scope") == "all_projects"
    typer.echo(_text(language, "Loopora status", "Loopora 状态"))
    typer.echo(
        _text(language, "Scope: all target projects", "范围：全部目标项目")
        if all_projects
        else _text(language, f"Project: {payload.get('workdir')}", f"项目：{payload.get('workdir')}")
    )
    counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
    typer.echo(
        _text(
            language,
            f"Needs attention: {counts.get('needs_attention', 0)} · Recent: {counts.get('recent', 0)} · Saved, not run: {counts.get('saved_not_run', 0)}",
            f"待处理：{counts.get('needs_attention', 0)} · 最近：{counts.get('recent', 0)} · 已保存未运行：{counts.get('saved_not_run', 0)}",
        )
    )
    _print_runtime_reconciliation(payload, language=language)
    _print_section(payload, "attention", _text(language, "Needs attention", "需要处理"), limit=6)
    _print_section(payload, "recent", _text(language, "Recent results", "最近结果"), limit=3)
    _print_section(payload, "saved_not_run", _text(language, "Saved, not run", "已保存未运行"), limit=3)
    if payload.get("status") == "empty":
        typer.echo(_text(language, "No existing Loopora work in this scope.", "此范围内没有已有 Loopora 工作。"))
    actions = payload.get("next_actions") if isinstance(payload.get("next_actions"), list) else []
    if actions and isinstance(actions[0], dict) and actions[0].get("command"):
        typer.echo(_text(language, "Next:", "下一步："))
        typer.echo(str(actions[0]["command"]))
    if payload.get("read_only") is True:
        typer.echo(_text(language, "Read-only: no work was started or changed.", "只读：未启动或修改任何工作。"))
    else:
        typer.echo(
            _text(
                language,
                "Reconciliation was explicit: only orphaned records or already cancellation-requested planning were repaired; no work was started or retried.",
                "已显式执行协调：只修复孤儿记录或已请求取消的规划；未启动或重试任何工作。",
            )
        )


def _print_runtime_reconciliation(payload: dict[str, object], *, language: str) -> None:
    state = payload.get("runtime_reconciliation")
    if not isinstance(state, dict):
        return
    run_count = int(state.get("stale_run_count") or 0)
    session_count = int(state.get("orphaned_planning_session_count") or 0)
    if state.get("status") == "required":
        typer.echo(
            _text(
                language,
                f"Runtime reconciliation required: {run_count} stale Run(s), {session_count} orphaned planning session(s); persisted records were not changed.",
                f"需要协调运行状态：{run_count} 个陈旧 Run，{session_count} 个孤儿规划会话；持久化记录尚未修改。",
            )
        )
    elif state.get("status") == "applied":
        typer.echo(
            _text(
                language,
                f"Runtime reconciliation applied: {run_count} stale Run(s), {session_count} orphaned planning session(s).",
                f"已协调运行状态：{run_count} 个陈旧 Run，{session_count} 个孤儿规划会话。",
            )
        )


def _print_section(payload: dict[str, object], key: str, heading: str, *, limit: int) -> None:
    items = payload.get(key) if isinstance(payload.get(key), list) else []
    if not items:
        return
    typer.echo(f"{heading}:")
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("reason") or item.get("summary") or item.get("status") or "")
        action = str(item.get("action") or "")
        detail = f" — {label}" if label else ""
        next_label = f" → {action}" if action else ""
        typer.echo(f"- [{item.get('status')}] {item.get('name')} ({item.get('id')}){detail}{next_label}")
    hidden = len(items) - limit
    if hidden > 0:
        typer.echo(f"  +{hidden} more; use --json for the complete projection")


def _text(language: str, en: str, zh: str) -> str:
    return zh if language == "zh" else en


__all__ = ["STATUS_HELP_EPILOG", "print_existing_work_status", "register_status_command"]
