from __future__ import annotations

import shlex

import typer

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_recovery_archive_guidance import copyable_recovery_archive_command, recovery_archive_action
from loopora.cli_recovery_language import localized_recovery_command, recovery_text

DEV_RESET_SUMMARY_SCHEMA_VERSION = 5


def dev_reset_json_payload(result: dict) -> dict:
    planned = [str(item) for item in list(result.get("planned") or []) if str(item).strip()]
    removed = [str(item) for item in list(result.get("removed") or []) if str(item).strip()]
    skipped = [str(item) for item in list(result.get("skipped") or []) if str(item).strip()]
    dry_run = result.get("dry_run") is not False
    scope = str(result.get("scope") or "all").strip() or "all"
    scope_description = dev_reset_scope_description(scope)
    recovery_archive_command = _dev_reset_recovery_archive_command(result, planned=planned, dry_run=dry_run)
    next_actions = _dev_reset_next_actions(
        result,
        planned=planned,
        removed=removed,
        dry_run=dry_run,
        scope=scope,
    )
    payload = {
        "dev_reset_summary": {
            "schema_version": DEV_RESET_SUMMARY_SCHEMA_VERSION,
            "workdir": str(result.get("workdir") or "").strip(),
            "workdir_state": _dev_reset_workdir_state_status(result),
            "scope": scope,
            "dry_run": dry_run,
            "planned_count": len(planned),
            "removed_count": len(removed),
            "skipped_count": len(skipped),
            "state": "reset_preview" if dry_run else "reset_complete",
            "scope_description": scope_description,
            "recovery_archive_recommended": bool(recovery_archive_command),
            "next_action_kinds": [action["kind"] for action in next_actions],
        },
        **result,
        "scope_description": scope_description,
        "recovery_archive_command": recovery_archive_command,
        "next_actions": next_actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="dev_reset_summary")


def print_dev_reset_result(result: dict, *, language: str = "en") -> None:
    planned = [str(item) for item in list(result.get("planned") or []) if str(item).strip()]
    removed = [str(item) for item in list(result.get("removed") or []) if str(item).strip()]
    skipped = [str(item) for item in list(result.get("skipped") or []) if str(item).strip()]
    dry_run = result.get("dry_run") is not False
    scope = str(result.get("scope") or "all").strip() or "all"
    heading = recovery_text(
        language,
        "Loopora v3 development reset preview" if dry_run else "Loopora v3 development reset complete",
        "Loopora v3 开发状态重置预览" if dry_run else "Loopora v3 开发状态重置完成",
    )
    typer.echo(heading)
    typer.echo(recovery_text(language, f"workdir: {result.get('workdir')}", f"目标项目：{result.get('workdir')}"))
    if not _dev_reset_workdir_ready(result):
        state = _dev_reset_workdir_state_status(result)
        state_text = {"missing": "不存在", "not_directory": "不是目录", "uninspectable": "无法检查"}.get(state, state)
        typer.echo(recovery_text(language, f"workdir_state: {state}", f"项目目录状态：{state_text}"))
    typer.echo(recovery_text(language, f"scope: {scope}", f"重置范围：{scope}"))
    typer.echo(
        recovery_text(
            language,
            f"scope_boundary: {dev_reset_scope_description(scope)}",
            f"范围边界：{_dev_reset_scope_description_zh(scope)}",
        )
    )
    typer.echo(recovery_text(language, f"dry_run: {str(dry_run).lower()}", f"仅预览：{'是' if dry_run else '否'}"))
    typer.echo(recovery_text(language, f"planned_count: {len(planned)}", f"计划删除：{len(planned)}"))
    typer.echo(recovery_text(language, f"removed_count: {len(removed)}", f"已删除：{len(removed)}"))
    if planned:
        typer.echo(recovery_text(language, "planned:", "计划删除的 Loopora 状态："))
        for item in planned:
            typer.echo(f"- {item}")
    if removed:
        typer.echo(recovery_text(language, "removed:", "已删除："))
        for item in removed:
            typer.echo(f"- {item}")
    if skipped:
        typer.echo(recovery_text(language, "skipped_non_loopora_files:", "已跳过非 Loopora 文件："))
        for item in skipped:
            typer.echo(f"- {item}")
    recovery_archive_command = _dev_reset_recovery_archive_command(result, planned=planned, dry_run=dry_run)
    if recovery_archive_command:
        recovery_archive_command = localized_recovery_command(recovery_archive_command, language=language)
        typer.echo(
            recovery_text(
                language,
                f"recovery_archive_before_reset: {recovery_archive_command}",
                f"重置前私有恢复归档：{recovery_archive_command}",
            )
        )
    typer.echo(
        _dev_reset_next_line(
            result,
            planned=planned,
            removed=removed,
            dry_run=dry_run,
            scope=scope,
            language=language,
        )
    )


def dev_reset_scope_description(scope: str) -> str:
    if scope == "app":
        return "app scope resets only local App database files; project .loopora state and managed Agent entries are left alone"
    return "all scope resets Loopora-owned App database files, project .loopora state, and managed Agent entries; unowned host files are skipped"


def _dev_reset_scope_description_zh(scope: str) -> str:
    if scope == "app":
        return "app 只重置本地 App 数据库文件；项目 .loopora 状态和托管 Agent 入口保持不变"
    return "all 会重置 Loopora 所有的 App 数据库文件、项目 .loopora 状态和托管 Agent 入口；不属于 Loopora 的宿主文件会被跳过"


def _dev_reset_next_line(  # noqa: PLR0913 - reset summary rendering keeps the stable plan inputs explicit.
    result: dict,
    *,
    planned: list[str],
    removed: list[str],
    dry_run: bool,
    scope: str,
    language: str = "en",
) -> str:
    if dry_run:
        target = "local App database files" if scope == "app" else "Loopora-owned development state"
        if planned:
            return _dev_reset_preview_apply_next_line(result, target=target, scope=scope, language=language)
        suffix = _dev_reset_choose_project_suffix(result, language=language)
        return recovery_text(
            language,
            f"next: nothing to delete; no --yes reset is needed for {target}{suffix}",
            f"下一步：没有需要删除的状态；无需为{_dev_reset_target_zh(scope)}运行 --yes{suffix}",
        )
    if not _dev_reset_workdir_ready(result):
        doctor_template = localized_recovery_command(_dev_reset_doctor_command_template(), language=language)
        return (
            recovery_text(
                language,
                f"next: choose an existing project, then rerun {doctor_template} "
                "to confirm local readiness before opening Web or running /loopora-plan",
                f"下一步：选择现有项目，再重跑 {doctor_template}；打开 Web 或运行 /loopora-plan 前先确认本地就绪。",
            )
        )
    doctor_command = localized_recovery_command(_dev_reset_doctor_command(result), language=language)
    if removed:
        return recovery_text(
            language,
            f"next: rerun {doctor_command} to confirm local readiness before opening Web or running /loopora-plan",
            f"下一步：重跑 {doctor_command}；打开 Web 或运行 /loopora-plan 前先确认本地就绪。",
        )
    return recovery_text(
        language,
        f"next: no files were removed; rerun {doctor_command} if readiness still looks wrong",
        f"下一步：没有文件被删除；如果就绪状态仍不正确，请重跑 {doctor_command}。",
    )


def _dev_reset_preview_apply_next_line(result: dict, *, target: str, scope: str, language: str) -> str:
    apply_command = localized_recovery_command(_dev_reset_apply_command(result, scope=scope), language=language)
    if _dev_reset_workdir_ready(result):
        doctor_command = localized_recovery_command(_dev_reset_doctor_command(result), language=language)
        recovery_command = localized_recovery_command(
            copyable_recovery_archive_command(str(result.get("workdir") or "")),
            language=language,
        )
        return recovery_text(
            language,
            f"next: review planned {target}; create and inspect the private archive first: {recovery_command}; "
            f"apply only after it succeeds: {apply_command}; then confirm readiness: {doctor_command}",
            f"下一步：审查计划删除的{_dev_reset_target_zh(scope)}；先创建并检查私有归档：{recovery_command}；"
            f"检查成功后才能应用：{apply_command}；然后确认就绪：{doctor_command}",
        )
    doctor_template = localized_recovery_command(_dev_reset_doctor_command_template(), language=language)
    return recovery_text(
        language,
        f"next: review planned {target}; apply only if acceptable: {apply_command}; "
        f"then choose an existing project and confirm readiness: {doctor_template}",
        f"下一步：审查计划删除的{_dev_reset_target_zh(scope)}；确认可接受后才能应用：{apply_command}；"
        f"然后选择现有项目并确认就绪：{doctor_template}",
    )


def _dev_reset_choose_project_suffix(result: dict, *, language: str = "en") -> str:
    if _dev_reset_workdir_ready(result):
        return ""
    doctor_template = localized_recovery_command(_dev_reset_doctor_command_template(), language=language)
    return recovery_text(
        language,
        f"; choose an existing project and rerun {doctor_template} if readiness still looks wrong",
        f"；如果就绪状态仍不正确，请选择现有项目并重跑 {doctor_template}",
    )


def _dev_reset_target_zh(scope: str) -> str:
    return "本地 App 数据库文件" if scope == "app" else "Loopora 所有的开发状态"


def _dev_reset_doctor_command(result: dict) -> str:
    workdir = str(result.get("workdir") or ".").strip() or "."
    return copyable_loopora_command(f"loopora doctor --workdir {shlex.quote(workdir)}")


def _dev_reset_doctor_command_template() -> str:
    return copyable_loopora_command("loopora doctor --workdir <project>")


def _dev_reset_apply_command(result: dict, *, scope: str) -> str:
    workdir = str(result.get("workdir") or ".").strip() or "."
    return copyable_loopora_command(
        f"loopora dev reset --scope {shlex.quote(scope)} --workdir {shlex.quote(workdir)} --yes"
    )


def _dev_reset_next_actions(
    result: dict,
    *,
    planned: list[str],
    removed: list[str],
    dry_run: bool,
    scope: str,
) -> list[dict[str, object]]:
    if dry_run and planned:
        actions: list[dict[str, object]] = [
            {
                "kind": "review_reset_scope",
                "scope": scope,
                "scope_description": dev_reset_scope_description(scope),
            },
        ]
        recovery_command = _dev_reset_recovery_archive_command(result, planned=planned, dry_run=dry_run)
        apply_after = "review_reset_scope"
        if recovery_command:
            actions.append(recovery_archive_action(recovery_command, after_action="review_reset_scope"))
            apply_after = "create_recovery_archive"
        actions.append(
            {
                "kind": "apply_reset_after_review",
                "command": _dev_reset_apply_command(result, scope=scope),
                "destructive": True,
                "after_action": apply_after,
            },
        )
        if _dev_reset_workdir_ready(result):
            actions.append(
                {
                    "kind": "confirm_readiness_after_reset",
                    "command": _dev_reset_doctor_command(result),
                    "after_action": "apply_reset_after_review",
                }
            )
        else:
            actions.append(_dev_reset_choose_project_action(after_action="apply_reset_after_review"))
        return actions
    if dry_run:
        actions = [{"kind": "no_reset_needed"}]
        if not _dev_reset_workdir_ready(result):
            actions.append(_dev_reset_choose_project_action())
        return actions
    if not _dev_reset_workdir_ready(result):
        return [_dev_reset_choose_project_action()]
    command = _dev_reset_doctor_command(result)
    kind = "confirm_readiness" if removed else "confirm_readiness_if_needed"
    return [{"kind": kind, "command": command}]


def _dev_reset_choose_project_action(after_action: str = "") -> dict[str, object]:
    action: dict[str, object] = {
        "kind": "choose_project_for_readiness",
        "command_template": _dev_reset_doctor_command_template(),
    }
    if after_action:
        action["after_action"] = after_action
    return action


def _dev_reset_recovery_archive_command(result: dict, *, planned: list[str], dry_run: bool) -> str:
    if not dry_run or not planned or result.get("app_database_present") is not True:
        return ""
    if not _dev_reset_workdir_ready(result):
        return ""
    return copyable_recovery_archive_command(str(result.get("workdir") or ""))


def _dev_reset_workdir_ready(result: dict) -> bool:
    return _dev_reset_workdir_state_status(result) == "ready"


def _dev_reset_workdir_state_status(result: dict) -> str:
    state = result.get("workdir_state")
    if isinstance(state, dict):
        return str(state.get("status") or "ready").strip() or "ready"
    return "ready"
