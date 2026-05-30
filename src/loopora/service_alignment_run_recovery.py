from __future__ import annotations

from collections.abc import Callable

from loopora.agent_adapters import agent_loop_command, agent_loop_json_command
from loopora.event_redaction import redact_sensitive_value
from loopora.service_alignment_context import (
    alignment_context_title_from_session,
    alignment_prefers_chinese,
    alignment_source_option_id,
    bounded_alignment_context_options,
)
from loopora.service_alignment_stage import alignment_agreement_text_snippet
from loopora.service_types import LooporaError, TERMINAL_RUN_STATUSES
from loopora.structured_numbers import structured_non_negative_int
from loopora.task_verdicts import PASSING_TASK_VERDICT_STATUSES


AGENT_RECOVERY_EVENT_LIMIT = 50
AGENT_RECOVERY_SESSION_LIMIT = 100

AGENT_CONTEXT_BINDING_RECOVERY_KEYS = {
    "path",
    "alignment_session_id",
    "alignment_status",
    "linked_run_id",
    "linked_loop_id",
    "linked_bundle_id",
    "workdir",
    "host_context_id",
    "context_source",
    "updated_at",
    "requires_web_alignment",
    "requires_candidate_repair",
    "loopora_fit_contradiction",
    "preview_path",
    "run_path",
}


def agent_recovery_alignment_sessions(repository: object) -> list[dict]:
    list_sessions = getattr(repository, "list_all_alignment_sessions", None)
    if callable(list_sessions):
        return list(list_sessions())
    return list(repository.list_alignment_sessions(limit=AGENT_RECOVERY_SESSION_LIMIT))


def agent_recovery_session_events(repository: object, session_id: str) -> list[dict]:
    return list(repository.list_alignment_events(session_id, limit=AGENT_RECOVERY_EVENT_LIMIT))


def agent_recovery_session_has_candidate_yaml(repository: object, session_id: str) -> bool:
    return agent_candidate_events_include_yaml(agent_recovery_session_events(repository, session_id))


def agent_recovery_agent_entry_candidate_event(repository: object, session_id: str) -> dict:
    return latest_agent_entry_event(agent_recovery_session_events(repository, session_id), "agent_candidate_received")


def agent_recovery_agent_entry_ready_event(repository: object, session_id: str) -> dict:
    return latest_agent_entry_event(agent_recovery_session_events(repository, session_id), "agent_candidate_ready_content")


def agent_recovery_bundle_sync_failed_event(repository: object, session_id: str) -> dict:
    return latest_alignment_bundle_sync_failed_event(agent_recovery_session_events(repository, session_id))


def agent_run_context_source_entries(
    repository: object,
    *,
    root: object,
    adapter: str,
    same_workdir: Callable[[object, object], bool],
) -> list[tuple[dict, dict, str]]:
    entries: list[tuple[dict, dict, str]] = []
    for session in agent_recovery_alignment_sessions(repository):
        if not same_workdir(session.get("workdir"), root):
            continue
        candidate_event = agent_recovery_agent_entry_candidate_event(repository, str(session.get("id") or ""))
        if not candidate_event:
            continue
        payload = agent_entry_candidate_payload(candidate_event)
        event_adapter = agent_entry_candidate_adapter(session, payload)
        if adapter and event_adapter != adapter:
            continue
        entries.append((session, payload, event_adapter))
    return entries


def agent_run_context_choices(
    repository: object,
    *,
    root: object,
    adapter: str,
    same_workdir: Callable[[object, object], bool],
    get_run: Callable[[str], dict],
) -> list[dict]:
    choices: list[dict] = []
    seen: set[str] = set()
    for session, payload, event_adapter in agent_run_context_source_entries(
        repository,
        root=root,
        adapter=adapter,
        same_workdir=same_workdir,
    ):
        choice = agent_run_context_choice_from_session(
            repository,
            session,
            adapter=event_adapter,
            payload=payload,
            get_run=get_run,
        )
        option_id = str(choice.get("option_id") or "")
        if option_id and option_id not in seen:
            choices.append(choice)
            seen.add(option_id)
    return bounded_alignment_context_options(choices)


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


def agent_run_context_choice_from_session(
    repository: object,
    session: dict,
    *,
    adapter: str,
    get_run: Callable[[str], dict],
    payload: dict | None = None,
) -> dict:
    linked_run_id = str(session.get("linked_run_id") or "").strip()
    linked_run_status = ""
    task_verdict_status = ""
    task_verdict_summary = ""
    linked_run_found = True
    if linked_run_id:
        try:
            run = get_run(linked_run_id)
            linked_run_status = str(run.get("status") or "")
            task_verdict = agent_run_context_task_verdict(run)
            task_verdict_status = str(task_verdict.get("status") or "")
            task_verdict_summary = str(task_verdict.get("summary") or "")
        except LooporaError:
            linked_run_found = False
    next_action = agent_run_context_next_action(
        session_status=str(session.get("status") or ""),
        linked_run_id=linked_run_id,
        linked_run_status=linked_run_status,
        task_verdict_status=task_verdict_status,
        linked_run_found=linked_run_found,
    )
    choice = agent_run_context_choice_payload(
        session,
        adapter=adapter,
        payload=payload,
        title=alignment_context_title_from_session(session),
        linked_run_status=linked_run_status,
        task_verdict_status=task_verdict_status,
        task_verdict_summary=task_verdict_summary,
        next_action=next_action,
    )
    if next_action == "repair_failed_preview":
        session_id = str(session.get("id") or "").strip()
        failed_event = agent_recovery_bundle_sync_failed_event(repository, session_id)
        failed_payload = failed_event.get("payload") if isinstance(failed_event.get("payload"), dict) else {}
        choice.update(agent_failed_preview_choice_repair_fields(session, payload=payload, failed_payload=failed_payload))
    return choice


def agent_run_context_next_action(
    *,
    session_status: str,
    linked_run_id: str,
    linked_run_status: str = "",
    task_verdict_status: str = "",
    linked_run_found: bool = True,
) -> str:
    if linked_run_id:
        if not linked_run_found:
            return "stale_linked_run"
        if linked_run_status in TERMINAL_RUN_STATUSES:
            return "replay_terminal_pass" if task_verdict_status in PASSING_TASK_VERDICT_STATUSES else "continue_terminal_evidence"
        return "resume_active_run"
    if session_status == "failed":
        return "repair_failed_preview"
    if session_status not in {"ready", "imported"}:
        return "preview_not_ready"
    return "start_ready_preview"


def agent_run_context_choice_payload(  # noqa: PLR0913 - recovery choice payloads expose explicit stable projection inputs.
    session: dict,
    *,
    adapter: str,
    title: str,
    payload: dict | None = None,
    linked_run_status: str = "",
    task_verdict_status: str = "",
    task_verdict_summary: str = "",
    next_action: str = "start_ready_preview",
) -> dict:
    session_id = str(session.get("id") or "").strip()
    linked_run_id = str(session.get("linked_run_id") or "").strip()
    option_id = alignment_source_option_id("agent_run", session_id)
    entry_source = str((payload or {}).get("entry_source") or "")
    choice_status, choice_hint_en, choice_hint_zh = agent_run_context_choice_hint(next_action)
    runnable = next_action not in {"preview_not_ready", "repair_failed_preview", "stale_linked_run"}
    next_slash_command = f"/loopora-run option:{option_id}" if runnable else ""
    next_cli_command = (
        agent_loop_command(
            adapter,
            str(session.get("workdir") or "."),
            entry_source=entry_source,
            source_option_id=option_id,
        )
        if runnable and adapter
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


def agent_entry_candidate_payload(candidate_event: dict) -> dict:
    return candidate_event.get("payload") if isinstance(candidate_event.get("payload"), dict) else {}


def agent_entry_candidate_adapter(session: dict, payload: dict) -> str:
    return str(payload.get("adapter") or session.get("executor_kind") or "").strip()


def agent_entry_review_suggested_reply(session: dict, *, review_mode: str, task_message: str) -> str:
    task_anchor = alignment_agreement_text_snippet(task_message, limit=520)
    if alignment_prefers_chinese(session):
        if review_mode == "not_fit":
            return (
                "请先按这次 /loopora-plan 的任务锚点重新判断是否适合 Loopora："
                f"{task_anchor}\n"
                "如果仍要继续，请明确后续轮次会新增哪些证据、handoff 或 GateKeeper 裁决价值；"
                "如果不适合，请不要生成可运行 Loop。"
            )
        return (
            "请基于这次 /loopora-plan 的任务锚点继续 Web review："
            f"{task_anchor}\n"
            "推荐采用证据优先路径：先确认 Loopora fit，再把完成标准、伪完成风险、证据预期、"
            "执行策略、判断取舍、残余风险和本地治理责任整理成可确认的工作协议；"
            "确认后再生成可审查的 Loop 预览。"
        )
    if review_mode == "not_fit":
        return (
            "First re-check whether this /loopora-plan task anchor fits Loopora: "
            f"{task_anchor}\n"
            "If we should continue, explain what later evidence, handoffs, or GateKeeper judgment would add; "
            "if it does not fit, do not generate a runnable Loop."
        )
    return (
        "Continue Web review from this /loopora-plan task anchor: "
        f"{task_anchor}\n"
        "Use the evidence-first path: first confirm Loopora fit, then turn the success criteria, fake-done risks, "
        "evidence expectations, execution strategy, judgment tradeoffs, residual-risk policy, and local governance "
        "into a confirmable working agreement before generating a reviewable Loop preview."
    )


def agent_entry_review_decision_options(session: dict, *, review_mode: str, task_message: str) -> list[dict]:
    suggested_reply = agent_entry_review_suggested_reply(session, review_mode=review_mode, task_message=task_message)
    task_anchor = alignment_agreement_text_snippet(task_message, limit=420)
    if alignment_prefers_chinese(session):
        if review_mode == "not_fit":
            return [
                {
                    "id": "skip_loop",
                    "label": "先不生成 Loop（推荐）",
                    "description": "任务锚点更像一次性任务或已有硬检查足够，先避免把它包装成长期 Loop。",
                    "recommended": True,
                    "user_reply": f"同意，先不生成 Loop 方案。本次任务锚点：{task_anchor}",
                },
                {
                    "id": "reframe_as_loop",
                    "label": "重定义成长期 Loop",
                    "description": "我会说明后续证据、handoff 或 GateKeeper 裁决为什么值得保留。",
                    "recommended": False,
                    "user_reply": suggested_reply,
                },
            ]
        return [
            {
                "id": "continue_web_review_evidence_first",
                "label": "按证据优先继续 Web review（推荐）",
                "description": "把宿主 Agent 的任务锚点转成可确认工作协议，再生成 Loop 预览。",
                "recommended": True,
                "user_reply": suggested_reply,
            },
            {
                "id": "recheck_loop_fit",
                "label": "先重新判断是否需要 Loop",
                "description": "如果这其实是一轮任务或已有检查足够，先阻止编排。",
                "recommended": False,
                "user_reply": (
                    "请先重新判断这个任务是否适合 Loopora，而不是直接生成 Loop。"
                    f"任务锚点：{task_anchor}"
                ),
            },
        ]
    if review_mode == "not_fit":
        return [
            {
                "id": "skip_loop",
                "label": "Skip Loop (Recommended)",
                "description": "The task anchor looks one-off or already covered by hard checks, so do not package it as a long-running Loop.",
                "recommended": True,
                "user_reply": f"Agreed; do not generate a Loop plan yet. Task anchor: {task_anchor}",
            },
            {
                "id": "reframe_as_loop",
                "label": "Reframe as a Loop",
                "description": "I will explain why later evidence, handoffs, or GateKeeper judgment should survive.",
                "recommended": False,
                "user_reply": suggested_reply,
            },
        ]
    return [
        {
            "id": "continue_web_review_evidence_first",
            "label": "Continue evidence-first review (Recommended)",
            "description": "Turn the host Agent task anchor into a confirmable working agreement, then generate the Loop preview.",
            "recommended": True,
            "user_reply": suggested_reply,
        },
        {
            "id": "recheck_loop_fit",
            "label": "Re-check Loop fit",
            "description": "If this is only one pass or hard checks already decide it, block composition first.",
            "recommended": False,
            "user_reply": (
                "Please re-check whether this task actually fits Loopora before generating a Loop. "
                f"Task anchor: {task_anchor}"
            ),
        },
    ]


def agent_entry_review_projection(
    session: dict,
    *,
    candidate_event: dict,
    task_message: str,
    missing_judgment_item_ids: list[str],
) -> dict:
    if not candidate_event:
        return {}
    payload = agent_entry_candidate_payload(candidate_event)
    requires_web_alignment = payload.get("requires_web_alignment") is True
    requires_candidate_repair = payload.get("requires_candidate_repair") is True
    loopora_fit_contradiction = payload.get("loopora_fit_contradiction") is True
    review_mode = "not_fit" if loopora_fit_contradiction else "missing_candidate_plan"
    status = str(session.get("status") or "")
    stage = str(session.get("alignment_stage") or "")
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    agreement_started = bool(str(agreement.get("summary") or "").strip()) or stage in {
        "agreement_ready",
        "confirmed",
        "compiling",
        "ready_review",
    }
    if not requires_web_alignment or status in {"ready", "imported", "running_loop"} or agreement_started:
        return {}
    suggested_reply = agent_entry_review_suggested_reply(
        session,
        review_mode=review_mode,
        task_message=task_message,
    )
    return {
        "schema_version": 1,
        "source": "agent_entry",
        "review_mode": review_mode,
        "not_runnable": status != "ready",
        "requires_web_alignment": requires_web_alignment,
        "requires_candidate_repair": requires_candidate_repair,
        "has_candidate_yaml": payload.get("has_candidate_yaml") is True,
        "loopora_fit_contradiction": loopora_fit_contradiction,
        "adapter": str(payload.get("adapter") or session.get("executor_kind") or ""),
        "entry_source": str(payload.get("entry_source") or ""),
        "source_path": str(payload.get("source_path") or ""),
        "candidate_sha256": str(payload.get("candidate_sha256") or ""),
        "candidate_bytes": structured_non_negative_int(payload.get("candidate_bytes"), default=0),
        "ready_candidate_sha256": str(payload.get("ready_candidate_sha256") or ""),
        "ready_candidate_bytes": structured_non_negative_int(payload.get("ready_candidate_bytes"), default=0),
        "task_message": task_message,
        "missing_judgment_item_ids": list(missing_judgment_item_ids),
        "suggested_reply": suggested_reply,
        "decision_options": agent_entry_review_decision_options(
            session,
            review_mode=review_mode,
            task_message=task_message,
        ),
    }


def agent_entry_launch_projection(session: dict, *, candidate_event: dict, ready_event: dict | None = None) -> dict:
    if not candidate_event:
        return {}
    payload = agent_entry_candidate_payload(candidate_event)
    adapter = str(payload.get("adapter") or session.get("executor_kind") or "").strip()
    if not adapter:
        return {}
    entry_source = str(payload.get("entry_source") or "").strip()
    host_context_id = str(payload.get("host_context_id") or "").strip()
    workdir = str(session.get("workdir") or "").strip()
    ready_payload = ready_event.get("payload") if isinstance((ready_event or {}).get("payload"), dict) else {}
    ready_sha = str(ready_payload.get("ready_candidate_sha256") or payload.get("ready_candidate_sha256") or "").strip()
    ready_bytes = structured_non_negative_int(
        ready_payload.get("ready_candidate_bytes", payload.get("ready_candidate_bytes")),
        default=0,
    )
    return {
        "schema_version": 1,
        "source": "agent_entry",
        "adapter": adapter,
        "entry_source": entry_source,
        "host_context_id": host_context_id,
        "slash_command": "/loopora-run",
        "loop_command": agent_loop_json_command(
            adapter,
            workdir,
            entry_source=entry_source,
            context_id=host_context_id,
        ),
        "workdir": workdir,
        "candidate_sha256": str(payload.get("candidate_sha256") or ""),
        "candidate_bytes": structured_non_negative_int(payload.get("candidate_bytes"), default=0),
        "ready_candidate_sha256": ready_sha,
        "ready_candidate_bytes": ready_bytes,
    }


def agent_exact_binding_recovery_action(choice: dict) -> str:
    if choice.get("linked_run_id"):
        return "resume_run"
    if choice.get("alignment_status") in {"ready", "imported"}:
        return "start_ready_preview"
    return "blocked"


def agent_failed_preview_choice_repair_fields(
    session: dict,
    *,
    payload: dict | None = None,
    failed_payload: dict | None = None,
) -> dict:
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    failed_payload = failed_payload if isinstance(failed_payload, dict) else {}
    validation_error = str(
        validation.get("error") or session.get("error_message") or failed_payload.get("error") or ""
    ).strip()
    source_path = str((payload or {}).get("source_path") or "").strip()
    preview_plan_copy = str(
        session.get("bundle_path") or validation.get("bundle_path") or failed_payload.get("bundle_path") or ""
    ).strip()
    summary = {
        "validation_error": validation_error,
        "plan_file_to_repair": source_path or preview_plan_copy,
        "preview_plan_copy": preview_plan_copy,
        "next_repair_step": "repair the candidate plan file, rerun /loopora-plan, then use /loopora-run only after the preview is ready",
    }
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def agent_redacted_context_binding(binding: dict) -> dict:
    return {
        key: redact_sensitive_value(key, value)
        for key, value in binding.items()
        if key in AGENT_CONTEXT_BINDING_RECOVERY_KEYS
    }


def latest_alignment_bundle_sync_failed_event(events: list[dict]) -> dict:
    failed_events = [
        event
        for event in events
        if event.get("event_type") == "alignment_bundle_sync_failed" and isinstance(event.get("payload"), dict)
    ]
    return failed_events[-1] if failed_events else {}


def latest_agent_entry_event(events: list[dict], event_type: str) -> dict:
    entry_events = [
        event
        for event in events
        if event.get("event_type") == event_type
        and isinstance(event.get("payload"), dict)
        and event["payload"].get("candidate_origin") == "agent_entry"
    ]
    return entry_events[-1] if entry_events else {}


def agent_candidate_events_include_yaml(events: list[dict]) -> bool:
    return any(
        event.get("event_type") == "agent_candidate_received"
        and isinstance(event.get("payload"), dict)
        and event["payload"].get("has_candidate_yaml") is True
        for event in events
    )


def agent_run_context_task_verdict(run: dict) -> dict:
    verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
    return verdict if isinstance(verdict, dict) else {}


def agent_run_context_choice_label_prefix_en(action: str) -> str:
    labels = {
        "resume_active_run": "Resume Agent run",
        "start_ready_preview": "Start READY preview",
        "replay_terminal_pass": "Replay terminal run",
        "continue_terminal_evidence": "Continue evidence from terminal run",
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
