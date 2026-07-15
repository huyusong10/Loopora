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
    alignment_missing_item_label as alignment_missing_item_label,
    alignment_missing_items_followup_question as alignment_missing_items_followup_question,
    alignment_output_message_plan as alignment_output_message_plan,
)
from loopora.service_alignment_traceability_projection import (
    alignment_bundle_agreement_projection_text as alignment_bundle_agreement_projection_text,
    alignment_bundle_runtime_responsibility_projection_text as alignment_bundle_runtime_responsibility_projection_text,
    alignment_governance_marker_responsibility_issues as alignment_governance_marker_responsibility_issues,
    alignment_session_user_task_text as alignment_session_user_task_text,
    alignment_traceability_term_is_present as alignment_traceability_term_is_present,
    normalize_alignment_traceability_text as normalize_alignment_traceability_text,
)

"""Generated-bundle issue selection for alignment output staging."""

from loopora.alignment_readiness_rules import (
    has_any_marker,
    workdir_facts_claims_unsupported_observed_stack,
)

from loopora.service_alignment_traceability_projection import alignment_bundle_visible_text

def alignment_bundle_workdir_fact_issues(bundle: dict, *, workdir_snapshot: str) -> list[str]:
    fields: dict[str, object] = {
        "collaboration_summary": bundle.get("collaboration_summary"),
        "spec.markdown": (bundle.get("spec") or {}).get("markdown") if isinstance(bundle.get("spec"), dict) else "",
        "workflow.collaboration_intent": (
            (bundle.get("workflow") or {}).get("collaboration_intent")
            if isinstance(bundle.get("workflow"), dict)
            else ""
        ),
    }
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        key = str(role.get("key", "") or "role")
        for field_name in ("description", "prompt_markdown", "posture_notes"):
            fields[f"role_definition {key}.{field_name}"] = role.get(field_name)
    return [
        f"bundle field {field_name} must not claim an observed workdir stack unsupported by Workdir Snapshot"
        for field_name, value in fields.items()
        if workdir_facts_claims_unsupported_observed_stack(
            str(value or "").lower(),
            workdir_snapshot=workdir_snapshot,
        )
    ]

def alignment_improvement_bundle_issues(working_agreement: object, bundle: dict) -> list[str]:
    agreement = working_agreement if isinstance(working_agreement, dict) else {}
    if str(agreement.get("mode") or "") != "improvement":
        return []
    text = alignment_bundle_visible_text(bundle).lower()
    issues: list[str] = []
    if not has_any_marker(
        text,
        (
            "source intent",
            "source loop",
            "source bundle",
            "source workdir",
            "source defaults",
            "source posture",
            "stable intent",
            "stable task intent",
            "existing loop",
            "existing bundle",
            "base candidate",
            "既有意图",
            "来源 loop",
            "来源 bundle",
            "来源意图",
            "稳定意图",
            "原 bundle",
        ),
    ):
        issues.append("improvement bundle must state what source intent, workdir, defaults, or posture is preserved")
    if not has_any_marker(
        text,
        (
            "feedback-driven",
            "feedback",
            "run evidence",
            "evidence summary",
            "evidence gap",
            "gatekeeper verdict",
            "coverage",
            "delta",
            "反馈驱动",
            "反馈",
            "运行证据",
            "证据摘要",
            "证据缺口",
            "变化",
        ),
    ):
        issues.append("improvement bundle must state the feedback-driven governance delta")
    if not has_any_marker(
        text,
        (
            "spec",
            "role",
            "roles",
            "workflow",
            "evidence",
            "gatekeeper",
            "证据",
            "角色",
            "裁决",
            "治理面",
            "任务契约",
        ),
    ):
        issues.append("improvement bundle must map the delta to spec, roles, workflow, evidence, or GateKeeper")
    source = agreement.get("source") if isinstance(agreement.get("source"), dict) else {}
    source_bundle_id = str(source.get("source_bundle_id") or "").strip()
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    generated_bundle_id = str(metadata.get("bundle_id") or "").strip()
    if source_bundle_id and generated_bundle_id == source_bundle_id:
        issues.append(
            "improvement bundle must not reuse the source bundle id as metadata.bundle_id; "
            "leave bundle_id empty or choose a new standalone candidate id"
        )
    has_run_context = str(source.get("source_type") or "") == "run" and (
        source.get("coverage_summary")
        or source.get("evidence_summary")
        or source.get("task_verdict")
        or source.get("gatekeeper_verdict")
    )
    if has_run_context and not has_any_marker(
        text,
        (
            "run evidence",
            "coverage",
            "verdict",
            "gatekeeper verdict",
            "evidence summary",
            "运行证据",
            "覆盖",
            "裁决",
            "证据摘要",
        ),
    ):
        issues.append("improvement bundle must translate run evidence, coverage, or GateKeeper verdict into bundle changes")
    source_completion_mode = str(source.get("source_completion_mode") or "").strip().lower()
    if source_completion_mode and source_completion_mode != "gatekeeper":
        has_source_completion_mode_delta = has_any_marker(
            text,
            (
                "completion mode",
                "completion_mode",
                "`rounds`",
                "rounds completion",
                "source uses rounds",
                "run lifecycle",
                "lifecycle completion",
                "source completion",
                "完成模式",
                "运行生命周期",
                "生命周期收束",
            ),
        ) and has_any_marker(
            text,
            (
                "gatekeeper",
                "task verdict",
                "evidence-based verdict",
                "证据裁决",
                "loop 裁决",
                "任务裁决",
                "守门",
            ),
        )
        if not has_source_completion_mode_delta:
            issues.append("improvement bundle must state the source completion-mode governance delta")
    return issues


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
        labels = ", ".join(alignment_missing_item_label(item, prefers_chinese=gate.prefers_chinese) for item in missing)
        error = (
            f"我还不能直接生成 Loop 方案；对齐检查还缺：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; these readiness checks are incomplete: {labels}. Please fill in this information first."
        )
    elif gate.evidence_issues:
        labels = ", ".join(alignment_missing_item_label(item, prefers_chinese=gate.prefers_chinese) for item in gate.evidence_issues)
        error = (
            f"我还不能直接生成 Loop 方案；这些对齐证据还不够具体：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; this readiness evidence is not specific enough: {labels}. Please fill in this information first."
        )
    elif gate.improvement_issues:
        labels = ", ".join(alignment_missing_item_label(item, prefers_chinese=gate.prefers_chinese) for item in gate.improvement_issues)
        error = (
            f"我还不能直接生成 Loop 方案；这些改进判断还不够具体：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; these improvement judgments are not specific enough: {labels}. Please fill in this information first."
        )
    elif gate.language_issues:
        labels = ", ".join(alignment_missing_item_label(item, prefers_chinese=gate.prefers_chinese) for item in gate.language_issues)
        error = (
            f"我还不能直接生成 Loop 方案；这些用户可见对齐证据需要使用中文：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; these user-facing alignment fields need the user's language: {labels}. Please fill in this information first."
        )
    return error


def alignment_bundle_stage_missing_items(gate: AlignmentBundleStageGate) -> list[str]:
    items: list[str] = []
    ready_for_bundle_gate = (
        gate.stage in gate.confirmed_stages
        and gate.phase == "bundle"
        and bool(gate.agreement_summary)
        and isinstance(gate.checklist, dict)
    )
    if ready_for_bundle_gate and isinstance(gate.checklist, dict):
        missing = [key for key in gate.readiness_keys if gate.checklist.get(key) is not True]
        if missing:
            items = missing
        elif gate.evidence_issues:
            items = list(gate.evidence_issues)
        elif gate.improvement_issues:
            items = list(gate.improvement_issues)
        elif gate.language_issues:
            items = list(gate.language_issues)
    return items
