from __future__ import annotations

from dataclasses import dataclass

from loopora.service_alignment_agreement_stage import (
    AlignmentAgreementReadyStagePlan as AlignmentAgreementReadyStagePlan,
    AlignmentUserMessageStagePlan as AlignmentUserMessageStagePlan,
    alignment_agreement_ready_stage_plan as alignment_agreement_ready_stage_plan,
    alignment_agreement_readiness_checklist_issues as alignment_agreement_readiness_checklist_issues,
    alignment_agreement_text_snippet as alignment_agreement_text_snippet,
    alignment_agreement_working_agreement as alignment_agreement_working_agreement,
    alignment_merge_improvement_context as alignment_merge_improvement_context,
    alignment_message_confirms_agreement as alignment_message_confirms_agreement,
    alignment_user_message_stage_plan as alignment_user_message_stage_plan,
    alignment_visible_agreement_message as alignment_visible_agreement_message,
)
from loopora.service_alignment_clarifying_questions import (
    alignment_questionnaire_overload as alignment_questionnaire_overload,
)
from loopora.service_alignment_language import (
    alignment_agreement_language_issues as alignment_agreement_language_issues,
    alignment_bundle_language_issues as alignment_bundle_language_issues,
)
from loopora.service_alignment_stage_messages import (
    AlignmentAgreementBlockCandidate as AlignmentAgreementBlockCandidate,
    AlignmentAgreementBlockPlan as AlignmentAgreementBlockPlan,
    AlignmentClarifyingStagePlan as AlignmentClarifyingStagePlan,
    AlignmentOutputMessagePlan as AlignmentOutputMessagePlan,
    alignment_agreement_block_plan as alignment_agreement_block_plan,
    alignment_block_message as alignment_block_message,
    alignment_clarifying_reframe_message as alignment_clarifying_reframe_message,
    alignment_clarifying_stage_plan as alignment_clarifying_stage_plan,
    alignment_fallback_assistant_message as alignment_fallback_assistant_message,
    alignment_output_message_plan as alignment_output_message_plan,
)
from loopora.service_alignment_stage_bundle_issues import (
    alignment_bundle_workdir_fact_issues as alignment_bundle_workdir_fact_issues,
    alignment_improvement_bundle_issues as alignment_improvement_bundle_issues,
)
from loopora.service_alignment_traceability_projection import (
    alignment_bundle_agreement_projection_text as alignment_bundle_agreement_projection_text,
    alignment_bundle_runtime_responsibility_projection_text as alignment_bundle_runtime_responsibility_projection_text,
    alignment_governance_marker_responsibility_issues as alignment_governance_marker_responsibility_issues,
    alignment_session_user_task_text as alignment_session_user_task_text,
    alignment_traceability_term_is_present as alignment_traceability_term_is_present,
    normalize_alignment_traceability_text as normalize_alignment_traceability_text,
)


@dataclass(frozen=True)
class AlignmentBundleStageGate:
    stage: str
    confirmed_stages: set[str]
    phase: str
    agreement_summary: str
    checklist: object
    readiness_keys: list[str]
    evidence_issues: list[str]
    improvement_issues: list[str]
    language_issues: list[str]
    prefers_chinese: bool


def alignment_bundle_stage_error(gate: AlignmentBundleStageGate) -> str:
    missing = [key for key in gate.readiness_keys if isinstance(gate.checklist, dict) and gate.checklist.get(key) is not True]
    error = ""
    if gate.stage not in gate.confirmed_stages:
        error = (
            "我还需要先完成需求对齐并得到你的明确确认，再生成 Loop 方案。"
            if gate.prefers_chinese
            else "I need to finish alignment and get your explicit confirmation before generating the Loop plan."
        )
    elif gate.phase != "bundle":
        error = (
            "我还需要先完成需求对齐，再生成 Loop 方案。请先确认边界、成功标准和协作方式。"
            if gate.prefers_chinese
            else "I need to finish alignment before generating the Loop plan. Please confirm the boundary, success criteria, and collaboration shape first."
        )
    elif not gate.agreement_summary:
        error = (
            "我还需要先整理一份工作协议摘要并得到确认，然后再生成 Loop 方案。"
            if gate.prefers_chinese
            else "I need a confirmed working agreement summary before generating the Loop plan."
        )
    elif not isinstance(gate.checklist, dict):
        error = (
            "我还需要先补齐对齐检查清单，再生成 Loop 方案。"
            if gate.prefers_chinese
            else "I need the alignment readiness checklist before generating the Loop plan."
        )
    elif missing:
        labels = ", ".join(missing)
        error = (
            f"我还不能直接生成 Loop 方案；对齐检查还缺：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; these readiness checks are incomplete: {labels}. Please fill in this information first."
        )
    elif gate.evidence_issues:
        labels = ", ".join(gate.evidence_issues)
        error = (
            f"我还不能直接生成 Loop 方案；这些对齐证据还不够具体：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; this readiness evidence is not specific enough: {labels}. Please fill in this information first."
        )
    elif gate.improvement_issues:
        labels = ", ".join(gate.improvement_issues)
        error = (
            f"我还不能直接生成 Loop 方案；这些改进判断还不够具体：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; these improvement judgments are not specific enough: {labels}. Please fill in this information first."
        )
    elif gate.language_issues:
        labels = ", ".join(gate.language_issues)
        error = f"我还不能直接生成 Loop 方案；这些用户可见对齐证据需要使用中文：{labels}。请先补齐这些信息。"
    return error
