from __future__ import annotations

from pathlib import Path
import shlex
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command, rewrite_loopora_help_commands
from loopora.cli_recovery_language import localized_recovery_command, recovery_text
from loopora.cli_recovery_projection import (
    recovery_create_json_payload,
    recovery_create_next_actions,
    recovery_inspect_json_payload,
    recovery_inspect_next_actions,
    recovery_restore_json_payload,
    recovery_restore_state,
)
from loopora.cli_shared import JsonOutputOption, echo_json, handle_error
from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.recovery_archive import RecoveryActiveWorkError, create_recovery_archive, inspect_recovery_archive
from loopora.recovery_restore import restore_recovery_archive
from loopora.service_types import LooporaError

RECOVERY_HELP_EPILOG = (
    "Recovery archives are private exact-path safeguards for Loopora's App catalog and one target project's managed "
    "Loops, Runs, evidence, and planning sessions. Create one before a development reset or risky local-state change. "
    "They include prompts, transcripts, raw model output, evidence, settings, and absolute paths, so never use them as "
    "public support bundles. Inspect verifies checksums and SQLite integrity. Restore previews by default, refuses path "
    "mismatches or changed files, and writes only after --yes."
)
RecoveryWorkdirOption = Annotated[
    Path,
    typer.Option("--workdir", exists=False, file_okay=True, dir_okay=True, help="Exact target project directory."),
]
RecoveryOutputOption = Annotated[
    Path | None,
    typer.Option("--output", "-o", help="ZIP output path; defaults to the current directory."),
]
RecoveryForceOption = Annotated[bool, typer.Option("--force", help="Replace an existing recovery ZIP.")]
RecoveryYesOption = Annotated[bool, typer.Option("--yes", help="Apply a conflict-free restore preview.")]
RecoveryLanguageOption = Annotated[
    str,
    typer.Option(
        "--language",
        help="Plain recovery language: en or zh; common aliases like en-US and zh-CN are normalized.",
    ),
]
RecoveryInspectArchiveArgument = Annotated[
    Path,
    typer.Argument(..., exists=False, file_okay=True, dir_okay=True, help="Recovery ZIP to verify."),
]
RecoveryRestoreArchiveArgument = Annotated[
    Path,
    typer.Argument(..., exists=False, file_okay=True, dir_okay=True, help="Recovery ZIP to restore."),
]


def register_recovery_commands(app: typer.Typer) -> None:
    _register_recovery_create(app)
    _register_recovery_inspect(app)
    _register_recovery_restore(app)


def _register_recovery_create(app: typer.Typer) -> None:
    @app.command("create")
    def create(
        workdir: RecoveryWorkdirOption,
        output: RecoveryOutputOption = None,
        *,
        force: RecoveryForceOption = False,
        language: RecoveryLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Create a private full-recovery archive for one target project."""
        language = _normalize_recovery_language(language, workdir=workdir, json_output=json_output)
        try:
            result = create_recovery_archive(workdir=workdir, output=output, overwrite=force)
        except RecoveryActiveWorkError as exc:
            _render_active_work_recovery(
                exc,
                workdir=workdir,
                output=output,
                force=force,
                language=language,
                json_output=json_output,
            )
            return
        except (LooporaError, OSError) as exc:
            handle_error(exc, json_output=json_output, recovery_workdir=workdir)
            return
        if json_output:
            echo_json(recovery_create_json_payload(result))
            return
        typer.echo(recovery_text(language, f"Recovery archive: {result['path']}", f"私有恢复归档：{result['path']}"))
        typer.echo(
            recovery_text(
                language,
                f"Included: {result['file_count']} managed files; private full-recovery content.",
                f"已包含：{result['file_count']} 个托管文件；内容用于完整私有恢复。",
            )
        )
        typer.echo(
            recovery_text(
                language,
                "Sharing: not public-safe; contains local paths, prompts, transcripts, model output, and evidence.",
                "共享边界：不可公开；其中包含本地路径、prompt、对话记录、模型输出和证据。",
            )
        )
        inspect_action = recovery_create_next_actions(result)[0]
        inspect_command = str(inspect_action["command"])
        inspect_command = localized_recovery_command(inspect_command, language=language)
        typer.echo(recovery_text(language, "Next:", "下一步："))
        typer.echo(
            recovery_text(
                language,
                f"- Verify checksums, scope, and SQLite integrity first: {inspect_command}",
                f"- 先验证 checksum、归档范围和 SQLite 完整性：{inspect_command}",
            )
        )


def _render_active_work_recovery(  # noqa: PLR0913 - blocked archive rendering keeps retry inputs explicit.
    exc: RecoveryActiveWorkError,
    *,
    workdir: Path,
    output: Path | None,
    force: bool,
    language: str,
    json_output: bool,
) -> None:
    status_command = copyable_loopora_command(
        f"loopora status --workdir {shlex.quote(str(workdir.resolve(strict=False)))}"
    )
    retry_command = _recovery_create_retry_command(workdir=workdir, output=output, force=force)
    actions = [
        {"kind": "inspect_active_work", "command": status_command},
        {
            "kind": "resolve_active_work",
            "after_action": "inspect_active_work",
            "note": "Stop live work, or use the scoped status --reconcile action only for workers confirmed gone.",
        },
        {
            "kind": "retry_recovery_archive",
            "command": retry_command,
            "after_action": "resolve_active_work",
        },
    ]
    if json_output:
        echo_json(
            {
                "status": "blocked_by_active_work",
                "error": str(exc),
                "active_run_count": exc.active_runs,
                "active_planning_session_count": exc.active_planning_sessions,
                "next_actions": actions,
            }
        )
        raise typer.Exit(code=1)
    status_command = localized_recovery_command(status_command, language=language)
    retry_command = localized_recovery_command(retry_command, language=language)
    active_summary = (
        f"无法创建恢复归档：仍有 {exc.active_runs} 个 active Run 和 "
        f"{exc.active_planning_sessions} 个 active planning session。"
    )
    typer.secho(recovery_text(language, str(exc), active_summary), fg=typer.colors.RED, err=True)
    typer.echo(
        recovery_text(
            language,
            f"Inspect active or orphaned work: {status_command}",
            f"检查仍在运行或失去 worker 的工作：{status_command}",
        ),
        err=True,
    )
    typer.echo(
        recovery_text(
            language,
            "Resolve: stop live work, or use the scoped status --reconcile action only when status confirms its local worker is gone.",
            "解决方式：停止仍在运行的工作；只有 status 确认本地 worker 已消失时，才使用限定项目范围的 --reconcile 动作。",
        ),
        err=True,
    )
    typer.echo(recovery_text(language, f"Retry archive: {retry_command}", f"重试归档：{retry_command}"), err=True)
    raise typer.Exit(code=1)


def _recovery_create_retry_command(*, workdir: Path, output: Path | None, force: bool) -> str:
    command = f"loopora recovery create --workdir {shlex.quote(str(workdir.resolve(strict=False)))}"
    if output is not None:
        command += f" --output {shlex.quote(str(output.expanduser().resolve(strict=False)))}"
    if force:
        command += " --force"
    return copyable_loopora_command(command)

def _register_recovery_inspect(app: typer.Typer) -> None:
    @app.command("inspect")
    def inspect(
        archive: RecoveryInspectArchiveArgument,
        *,
        language: RecoveryLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Verify archive format, checksums, scope, and SQLite integrity."""
        language = _normalize_recovery_language(language, workdir=None, json_output=json_output)
        try:
            result = inspect_recovery_archive(archive)
        except (LooporaError, OSError) as exc:
            handle_error(exc, json_output=json_output)
            return
        if json_output:
            echo_json(recovery_inspect_json_payload(result))
            return
        source = result["source"]
        typer.echo(
            recovery_text(
                language,
                f"Recovery archive: valid ({result['file_count']} managed files)",
                f"恢复归档：有效（{result['file_count']} 个托管文件）",
            )
        )
        typer.echo(recovery_text(language, f"Source App home: {source['app_home']}", f"来源 App home：{source['app_home']}"))
        typer.echo(recovery_text(language, f"Source project: {source['workdir']}", f"来源项目：{source['workdir']}"))
        typer.echo(
            recovery_text(
                language,
                f"Database schema: {result['database_schema_version']}",
                f"数据库 schema：{result['database_schema_version']}",
            )
        )
        typer.echo(
            recovery_text(
                language,
                "Scope: private exact-path recovery; not a public support bundle.",
                "范围：私有精确路径恢复；不是可公开的支持包。",
            )
        )
        actions = recovery_inspect_next_actions(result)
        commands = {
            str(action["kind"]): localized_recovery_command(str(action["command"]), language=language)
            for action in actions
        }
        typer.echo(recovery_text(language, "Next:", "下一步："))
        typer.echo(
            recovery_text(
                language,
                f"- Continue a planned App-state recovery with a no-write reset preview: {commands['preview_app_database_reset']}",
                f"- 如需继续既定 App 状态恢复，先运行无写入的重置预览：{commands['preview_app_database_reset']}",
            )
        )
        typer.echo(
            recovery_text(
                language,
                f"- Only when recovering missing files, preview exact-path restore: {commands['preview_exact_path_restore']}",
                f"- 只有需要找回缺失文件时，才预览精确路径恢复：{commands['preview_exact_path_restore']}",
            )
        )
        typer.echo(
            recovery_text(
                language,
                f"- Otherwise re-check current readiness: {commands['confirm_readiness']}",
                f"- 否则重新检查当前就绪状态：{commands['confirm_readiness']}",
            )
        )

def _register_recovery_restore(app: typer.Typer) -> None:
    @app.command("restore")
    def restore(
        archive: RecoveryRestoreArchiveArgument,
        workdir: RecoveryWorkdirOption = Path(),
        *,
        yes: RecoveryYesOption = False,
        language: RecoveryLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Preview or apply exact-path recovery without overwriting changed files."""
        language = _normalize_recovery_language(language, workdir=workdir, json_output=json_output)
        try:
            result = restore_recovery_archive(archive=archive, workdir=workdir, apply=yes)
        except (LooporaError, OSError) as exc:
            handle_error(exc, json_output=json_output, recovery_workdir=workdir)
            return
        if json_output:
            echo_json(recovery_restore_json_payload(result))
        else:
            _print_restore_result(recovery_restore_json_payload(result), language=language)
        if result["status"] == "blocked":
            raise typer.Exit(code=1)


def _print_restore_result(result: dict, *, language: str = "en") -> None:
    state = recovery_restore_state(result)
    status = str(result["status"])
    status_text = {"preview": "预览", "restored": "已恢复", "blocked": "受阻"}.get(status, status)
    if state == "no_restore_needed":
        typer.echo(recovery_text(language, "Recovery restore: no restore needed", "恢复操作：无需恢复"))
    else:
        typer.echo(recovery_text(language, f"Recovery restore: {status}", f"恢复操作：{status_text}"))
    typer.echo(recovery_text(language, f"Would restore: {len(result['planned'])}", f"计划恢复：{len(result['planned'])}"))
    typer.echo(
        recovery_text(
            language,
            f"Already present and identical: {len(result['already_present'])}",
            f"已存在且内容相同：{len(result['already_present'])}",
        )
    )
    typer.echo(recovery_text(language, f"Conflicts: {len(result['conflicts'])}", f"冲突：{len(result['conflicts'])}"))
    for path in result["conflicts"][:5]:
        typer.echo(recovery_text(language, f"- changed target kept: {path}", f"- 保留已变化的目标：{path}"))
    if state == "restore_preview":
        command = str(_recovery_action(result, "apply_recovery_restore").get("command") or "")
        command = localized_recovery_command(command, language=language)
        typer.echo(
            recovery_text(
                language,
                f"Apply only after reviewing this private exact-path restore: {command}",
                f"只有审查这次私有精确路径恢复后才能应用：{command}",
            )
        )
    elif state == "no_restore_needed":
        typer.echo(
            recovery_text(
                language,
                "No restore is needed; every archived file is already present and identical. No files were changed.",
                "无需恢复；归档中的每个文件都已存在且内容相同。没有文件被改动。",
            )
        )
        doctor = str(_recovery_action(result, "confirm_readiness_if_needed").get("command") or "")
        doctor = localized_recovery_command(doctor, language=language)
        typer.echo(recovery_text(language, f"Next if readiness still needs confirmation: {doctor}", f"如果仍需确认就绪，下一步：{doctor}"))
    elif state == "restore_complete":
        typer.echo(recovery_text(language, f"Restored: {len(result['restored'])}", f"已恢复：{len(result['restored'])}"))
        doctor = str(_recovery_action(result, "confirm_readiness").get("command") or "")
        doctor = localized_recovery_command(doctor, language=language)
        typer.echo(recovery_text(language, f"Next: {doctor}", f"下一步：{doctor}"))
    else:
        typer.echo(
            recovery_text(
                language,
                "No files were changed. Move or remove conflicting targets intentionally, then preview again.",
                "没有文件被改动。请有意识地移动或删除冲突目标，然后重新预览。",
            )
        )
        retry = str(_recovery_action(result, "retry_restore_preview").get("command") or "")
        retry = localized_recovery_command(retry, language=language)
        typer.echo(recovery_text(language, f"Retry preview after resolving conflicts: {retry}", f"解决冲突后重试预览：{retry}"))


def _recovery_action(payload: dict, kind: str) -> dict:
    return next(
        (
            item
            for item in list(payload.get("next_actions") or [])
            if isinstance(item, dict) and str(item.get("kind") or "") == kind
        ),
        {},
    )


def _normalize_recovery_language(language: str, *, workdir: Path | None, json_output: bool) -> str:
    try:
        return normalize_fit_guidance_language(language)
    except ValueError as exc:
        if json_output:
            handle_error(ValueError(f"invalid --language: {exc}"), json_output=True, recovery_workdir=workdir)
            return "en"
        typer.echo(f"invalid --language: {exc}", err=True)
        raise typer.Exit(code=2) from exc


def recovery_help_epilog() -> str:
    return rewrite_loopora_help_commands(RECOVERY_HELP_EPILOG)
