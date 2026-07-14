from __future__ import annotations

from collections.abc import Mapping

from loopora.fit_review_catalog import (
    FIT_FIRST_TASK_MESSAGE_EXAMPLE_STATE,
    FIT_FIRST_TASK_MESSAGE_STATUS,
    FIT_REVIEW_SETUP_GATE,
)


def _fit_review_draft_first_task_message(
    *,
    slots: dict[str, str],
    language: str,
) -> str:
    task_slot = slots["task"]
    fit_reason_slot = slots["loopora_fit_reason"]
    fake_done_slot = slots["fake_done_risks"]
    evidence_slot = slots["required_evidence"]
    tradeoff_slot = slots["judgment_tradeoffs"]
    direct_path_slot = slots.get("direct_path_check", "").strip()
    if language == "zh":
        direct_path_fragment = f"直接路径检查：{direct_path_slot}；" if direct_path_slot else ""
        return (
            "/loopora-plan\n\n"
            f"Loopora 适配：{fit_reason_slot}；"
            f"{direct_path_fragment}"
            f"目标：{task_slot}；"
            f"伪完成风险：{fake_done_slot}；"
            f"必需证据：{evidence_slot}；"
            f"判断取舍：{tradeoff_slot}。"
        )
    direct_path_fragment = f"Direct-path check: {direct_path_slot}; " if direct_path_slot else ""
    return (
        "/loopora-plan\n\n"
        f"Loopora fit: {fit_reason_slot}; "
        f"{direct_path_fragment}"
        f"Goal: {task_slot}; "
        f"Fake-done risks: {fake_done_slot}; "
        f"Required evidence: {evidence_slot}; "
        f"Judgment tradeoffs: {tradeoff_slot}."
    )


def _fit_first_task_message_example(*, language: str) -> str:
    if language == "zh":
        return _fit_review_draft_first_task_message(
            slots={
                "task": "交付一个保留审计追踪的支持运营事件看板",
                "loopora_fit_reason": "多轮证据治理能避免开心路径 UI 掩盖权限、回滚和审计缺口",
                "fake_done_risks": "只有开心路径 UI，没有重放/错误证据、权限检查缺失，或回滚不清楚",
                "required_evidence": "项目测试、一次浏览器 journey，以及守门者可审查的证据摘要",
                "judgment_tradeoffs": "范围保持窄；数据安全未证明时 fail closed",
            },
            language=language,
        )
    return _fit_review_draft_first_task_message(
        slots={
            "task": "ship a support-ops incident dashboard that preserves audit trails",
            "loopora_fit_reason": "multi-round evidence review is needed for permission, replay, error, and rollback proof",
            "fake_done_risks": "happy-path UI with no replay/error proof, missing permission checks, or unclear rollback",
            "required_evidence": "project tests, one browser journey, and a GateKeeper-readable evidence summary",
            "judgment_tradeoffs": "keep scope narrow, fail closed on unproven data safety",
        },
        language=language,
    )


def _fit_first_task_message_example_state() -> dict[str, object]:
    return dict(FIT_FIRST_TASK_MESSAGE_EXAMPLE_STATE)


def _primary_first_task_message(payload: dict[str, object]) -> tuple[str, str]:
    task_review = payload.get("task_fit_review")
    if isinstance(task_review, dict):
        draft = str(task_review.get("draft_first_task_message") or "").strip()
        if draft:
            return draft, "task_review_draft"
    return "", "not_available_until_review"


def _primary_first_task_message_state(payload: dict[str, object]) -> tuple[str, bool]:
    task_review = payload.get("task_fit_review")
    if not isinstance(task_review, dict):
        return FIT_FIRST_TASK_MESSAGE_STATUS["example"], False
    summary = task_review.get("task_fit_review_summary")
    if isinstance(summary, Mapping) and str(summary.get("draft_first_task_message_status") or "") == FIT_FIRST_TASK_MESSAGE_STATUS["direct_input"]:
        return FIT_FIRST_TASK_MESSAGE_STATUS["direct_input"], False
    if _task_fit_review_prefers_direct(task_review):
        return FIT_FIRST_TASK_MESSAGE_STATUS["direct"], False
    if _task_fit_review_ready_for_plan_message(task_review):
        return FIT_FIRST_TASK_MESSAGE_STATUS["ready"], True
    return FIT_FIRST_TASK_MESSAGE_STATUS["preview"], False


def _task_fit_review_prefers_direct(task_review: Mapping[str, object]) -> bool:
    summary = task_review.get("task_fit_review_summary") if isinstance(task_review, Mapping) else {}
    return isinstance(summary, Mapping) and str(summary.get("setup_blocker") or "") == FIT_REVIEW_SETUP_GATE["direct_blocker"]


def _task_fit_review_ready_for_plan_message(task_review: Mapping[str, object]) -> bool:
    summary = task_review.get("task_fit_review_summary") if isinstance(task_review, Mapping) else {}
    return isinstance(summary, Mapping) and bool(summary.get("ready_for_loopora_plan_message"))


def _primary_first_task_message_state_payload(
    *,
    source: str,
    status: str,
    copy_allowed: bool,
) -> dict[str, object]:
    return {
        "source": source,
        "status": status,
        "ready": copy_allowed,
        "copy_allowed": copy_allowed,
        "completed_review": status == FIT_FIRST_TASK_MESSAGE_STATUS["ready"],
    }


def _project_primary_first_task_message_state(
    payload: dict[str, object],
    *,
    message: str,
    source: str,
    status: str,
    copy_allowed: bool,
) -> None:
    state = _primary_first_task_message_state_payload(
        source=source,
        status=status,
        copy_allowed=copy_allowed,
    )
    payload["primary_first_task_message"] = message
    payload["primary_first_task_message_source"] = source
    payload["primary_first_task_message_status"] = status
    payload["primary_first_task_message_ready"] = copy_allowed
    payload["primary_first_task_message_copy_allowed"] = copy_allowed
    payload["primary_first_task_message_state"] = state
    fit_summary = payload.get("fit_guidance_summary")
    if isinstance(fit_summary, dict):
        fit_summary["primary_first_task_message_state"] = dict(state)
