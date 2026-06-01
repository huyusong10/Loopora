from __future__ import annotations

from dataclasses import dataclass

from loopora.service_alignment_clarifying_questions import alignment_clarifying_question_issues
from loopora.service_alignment_decision_options import alignment_needs_user_input, default_alignment_decision_options
from loopora.service_alignment_language import alignment_assistant_message_language_issue


@dataclass(frozen=True)
class AlignmentOutputMessagePlan:
    assistant_message: str
    bundle_yaml: str
    missing_items: list[str] | None
    has_bundle_for_options: bool
    event_type: str = ""
    event_payload: dict | None = None
    force_needs_user_input: bool = False
    use_default_decision_options: bool = False


@dataclass(frozen=True)
class AlignmentAgreementBlockCandidate:
    issues: list[str]
    event_type: str
    fallback_message: str


@dataclass(frozen=True)
class AlignmentAgreementBlockPlan:
    event_type: str
    event_payload: dict
    output_updates: dict


@dataclass(frozen=True)
class AlignmentClarifyingStagePlan:
    update_fields: dict
    output_updates: dict
    event_type: str = ""
    event_payload: dict | None = None


def alignment_agreement_block_plan(
    candidates: list[AlignmentAgreementBlockCandidate],
    *,
    prefers_chinese: bool,
) -> AlignmentAgreementBlockPlan | None:
    for candidate in candidates:
        missing = list(candidate.issues)
        if not missing:
            continue
        return AlignmentAgreementBlockPlan(
            event_type=candidate.event_type,
            event_payload={"alignment_stage": "clarifying", "missing": missing},
            output_updates={
                "alignment_phase": "clarifying",
                "agreement_summary": "",
                "bundle_yaml": "",
                "needs_user_input": True,
                "alignment_missing_items": missing,
                "assistant_message": alignment_block_message(
                    prefers_chinese=prefers_chinese,
                    event_type=candidate.event_type,
                    missing=missing,
                    fallback_zh=candidate.fallback_message,
                ),
            },
        )
    return None


def alignment_output_message_plan(
    output: dict,
    *,
    stage_error: str,
    missing_items: list[str] | None,
    prefers_chinese: bool,
) -> AlignmentOutputMessagePlan:
    assistant_message = str(output.get("assistant_message", "") or "").strip()
    bundle_yaml = str(output.get("bundle_yaml", "") or "").strip()
    if stage_error:
        return AlignmentOutputMessagePlan(
            assistant_message=stage_error,
            bundle_yaml="",
            missing_items=None,
            has_bundle_for_options=False,
            event_type="alignment_stage_blocked",
            event_payload={"status": "waiting_user", "error": stage_error},
            force_needs_user_input=True,
            use_default_decision_options=True,
        )
    if assistant_message and alignment_assistant_message_language_issue(assistant_message, prefers_chinese=prefers_chinese):
        return AlignmentOutputMessagePlan(
            assistant_message=alignment_fallback_assistant_message(
                has_bundle=bool(bundle_yaml),
                needs_user_input=alignment_needs_user_input(output),
            ),
            bundle_yaml=bundle_yaml,
            missing_items=missing_items,
            has_bundle_for_options=bool(bundle_yaml),
            event_type="alignment_language_mismatch",
            event_payload={"missing": ["assistant_message"], "surface": "assistant_message"},
            use_default_decision_options=True,
        )
    return AlignmentOutputMessagePlan(
        assistant_message=assistant_message,
        bundle_yaml=bundle_yaml,
        missing_items=missing_items,
        has_bundle_for_options=bool(bundle_yaml),
    )


def alignment_block_message(
    *,
    prefers_chinese: bool,
    event_type: str,
    missing: list[str],
    fallback_zh: str,
) -> str:
    labels = ", ".join(missing)
    if prefers_chinese:
        return fallback_zh.format(missing=labels)
    if event_type == "alignment_checklist_incomplete":
        return (
            "I can't prepare the confirmation agreement yet; these readiness checks are incomplete: "
            f"{labels}. Please answer the next Loop-shaping question first."
        )
    if event_type == "alignment_evidence_incomplete":
        return (
            "I can't prepare the confirmation agreement yet; this readiness evidence is not specific enough: "
            f"{labels}. Please answer the next Loop-shaping question first."
        )
    if event_type == "alignment_improvement_incomplete":
        return (
            "I can't prepare the improvement agreement yet; these source-based improvement judgments "
            f"are not specific enough: {labels}. Please answer the next Loop-shaping question first."
        )
    if event_type == "alignment_language_mismatch":
        return (
            "I can't prepare the confirmation agreement yet; these user-facing agreement fields need "
            f"the user's language: {labels}. Please rewrite those judgments."
        )
    return fallback_zh.format(missing=labels)


def alignment_fallback_assistant_message(*, has_bundle: bool, needs_user_input: bool) -> str:
    if has_bundle:
        return "已整理成一个可导入的 Loopora bundle。"
    if needs_user_input:
        return "我需要继续用中文对齐；请先确认一个会改变 Loop 形状的点：这次更怕结果看起来完成但证据不足，还是推进太慢？"
    return "我需要继续用中文对齐后再继续。"


def alignment_clarifying_reframe_message(*, prefers_chinese: bool) -> str:
    if prefers_chinese:
        return (
            "我先给一个推荐判断：默认应该优先阻断“看起来完成但证据不足”的结果，"
            "这样后续运行不会靠漂亮叙事过关。你可以直接选推荐，也可以改成更偏速度的方向。"
        )
    return (
        "My recommended default is to block results that look done but lack evidence, so the run cannot "
        "pass on a polished story alone. You can choose that recommendation or switch toward speed."
    )


def alignment_clarifying_stage_plan(output: dict, *, prefers_chinese: bool) -> AlignmentClarifyingStagePlan:
    question_issues = alignment_clarifying_question_issues(output)
    if not question_issues:
        return AlignmentClarifyingStagePlan(update_fields={"alignment_stage": "clarifying"}, output_updates={})
    return AlignmentClarifyingStagePlan(
        update_fields={"alignment_stage": "clarifying"},
        output_updates={
            "assistant_message": alignment_clarifying_reframe_message(prefers_chinese=prefers_chinese),
            "decision_options": default_alignment_decision_options(prefers_chinese=prefers_chinese),
            "needs_user_input": True,
            "bundle_yaml": "",
        },
        event_type="alignment_question_reframed",
        event_payload={"alignment_stage": "clarifying", "issues": question_issues},
    )
