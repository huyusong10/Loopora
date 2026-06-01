from __future__ import annotations

from loopora.executor_alignment_agreement_responses import (
    alignment_agreement_response as alignment_agreement_response,
    alignment_chinese_agreement_response as alignment_chinese_agreement_response,
    alignment_chinese_improvement_agreement_response as alignment_chinese_improvement_agreement_response,
    alignment_chinese_refund_agreement_response as alignment_chinese_refund_agreement_response,
    alignment_improvement_agreement_response as alignment_improvement_agreement_response,
    alignment_refund_agreement_response as alignment_refund_agreement_response,
)
from loopora.executor_alignment_bundle_fixtures import (
    alignment_bundle_yaml,
    alignment_chinese_bundle_yaml,
    alignment_chinese_improvement_bundle_yaml,
    alignment_improvement_bundle_yaml,
)
from loopora.executor_alignment_readiness_responses import (
    alignment_chinese_improvement_readiness_evidence as alignment_chinese_improvement_readiness_evidence,
    alignment_chinese_readiness_evidence as alignment_chinese_readiness_evidence,
    alignment_improvement_readiness_evidence as alignment_improvement_readiness_evidence,
    alignment_readiness_evidence as alignment_readiness_evidence,
)

def alignment_response(
    *,
    status: str,
    assistant_message: str,
    needs_user_input: bool,
    bundle_yaml: str,
    phase: str,
) -> dict:
    ready = phase == "bundle"
    checklist = {
        "loop_fit": ready,
        "task_scope": ready,
        "success_surface": ready,
        "fake_done_risks": ready,
        "evidence_preferences": ready,
        "execution_strategy": ready,
        "residual_risk_policy": ready,
        "judgment_tradeoffs": ready,
        "local_governance": ready,
        "role_posture": ready,
        "workflow_shape": ready,
        "explicit_confirmation": ready,
    }
    evidence = (
        alignment_readiness_evidence()
        if ready
        else {
            "loop_fit": "",
            "task_scope": "",
            "success_surface": "",
            "fake_done_risks": "",
            "evidence_preferences": "",
            "execution_strategy": "",
            "residual_risk_policy": "",
            "judgment_tradeoffs": "",
            "local_governance": "",
            "role_posture": "",
            "workflow_shape": "",
            "workdir_facts": "",
            "open_questions": "Need more task-shaping answers before compiling the loop plan.",
        }
    )
    return {
        "status": status,
        "assistant_message": assistant_message,
        "needs_user_input": needs_user_input,
        "decision_options": [],
        "bundle_yaml": bundle_yaml,
        "session_ref": {
            "session_id": "",
            "thread_id": "",
            "conversation_id": "",
            "provider": "fake",
            "raw_json": "",
        },
        "alignment_phase": phase,
        "agreement_summary": "Use a focused Builder, evidence Inspector, and strict GateKeeper." if ready else "",
        "readiness_checklist": checklist,
        "readiness_evidence": evidence,
    }


def alignment_default_bundle_response(
    workdir: str,
    *,
    prefers_chinese: bool,
    is_improvement: bool = False,
    use_generic_bundle: bool = False,
) -> dict:
    payload = alignment_response(
        status="bundle",
        assistant_message=("已整理成一个可导入的 Loopora bundle。" if prefers_chinese else "I prepared an importable Loopora bundle."),
        needs_user_input=False,
        bundle_yaml=alignment_chinese_bundle_yaml(workdir) if prefers_chinese else alignment_bundle_yaml(workdir),
        phase="bundle",
    )
    if prefers_chinese:
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来生成这个 Loop 方案。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
    if is_improvement:
        payload["agreement_summary"] = (
            "保留既有 Loop 的稳定意图，并基于反馈修订证据、角色和 GateKeeper 裁决。"
            if prefers_chinese
            else "Preserve the source Loop's stable intent while changing evidence, role posture, and GateKeeper judgment from feedback."
        )
        payload["readiness_evidence"] = alignment_chinese_improvement_readiness_evidence() if prefers_chinese else alignment_improvement_readiness_evidence()
        if not use_generic_bundle:
            payload["bundle_yaml"] = alignment_chinese_improvement_bundle_yaml(workdir) if prefers_chinese else alignment_improvement_bundle_yaml(workdir)
    return payload
