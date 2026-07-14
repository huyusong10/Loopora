from __future__ import annotations

from collections.abc import Mapping

from loopora.fit_review_catalog import FIT_FIRST_TASK_MESSAGE_STATUS


def compact_first_use_lines(payload: Mapping[str, object], *, surface: str) -> list[str]:
    language = str(payload.get("language") or "en")
    status = str(payload.get("task_review_status") or FIT_FIRST_TASK_MESSAGE_STATUS["example"])
    title_zh = "启动" if surface == "start" else "适配"
    lines = [_text(language, f"Loopora {surface}", f"Loopora {title_zh}")]
    workdir = str(payload.get("workdir") or "").strip()
    if workdir:
        lines.append(_text(language, f"Project: {workdir}", f"项目：{workdir}"))

    if status == FIT_FIRST_TASK_MESSAGE_STATUS["direct"]:
        lines.extend(_direct_path_lines(payload, language=language))
    elif status == FIT_FIRST_TASK_MESSAGE_STATUS["direct_input"]:
        lines.extend(_direct_input_lines(payload, language=language))
    elif status == FIT_FIRST_TASK_MESSAGE_STATUS["preview"]:
        lines.extend(_incomplete_review_lines(payload, language=language))
    elif status == FIT_FIRST_TASK_MESSAGE_STATUS["ready"]:
        lines.extend(_completed_review_lines(payload, language=language))
    else:
        lines.extend(_cold_start_lines(payload, language=language))

    lines.append(
        _text(
            language,
            "Need the full decision record, every route, or recovery diagnostics? Rerun this command with --details.",
            "需要完整判断记录、全部路线或恢复诊断？请用 --details 重跑当前命令。",
        )
    )
    return lines


def _cold_start_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    choose_workdir = _action(payload, "choose_workdir")
    if choose_workdir:
        return [
            _text(language, "Fit review: not started.", "适配审查：尚未开始。"),
            _text(language, "Next: choose the target project, then describe the task:", "下一步：选择目标项目，然后描述任务："),
            _command(choose_workdir),
            _text(
                language,
                "Loopora will not install, create, or run anything during this review.",
                "审查期间 Loopora 不会安装、创建或运行任何内容。",
            ),
        ]
    return [
        _text(language, "Fit review: not started.", "适配审查：尚未开始。"),
        *_web_review_lines(payload, language=language),
        *_terminal_review_lines(payload, language=language),
        _blocked_until_review_line(language),
    ]


def _incomplete_review_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    review = payload.get("task_fit_review")
    inputs = review.get("review_inputs") if isinstance(review, Mapping) else {}
    task = str(inputs.get("task") or "").strip() if isinstance(inputs, Mapping) else ""
    missing_ids = list(review.get("missing_first_task_input_ids") or []) if isinstance(review, Mapping) else []
    lines = [_text(language, "Fit review: needs human judgment.", "适配审查：需要人工判断。")]
    if task:
        lines.append(_text(language, f"Task: {task}", f"任务：{task}"))
    missing = ", ".join(_missing_label(str(item), language=language) for item in missing_ids)
    if missing:
        lines.append(_text(language, f"Still needed: {missing}.", f"仍需补充：{missing}。"))
    web_lines = _web_review_lines(payload, language=language)
    if web_lines:
        lines.extend(web_lines)
        lines.extend(_terminal_review_lines(payload, language=language))
    else:
        choose_workdir = _action(payload, "choose_workdir")
        if choose_workdir:
            lines.extend(
                [
                    _text(language, "Recommended: continue from the target project:", "推荐：从目标项目继续："),
                    _command(choose_workdir),
                ]
            )
        else:
            lines.extend(_terminal_review_lines(payload, language=language))
    lines.append(_blocked_until_review_line(language))
    return lines


def _completed_review_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    lines = [
        _text(
            language,
            "Fit review: complete; continue only if you still agree Loopora is the right route.",
            "适配审查：已完成；只有你仍确认 Loopora 是正确路线时才继续。",
        )
    ]
    message = str(payload.get("primary_first_task_message") or "").strip()
    if bool(payload.get("target_project_required")) or not str(payload.get("workdir") or "").strip():
        choose_workdir = _action(payload, "choose_workdir")
        if choose_workdir:
            lines.extend(
                [
                    _text(language, "Next: choose the target project before selecting a route:", "下一步：选择路线前先选择目标项目："),
                    _command(choose_workdir),
                ]
            )
        _append_prepared_handoff(lines, message=message, language=language, prerequisite="target_and_setup")
        return lines
    if not bool(payload.get("setup_commands_ready")):
        recovery = _action(payload, "create_workdir") or _action(payload, "choose_workdir")
        lines.append(_text(language, "Target project: not ready for Loopora routes.", "目标项目：尚未准备好使用 Loopora 路线。"))
        if recovery and _command(recovery):
            lines.extend([_text(language, "Next:", "下一步："), _command(recovery)])
        lines.append(
            _text(
                language,
                "Web, same-Agent setup, and run stay blocked until the target project is usable.",
                "目标项目可用前，Web、同一 Agent 设置和运行保持阻止。",
            )
        )
        _append_prepared_handoff(lines, message=message, language=language, prerequisite="target_and_setup")
        return lines

    web = _route_action(payload, "open_web_creation_choices")
    if web and bool(web.get("command_ready")):
        lines.extend(
            [
                _text(language, "Outside an Agent session, continue in Web:", "不在 Agent 会话中时，在 Web 中继续："),
                _command(web),
            ]
        )
    install = _route_action(payload, "install_agent_entry")
    setup_command = _same_agent_setup_command(install) if bool(install.get("command_ready")) else ""
    if setup_command:
        lines.extend(
            [
                _text(
                    language,
                    "Already in Codex, Claude Code, or OpenCode? Set up or verify the detected current host first:",
                    "已经在 Codex、Claude Code 或 OpenCode 中？先设置或验证检测到的当前宿主：",
                ),
                setup_command,
            ]
        )
    elif install and install.get("selection_required") is True:
        lines.append(
            _text(
                language,
                "Same-Agent setup needs an explicit host choice; rerun with --details only if already inside Codex, Claude Code, or OpenCode.",
                "同一 Agent 设置需要明确选择宿主；只有已经在 Codex、Claude Code 或 OpenCode 中时，才用 --details 查看选择。",
            )
        )
    return_to_agent = _route_action(payload, "return_to_agent")
    if message and bool(return_to_agent.get("command_ready")):
        lines.extend(
            [
                _text(language, "Ready same-Agent handoff (paste as one message):", "已就绪的同一 Agent 交接（作为一条消息粘贴）："),
                message,
            ]
        )
    else:
        _append_prepared_handoff(lines, message=message, language=language, prerequisite="setup")
    lines.append(
        _text(
            language,
            "Run only after the READY preview matches the reviewed task judgment.",
            "只有 READY 预览与已审查任务判断一致后才运行。",
        )
    )
    return lines


def _append_prepared_handoff(
    lines: list[str],
    *,
    message: str,
    language: str,
    prerequisite: str,
) -> None:
    if not message:
        return
    if prerequisite == "target_and_setup":
        label = _text(
            language,
            "Reviewed handoff prepared; save it now, but paste it only after choosing the target and same-Agent setup reports ready:",
            "已审查交接已准备好；现在可以保存，但只有选择目标且同一 Agent 设置报告就绪后才能粘贴：",
        )
    else:
        label = _text(
            language,
            "Reviewed handoff prepared; save it now, but paste it only after the same-Agent setup command above reports ready:",
            "已审查交接已准备好；现在可以保存，但只有上面的同一 Agent 设置命令报告就绪后才能粘贴：",
        )
    lines.extend([label, message])


def _direct_path_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    review = payload.get("task_fit_review")
    inputs = review.get("review_inputs") if isinstance(review, Mapping) else {}
    reason = str(inputs.get("direct_path_check") or "").strip() if isinstance(inputs, Mapping) else ""
    lines = [_text(language, "Decision: use the direct path; Loopora setup stays blocked.", "决策：使用直接路径；Loopora 设置保持阻止。")]
    if reason:
        lines.append(_text(language, f"Why: {reason}", f"理由：{reason}"))
    direct = _action(payload, "use_direct_agent_or_hard_checks")
    note = str(direct.get("note") or "").strip() if direct else ""
    if note:
        lines.append(note)
    return lines


def _direct_input_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    action = _action(payload, "complete_direct_decision")
    lines = [
        _text(
            language,
            "Direct-path decision: add why direct Agent work, hard checks, or the project process is enough.",
            "直接路径决策：请补充为何直接 Agent、硬性检查或项目流程已经足够。",
        )
    ]
    if action and _command(action):
        lines.extend([_text(language, "Next:", "下一步："), _command(action)])
    lines.append(_text(language, "Loopora setup stays blocked until that reason is recorded.", "记录该理由前，Loopora 设置保持阻止。"))
    return lines


def _web_review_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    action = _action(payload, "continue_fit_review_in_web")
    command = _command(action)
    if not action or not command:
        return []
    lines = [_text(language, "Recommended: continue the fit review in Web:", "推荐：在 Web 中继续适配审查："), command]
    open_url = str(action.get("open_url") or "").strip()
    if open_url:
        lines.append(_text(language, f"Open after Web starts: {open_url}", f"Web 启动后打开：{open_url}"))
    return lines


def _terminal_review_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    command = _command(_action(payload, "complete_review_inputs"))
    if not command:
        return []
    compact_command = command.split(" --fit-reason", maxsplit=1)[0]
    if " --details" not in compact_command:
        compact_command += " --details"
    return [_text(language, "Terminal alternative:", "终端备用入口："), compact_command]


def _blocked_until_review_line(language: str) -> str:
    return _text(
        language,
        "Setup, creation, and run stay blocked until the fit review is complete.",
        "适配审查完成前，设置、创建和运行保持阻止。",
    )


def _action(payload: Mapping[str, object], kind: str) -> Mapping[str, object]:
    for field in ("review_actions", "next_actions", "direct_path_next_actions"):
        for item in list(payload.get(field) or []):
            if isinstance(item, Mapping) and str(item.get("kind") or "") == kind:
                return item
    return {}


def _route_action(payload: Mapping[str, object], kind: str) -> Mapping[str, object]:
    for item in list(payload.get("route_actions_after_strong_fit") or []):
        if isinstance(item, Mapping) and str(item.get("kind") or "") == kind:
            return item
    return {}


def _command(action: Mapping[str, object]) -> str:
    return str(action.get("command") or action.get("command_template") or "").strip()


def _same_agent_setup_command(action: Mapping[str, object]) -> str:
    return _command(action)


def _missing_label(input_id: str, *, language: str) -> str:
    labels = {
        "loopora_fit_reason": ("fit reason", "适配理由"),
        "fake_done_risks": ("fake-done risk", "伪完成风险"),
        "required_evidence": ("required evidence", "必需证据"),
        "judgment_tradeoffs": ("judgment tradeoffs", "判断取舍"),
        "direct_decision_input": ("direct-path reason", "直接路径理由"),
        "task": ("task goal", "任务目标"),
    }
    english, chinese = labels.get(input_id, (input_id.replace("_", " "), input_id.replace("_", " ")))
    return chinese if language == "zh" else english


def _text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english
