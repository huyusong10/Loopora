from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.alignment_readiness_rules import (
    alignment_improvement_readiness_issues,
    readiness_evidence_issues,
)
from loopora.service_alignment_agreement_stage import (
    alignment_agreement_ready_stage_plan,
    alignment_agreement_readiness_checklist_issues,
    alignment_agreement_working_agreement,
    alignment_merge_improvement_context,
    alignment_visible_agreement_message,
)
from loopora.service_alignment_language import (
    alignment_agreement_language_issues,
    alignment_generation_prefers_chinese,
    alignment_prefers_chinese,
)
from loopora.service_alignment_stage import (
    AlignmentBundleStageGate,
    alignment_bundle_stage_error,
)
from loopora.service_alignment_stage_messages import (
    AlignmentAgreementBlockCandidate,
    alignment_agreement_block_plan,
    alignment_clarifying_stage_plan,
)
from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot
from loopora.utils import utc_now


@dataclass(frozen=True)
class AlignmentOutputStagePlan:
    update_fields: dict
    output_updates: dict
    event_type: str = ""
    event_payload: dict | None = None


class AlignmentOutputStageRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class AlignmentOutputStageContext:
    repository: AlignmentOutputStageRepository
    decorate_session: Callable[[dict], dict]
    now: Callable[[], str] = utc_now


@dataclass(frozen=True)
class AlignmentOutputStageRequest:
    session_id: str
    session: dict
    output: dict
    readiness_keys: list[str]
    readiness_evidence_keys: list[str]


def apply_alignment_output_stage(
    context: AlignmentOutputStageContext,
    request: AlignmentOutputStageRequest,
) -> dict:
    stage_plan = alignment_output_stage_plan(
        request.session,
        request.output,
        captured_at=context.now(),
        readiness_keys=request.readiness_keys,
        readiness_evidence_keys=request.readiness_evidence_keys,
    )
    if stage_plan is None:
        return request.session
    updated = context.repository.update_alignment_session(request.session_id, **stage_plan.update_fields)
    request.output.update(stage_plan.output_updates)
    if stage_plan.event_type:
        context.repository.append_alignment_event(
            request.session_id,
            stage_plan.event_type,
            stage_plan.event_payload or {},
        )
    return context.decorate_session(updated)


def alignment_output_stage_plan(
    session: dict,
    output: dict,
    *,
    captured_at: str,
    readiness_keys: list[str],
    readiness_evidence_keys: list[str],
) -> AlignmentOutputStagePlan | None:
    phase = str(output.get("alignment_phase", "") or "").strip()
    agreement_summary = str(output.get("agreement_summary", "") or "").strip()
    checklist = output.get("readiness_checklist")
    if phase == "agreement" and agreement_summary:
        block_plan = alignment_agreement_block_plan(
            [
                AlignmentAgreementBlockCandidate(
                    issues=alignment_agreement_readiness_checklist_issues(
                        checklist,
                        readiness_keys=readiness_keys,
                    ),
                    event_type="alignment_checklist_incomplete",
                    fallback_message="我还不能整理确认协议；这些对齐检查还没完成：{missing}。请先问一个会改变 Loop 方案的问题。",
                ),
                AlignmentAgreementBlockCandidate(
                    issues=readiness_evidence_issues(
                        output,
                        workdir_snapshot=alignment_workdir_snapshot(Path(session["workdir"])),
                    ),
                    event_type="alignment_evidence_incomplete",
                    fallback_message="我还不能整理确认协议；这些对齐证据还不够具体：{missing}。请先补一个会改变 Loop 方案的问题。",
                ),
                AlignmentAgreementBlockCandidate(
                    issues=alignment_improvement_readiness_issues(session, output),
                    event_type="alignment_improvement_incomplete",
                    fallback_message="我还不能整理改进协议；这些基于已有方案的改进判断还不够具体：{missing}。请先补一个会改变 Loop 方案的问题。",
                ),
                AlignmentAgreementBlockCandidate(
                    issues=alignment_agreement_language_issues(
                        output,
                        evidence_keys=readiness_evidence_keys,
                        prefers_chinese=alignment_generation_prefers_chinese(session),
                    ),
                    event_type="alignment_language_mismatch",
                    fallback_message="我还不能整理确认协议；用户可见工作协议需要使用中文：{missing}。请用中文重写这些判断。",
                ),
            ],
            prefers_chinese=alignment_prefers_chinese(session),
        )
        if block_plan is not None:
            return AlignmentOutputStagePlan(
                update_fields={"alignment_stage": "clarifying"},
                output_updates=block_plan.output_updates,
                event_type=block_plan.event_type,
                event_payload=block_plan.event_payload,
            )
        working_agreement = alignment_agreement_working_agreement(output, captured_at=captured_at)
        working_agreement = alignment_merge_improvement_context(
            session.get("working_agreement"),
            working_agreement,
        )
        ready_plan = alignment_agreement_ready_stage_plan(
            working_agreement,
            assistant_message=alignment_visible_agreement_message(
                working_agreement,
                prefers_chinese=alignment_prefers_chinese(session),
            ),
            prefers_chinese=alignment_prefers_chinese(session),
        )
        return AlignmentOutputStagePlan(
            update_fields=ready_plan.update_fields,
            output_updates=ready_plan.output_updates,
            event_type=ready_plan.event_type,
            event_payload=ready_plan.event_payload,
        )
    if phase == "clarifying":
        clarifying_plan = alignment_clarifying_stage_plan(
            output,
            prefers_chinese=alignment_prefers_chinese(session),
        )
        return AlignmentOutputStagePlan(
            update_fields=clarifying_plan.update_fields,
            output_updates=clarifying_plan.output_updates,
            event_type=clarifying_plan.event_type,
            event_payload=clarifying_plan.event_payload,
        )
    return None


def alignment_output_bundle_stage_error(
    session: dict,
    output: dict,
    *,
    confirmed_stages: set[str],
    readiness_keys: list[str],
    readiness_evidence_keys: list[str],
) -> str:
    stage = str(session.get("alignment_stage", "") or "clarifying").strip()
    phase = str(output.get("alignment_phase", "") or "").strip()
    agreement_summary = str(output.get("agreement_summary", "") or "").strip()
    checklist = output.get("readiness_checklist")
    evidence_issues = readiness_evidence_issues(
        output,
        workdir_snapshot=alignment_workdir_snapshot(Path(session["workdir"])),
    )
    improvement_issues = alignment_improvement_readiness_issues(session, output)
    language_issues = alignment_agreement_language_issues(
        output,
        evidence_keys=readiness_evidence_keys,
        prefers_chinese=alignment_generation_prefers_chinese(session),
    )
    return alignment_bundle_stage_error(
        AlignmentBundleStageGate(
            stage=stage,
            confirmed_stages=confirmed_stages,
            phase=phase,
            agreement_summary=agreement_summary,
            checklist=checklist,
            readiness_keys=readiness_keys,
            evidence_issues=evidence_issues,
            improvement_issues=improvement_issues,
            language_issues=language_issues,
            prefers_chinese=alignment_prefers_chinese(session),
        )
    )
