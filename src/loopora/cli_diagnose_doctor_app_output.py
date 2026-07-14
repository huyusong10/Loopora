from __future__ import annotations

import typer

from loopora.cli_diagnose_doctor_language import doctor_text
from loopora.cli_recovery_language import localized_recovery_command
from loopora.cli_serve_language import localized_serve_command


def print_doctor_app_state(report: dict, *, language: str = "en") -> None:
    app_state = report.get("app_state") if isinstance(report.get("app_state"), dict) else {}
    if app_state:
        status = str(app_state.get("status") or "unknown")
        web_ready = app_state.get("web_ready") is True
        if language == "zh":
            typer.echo(f"App 状态：{_doctor_app_status_zh(status)}（{status}；Web 就绪：{'是' if web_ready else '否'}）")
        else:
            typer.echo(f"App state: {status} (Web ready: {'yes' if web_ready else 'no'})")
        if app_state.get("needs_attention"):
            summary = str(app_state.get("summary") or "").strip()
            if summary:
                localized_summary = _doctor_app_summary_zh(status) if language == "zh" else summary
                typer.echo(doctor_text(language, f"  note: {localized_summary}", f"  说明：{localized_summary}"))
            commands = app_state.get("commands") if isinstance(app_state.get("commands"), dict) else {}
            recovery_archive = str(commands.get("recovery_archive") or "").strip()
            if recovery_archive:
                recovery_archive = localized_recovery_command(recovery_archive, language=language)
                typer.echo(doctor_text(language, f"  recovery archive before reset: {recovery_archive}", f"  重置前私有恢复归档：{recovery_archive}"))
            preview_command = str(commands.get("preview_reset") or commands.get("reset") or "").strip()
            if preview_command:
                preview_command = localized_recovery_command(preview_command, language=language)
                typer.echo(doctor_text(language, f"  reset preview: {preview_command}", f"  重置预览：{preview_command}"))
                apply_command = str(commands.get("apply_reset") or "").strip()
                if apply_command:
                    apply_command = localized_recovery_command(apply_command, language=language)
                    typer.echo(doctor_text(language, f"  reset apply after review: {apply_command}", f"  审查后应用重置：{apply_command}"))
                else:
                    typer.echo(doctor_text(language, "  apply: rerun that command with --yes after reviewing the planned deletions", "  应用：审查计划删除项后，用 --yes 重跑该命令"))
            temporary_serve = str(commands.get("temporary_serve") or "").strip()
            if temporary_serve:
                temporary_serve = localized_serve_command(temporary_serve, language=language)
                typer.echo(doctor_text(language, f"  temporary Web preview: {temporary_serve}", f"  临时 Web 预览：{temporary_serve}"))
                typer.echo(
                    doctor_text(
                        language,
                        "  temporary Web note: uses a new empty App home for preview or troubleshooting; "
                        "it does not delete, migrate, or repair the blocked App database.",
                        "  临时 Web 说明：使用新的空 App Home 做预览或排障；不会删除、迁移或修复被阻止的 App 数据库。",
                    )
                )


def _doctor_app_status_zh(status: str) -> str:
    return {
        "not_initialized": "尚未初始化",
        "current": "当前版本",
        "current_shape_unversioned": "当前结构但未标版本",
        "development_reset_required": "需要开发重置",
        "future_version": "来自更新版本",
        "unreadable": "无法读取",
    }.get(status, "未知")


def _doctor_app_summary_zh(status: str) -> str:
    return {
        "development_reset_required": "现有本地 App 数据库不兼容；预览重置范围前，先创建私有恢复归档。",
        "future_version": "App 数据库来自更新的 Loopora；请使用匹配版本，或先归档再审查重置。",
        "unreadable": "无法读取 App 数据库；请先检查或恢复本地 App 状态。",
        "current_shape_unversioned": "数据库结构可用但缺少版本标记；正常启动会处理该标记。",
    }.get(status, "本地 App 状态需要处理。")
