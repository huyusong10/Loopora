from __future__ import annotations

from loopora.executor_alignment_readiness_responses import (
    alignment_chinese_improvement_readiness_evidence,
    alignment_chinese_readiness_evidence,
    alignment_improvement_readiness_evidence,
    alignment_readiness_evidence,
)


def alignment_agreement_response() -> dict:
    return {
        "status": "question",
        "assistant_message": "我会按这个工作协议生成：先做聚焦实现，再收集可复现证据，最后由守门者保守裁决。请回复“确认”后我再生成 Loop 方案。",
        "needs_user_input": True,
        "decision_options": [
            {
                "id": "confirm_agreement",
                "label": "采用这个方向（推荐）",
                "description": "按这份工作协议生成 Loop 方案。",
                "recommended": True,
                "user_reply": "确认，采用这个方向。",
            },
            {
                "id": "adjust_agreement",
                "label": "我想调整",
                "description": "先修改其中一个判断，再生成方案。",
                "recommended": False,
                "user_reply": "我想调整这份工作协议：",
            },
        ],
        "bundle_yaml": "",
        "session_ref": {
            "session_id": "",
            "thread_id": "",
            "conversation_id": "",
            "provider": "fake",
            "raw_json": "",
        },
        "alignment_phase": "agreement",
        "agreement_summary": "Use a focused Builder, evidence Inspector, and strict GateKeeper.",
        "readiness_checklist": {
            "loop_fit": True,
            "task_scope": True,
            "success_surface": True,
            "fake_done_risks": True,
            "evidence_preferences": True,
            "execution_strategy": True,
            "residual_risk_policy": True,
            "judgment_tradeoffs": True,
            "local_governance": True,
            "role_posture": True,
            "workflow_shape": True,
            "explicit_confirmation": False,
        },
        "readiness_evidence": alignment_readiness_evidence(open_questions="Waiting for explicit user confirmation of the working agreement."),
    }


def alignment_chinese_agreement_response() -> dict:
    payload = alignment_agreement_response()
    payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
    payload["readiness_evidence"] = alignment_chinese_readiness_evidence(open_questions="等待用户明确确认这份工作协议。")
    return payload


def alignment_improvement_agreement_response() -> dict:
    payload = alignment_agreement_response()
    payload["assistant_message"] = (
        "Please confirm this improvement agreement; I will preserve the stable source Loop and revise only the feedback-driven governance surfaces."
    )
    payload["agreement_summary"] = (
        "Preserve the existing Loop's stable task intent and workdir, then change the evidence, role posture, and GateKeeper strictness that feedback shows are weak."
    )
    payload["readiness_evidence"] = alignment_improvement_readiness_evidence(
        open_questions="Waiting for explicit user confirmation of the improvement agreement."
    )
    return payload


def alignment_chinese_improvement_agreement_response() -> dict:
    payload = alignment_chinese_agreement_response()
    payload["assistant_message"] = "请确认这份改进协议；我会保留既有 Loop 的稳定意图，只修订反馈指向的治理面。"
    payload["agreement_summary"] = "保留既有 Loop 的稳定任务意图和 workdir，并基于反馈改进证据、角色姿态和 GateKeeper 严格度。"
    payload["readiness_evidence"] = alignment_chinese_improvement_readiness_evidence(open_questions="等待用户明确确认这份改进协议。")
    return payload


def alignment_chinese_refactor_improvement_agreement_response(feedback_text: str) -> dict:
    from loopora.executor_alignment_agreement_improvement_responses import (
        alignment_chinese_refactor_improvement_agreement_response as _alignment_chinese_refactor_improvement_agreement_response,
    )

    return _alignment_chinese_refactor_improvement_agreement_response(feedback_text)


def alignment_task_anchored_agreement_response(
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> dict:
    from loopora.executor_alignment_agreement_task_dispatch import (
        alignment_task_anchored_agreement_response as _alignment_task_anchored_agreement_response,
    )

    return _alignment_task_anchored_agreement_response(
        task_text,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )


def alignment_refund_agreement_response() -> dict:
    from loopora.executor_alignment_agreement_refund_responses import (
        alignment_refund_agreement_response as _alignment_refund_agreement_response,
    )

    return _alignment_refund_agreement_response()


def alignment_chinese_refund_agreement_response() -> dict:
    from loopora.executor_alignment_agreement_refund_responses import (
        alignment_chinese_refund_agreement_response as _alignment_chinese_refund_agreement_response,
    )

    return _alignment_chinese_refund_agreement_response()
