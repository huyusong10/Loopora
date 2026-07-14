from __future__ import annotations

from loopora.service_alignment_agreement_confirmation_terms import (
    AGREEMENT_ADJUSTMENT_TOKENS,
    AGREEMENT_CONFIRMATION_TOKENS,
    AGREEMENT_NO_CHANGE_MARKERS,
)


def alignment_message_confirms_agreement(message: str) -> bool:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return False
    if normalized in {"no", "nope"}:
        return False
    negative_scan = normalized
    for no_change_marker in AGREEMENT_NO_CHANGE_MARKERS:
        negative_scan = negative_scan.replace(no_change_marker, "")
    if any(token in negative_scan for token in AGREEMENT_ADJUSTMENT_TOKENS):
        return False
    return any(token in normalized for token in AGREEMENT_CONFIRMATION_TOKENS)


def alignment_message_selects_skip_loop(session: dict, message: str) -> bool:
    if not alignment_latest_assistant_offered_skip_loop(session):
        return False
    normalized = " ".join(str(message or "").strip().lower().split())
    if not normalized:
        return False
    skip_patterns = (
        "do not generate a loop",
        "don't generate a loop",
        "do not generate a loop plan",
        "don't generate a loop plan",
        "skip loop",
        "skip the loop",
        "skip loopora",
        "end loopora-plan",
        "end /loopora-plan",
        "先不生成 loop",
        "不生成 loop",
        "不生成 loop 方案",
        "跳过 loop",
        "跳过 loopora",
        "结束 /loopora-plan",
        "结束 loopora-plan",
        "结束 loopora plan",
    )
    return any(pattern in normalized for pattern in skip_patterns)


def alignment_latest_assistant_offered_skip_loop(session: dict) -> bool:
    for entry in reversed(list(session.get("transcript") or [])):
        if not isinstance(entry, dict):
            continue
        if entry.get("role") != "assistant":
            continue
        options = entry.get("decision_options")
        if isinstance(options, list) and any(
            isinstance(option, dict) and str(option.get("id") or "") in {"skip_loop", "end_loopora_plan", "end_loopora_alignment"} for option in options
        ):
            return True
        return alignment_assistant_content_offers_skip_loop(entry.get("content"))
    return False


def alignment_assistant_content_offers_skip_loop(content: object) -> bool:
    normalized = " ".join(str(content or "").strip().lower().split())
    if not normalized:
        return False
    skip_markers = (
        "not a runnable loop",
        "not fit for loopora",
        "not suitable for loopora",
        "not suitable to compose as a loop",
        "skip loop for now",
        "不适合 loopora",
        "不适合编排成 loopora loop",
        "不适合编排成 loop",
        "先不生成 loop",
        "不会伪装成可运行 loop",
        "不是可运行 loop",
    )
    return any(marker in normalized for marker in skip_markers)


def alignment_skip_loop_confirmation_message(message: str) -> str:
    if any("\u4e00" <= char <= "\u9fff" for char in str(message or "")):
        return "已按你的选择停止生成 Loop 方案；这条对齐会话不会写入 bundle，也不会启动运行。"
    return "Understood. I won't generate a Loop plan for this alignment session, and no bundle or run will start."


def alignment_agreement_readiness_checklist_issues(checklist: object, *, readiness_keys: list[str]) -> list[str]:
    if not isinstance(checklist, dict):
        return ["readiness_checklist"]
    return [key for key in readiness_keys if key != "explicit_confirmation" and checklist.get(key) is not True]
