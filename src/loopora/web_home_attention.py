from __future__ import annotations

from datetime import datetime

from loopora.service_alignment_status import ALIGNMENT_ACTIVE_STATUSES
from loopora.service_alignment_session_projection import alignment_session_summary
from loopora.service_types import LooporaError
from loopora.service_types import TERMINAL_RUN_STATUSES
from loopora.run_result_recording import RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
from loopora.web_overviews import _decorate_loop_overview
from loopora.web_task_verdict_overviews import terminal_task_verdict_needs_evidence
from loopora.web_url_utils import with_query_params
from loopora.workdir_inputs import same_workdir_identity


def home_loop_sections(
    service,
    *,
    workdir_context: str = "",
    reconcile_orphans: bool = True,
) -> dict[str, list[dict]]:
    loops = [decorate_home_loop_overview(service, loop) for loop in service.list_loops()]
    if workdir_context:
        loops = [loop for loop in loops if same_workdir_identity(loop.get("workdir"), workdir_context)]
    active_loop_items = [loop for loop in loops if loop_needs_active_attention(loop)]
    active_loops = sort_home_attention_loops(
        [
            *active_loop_items,
            *active_alignment_session_attention_items(
                service,
                workdir_context=workdir_context,
                reconcile_orphans=reconcile_orphans,
            ),
        ]
    )
    active_loop_ids = {loop.get("id") for loop in active_loop_items}
    recent_loops = select_home_recent_loops(loops, active_loop_ids=active_loop_ids)
    return {
        "loops": loops,
        "active_loops": active_loops,
        "recent_loops": recent_loops,
    }


def active_alignment_session_attention_items(
    service,
    *,
    workdir_context: str = "",
    reconcile_orphans: bool = True,
) -> list[dict]:
    items = []
    for session in _alignment_sessions_for_attention(service, reconcile_orphans=reconcile_orphans):
        if not _alignment_session_needs_home_attention(session):
            continue
        if workdir_context and not same_workdir_identity(session.get("workdir"), workdir_context):
            continue
        items.append(home_alignment_session_attention_item(session))
    return items


def _alignment_sessions_for_attention(service, *, reconcile_orphans: bool) -> list[dict]:
    reconcile = getattr(service, "reconcile_orphaned_alignment_sessions", None)
    if reconcile_orphans and callable(reconcile):
        reconcile()
    repository = getattr(service, "repository", None)
    list_all_sessions = getattr(repository, "list_all_alignment_sessions", None)
    if callable(list_all_sessions):
        return [
            alignment_session_summary(session, active_statuses=ALIGNMENT_ACTIVE_STATUSES)
            for session in list_all_sessions()
        ]
    list_sessions = getattr(service, "list_alignment_sessions", None)
    if callable(list_sessions):
        return list_sessions(limit=100)
    return []


def home_alignment_session_attention_item(session: dict) -> dict:
    status = str(session.get("status") or "running")
    title = str(session.get("title") or session.get("id") or "Web conversation")
    last_message = str(session.get("last_message") or "").strip()
    session_id = str(session.get("id") or "")
    workdir = str(session.get("workdir") or "")
    failure_recovery = session.get("failure_recovery") if isinstance(session.get("failure_recovery"), dict) else {}
    if status == "failed":
        candidate_available = failure_recovery.get("candidate_plan_available") is True
        worker_interrupted = failure_recovery.get("kind") == "resume_interrupted_planning"
        reason_kind = (
            "alignment_candidate_failed"
            if candidate_available
            else ("alignment_worker_interrupted" if worker_interrupted else "alignment_generation_failed")
        )
        reason_zh = "候选 Plan File 需要修复" if candidate_available else ("本地规划进程已中断" if worker_interrupted else "智能体未生成 Plan File")
        reason_en = "Candidate Plan File needs repair" if candidate_available else ("Local planning was interrupted" if worker_interrupted else "Agent did not produce a Plan File")
        action_kind = "repair_alignment_bundle" if candidate_available else "retry_alignment_generation"
        action_zh = "修复候选方案" if candidate_available else ("继续规划" if worker_interrupted else "修复智能体并重试")
        action_en = "Repair candidate" if candidate_available else ("Resume planning" if worker_interrupted else "Fix Agent and retry")
        priority = 10
        card_hint_zh = "原任务和工作协议已保留；回到对话即可继续。" if worker_interrupted else "已保留原任务；回到对话后按真实失败域恢复。"
        card_hint_en = "The task and working agreement were preserved; return to continue." if worker_interrupted else "The original task is preserved; return to recover from the actual failure domain."
    elif status == "ready":
        reason_kind = "alignment_ready"
        reason_zh = "Plan File 候选已准备好"
        reason_en = "Plan File candidate is ready"
        action_kind = "review_alignment_bundle"
        action_zh = "审阅并创建 Loop"
        action_en = "Review and create Loop"
        priority = 25
        card_hint_zh = "审阅 READY 候选方案后创建 Loop。"
        card_hint_en = "Review the READY candidate, then create the Loop."
    else:
        reason_kind = "alignment_active"
        reason_zh = "Web 对话正在编排"
        reason_en = "Web conversation is composing"
        action_kind = "resume_alignment_session"
        action_zh = "回到对话"
        action_en = "Resume chat"
        priority = 70
        card_hint_zh = "Agent 正在推进这个 Loop 草案。"
        card_hint_en = "The Agent is still working on this loop draft."
    return {
        "id": session_id,
        "source_kind": "alignment_session",
        "name": title,
        "workdir": workdir,
        "card_href": _alignment_session_card_href(session_id, workdir=workdir),
        "latest_status": status,
        "status_label": str(session.get("status_label") or status),
        "updated_at": session.get("updated_at", ""),
        "created_at": session.get("created_at", ""),
        "attention_reason_kind": reason_kind,
        "attention_reason_zh": reason_zh,
        "attention_reason_en": reason_en,
        "attention_action_kind": action_kind,
        "attention_action_zh": action_zh,
        "attention_action_en": action_en,
        "attention_priority": priority,
        "card_hint_zh": card_hint_zh,
        "card_hint_en": card_hint_en,
        "card_excerpt_zh": last_message,
        "card_excerpt_en": last_message,
    }


def _alignment_session_needs_home_attention(session: dict) -> bool:
    status = str(session.get("status") or "").strip()
    if status in ALIGNMENT_ACTIVE_STATUSES:
        return True
    if status == "failed":
        recovery = session.get("failure_recovery") if isinstance(session.get("failure_recovery"), dict) else {}
        return recovery.get("needs_attention") is True
    return status == "ready" and not any(
        str(session.get(field) or "").strip()
        for field in ("linked_bundle_id", "linked_loop_id", "linked_run_id")
    )


def _alignment_session_card_href(session_id: str, *, workdir: str = "") -> str:
    return with_query_params(
        "/loops/new/bundle",
        alignment_session_id=session_id,
        workdir=str(workdir or "").strip() or None,
    )


def decorate_home_loop_overview(service, loop: dict) -> dict:
    overview = _decorate_loop_overview(loop)
    overview = _with_home_loop_start_projection(service, overview)
    latest_run_id = str(overview.get("latest_run_id") or "").strip()
    if not latest_run_id:
        return _with_home_attention_projection(
            {
                **overview,
                **_home_recorded_basis_projection({}),
                **_home_continuation_projection({}),
            }
        )
    continuation_projection = _home_continuation_projection(
        _home_run_continuation_outcome(service, latest_run_id)
    )
    acceptance_state = service.run_result_acceptance_state(latest_run_id)
    recordable = acceptance_state.get("recordable", True)
    recording_blocked_reason = str(acceptance_state.get("recording_blocked_reason") or "")
    if not acceptance_state.get("accepted"):
        return _with_home_attention_projection(
            {
                **overview,
                "latest_run_result_accepted": False,
                "latest_run_result_recordable": recordable,
                "latest_run_result_recording_blocked_reason": recording_blocked_reason,
                **_home_recorded_basis_projection({}),
                **continuation_projection,
            }
        )
    return _with_home_attention_projection(
        {
            **overview,
            "latest_run_result_accepted": True,
            "latest_run_result_recordable": recordable,
            "latest_run_result_recording_blocked_reason": recording_blocked_reason,
            "latest_run_result_recorded_verdict_kind": str(acceptance_state.get("recorded_verdict_kind") or ""),
            **_home_recorded_basis_projection(acceptance_state),
            **continuation_projection,
        }
    )


def _home_recorded_basis_projection(acceptance_state: dict) -> dict[str, object]:
    basis = acceptance_state.get("recorded_coverage_target_basis")
    basis = basis if isinstance(basis, dict) else {}
    required = basis.get("required") if isinstance(basis.get("required"), dict) else {}
    advisory = basis.get("advisory") if isinstance(basis.get("advisory"), dict) else {}
    return {
        "latest_run_result_recorded_coverage_target_basis": basis,
        "latest_run_result_recorded_required_target_count": int(required.get("total") or 0),
        "latest_run_result_recorded_required_covered_count": int(required.get("covered") or 0),
        "latest_run_result_recorded_advisory_open_count": int(advisory.get("open") or 0),
        "latest_run_result_recorded_advisory_follow_up_available": (
            acceptance_state.get("recorded_advisory_follow_up_available") is True
        ),
    }


def _home_run_continuation_outcome(service, run_id: str) -> dict:
    projection = getattr(service, "run_continuation_outcome", None)
    if not callable(projection):
        return {}
    try:
        result = projection(run_id)
    except LooporaError:
        return {}
    return result if isinstance(result, dict) else {}


def _home_continuation_projection(outcome: dict) -> dict[str, object]:
    projection: dict[str, object] = {
        "latest_run_follow_up_outcome": outcome,
        "latest_run_follow_up_status": str(outcome.get("status") or ""),
        "latest_run_follow_up_focus_target_count": int(outcome.get("focus_target_count") or 0),
        "latest_run_follow_up_improved_target_count": int(outcome.get("improved_target_count") or 0),
        "latest_run_follow_up_remaining_target_count": int(outcome.get("remaining_target_count") or 0),
        "latest_run_follow_up_blocked_target_count": int(outcome.get("blocked_target_count") or 0),
    }
    status = projection["latest_run_follow_up_status"]
    if status == "no_progress":
        projection.update(
            {
                "card_hint_zh": "原任务裁决仍通过；本次建议跟进未取得证据增量。",
                "card_hint_en": "The original task verdict still passes; this advisory follow-up made no evidence progress.",
            }
        )
    elif status == "blocked":
        projection.update(
            {
                "card_hint_zh": "原任务裁决保持不变；本次建议跟进发现了阻塞。",
                "card_hint_en": "The original task verdict is unchanged; this advisory follow-up found blockers.",
            }
        )
    return projection


def _with_home_loop_start_projection(service, overview: dict) -> dict:
    loop_id = str(overview.get("id") or "").strip()
    agent_entry_start = _home_loop_agent_entry_start(service, loop_id)
    return {
        **overview,
        "agent_entry_start": agent_entry_start,
        "can_start_web_run": not bool(agent_entry_start),
    }


def _home_loop_agent_entry_start(service, loop_id: str) -> dict:
    if not loop_id:
        return {}
    projection = getattr(service, "agent_entry_loop_start_projection", None)
    if not callable(projection):
        return {}
    try:
        result = projection(loop_id)
    except LooporaError:
        return {}
    return result if isinstance(result, dict) else {}


def loop_needs_active_attention(loop: dict) -> bool:
    if loop.get("latest_status") in {"queued", "running", "awaiting_agent"}:
        return True
    if loop.get("latest_run_result_accepted"):
        return False
    if (
        loop.get("latest_run_result_recordable") is False
        and str(loop.get("latest_status") or "").strip().lower() in TERMINAL_RUN_STATUSES
        and _recording_blocked_reason(loop) == RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
    ):
        return True
    if terminal_task_verdict_needs_evidence(
        loop.get("latest_status"),
        loop.get("latest_task_verdict_status"),
    ):
        return True
    return loop.get("latest_run_follow_up_status") in {"blocked", "no_progress"}


def sort_home_attention_loops(loops: list[dict]) -> list[dict]:
    return sorted(loops, key=_home_attention_sort_key)


def select_home_recent_loops(loops: list[dict], *, active_loop_ids: set[object], limit: int = 6) -> list[dict]:
    recent_candidates = [
        loop for loop in loops if loop.get("latest_run_id") and loop.get("id") not in active_loop_ids
    ]
    return sorted(recent_candidates, key=_home_recent_sort_key)[:limit]


def _with_home_attention_projection(loop: dict) -> dict:
    return {**loop, **_home_attention_projection(loop)}


def _home_attention_projection(loop: dict) -> dict[str, object]:
    status = str(loop.get("latest_status") or "").strip().lower()
    task_status = str(loop.get("latest_task_verdict_status") or "").strip().lower()
    active_reasons = {
        "queued": (80, "run_active", "运行正在推进", "Run in progress", "open_progress", "查看进展", "Open progress"),
        "running": (80, "run_active", "运行正在推进", "Run in progress", "open_progress", "查看进展", "Open progress"),
        "awaiting_agent": (
            20,
            "awaiting_agent",
            "等待 Agent 提交下一步",
            "Waiting for Agent",
            "continue_agent",
            "继续 Agent",
            "Continue Agent",
        ),
    }
    evidence_reasons = {
        "failed": (
            10,
            "failed_verdict",
            "未通过裁决需要处理",
            "Failed verdict needs action",
            "review_failed_verdict",
            "处理裁决",
            "Review verdict",
        ),
        "not_evaluated": (
            40,
            "not_evaluated",
            "结论未评估",
            "Verdict not evaluated",
            "review_unvalidated_verdict",
            "检查结论",
            "Review result",
        ),
        "insufficient_evidence": (
            30,
            "needs_evidence",
            "需要补证据",
            "Needs evidence",
            "continue_evidence",
            "补充证据",
            "Continue evidence",
        ),
    }
    projection = None
    if status in active_reasons:
        projection = active_reasons[status]
    elif loop.get("latest_run_result_accepted"):
        projection = (
            90,
            "recorded_result",
            "结论已记录",
            "Result recorded",
            "review_recorded_result",
            "查看记录",
            "Open record",
        )
    elif (
        loop.get("latest_run_result_recordable") is False
        and status in TERMINAL_RUN_STATUSES
        and _recording_blocked_reason(loop) == RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
    ):
        projection = (
            15,
            "run_recovery",
            "运行需要重试",
            "Run needs retry",
            "retry_run",
            "重试运行",
            "Retry run",
        )
    elif terminal_task_verdict_needs_evidence(status, task_status):
        projection = evidence_reasons.get(task_status, evidence_reasons["insufficient_evidence"])
    elif loop.get("latest_run_follow_up_status") == "blocked":
        projection = (
            25,
            "advisory_follow_up_blocked",
            "建议跟进遇到阻塞",
            "Advisory follow-up is blocked",
            "review_advisory_follow_up",
            "检查跟进证据",
            "Review follow-up",
        )
    elif loop.get("latest_run_follow_up_status") == "no_progress":
        projection = (
            35,
            "advisory_follow_up_no_progress",
            "建议跟进未取得证据进展",
            "Advisory follow-up made no evidence progress",
            "review_advisory_follow_up",
            "检查跟进证据",
            "Review follow-up",
        )
    else:
        projection = (99, "", "", "", "", "", "")
    (
        priority,
        reason_kind,
        reason_zh,
        reason_en,
        action_kind,
        action_zh,
        action_en,
    ) = projection
    return {
        "attention_reason_kind": reason_kind,
        "attention_reason_zh": reason_zh,
        "attention_reason_en": reason_en,
        "attention_action_kind": action_kind,
        "attention_action_zh": action_zh,
        "attention_action_en": action_en,
        "attention_priority": priority,
    }


def _recording_blocked_reason(loop: dict) -> str:
    return str(loop.get("latest_run_result_recording_blocked_reason") or "").strip()


def _home_attention_sort_key(loop: dict) -> tuple[int, float, str]:
    priority = int(loop.get("attention_priority") or 99)
    return (priority, -_home_recent_timestamp(loop), str(loop.get("id") or ""))


def _home_recent_sort_key(loop: dict) -> tuple[float, str]:
    return (-_home_recent_timestamp(loop), str(loop.get("id") or ""))


def _home_recent_timestamp(loop: dict) -> float:
    latest_stamp = (
        str(loop.get("latest_run_updated_at") or "").strip()
        or str(loop.get("updated_at") or "").strip()
        or str(loop.get("created_at") or "").strip()
    )
    return _timestamp_seconds(latest_stamp)


def _timestamp_seconds(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0
