from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from loopora.service_alignment_decision_options import (
    default_alignment_decision_options,
    normalize_alignment_missing_items,
    visible_alignment_decision_options,
)
from loopora.service_alignment_language import alignment_generation_prefers_chinese, alignment_prefers_chinese
from loopora.service_alignment_output_stage import alignment_output_bundle_stage_error
from loopora.service_alignment_stage_messages import alignment_output_message_plan


class AlignmentOutputMessageRepository(Protocol):
    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class AlignmentOutputMessageContext:
    repository: AlignmentOutputMessageRepository


@dataclass(frozen=True)
class AlignmentOutputMessageRequest:
    session_id: str
    session: dict
    output: dict
    confirmed_stages: set[str]
    missing_item_ids: set[str]
    readiness_keys: list[str]
    readiness_evidence_keys: list[str]


@dataclass(frozen=True)
class AlignmentOutputMessageResult:
    assistant_message: str
    bundle_yaml: str
    decision_options: list[dict]
    missing_items: list[str] | None


def alignment_output_message_bundle_and_options(
    context: AlignmentOutputMessageContext,
    request: AlignmentOutputMessageRequest,
) -> AlignmentOutputMessageResult:
    output = request.output
    session = request.session
    bundle_yaml = str(output.get("bundle_yaml", "") or "").strip()
    missing_items = normalize_alignment_missing_items(
        output.get("alignment_missing_items"),
        allowed_item_ids=request.missing_item_ids,
    )
    stage_error = (
        alignment_output_bundle_stage_error(
            session,
            output,
            confirmed_stages=request.confirmed_stages,
            readiness_keys=request.readiness_keys,
            readiness_evidence_keys=request.readiness_evidence_keys,
        )
        if bundle_yaml
        else ""
    )
    message_plan = alignment_output_message_plan(
        output,
        stage_error=stage_error,
        missing_items=missing_items,
        prefers_chinese=alignment_generation_prefers_chinese(session),
    )
    if message_plan.force_needs_user_input:
        output["needs_user_input"] = True
    if message_plan.event_type:
        context.repository.append_alignment_event(
            request.session_id,
            message_plan.event_type,
            message_plan.event_payload or {},
        )
    if message_plan.use_default_decision_options:
        output["decision_options"] = default_alignment_decision_options(prefers_chinese=alignment_prefers_chinese(session))
    decision_options = visible_alignment_decision_options(
        output,
        has_bundle=message_plan.has_bundle_for_options,
        prefers_chinese=alignment_prefers_chinese(session),
    )
    return AlignmentOutputMessageResult(
        assistant_message=message_plan.assistant_message,
        bundle_yaml=message_plan.bundle_yaml,
        decision_options=decision_options,
        missing_items=message_plan.missing_items,
    )
