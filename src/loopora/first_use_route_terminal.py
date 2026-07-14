from __future__ import annotations

from collections.abc import Mapping, Sequence


def first_use_route_action_status_lines(
    payload: Mapping[str, object],
    *,
    route_actions: Sequence[Mapping[str, object]],
    language: str,
) -> list[str]:
    if not bool(payload.get("setup_commands_ready")):
        return []
    ready_kinds = _route_status_kinds(payload, "route_action_ready_kinds")
    blocked_kinds = _route_status_kinds(payload, "route_action_blocked_kinds")
    fit_review_required = bool(payload.get("fit_review_recommended_before_setup"))
    actions_by_kind = {str(action.get("kind") or "").strip(): action for action in route_actions if str(action.get("kind") or "").strip()}
    lines: list[str] = []
    if ready_kinds:
        labels, after_lines = _route_ready_status_labels(ready_kinds, actions_by_kind, language=language)
        if labels:
            joined = "; ".join(labels)
            if fit_review_required:
                lines.append(_text(language, f"- Ready before setup: {joined}.", f"- 设置前可执行：{joined}。"))
            else:
                lines.append(_text(language, f"- Ready now: {joined}.", f"- 现在可执行：{joined}。"))
        lines.extend(after_lines)
    if blocked_kinds:
        blockers = payload.get("route_action_command_blockers")
        blockers_by_kind = blockers if isinstance(blockers, Mapping) else {}
        labels = [
            _route_blocked_status_label(
                kind,
                blockers_by_kind,
                action=actions_by_kind.get(kind, {}),
                install_action=actions_by_kind.get("install_agent_entry", {}),
                language=language,
            )
            for kind in blocked_kinds
        ]
        joined = "; ".join(label for label in labels if label)
        if joined:
            if fit_review_required:
                lines.append(
                    _text(
                        language,
                        f"- After fit review, still blocked until prerequisites are resolved: {joined}.",
                        f"- 适配审查后仍需处理前置条件：{joined}。",
                    )
                )
                return lines
            lines.append(
                _text(
                    language,
                    f"- Blocked until prerequisites are resolved: {joined}.",
                    f"- 前置条件处理前保持阻止：{joined}。",
                )
            )
    return lines


def first_use_route_preview_status_line(payload: Mapping[str, object], *, language: str) -> str:
    if bool(payload.get("route_preview_executable")):
        return ""
    blockers = [_route_preview_blocker_label(str(blocker or "").strip(), language=language) for blocker in list(payload.get("route_preview_blockers") or [])]
    labels = [label for label in blockers if label]
    if not labels:
        return ""
    joined = "; ".join(labels)
    return _text(
        language,
        f"- Preview only: route commands are not the next step yet; first resolve: {joined}.",
        f"- 仅预览：路线命令还不是下一步；先处理：{joined}。",
    )


def _route_status_kinds(payload: Mapping[str, object], key: str) -> list[str]:
    return [str(item).strip() for item in list(payload.get(key) or []) if str(item).strip()]


def _route_ready_status_labels(
    ready_kinds: list[str],
    actions_by_kind: Mapping[str, Mapping[str, object]],
    *,
    language: str,
) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    after_lines: list[str] = []
    for kind in ready_kinds:
        action = actions_by_kind.get(kind, {})
        install_action = actions_by_kind.get("install_agent_entry", {})
        label = _route_status_label(kind, action=action, language=language)
        after_label = _route_after_status_label(action, install_action=install_action, language=language)
        if after_label:
            after_lines.append(_text(language, f"- After {after_label}: {label}.", f"- {after_label}后：{label}。"))
        else:
            labels.append(label)
    return labels, after_lines


def _route_blocked_status_label(
    kind: str,
    blockers_by_kind: Mapping[str, object],
    *,
    action: Mapping[str, object],
    install_action: Mapping[str, object],
    language: str,
) -> str:
    blocker_values = blockers_by_kind.get(kind)
    blockers = [str(item).strip() for item in list(blocker_values or []) if str(item).strip()]
    blocker_labels = [_route_blocker_status_label(blocker, language=language) for blocker in blockers]
    labels = [label for label in blocker_labels if label]
    route_label = _route_status_label_with_after(kind, action=action, install_action=install_action, language=language)
    if not labels:
        return route_label
    joined = ", ".join(labels)
    return _text(language, f"{route_label} ({joined})", f"{route_label}（{joined}）")


def _route_status_label(kind: str, *, action: Mapping[str, object] | None = None, language: str) -> str:
    labels = {
        "check_fit_first": ("fit review", "适配审查"),
        "open_web_creation_choices": ("Fit Guide/Web choices", "适用性判断/Web 选择"),
        "install_agent_entry": (
            "same-Agent setup choice" if action and action.get("selection_required") is True else "detected same-Agent setup",
            "同一 Agent 设置选择" if action and action.get("selection_required") is True else "已检测的同一 Agent 设置",
        ),
        "confirm_readiness": ("doctor readiness check", "doctor 就绪检查"),
        "return_to_agent": ("/loopora-plan", "/loopora-plan"),
        "run_after_review": ("/loopora-run", "/loopora-run"),
        "support": ("support route", "支持路线"),
    }
    english, chinese = labels.get(kind, (kind.replace("_", " "), kind.replace("_", " ")))
    return chinese if language == "zh" else english


def _route_status_label_with_after(
    kind: str,
    *,
    action: Mapping[str, object],
    install_action: Mapping[str, object],
    language: str,
) -> str:
    label = _route_status_label(kind, action=action, language=language)
    after_label = _route_after_status_label(action, install_action=install_action, language=language)
    if not after_label:
        return label
    return f"{after_label}后的{label}" if language == "zh" else f"{label} after {after_label}"


def _route_after_status_label(
    action: Mapping[str, object],
    *,
    install_action: Mapping[str, object] | None = None,
    language: str,
) -> str:
    if str(action.get("after_action") or "") == "install_agent_entry":
        return _route_status_label("install_agent_entry", action=install_action, language=language)
    return ""


def _route_blocker_status_label(blocker: str, *, language: str) -> str:
    labels = {
        "app_state_not_ready": ("App/Web readiness", "App/Web 就绪状态"),
        "web_port_unavailable": ("usable local Web port", "可用本地 Web 端口"),
        "same_agent_entry_required": ("same-Agent project entry", "同一 Agent 项目入口"),
        "first_task_message_not_ready": ("copyable /loopora-plan task message", "可复制的 /loopora-plan 任务消息"),
        "ready_review_required": ("READY preview review", "READY 预览审查"),
        "target_project_required": ("usable target project", "可用目标项目"),
        "target_project_unready": ("usable target project", "可用目标项目"),
        "review_inputs_required": ("completed fit review", "补齐适配审查"),
        "fit_review_required": ("completed fit review", "补齐适配审查"),
    }
    english, chinese = labels.get(blocker, (blocker.replace("_", " "), blocker.replace("_", " ")))
    return chinese if language == "zh" else english


def _route_preview_blocker_label(blocker: str, *, language: str) -> str:
    labels = {
        "review_inputs_required": ("completed fit review", "补齐适配审查"),
        "target_project_required": ("usable target project", "可用目标项目"),
        "target_project_unready": ("usable target project", "可用目标项目"),
        "prefer_direct_path": ("direct-path decision", "直接路径决策"),
        "missing_direct_decision_input": ("direct-path reason", "直接路径理由"),
    }
    english, chinese = labels.get(blocker, (blocker.replace("_", " "), blocker.replace("_", " ")))
    return chinese if language == "zh" else english


def _text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english


__all__ = (
    "first_use_route_action_status_lines",
    "first_use_route_preview_status_line",
)
