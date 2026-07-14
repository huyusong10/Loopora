from __future__ import annotations

from collections.abc import Mapping
import shlex

from loopora import fit_guidance_web_route as _fit_web_route
from loopora.agent_adapter_command_prefix import DEFAULT_LOOPORA_CLI_ENTRY, rewrite_loopora_command_entry
from loopora.agent_native_adapter_identity import AGENT_ADAPTER_KINDS
from loopora.first_use_same_agent_setup import first_use_same_agent_setup_action
from loopora.first_use_web_guidance import WEB_CREATION_CHOICE_LABEL
from loopora.fit_review_guidance import (
    _fit_direct_decision_completion_command,
    _task_fit_review_needs_direct_decision_input,
    _task_fit_review_prefers_direct,
    _task_fit_review_ready_for_setup,
)

FIT_WORKDIR_PLACEHOLDER = _fit_web_route.FIT_WORKDIR_PLACEHOLDER
FIT_WORKDIR_ARG = _fit_web_route.FIT_WORKDIR_ARG
FIT_WEB_HOST = _fit_web_route.FIT_WEB_HOST
FIT_WEB_PORT = _fit_web_route.FIT_WEB_PORT
FIT_COMMAND_FIELD_KEYS = ("command", "command_template")
FIT_WEB_CREATION_COMMAND = f"loopora serve --open --workdir {FIT_WORKDIR_ARG} --host {FIT_WEB_HOST} --port {FIT_WEB_PORT}"
FIT_SUPPORT_COMMAND = f"loopora support --workdir {FIT_WORKDIR_ARG}"
FIT_AGENT_ADAPTER_CHOICES = AGENT_ADAPTER_KINDS
_fit_command_with_web_target = _fit_web_route.fit_command_with_web_target
_fit_default_web_route_context = _fit_web_route.fit_default_web_route_context
_fit_web_route_action = _fit_web_route.fit_web_route_action
_fit_web_route_context = _fit_web_route.fit_web_route_context

FIT_NEXT_ACTIONS = [
    {
        "kind": "open_web_creation_choices",
        "command": FIT_WEB_CREATION_COMMAND,
        "note": (
            f"outside an Agent session, choose {WEB_CREATION_CHOICE_LABEL} first; continue Web/import/manual work in Web "
            "after READY review; choose same-Agent setup only from the current Agent host"
        ),
    },
    {
        "kind": "install_agent_entry",
        "command": f"loopora init current --workdir {FIT_WORKDIR_ARG}",
        "selection_required": True,
        "note": "Detect the current Agent host first; choose codex, claude, or opencode only if detection is unavailable or ambiguous.",
        "adapter_choices": [
            {"adapter": adapter, "command": f"loopora init {adapter} --workdir {FIT_WORKDIR_ARG}"}
            for adapter in FIT_AGENT_ADAPTER_CHOICES
        ],
    },
    {
        "kind": "confirm_readiness",
        "command": f"loopora doctor --workdir {FIT_WORKDIR_ARG}",
        "after_action": "install_agent_entry",
        "note": "After installing the matching same-Agent project entry, confirm readiness before /loopora-plan.",
    },
    {
        "kind": "return_to_agent",
        "command": "/loopora-plan",
        "note": (
            "same Agent session: bring the Loopora fit reason, task goal, fake-done risk, required evidence, "
            "judgment tradeoffs, and optional direct-path context"
        ),
    },
    {
        "kind": "run_after_review",
        "command": "/loopora-run",
        "note": "run only after the Loop preview matches the task judgment",
    },
    {
        "kind": "support",
        "command": FIT_SUPPORT_COMMAND,
    },
]
FIT_DIRECT_PATH_NEXT_ACTIONS = [
    {
        "kind": "use_direct_agent_or_hard_checks",
        "note": (
            "if the review shows no strong-fit signal, do not install same-Agent project entries; "
            "use the direct Agent, /goal, hard checks, or the project process that can fully judge this task"
        ),
    },
]
FIT_NEXT_ACTION_NOTES_ZH = {
    "return_to_agent": "同一 Agent 会话：带上 Loopora 适配理由、任务目标、伪完成风险、必需证据、判断取舍和可选直接路径上下文",
    "open_web_creation_choices": (
        "不在 Agent 会话中时，先选择适用性判断/Web 选择；READY 审查后 Web/导入/手动工作继续在 Web 中进行，"
        "只有当前已经在 Agent 宿主中时才选择同一 Agent 设置"
    ),
    "install_agent_entry": "先检测当前 Agent 宿主；只有检测不可用或存在歧义时，才明确选择 codex、claude 或 opencode",
    "confirm_readiness": "安装匹配的同一 Agent 项目入口后，在 /loopora-plan 前确认就绪",
    "choose_workdir": "请先进入目标项目目录，再运行此命令获取路线命令。",
    "run_after_review": "仅在 Loop 预览符合任务判断后运行",
    "support": "使用/设置帮助",
    "continue_if_strong_fit": "只有补全后的审查仍显示 Loopora 很适合时才继续",
    "complete_direct_decision": "补齐直接路径理由后，才能记录不用 Loopora 的决定",
    "record_direct_decision": "如果审查显示不需要 Loopora，用直接路径理由记录这个停止决定",
    "fill_review_inputs": "设置前先补齐缺失的判断输入",
    "use_direct_agent_or_hard_checks": (
        "如果审查没有强适配信号，不要安装同一 Agent 项目入口；"
        "改用可完整裁决该任务的直接 Agent、/goal、硬性检查或项目流程"
    ),
}


def _localized_next_action(action: dict[str, object], *, language: str) -> dict[str, object]:
    localized = dict(action)
    if language == "zh":
        kind = str(localized.get("kind") or "").strip()
        if kind in FIT_NEXT_ACTION_NOTES_ZH:
            localized["note"] = FIT_NEXT_ACTION_NOTES_ZH[kind]
    return localized


def _localized_fit_next_actions(
    *,
    language: str,
    cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY,
    workdir_arg: str = FIT_WORKDIR_ARG,
    web_route: Mapping[str, object] | None = None,
    current_agent_host: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    for action in FIT_NEXT_ACTIONS:
        localized = _localized_next_action(action, language=language)
        if str(localized.get("kind") or "") == "open_web_creation_choices":
            localized = _fit_web_route_action(
                localized,
                workdir_arg=workdir_arg,
                cli_entry=cli_entry,
                language=language,
                web_route=web_route,
            )
            actions.append(localized)
            continue
        if str(localized.get("kind") or "") == "install_agent_entry":
            actions.append(
                first_use_same_agent_setup_action(
                    workdir_arg=workdir_arg,
                    language=language,
                    cli_entry=cli_entry,
                    current_agent_host=current_agent_host,
                )
            )
            continue
        command = str(localized.get("command") or "").strip()
        if command:
            kind = str(localized.get("kind") or "").strip()
            if kind == "support" and language != "en":
                command = command.replace(
                    "loopora support",
                    f"loopora support --language {shlex.quote(language)}",
                    1,
                )
            elif kind == "confirm_readiness" and language != "en":
                command = f"{command} --language {shlex.quote(language)}"
            command = _fit_command_with_web_target(
                command,
                kind=kind,
                web_route=web_route,
            )
            command = command.replace(FIT_WORKDIR_ARG, workdir_arg)
            localized["command"] = rewrite_loopora_command_entry(command, cli_entry=cli_entry)
        actions.append(localized)
    return actions


def _direct_path_record_decision_action(
    review_inputs: Mapping[str, object] | None,
    *,
    language: str,
    cli_entry: str,
    workdir: str = "",
) -> dict[str, object]:
    inputs = {"task": str((review_inputs or {}).get("task") or "").strip(), "direct_path_check": ""}
    return {
        "kind": "record_direct_decision",
        "command_template": _fit_direct_decision_completion_command(
            inputs,
            language=language,
            cli_entry=cli_entry,
            workdir=workdir,
        ),
        "command_ready": False,
        "command_blockers": ["direct_decision_input_required"],
        "note": "record this stop decision with a direct-path reason before setup",
        "local_only": True,
    }


def _localized_direct_path_next_actions(
    *,
    language: str,
    cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY,
    workdir: str = "",
    review_inputs: Mapping[str, object] | None = None,
    include_record_action: bool = True,
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    if include_record_action:
        actions.append(
            _direct_path_record_decision_action(
                review_inputs,
                language=language,
                cli_entry=cli_entry,
                workdir=workdir,
            )
        )
    actions.extend(dict(action) for action in FIT_DIRECT_PATH_NEXT_ACTIONS)
    return [_localized_next_action(action, language=language) for action in actions]


def _next_actions_for_task_fit_review(
    task_review: dict[str, object],
    *,
    language: str,
    cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY,
) -> list[dict[str, object]]:
    if _task_fit_review_prefers_direct(task_review):
        return _localized_direct_path_next_actions(language=language, include_record_action=False)
    if _task_fit_review_needs_direct_decision_input(task_review):
        completion_command = str(task_review.get("review_completion_command") or "").strip()
        actions = [
            {
                "kind": "complete_direct_decision",
                "command_template": completion_command,
                "command_ready": False,
                "command_blockers": ["direct_decision_input_required"],
                "note": "add a direct-path reason before recording that Loopora is not needed",
            }
        ]
        return [_localized_next_action(action, language=language) for action in actions]
    if _task_fit_review_ready_for_setup(task_review):
        return _localized_fit_next_actions(language=language, cli_entry=cli_entry)

    completion_command = str(task_review.get("review_completion_command") or "").strip()
    actions: list[dict[str, object]] = []
    if completion_command:
        actions.append(
            {
                "kind": "complete_review_inputs",
                "command_template": completion_command,
                "command_ready": False,
                "command_blockers": ["review_inputs_required"],
            }
        )
    else:
        actions.append({"kind": "fill_review_inputs", "note": "fill the missing review inputs before setup"})
    actions.append(
        {
            "kind": "continue_if_strong_fit",
            "command_ready": False,
            "command_blockers": ["review_inputs_required"],
            "note": "continue only if the completed review still shows Loopora is a strong fit",
        }
    )
    return [_localized_next_action(action, language=language) for action in actions]
