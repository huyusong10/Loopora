from __future__ import annotations

from loopora.first_use_web_recovery import first_use_web_readiness_note
from loopora.fit_guidance import normalize_fit_guidance_language


def fit_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english


def payload_language(payload: dict[str, object]) -> str:
    try:
        return normalize_fit_guidance_language(str(payload.get("language") or "en"))
    except ValueError:
        return "en"


def payload_list(payload: dict[str, object], key: str) -> list[str]:
    values = payload.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


def payload_dict_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    values = payload.get(key)
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, dict)]


def localized_fit_action_note(action: dict[str, object], *, language: str) -> str:
    kind = str(action.get("kind") or "").strip()
    if language != "zh":
        note = str(action.get("note") or "").strip()
        preflight_note = fit_web_route_preflight_note(action, language=language)
        return f"{preflight_note}; {note}" if preflight_note and note else preflight_note or note
    notes = {
        "return_to_agent": (
            "同一 Agent 会话：带上 Loopora 适配理由、任务目标、伪完成风险、必需证据、判断取舍和可选直接路径上下文"
        ),
        "open_web_creation_choices": (
            "不在 Agent 会话中时，先选择适用性判断/Web 选择；READY 审查后 Web/导入/手动工作继续在 Web 中进行，"
            "只有当前已经在 Agent 宿主中时才选择同一 Agent 设置"
        ),
        "run_after_review": "仅在 Loop 预览符合任务判断后运行",
        "record_direct_decision": "如果审查显示不需要 Loopora，用直接路径理由记录这个停止决定",
        "complete_direct_decision": "补齐直接路径理由后，才能记录不用 Loopora 的决定",
        "use_direct_agent_or_hard_checks": (
            "如果审查没有强适配信号，不要安装同一 Agent 项目入口；"
            "改用可完整裁决该任务的直接 Agent、/goal、硬性检查或项目流程"
        ),
    }
    note = notes.get(kind, str(action.get("note") or "").strip())
    preflight_note = fit_web_route_preflight_note(action, language=language)
    return f"{preflight_note}；{note}" if preflight_note and note else preflight_note or note


def fit_web_route_preflight_note(action: dict[str, object], *, language: str) -> str:
    return "; ".join(fit_web_route_preflight_notes(action, language=language))


def fit_web_route_preflight_notes(action: dict[str, object], *, language: str) -> list[str]:
    if str(action.get("kind") or "") not in {"open_web_creation_choices", "continue_fit_review_in_web"}:
        return []
    notes: list[str] = []
    status = str(action.get("preflight_status") or "")
    requested_port = int(action.get("requested_port") or 8742)
    port = int(action.get("port") or 8742)
    if status == "matching_service_reusable":
        notes.append(
            fit_text(
                language,
                f"A matching Loopora Web service is already running on port {requested_port}; this route reuses it",
                f"端口 {requested_port} 上已有匹配的 Loopora Web 服务；此路线会直接复用",
            )
        )
    elif status == "default_port_in_use_with_suggestion" and port != requested_port:
        notes.append(
            fit_text(
                language,
                f"Default Web port {requested_port} is already in use; this route uses available port {port}",
                f"默认 Web 端口 {requested_port} 已被占用；此路线改用可用端口 {port}",
            )
        )
    elif status == "default_port_in_use_no_suggestion":
        notes.append(
            fit_text(
                language,
                f"Default Web port {requested_port} is already in use; run doctor or choose another --port before starting Web",
                f"默认 Web 端口 {requested_port} 已被占用；启动 Web 前请运行 doctor 或选择其他 --port",
            )
        )
    elif status == "bind_unavailable":
        notes.append(
            fit_text(
                language,
                f"Web bind preflight could not use 127.0.0.1:{requested_port}; run doctor before starting Web",
                f"Web 绑定预检无法使用 127.0.0.1:{requested_port}；启动 Web 前请先运行 doctor",
            )
        )
    readiness_note = first_use_web_readiness_note(action, language=language).rstrip(".。")
    if readiness_note:
        notes.append(readiness_note)
    return notes


def fit_action_alternative_commands(action: dict[str, object]) -> list[str]:
    return [
        str(choice.get("command") or "").strip()
        for choice in fit_action_adapter_choices(action)
    ]


def fit_action_adapter_choices(action: dict[str, object]) -> list[dict[str, object]]:
    if action.get("selection_required") is not True:
        return []
    return [
        choice
        for choice in list(action.get("adapter_choices") or [])
        if isinstance(choice, dict) and str(choice.get("command") or "").strip()
    ]
