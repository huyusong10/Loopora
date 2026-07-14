from __future__ import annotations

from dataclasses import dataclass

from loopora.service_alignment_agreement_decisions import (
    alignment_message_confirms_agreement,
    alignment_message_selects_skip_loop,
    alignment_skip_loop_confirmation_message,
)


@dataclass(frozen=True)
class AlignmentUserMessageStagePlan:
    update_fields: dict
    event_type: str = ""
    event_payload: dict | None = None
    start_session: bool = True
    assistant_message: str = ""


def alignment_user_message_stage_plan(
    session: dict,
    message: str,
    *,
    captured_at: str,
    confirmed_stages: set[str],
) -> AlignmentUserMessageStagePlan:
    if alignment_message_selects_skip_loop(session, message):
        return AlignmentUserMessageStagePlan(
            update_fields={
                "status": "skipped",
                "alignment_stage": "clarifying",
                "finished_at": captured_at,
                "working_agreement": {
                    "skipped": True,
                    "skip_message": message,
                    "skipped_at": captured_at,
                },
            },
            event_type="alignment_skipped",
            event_payload={"status": "skipped", "reason": "user_selected_skip_loop"},
            start_session=False,
            assistant_message=alignment_skip_loop_confirmation_message(message),
        )
    stage = str(session.get("alignment_stage", "") or "clarifying")
    if stage == "agreement_ready":
        agreement = dict(session.get("working_agreement") or {})
        checklist = dict(agreement.get("readiness_checklist") or {})
        if alignment_message_confirms_agreement(message):
            checklist["explicit_confirmation"] = True
            agreement["readiness_checklist"] = checklist
            agreement["confirmed_at"] = captured_at
            agreement["confirmation_message"] = message
            return AlignmentUserMessageStagePlan(
                update_fields={"alignment_stage": "confirmed", "working_agreement": agreement},
                event_type="alignment_agreement_confirmed",
                event_payload={"alignment_stage": "confirmed"},
            )
        checklist["explicit_confirmation"] = False
        agreement["readiness_checklist"] = checklist
        agreement["confirmed_at"] = ""
        agreement["confirmation_message"] = ""
        return AlignmentUserMessageStagePlan(
            update_fields={"alignment_stage": "clarifying", "working_agreement": agreement},
            event_type="alignment_agreement_reopened",
            event_payload={"alignment_stage": "clarifying"},
        )
    return alignment_non_agreement_user_message_stage_plan(
        session,
        message,
        captured_at=captured_at,
        confirmed_stages=confirmed_stages,
    )


def alignment_non_agreement_user_message_stage_plan(
    session: dict,
    message: str,
    *,
    captured_at: str,
    confirmed_stages: set[str],
) -> AlignmentUserMessageStagePlan:
    status = str(session.get("status", "") or "")
    stage = str(session.get("alignment_stage", "") or "clarifying")
    if status == "ready":
        agreement = dict(session.get("working_agreement") or {})
        ready_review = dict(agreement.get("ready_review") or {})
        ready_review["feedback"] = message
        ready_review["requested_at"] = captured_at
        ready_review["source_status"] = status
        agreement["ready_review"] = ready_review
        return AlignmentUserMessageStagePlan(
            update_fields={"alignment_stage": "ready_review", "working_agreement": agreement},
            event_type="alignment_ready_review_started",
            event_payload={
                "alignment_stage": "ready_review",
                "feedback": message,
                "bundle_path": session.get("bundle_path", ""),
            },
        )
    if status in {"imported", "running_loop"}:
        return AlignmentUserMessageStagePlan(
            update_fields={
                "alignment_stage": "clarifying",
                "working_agreement": session.get("working_agreement") or {},
            },
        )
    if status == "failed" and stage not in confirmed_stages:
        return AlignmentUserMessageStagePlan(update_fields={"alignment_stage": "clarifying"})
    return AlignmentUserMessageStagePlan(update_fields={})
