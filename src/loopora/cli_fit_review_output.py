from __future__ import annotations

import typer

from loopora.cli_fit_output_common import (
    fit_text as _fit_text,
    localized_fit_action_note as _localized_fit_action_note,
    payload_dict_list as _payload_dict_list,
)


def task_fit_review_needs_completion(payload: dict[str, object]) -> bool:
    review = payload.get("task_fit_review")
    if not isinstance(review, dict):
        return "fit_review_required" in {str(item) for item in list(payload.get("setup_gate_blockers") or [])}
    summary = review.get("task_fit_review_summary")
    if not isinstance(summary, dict):
        return True
    return not bool(summary.get("ready_for_loopora_plan_message"))


def print_incomplete_task_fit_next_step(payload: dict[str, object], *, language: str) -> None:
    actions = [
        *_payload_dict_list(payload, "review_actions"),
        *[
            action
            for action in _payload_dict_list(payload, "next_actions")
            if str(action.get("kind") or "")
            in {"complete_review_inputs", "complete_direct_decision", "create_workdir", "choose_workdir", "support"}
        ],
    ]
    if not actions:
        return
    typer.echo(_incomplete_task_fit_next_step_heading(payload, language=language))
    for index, action in enumerate(actions, start=1):
        _print_incomplete_task_fit_action(action, index=index, language=language)
    typer.echo(_incomplete_task_fit_route_state(payload, language=language))


def print_direct_path_next_actions(payload: dict[str, object], *, language: str) -> None:
    actions = (
        _payload_dict_list(payload, "next_actions") if task_fit_review_prefers_direct(payload) else _payload_dict_list(payload, "direct_path_next_actions")
    )
    if not actions:
        return
    heading = (
        _fit_text(language, "Decision: use the direct path:", "决策：使用直接路径:")
        if task_fit_review_prefers_direct(payload)
        else _fit_text(language, "If review says Loopora is not needed:", "如果审查显示不需要 Loopora:")
    )
    typer.echo(heading)
    for action in actions:
        kind = str(action.get("kind") or "").strip()
        command = str(action.get("command") or "").strip()
        command_template = str(action.get("command_template") or "").strip()
        note = _localized_fit_action_note(action, language=language)
        label = _direct_path_action_label(kind, language=language)
        if command and note:
            typer.echo(f"- {label}: {command} ({note})")
        elif command:
            typer.echo(f"- {label}: {command}")
        elif command_template and note:
            typer.echo(f"- {label}: {command_template} ({note})")
        elif command_template:
            typer.echo(f"- {label}: {command_template}")
        elif note:
            typer.echo(f"- {note}")
        elif kind:
            typer.echo(f"- {label}")


def print_task_fit_review(payload: dict[str, object], *, language: str) -> None:
    review = payload.get("task_fit_review")
    if not isinstance(review, dict):
        return
    typer.echo(_fit_text(language, "Task fit review", "任务适配审查"))
    summary = review.get("task_fit_review_summary")
    review_state = _task_fit_review_output_state(summary)
    ready = review_state == "ready"
    setup_allowed = isinstance(summary, dict) and bool(summary.get("setup_allowed"))
    prefer_direct = review_state == "prefer_direct"
    direct_input_required = review_state == "direct_input"
    typer.echo(
        _fit_text(
            language,
            "Review required: yes; Loopora does not classify the task automatically.",
            "需要人工审查：是；Loopora 不会自动给任务分类。",
        )
    )
    typer.echo(_task_fit_review_plan_message(review_state, language=language))
    typer.echo(_task_fit_review_setup_message(review_state, setup_allowed=setup_allowed, language=language))
    missing_input_ids = review.get("missing_first_task_input_ids")
    if isinstance(missing_input_ids, list) and missing_input_ids:
        typer.echo(_fit_text(language, "Missing review inputs:", "缺失判断输入:"))
        for input_id in missing_input_ids:
            label = _fit_review_missing_input_label(str(input_id), language=language)
            if label:
                typer.echo(f"- {label}")
    else:
        typer.echo(_fit_text(language, "Missing review inputs: none", "缺失判断输入：无"))
    completion_command = str(review.get("review_completion_command") or "").strip()
    if completion_command:
        typer.echo(_fit_text(language, "Completion command:", "补全命令:"))
        typer.echo(completion_command)
    _print_task_fit_review_inputs(review, language=language, show_placeholders=not (prefer_direct or direct_input_required))
    if prefer_direct or direct_input_required:
        return
    if not ready:
        print_fit_review_questions(_payload_dict_list(review, "review_questions"), language=language)
    if ready:
        typer.echo(_fit_text(language, "Copyable one-message /loopora-plan handoff:", "可复制的单条 /loopora-plan 交接:"))
    else:
        typer.echo(
            _fit_text(
                language,
                "Preview first task message (complete review inputs before copying):",
                "第一条任务消息预览（复制前先补齐判断输入）:",
            )
        )
    typer.echo(str(review.get("draft_first_task_message") or ""))


def task_fit_review_prefers_direct(payload: dict[str, object]) -> bool:
    review = payload.get("task_fit_review")
    summary = review.get("task_fit_review_summary") if isinstance(review, dict) else {}
    return isinstance(summary, dict) and str(summary.get("setup_blocker") or "") == "prefer_direct_path"


def print_fit_review_questions(questions: list[dict[str, object]], *, language: str) -> None:
    if not questions:
        return
    typer.echo(_fit_text(language, "Answer before setup:", "设置前先回答:"))
    for question in questions:
        text_key = "text_zh" if language == "zh" else "text_en"
        text = str(question.get(text_key) or "").strip()
        if text:
            typer.echo(f"- {text}")


def _incomplete_task_fit_next_step_heading(payload: dict[str, object], *, language: str) -> str:
    if _task_fit_review_needs_direct_decision_input(payload):
        return _fit_text(
            language,
            "Next before recording the direct-path decision:",
            "记录直接路径决策前下一步:",
        )
    return _fit_text(language, "Next before setup:", "设置前下一步:")


def _incomplete_task_fit_route_state(payload: dict[str, object], *, language: str) -> str:
    if _task_fit_review_needs_direct_decision_input(payload):
        return _fit_text(
            language,
            "Loopora routes stay hidden until the direct-path reason is recorded.",
            "记录直接路径理由前，Loopora 路线保持隐藏。",
        )
    return _fit_text(
        language,
        "Fit review can continue in Web. Route choices stay hidden until the fit review is complete. This gate applies to setup, creation, and run, not the review itself.",
        "可以在 Web 中继续适配审查。适配审查补齐前，路线选择保持隐藏。这里指设置、创建和运行，不包括适配审查本身。",
    )


def _print_incomplete_task_fit_action(action: dict[str, object], *, index: int, language: str) -> None:
    kind = str(action.get("kind") or "").strip()
    command = str(action.get("command") or "").strip()
    command_template = str(action.get("command_template") or "").strip()
    note = _localized_fit_action_note(action, language=language)
    labels = {
        "complete_review_inputs": _fit_text(language, "Complete review inputs", "补齐判断输入"),
        "continue_fit_review_in_web": _fit_text(
            language,
            "Continue fit review in Web",
            "在 Web 中继续适配审查",
        ),
        "complete_direct_decision": _fit_text(language, "Complete direct-path decision", "补齐直接路径决策"),
        "create_workdir": _fit_text(language, "Create target directory", "创建目标目录"),
        "confirm_readiness": _fit_text(language, "Confirm readiness", "确认就绪"),
        "support": _fit_text(language, "Usage/setup help", "使用/设置帮助"),
    }
    label = labels.get(kind, "")
    if command and label:
        typer.echo(f"{index}. {label}: {command}")
    elif command:
        suffix = f" ({note})" if note else ""
        typer.echo(f"{index}. {command}{suffix}")
    elif command_template and label:
        suffix = f" ({note})" if note else ""
        typer.echo(f"{index}. {label}: {command_template}{suffix}")
    elif command_template:
        suffix = f" ({note})" if note else ""
        typer.echo(f"{index}. {command_template}{suffix}")
    elif note:
        typer.echo(f"{index}. {note}")
    open_url = str(action.get("open_url") or "").strip()
    if open_url:
        open_label = _fit_text(language, "Open after Web starts", "Web 启动后打开")
        typer.echo(f"   {open_label}: {open_url}")


def _direct_path_action_label(kind: str, *, language: str) -> str:
    labels = {
        "support": _fit_text(language, "Usage/setup help", "使用/设置帮助"),
        "record_direct_decision": _fit_text(language, "Record direct-path decision", "记录直接路径决策"),
        "use_direct_agent_or_hard_checks": _fit_text(
            language,
            "Direct Agent or hard checks",
            "直接 Agent 或硬性检查",
        ),
    }
    return labels.get(kind, kind.replace("_", " "))


def _task_fit_review_output_state(summary: object) -> str:
    if not isinstance(summary, dict):
        return "preview"
    setup_blocker = str(summary.get("setup_blocker") or "")
    if setup_blocker == "prefer_direct_path":
        return "prefer_direct"
    if setup_blocker == "missing_direct_decision_input":
        return "direct_input"
    return "ready" if bool(summary.get("ready_for_loopora_plan_message")) else "preview"


def _task_fit_review_plan_message(review_state: str, *, language: str) -> str:
    messages = {
        "prefer_direct": (
            "First /loopora-plan message: not generated because the review chose the direct path.",
            "第一条 /loopora-plan 消息：未生成，因为审查选择了直接路径。",
        ),
        "direct_input": (
            "First /loopora-plan message: not generated because the direct-path decision needs a direct-path reason.",
            "第一条 /loopora-plan 消息：未生成，因为直接路径决策需要直接路径理由。",
        ),
        "ready": (
            "First /loopora-plan handoff: ready to paste as one Agent message after you confirm the review.",
            "第一条 /loopora-plan 交接：确认审查后可作为一条 Agent 消息粘贴。",
        ),
        "preview": (
            "First /loopora-plan message: preview only until review inputs are complete.",
            "第一条 /loopora-plan 消息：判断输入补齐前仅作预览。",
        ),
    }
    english, chinese = messages.get(review_state, messages["preview"])
    return _fit_text(language, english, chinese)


def _task_fit_review_setup_message(review_state: str, *, setup_allowed: bool, language: str) -> str:
    if setup_allowed:
        return _fit_text(
            language,
            "Setup: ready only if the completed review still shows a strong fit.",
            "设置：仅当补全后的审查仍显示强适配时才继续。",
        )
    messages = {
        "prefer_direct": (
            "Setup: blocked because the review chose the direct path.",
            "设置：已阻止，因为审查选择了直接路径。",
        ),
        "direct_input": (
            "Setup: blocked until the direct-path reason is supplied.",
            "设置：已阻止；请先补齐直接路径理由。",
        ),
        "preview": (
            "Setup: blocked until the missing review inputs are complete.",
            "设置：已阻止；请先补齐缺失的判断输入。",
        ),
        "ready": (
            "Setup: blocked until a usable target project is supplied.",
            "设置：已阻止；请先提供可用目标项目。",
        ),
    }
    english, chinese = messages.get(review_state, messages["preview"])
    return _fit_text(language, english, chinese)


def _task_fit_review_needs_direct_decision_input(payload: dict[str, object]) -> bool:
    review = payload.get("task_fit_review")
    summary = review.get("task_fit_review_summary") if isinstance(review, dict) else {}
    return isinstance(summary, dict) and str(summary.get("setup_blocker") or "") == "missing_direct_decision_input"


def _print_task_fit_review_inputs(review: dict[str, object], *, language: str, show_placeholders: bool = True) -> None:
    inputs = review.get("review_inputs")
    if not isinstance(inputs, dict):
        typer.echo(f"task: {review.get('task') or ''}")
        return
    labels = _fit_review_input_labels(language)
    lines: list[str] = []
    for label, key, required in labels:
        label_text = label
        if not show_placeholders and key == "direct_path_check":
            label_text = _fit_text(language, "direct-path decision", "直接路径决策")
        value = str(inputs.get(key) or "").strip()
        if not required and not value:
            continue
        if not show_placeholders and not value:
            continue
        placeholder = _fit_text(language, "<fill before /loopora-plan>", "<在 /loopora-plan 前补齐>")
        lines.append(f"- {label_text}: {value or placeholder if show_placeholders else value}")
    if lines:
        typer.echo(_fit_text(language, "Review inputs:", "判断输入:"))
        for line in lines:
            typer.echo(line)


def _fit_review_input_labels(language: str) -> tuple[tuple[str, str, bool], ...]:
    if language == "zh":
        return (
            ("目标", "task", True),
            ("Loopora 适配理由", "loopora_fit_reason", True),
            ("直接路径检查", "direct_path_check", False),
            ("伪完成风险", "fake_done_risks", True),
            ("必需证据", "required_evidence", True),
            ("判断取舍", "judgment_tradeoffs", True),
        )
    return (
        ("goal", "task", True),
        ("Loopora fit reason", "loopora_fit_reason", True),
        ("direct-path check", "direct_path_check", False),
        ("fake-done risks", "fake_done_risks", True),
        ("required evidence", "required_evidence", True),
        ("judgment tradeoffs", "judgment_tradeoffs", True),
    )


def _fit_review_missing_input_label(input_id: str, *, language: str) -> str:
    if language == "zh":
        labels = {
            "task": "任务目标 (--task)",
            "loopora_fit_reason": "Loopora 适配理由 (--fit-reason)",
            "fake_done_risks": "伪完成风险 (--fake-done)",
            "required_evidence": "必需证据 (--evidence)",
            "judgment_tradeoffs": "判断取舍 (--tradeoffs)",
            "direct_decision_input": "直接路径理由 (--direct-path，可用 --task 保留任务上下文)",
        }
    else:
        labels = {
            "task": "task goal (--task)",
            "loopora_fit_reason": "Loopora fit reason (--fit-reason)",
            "fake_done_risks": "fake-done risks (--fake-done)",
            "required_evidence": "required evidence (--evidence)",
            "judgment_tradeoffs": "judgment tradeoffs (--tradeoffs)",
            "direct_decision_input": "direct-path reason (--direct-path, with optional --task context)",
        }
    return labels.get(input_id, input_id)
