from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from loopora.agent_adapter_command_prefix import rewrite_loopora_command_entry
from loopora.cli_recovery_archive_guidance import recovery_archive_action
from loopora.cli_recovery_language import localized_recovery_command
from loopora.app_state_readiness import app_state_report, app_state_web_readiness_blockers
from loopora.branding import APP_HOME_ENV

WEB_ROUTE_BLOCKED_PREFLIGHT_STATUSES = {"bind_unavailable", "default_port_in_use_no_suggestion"}


def first_use_web_creation_choice_blockers(projected: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    if str(projected.get("preflight_status") or "") in WEB_ROUTE_BLOCKED_PREFLIGHT_STATUSES:
        blockers.append("web_port_unavailable")
    blockers.extend(first_use_readiness_blocker_kinds(projected))
    return blockers


def first_use_readiness_blocker_kinds(source: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    for blocker in list(source.get("readiness_blockers") or []):
        if not isinstance(blocker, Mapping):
            continue
        blocker_kind = str(blocker.get("kind") or "").strip()
        if blocker_kind:
            blockers.append(blocker_kind)
    return blockers


def first_use_app_state_readiness_blocker_kinds(source: Mapping[str, object]) -> list[str]:
    return [kind for kind in first_use_readiness_blocker_kinds(source) if kind == "app_state_not_ready"]


def first_use_web_readiness_blockers(
    workdir_state: Mapping[str, object],
    *,
    app_state_report_fn: Callable[..., Mapping[str, object]] | None = None,
    app_state_web_readiness_blockers_fn: Callable[[Mapping[str, object]], list[dict[str, str]]] | None = None,
) -> list[dict[str, str]]:
    if not workdir_state or str(workdir_state.get("status") or "") != "ready":
        return []
    workdir = str(workdir_state.get("workdir") or "").strip()
    if not workdir:
        return []
    report_fn = app_state_report if app_state_report_fn is None else app_state_report_fn
    blockers_fn = (
        app_state_web_readiness_blockers
        if app_state_web_readiness_blockers_fn is None
        else app_state_web_readiness_blockers_fn
    )
    return blockers_fn(report_fn(Path(workdir), commands={}))


def first_use_web_readiness_note(action: Mapping[str, object], *, language: str) -> str:
    for blocker in list(action.get("readiness_blockers") or []):
        if not isinstance(blocker, Mapping):
            continue
        if str(blocker.get("kind") or "") != "app_state_not_ready":
            continue
        recovery = str(blocker.get("recovery_action") or "").strip()
        status = str(blocker.get("status") or "").strip()
        if recovery == "use_matching_loopora_version_or_reset" or status == "future_version":
            return _readiness_text(
                language,
                "Local App/Web state was created by a newer Loopora version; use a matching or newer Loopora version, or review the reset recovery below before starting Web.",
                "本地 App/Web 状态来自较新的 Loopora 版本；启动 Web 前请使用匹配或更新的 Loopora 版本，或先审查下方 reset 恢复动作。",
            )
        if recovery == "inspect_or_reset_app_state" or status == "unreadable":
            return _readiness_text(
                language,
                "Local App/Web state cannot be read; inspect or review the reset recovery below before starting Web.",
                "本地 App/Web 状态无法读取；启动 Web 前请先检查，或审查下方 reset 恢复动作。",
            )
        return _readiness_text(
            language,
            "Local App/Web state needs attention; review the reset recovery or temporary Web preview below before starting Web.",
            "本地 App/Web 状态需要处理；启动 Web 前请先审查下方 reset 恢复动作或临时 Web 预览。",
        )
    return ""


def first_use_web_recovery_actions(
    action: Mapping[str, object],
    *,
    workdir_arg: str,
    cli_entry: str,
    language: str,
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    for blocker in list(action.get("readiness_blockers") or []):
        if not isinstance(blocker, Mapping) or str(blocker.get("kind") or "") != "app_state_not_ready":
            continue
        recovery_kind = _first_use_app_state_recovery_kind(blocker)
        reset_command = rewrite_loopora_command_entry(
            f"loopora dev reset --scope app --workdir {workdir_arg}",
            cli_entry=cli_entry,
        )
        recovery_command = rewrite_loopora_command_entry(
            f"loopora recovery create --workdir {workdir_arg}",
            cli_entry=cli_entry,
        )
        reset_command = localized_recovery_command(reset_command, language=language)
        recovery_command = localized_recovery_command(recovery_command, language=language)
        archive_action = recovery_archive_action(recovery_command)
        archive_action["note"] = _readiness_text(
            language,
            "Create and inspect a private exact-path archive before resetting useful local history.",
            "重置有用的本地历史前，先创建并检查私有精确路径恢复归档。",
        )
        actions.append(archive_action)
        actions.append(
            {
                "kind": recovery_kind,
                "command": reset_command,
                "command_ready": True,
                "command_blockers": [],
                "note": _first_use_app_state_recovery_note(blocker, language=language),
                "after_action": "create_recovery_archive",
                "scope": "app",
                "local_only": True,
            }
        )
        temporary_action = _first_use_temporary_app_home_action(action, language=language)
        if temporary_action:
            actions.append(temporary_action)
    return actions


def _first_use_app_state_recovery_kind(blocker: Mapping[str, object]) -> str:
    recovery = str(blocker.get("recovery_action") or "").strip()
    if recovery in {"preview_app_database_reset", "use_matching_loopora_version_or_reset", "inspect_or_reset_app_state"}:
        return recovery
    return "inspect_app_state"


def _first_use_app_state_recovery_note(blocker: Mapping[str, object], *, language: str) -> str:
    recovery = str(blocker.get("recovery_action") or "").strip()
    status = str(blocker.get("status") or "").strip()
    if recovery == "use_matching_loopora_version_or_reset" or status == "future_version":
        return _readiness_text(
            language,
            "Use a matching or newer Loopora version when available; if choosing reset, review the app-scope reset before Web start.",
            "优先使用匹配或更新的 Loopora 版本；若选择 reset，启动 Web 前先审查 app 级 reset 范围。",
        )
    if recovery == "inspect_or_reset_app_state" or status == "unreadable":
        return _readiness_text(
            language,
            "Inspect local App state first; if choosing reset, review the app-scope reset before Web start.",
            "先检查本地 App 状态；若选择 reset，启动 Web 前先审查 app 级 reset 范围。",
        )
    return _readiness_text(
        language,
        "Review the local App database reset scope before starting Web; the preview does not delete project .loopora state or managed Agent entries.",
        "启动 Web 前先审查本地 App 数据库 reset 范围；预览不会删除项目 .loopora 状态或托管 Agent 入口。",
    )


def _first_use_temporary_app_home_action(action: Mapping[str, object], *, language: str) -> dict[str, object] | None:
    if str(action.get("preflight_status") or "") in WEB_ROUTE_BLOCKED_PREFLIGHT_STATUSES:
        return None
    command = str(action.get("command") or "").strip()
    if not command:
        return None
    return {
        "kind": "use_temporary_app_home",
        "command": f'{APP_HOME_ENV}="$(mktemp -d)" {command}',
        "command_ready": True,
        "command_blockers": [],
        "note": _readiness_text(
            language,
            "Uses a new empty App home for preview or troubleshooting; it does not delete, migrate, or repair the blocked App database.",
            "使用新的空 App home 进行预览或排障；不会删除、迁移或修复被阻止的 App 数据库。",
        ),
        "setup_independent": True,
        "local_only": True,
    }


def _readiness_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english
