from __future__ import annotations

from collections.abc import Mapping
import shlex

from loopora import fit_guidance_web_route as _fit_web_route
from loopora.agent_adapter_command_prefix import rewrite_loopora_command_entry
from loopora.fit_review_guidance import FIT_REVIEW_SETUP_GATE, _fit_supplied_review_option_args

FIT_WORKDIR_ARG = _fit_web_route.FIT_WORKDIR_ARG
_fit_command_with_web_target = _fit_web_route.fit_command_with_web_target


def _fit_workdir_arg(workdir_state: Mapping[str, object]) -> str:
    status = str(workdir_state.get("status") or "")
    if status in {"ready", "missing"}:
        return shlex.quote(str(workdir_state.get("workdir") or ""))
    return FIT_WORKDIR_ARG


def _fit_completion_workdir(workdir_state: Mapping[str, object]) -> str:
    if str(workdir_state.get("status") or "") in {"ready", "missing"}:
        return str(workdir_state.get("workdir") or "")
    return ""


def _fit_workdir_recovery_actions(
    workdir_state: Mapping[str, object],
    *,
    cli_entry: str,
    language: str,
    review_inputs: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    status = str(workdir_state.get("status") or "")
    if status == "ready":
        return []
    if not workdir_state:
        return [
            _fit_choose_workdir_action(
                workdir_state,
                cli_entry=cli_entry,
                language=language,
                review_inputs=review_inputs,
            ),
            _fit_generic_support_action(cli_entry=cli_entry, language=language),
        ]
    actions: list[dict[str, object]] = []
    commands = workdir_state.get("commands") if isinstance(workdir_state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "").strip()
    if create_command:
        actions.append({"kind": "create_workdir", "command": create_command})
        workdir = str(workdir_state.get("workdir") or "")
        actions.append(
            {
                "kind": "confirm_readiness",
                "command": rewrite_loopora_command_entry(
                    f"loopora doctor --workdir {shlex.quote(workdir)}",
                    cli_entry=cli_entry,
                ),
            }
        )
    else:
        actions.append(
            _fit_choose_workdir_action(
                workdir_state,
                cli_entry=cli_entry,
                language=language,
                review_inputs=review_inputs,
            )
        )
    actions.append(_fit_support_recovery_action(workdir_state, cli_entry=cli_entry, language=language))
    return actions


def _fit_incomplete_review_recovery_actions(
    recovery_actions: list[dict[str, object]],
    *,
    workdir_state: Mapping[str, object],
    cli_entry: str,
    language: str,
    web_route: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    if str(workdir_state.get("status") or "") != "ready":
        return recovery_actions
    return [
        *recovery_actions,
        _fit_support_recovery_action(workdir_state, cli_entry=cli_entry, language=language, web_route=web_route),
    ]


def _fit_read_only_support_actions(
    workdir_state: Mapping[str, object],
    *,
    cli_entry: str,
    language: str,
    web_route: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    if not workdir_state:
        return [_fit_generic_support_action(cli_entry=cli_entry, language=language)]
    return [_fit_support_recovery_action(workdir_state, cli_entry=cli_entry, language=language, web_route=web_route)]


def _fit_generic_support_action(*, cli_entry: str, language: str) -> dict[str, object]:
    language_arg = "" if language == "en" else f" --language {shlex.quote(language)}"
    return {
        "kind": "support",
        "command": rewrite_loopora_command_entry(f"loopora support{language_arg}", cli_entry=cli_entry),
        "command_ready": True,
        "command_blockers": [],
        "setup_independent": True,
        "local_only": True,
    }


def _fit_choose_workdir_action(
    workdir_state: Mapping[str, object],
    *,
    cli_entry: str,
    language: str,
    review_inputs: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "kind": "choose_workdir",
        "command": rewrite_loopora_command_entry(
            _fit_target_project_command(language, review_inputs=review_inputs),
            cli_entry=cli_entry,
        ),
        "note": _fit_workdir_choice_note(workdir_state, language=language),
        "command_ready": True,
        "command_blockers": [],
    }


def _fit_target_project_command(language: str, *, review_inputs: Mapping[str, object] | None = None) -> str:
    parts = ["loopora", "fit"]
    if language != "en":
        parts.extend(["--language", shlex.quote(language)])
    parts.extend(["--workdir", '"$PWD"'])
    parts.extend(_fit_supplied_review_option_args(review_inputs or {}))
    return " ".join(parts)


def _fit_support_recovery_action(
    workdir_state: Mapping[str, object],
    *,
    cli_entry: str,
    language: str,
    web_route: Mapping[str, object] | None = None,
) -> dict[str, object]:
    workdir = str(workdir_state.get("workdir") or "").strip()
    workdir_arg = shlex.quote(workdir) if workdir else '"$PWD"'
    language_arg = "" if language == "en" else f" --language {shlex.quote(language)}"
    command = _fit_command_with_web_target(
        f"loopora support{language_arg} --workdir {workdir_arg}",
        kind="support",
        web_route=web_route,
    )
    return {
        "kind": "support",
        "command": rewrite_loopora_command_entry(command, cli_entry=cli_entry),
        "command_ready": True,
        "command_blockers": [],
        "setup_independent": True,
        "local_only": True,
    }


def _fit_workdir_choice_note(workdir_state: Mapping[str, object], *, language: str) -> str:
    status = str(workdir_state.get("status") or "")
    if language == "zh":
        return {
            "required": "请先进入目标项目目录，再运行此命令获取路线命令。",
            "unavailable": "目标项目目录暂时无法检查；请改用可读取的项目目录。",
            "not_directory": "目标项目路径不是目录；请改用项目目录。",
        }.get(status or "required", "请先选择可用的目标项目目录。")
    if not workdir_state or status == "required":
        return "Run from the target project directory before copying route commands."
    return str(workdir_state.get("summary") or "Choose a usable target project directory.").strip()


def _fit_setup_command_blockers(
    task_review: Mapping[str, object],
    *,
    route_commands_are_placeholders: bool = True,
    workdir_state: Mapping[str, object] | None = None,
) -> list[str]:
    blockers: list[str] = []
    summary = task_review.get("task_fit_review_summary") if isinstance(task_review, Mapping) else {}
    if task_review and isinstance(summary, Mapping) and not bool(summary.get("setup_allowed")):
        setup_blocker = str(summary.get("setup_blocker") or "")
        if setup_blocker in {
            FIT_REVIEW_SETUP_GATE["direct_blocker"],
            FIT_REVIEW_SETUP_GATE["direct_input_blocker"],
        }:
            blockers.append(setup_blocker)
            return blockers
        blockers.append("review_inputs_required")
    workdir_status = str((workdir_state or {}).get("status") or "")
    if route_commands_are_placeholders:
        blockers.append("target_project_required")
    elif workdir_status and workdir_status != "ready":
        blockers.append("target_project_unready")
    return blockers


def _merge_review_and_workdir_recovery_actions(
    review_actions: object,
    workdir_actions: list[dict[str, object]],
) -> list[dict[str, object]]:
    actions = [action for action in list(review_actions or []) if isinstance(action, dict)]
    if not workdir_actions:
        return actions
    continuation = [action for action in actions if str(action.get("kind") or "") == "continue_if_strong_fit"]
    recovery = [action for action in actions if str(action.get("kind") or "") != "continue_if_strong_fit"]
    existing_kinds = {str(action.get("kind") or "") for action in recovery}
    recovery.extend(action for action in workdir_actions if str(action.get("kind") or "") not in existing_kinds)
    return [*recovery, *continuation]
