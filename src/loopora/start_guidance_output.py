from __future__ import annotations

from collections.abc import Mapping
import shlex

from loopora.fit_review_guidance import FIT_FIRST_TASK_MESSAGE_STATUS
from loopora.start_guidance_action_output import _action_line
from loopora.start_guidance_actions import (
    _action_command,
    _action_command_template,
    _actions,
    _payload_language,
    _payload_needs_direct_decision_input,
    _payload_prefers_direct,
    _route_actions,
    _text,
)
from loopora.start_guidance_constants import START_WORKDIR_PLACEHOLDER
from loopora.start_guidance_route_output import blocked_setup_lines as _blocked_setup_lines
from loopora.start_guidance_route_output import route_lines as _route_lines


def start_guidance_lines(payload: Mapping[str, object]) -> list[str]:
    language = _payload_language(payload)
    setup_allowed = bool(payload.get("setup_allowed"))
    lines = [
        _text(language, "Loopora start", "Loopora 启动向导"),
        _text(
            language,
            "Purpose: choose the first safe route; this command does not install same-Agent project entries, start Web, or classify the task.",
            "作用：选择第一条安全路线；此命令不会安装同一 Agent 项目入口、启动 Web，也不会替你给任务分类。",
        ),
    ]
    workdir = str(payload.get("workdir") or "").strip()
    if workdir:
        lines.append(_text(language, f"Target project: {workdir}", f"目标项目：{workdir}"))
    elif bool(payload.get("target_project_required")) and str(payload.get("workdir_arg") or "") == shlex.quote(START_WORKDIR_PLACEHOLDER):
        lines.append(
            _text(
                language,
                "Target project: not supplied; rerun start from the target project before copying route commands.",
                "目标项目：尚未提供；请先从目标项目重跑 start，再复制路线命令。",
            )
        )
    lines.extend(_fit_review_lines(payload, language=language))
    if _payload_prefers_direct(payload):
        lines.extend(_direct_path_lines(payload, language=language))
        return lines
    if _payload_needs_direct_decision_input(payload):
        lines.extend(_direct_decision_input_lines(payload, language=language))
        return lines
    first_task_message_lines = _first_task_message_lines(payload, language=language)
    first_task_message_ready = str(payload.get("primary_first_task_message_status") or "") == FIT_FIRST_TASK_MESSAGE_STATUS["ready"]
    if first_task_message_ready:
        lines.extend(first_task_message_lines)
    lines.extend(_direct_path_lines(payload, language=language))
    if _fit_review_routes_pending(payload):
        lines.extend(_fit_review_pending_lines(payload, language=language))
        return lines
    if setup_allowed:
        heading = (
            _text(language, "Route shape after choosing a target project:", "选择目标项目后的路线形状:")
            if not bool(payload.get("setup_commands_ready"))
            else _text(language, "Route preview after completed fit review:", "补齐适配审查后的路线预览:")
            if bool(payload.get("fit_review_recommended_before_setup"))
            else _text(language, "Choose the route:", "选择路线:")
        )
        lines.extend(_route_lines(payload, language=language, heading=heading))
    else:
        lines.extend(_blocked_setup_lines(payload, language=language))
    if not first_task_message_ready:
        lines.extend(first_task_message_lines)
    return lines


def _fit_review_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    status = str(payload.get("task_review_status") or "")
    if status == FIT_FIRST_TASK_MESSAGE_STATUS["direct"]:
        return [
            _text(
                language,
                "Fit review: complete; direct Agent, /goal, hard checks, or the project process is enough.",
                "适配审查：已完成；直接 Agent、/goal、硬性检查或项目流程已经足够。",
            ),
            _text(language, "Setup gate: blocked because the review chose the direct path.", "设置门禁：已阻止，因为审查选择了直接路径。"),
        ]
    if status == FIT_FIRST_TASK_MESSAGE_STATUS["direct_input"]:
        return [
            _text(
                language,
                "Fit review: direct-path decision needs a direct-path reason before it can be recorded.",
                "适配审查：直接路径决策需要直接路径理由，之后才能记录。",
            ),
            _text(language, "Setup gate: blocked until that direct-path reason is supplied.", "设置门禁：补齐直接路径理由前保持阻止。"),
        ]
    if status == FIT_FIRST_TASK_MESSAGE_STATUS["preview"]:
        return [
            _text(language, "Fit review: incomplete; complete judgment inputs before setup.", "适配审查：未补齐；设置前先补齐判断输入。"),
            _text(language, "Setup gate: blocked until the completed review still shows a strong fit.", "设置门禁：补全审查且仍显示强适配前保持阻止。"),
        ]
    if status == FIT_FIRST_TASK_MESSAGE_STATUS["ready"]:
        return [
            _text(
                language,
                "Fit review: complete; continue only if you agree Loopora is still the right route.",
                "适配审查：已补齐；只有你确认 Loopora 仍是正确入口时才继续。",
            )
        ]
    fit_completion_template = _action_command_template(_actions(payload, "next_actions"), "complete_review_inputs")
    fit_command = fit_completion_template or _action_command(_route_actions(payload), "check_fit_first")
    lines = [
        _text(language, "Fit review: not supplied.", "适配审查：尚未提供。"),
    ]
    if bool(payload.get("setup_commands_ready")) and bool(payload.get("fit_review_recommended_before_setup")):
        if fit_completion_template:
            lines.extend(
                [
                    _text(
                        language,
                        "Recommended next action: complete the fit review before setup:",
                        "推荐下一步：设置前先补齐适配审查：",
                    ),
                    fit_completion_template,
                ]
            )
        else:
            lines.append(
                _text(
                    language,
                    f"Recommended next action: record the fit review before setup: {fit_command}",
                    f"推荐下一步：设置前先记录适配审查：{fit_command}",
                )
            )
    else:
        lines.append(_text(language, f"If uncertain, decide fit before setup: {fit_command}", f"如果不确定，设置前先判断适配性：{fit_command}"))
    return lines


def _fit_review_routes_pending(payload: Mapping[str, object]) -> bool:
    return str(payload.get("task_review_status") or "") in {
        FIT_FIRST_TASK_MESSAGE_STATUS["example"],
        FIT_FIRST_TASK_MESSAGE_STATUS["preview"],
    }


def _fit_review_pending_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    status = str(payload.get("task_review_status") or "")
    visible_kinds = {"choose_workdir", "support"} if status == FIT_FIRST_TASK_MESSAGE_STATUS["example"] else {"complete_review_inputs", "support"}
    actions = [
        *_actions(payload, "review_actions"),
        *[action for action in _actions(payload, "next_actions") if str(action.get("kind") or "") in visible_kinds],
    ]
    lines: list[str] = []
    if actions:
        lines.append(_text(language, "Before route choice:", "选择路线前:"))
        lines.extend(_action_line(action, language=language) for action in actions)
    lines.append(
        _text(
            language,
            "Fit review can continue in Web. Route choices stay hidden until the fit review is complete. This gate applies to setup, creation, and run, not the review itself.",
            "可以在 Web 中继续适配审查。适配审查补齐前，路线选择保持隐藏。这里指设置、创建和运行，不包括适配审查本身。",
        )
    )
    return lines


def _direct_decision_input_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    lines = [_text(language, "Next before recording the direct-path decision:", "记录直接路径决策前下一步:")]
    lines.extend(_action_line(action, language=language) for action in _actions(payload, "next_actions"))
    return lines


def _first_task_message_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    message = str(payload.get("primary_first_task_message") or "").strip()
    if not message:
        return []
    status = str(payload.get("primary_first_task_message_status") or "")
    if status == FIT_FIRST_TASK_MESSAGE_STATUS["ready"]:
        heading = _text(language, "Copyable first /loopora-plan task message:", "可复制的第一条 /loopora-plan 任务消息:")
    elif status == FIT_FIRST_TASK_MESSAGE_STATUS["preview"]:
        heading = _text(
            language,
            "Preview first /loopora-plan task message; do not copy until review inputs are complete:",
            "第一条 /loopora-plan 任务消息预览；补齐判断输入前不要复制:",
        )
    else:
        return []
    return [heading, message]


def _direct_path_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    actions = _actions(payload, "next_actions") if _payload_prefers_direct(payload) else _actions(payload, "direct_path_next_actions")
    if not actions:
        return []
    heading = (
        _text(language, "Decision: use the direct path:", "决策：使用直接路径:")
        if _payload_prefers_direct(payload)
        else _text(language, "If review says Loopora is not needed:", "如果审查显示不需要 Loopora:")
    )
    lines = [heading]
    if _payload_prefers_direct(payload):
        lines.extend(_direct_path_review_input_lines(payload, language=language))
    lines.extend(_action_line(action, language=language) for action in actions)
    return lines


def _direct_path_review_input_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    inputs = _fit_review_inputs(payload)
    task = str(inputs.get("task") or "").strip()
    direct_path = str(inputs.get("direct_path_check") or "").strip()
    if not task and not direct_path:
        return []
    lines = [_text(language, "Review inputs:", "审查输入:")]
    if task:
        lines.append(_text(language, f"- goal: {task}", f"- 目标：{task}"))
    if direct_path:
        lines.append(_text(language, f"- direct-path decision: {direct_path}", f"- 直接路径决策：{direct_path}"))
    return lines


def _fit_review_inputs(payload: Mapping[str, object]) -> Mapping[str, object]:
    fit_payload = payload.get("fit_guidance") if isinstance(payload.get("fit_guidance"), Mapping) else {}
    review = fit_payload.get("task_fit_review") if isinstance(fit_payload.get("task_fit_review"), Mapping) else {}
    return review.get("review_inputs") if isinstance(review.get("review_inputs"), Mapping) else {}
