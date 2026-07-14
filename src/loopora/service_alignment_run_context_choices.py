from __future__ import annotations

from dataclasses import dataclass

from loopora.agent_adapters import agent_loop_command
from loopora.service_alignment_context import alignment_source_option_id
from loopora.service_alignment_run_context_recovery_fields import (
    AGENT_CONTEXT_BINDING_RECOVERY_KEYS as AGENT_CONTEXT_BINDING_RECOVERY_KEYS,
    agent_exact_binding_recovery_action as agent_exact_binding_recovery_action,
    agent_failed_preview_choice_repair_fields as agent_failed_preview_choice_repair_fields,
    agent_redacted_context_binding as agent_redacted_context_binding,
    agent_run_context_task_verdict as agent_run_context_task_verdict,
)
from loopora.service_types import TERMINAL_RUN_STATUSES
from loopora.task_verdicts import PASSING_TASK_VERDICT_STATUSES


@dataclass(frozen=True)
class AgentRunContextNextActionRequest:
    session_status: str
    linked_run_id: str
    linked_run_status: str = ""
    task_verdict_status: str = ""
    linked_run_lifecycle_failure: bool = False
    linked_run_found: bool = True


def agent_run_context_choice_summary(choices: list[dict]) -> dict[str, object]:
    runnable_count = sum(1 for choice in choices if isinstance(choice, dict) and choice.get("runnable") is not False)
    total_count = len([choice for choice in choices if isinstance(choice, dict)])
    non_runnable_count = max(0, total_count - runnable_count)
    if runnable_count == 0:
        selection_hint = "no runnable contexts are available; return to /loopora-plan or Web review for the listed previews."
    elif runnable_count == 1 and non_runnable_count:
        selection_hint = "one runnable context is available; non-runnable contexts need plan repair or Web review before they can run."
    elif runnable_count == 1:
        selection_hint = "one runnable context is available; select its option_id to continue."
    else:
        selection_hint = (
            f"{runnable_count} runnable contexts are available; choose the exact option_id for the active, READY, "
            "or terminal context you mean; non-runnable contexts need plan repair or Web review."
        )
    return {
        "choice_count": total_count,
        "runnable_choice_count": runnable_count,
        "non_runnable_choice_count": non_runnable_count,
        "selection_hint": selection_hint,
    }


def agent_run_context_next_action(request: AgentRunContextNextActionRequest) -> str:
    if request.linked_run_id:
        return _linked_run_context_next_action(request)
    if request.session_status == "failed":
        return "repair_failed_preview"
    if request.session_status not in {"ready", "imported"}:
        return "preview_not_ready"
    return "start_ready_preview"


def _linked_run_context_next_action(request: AgentRunContextNextActionRequest) -> str:
    if not request.linked_run_found:
        return "stale_linked_run"
    if request.linked_run_status in TERMINAL_RUN_STATUSES:
        if request.linked_run_lifecycle_failure:
            return "retry_lifecycle_failure"
        if request.task_verdict_status in PASSING_TASK_VERDICT_STATUSES:
            return "replay_terminal_pass"
        return "continue_terminal_evidence"
    return "resume_active_run"


def agent_run_context_choice_payload(  # noqa: PLR0913 - recovery choice payloads expose explicit stable projection inputs.
    session: dict,
    *,
    adapter: str,
    title: str,
    payload: dict | None = None,
    linked_run_status: str = "",
    task_verdict_status: str = "",
    task_verdict_summary: str = "",
    linked_run_lifecycle_failure: bool = False,
    recording_blocked_reason: str = "",
    next_action: str = "start_ready_preview",
) -> dict:
    session_id = str(session.get("id") or "").strip()
    linked_run_id = str(session.get("linked_run_id") or "").strip()
    option_id = alignment_source_option_id("agent_run", session_id)
    entry_source = str((payload or {}).get("entry_source") or "")
    choice_status, choice_hint_en, choice_hint_zh = agent_run_context_choice_hint(next_action)
    runnable = next_action not in {"preview_not_ready", "repair_failed_preview", "stale_linked_run"}
    workdir = str(session.get("workdir") or "").strip()
    next_slash_command = f"/loopora-run option:{option_id}" if runnable else ""
    next_cli_command = (
        agent_loop_command(
            adapter,
            workdir,
            entry_source=entry_source,
            source_option_id=option_id,
        )
        if runnable and adapter and workdir
        else ""
    )
    preview_path = f"/loops/new/bundle?alignment_session_id={session_id}" if session_id else ""
    choice = {
        "option_id": option_id,
        "action": next_action,
        "source_type": "agent_entry",
        "adapter": adapter,
        "alignment_session_id": session_id,
        "alignment_status": str(session.get("status") or ""),
        "linked_run_id": linked_run_id,
        "linked_run_status": linked_run_status,
        "linked_run_lifecycle_failure": linked_run_lifecycle_failure,
        "recording_blocked_reason": recording_blocked_reason,
        "task_verdict_status": task_verdict_status,
        "task_verdict_summary": task_verdict_summary,
        "choice_status": choice_status,
        "choice_hint_en": choice_hint_en,
        "choice_hint_zh": choice_hint_zh,
        "runnable": runnable,
        "next_plan_command": "" if runnable else "/loopora-plan",
        "updated_at": session.get("updated_at", ""),
        "entry_source": entry_source,
        "host_context_id": str((payload or {}).get("host_context_id") or ""),
        "preview_path": preview_path,
        "next_command": next_slash_command,
        "next_slash_command": next_slash_command,
        "next_cli_command": next_cli_command,
        "agent_cli_command": next_cli_command,
        "label_zh": f"{agent_run_context_choice_label_prefix_zh(next_action)}：{title}",
        "label_en": f"{agent_run_context_choice_label_prefix_en(next_action)}: {title}",
        "description_zh": "回到这个 Agent Native Loop 的现有运行或 READY 预览；不会重新规划。",
        "description_en": "Return to this Agent Native Loop's existing run or READY preview without replanning.",
    }
    if next_action == "preview_not_ready":
        choice["next_review_step"] = "open the preview, complete Web review or rerun /loopora-plan, then use /loopora-run only after it is ready"
    return choice


def agent_run_context_choice_label_prefix_en(action: str) -> str:
    labels = {
        "resume_active_run": "Resume Agent run",
        "start_ready_preview": "Start READY preview",
        "replay_terminal_pass": "Replay terminal run",
        "continue_terminal_evidence": "Continue evidence from terminal run",
        "retry_lifecycle_failure": "Retry failed run start",
        "preview_not_ready": "Review unfinished preview",
        "repair_failed_preview": "Repair Agent plan",
        "stale_linked_run": "Repair missing run link",
    }
    return labels.get(action, "Recover Agent context")


def agent_run_context_choice_label_prefix_zh(action: str) -> str:
    labels = {
        "resume_active_run": "恢复 Agent 运行",
        "start_ready_preview": "启动 READY 预览",
        "replay_terminal_pass": "回放已结束运行",
        "continue_terminal_evidence": "从已结束运行继续补证据",
        "retry_lifecycle_failure": "重试启动失败运行",
        "preview_not_ready": "检查未完成预览",
        "repair_failed_preview": "修复 Agent 方案",
        "stale_linked_run": "修复缺失运行关联",
    }
    return labels.get(action, "恢复 Agent 上下文")


def agent_run_context_choice_hint(action: str) -> tuple[str, str, str]:
    hints = {
        "resume_active_run": (
            "active_run",
            "Continue the in-progress run; choose this if work was interrupted mid-task.",
            "继续一个进行中的 run；如果任务中途被打断，选这个。",
        ),
        "start_ready_preview": (
            "ready_preview",
            "Start this READY preview as a run; choose this if it is the plan you just reviewed.",
            "把这个 READY 预览启动为 run；如果这是你刚确认的方案，选这个。",
        ),
        "replay_terminal_pass": (
            "terminal_passed",
            "Replay a terminal run whose task verdict already passed; no new Agent work starts unless the task scope changes.",
            "回放一个任务裁决已通过的已结束 run；除非任务范围变化，否则不会启动新的 Agent 工作。",
        ),
        "continue_terminal_evidence": (
            "terminal_unproven",
            "Continue from a terminal run whose task verdict is not proven; selecting this starts the next evidence pass.",
            "从任务裁决未证明的已结束 run 继续；选择它会启动下一轮补证据。",
        ),
        "retry_lifecycle_failure": (
            "terminal_retry",
            "Retry a terminal run that failed before evidence work could start; selecting this starts a fresh run from the reviewed Loop.",
            "重试一个在证据工作开始前失败的已结束 run；选择它会从已审查 Loop 启动新的运行。",
        ),
        "preview_not_ready": (
            "not_ready",
            "Not runnable yet; return to /loopora-plan or Web review before selecting it.",
            "还不能运行；先回到 /loopora-plan 或 Web review。",
        ),
        "repair_failed_preview": (
            "needs_repair",
            "Candidate plan failed validation; repair it with /loopora-plan before selecting it.",
            "候选方案校验失败；选它之前先用 /loopora-plan 修复。",
        ),
        "stale_linked_run": (
            "stale",
            "Linked run is missing; use Web review or /loopora-plan before continuing.",
            "关联 run 已缺失；继续前请使用 Web review 或 /loopora-plan。",
        ),
    }
    return hints.get(
        action,
        (
            "recoverable",
            "Recover this Loopora context without replanning.",
            "恢复这个 Loopora 上下文，不重新规划。",
        ),
    )
