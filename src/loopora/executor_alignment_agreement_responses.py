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
        "readiness_evidence": alignment_readiness_evidence(
            open_questions="Waiting for explicit user confirmation of the working agreement."
        ),
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


def alignment_refund_agreement_response() -> dict:
    payload = alignment_agreement_response()
    payload["assistant_message"] = (
        "Please confirm this refund working agreement; I will compile authorization, eligibility, "
        "audit, provider failure, and support handoff judgment into the Loop."
    )
    payload["agreement_summary"] = (
        "Govern the refund self-service flow around authorization, eligibility, audit trail, provider failure, "
        "double-refund blocking, and support handoff evidence."
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            "The refund task fits Loopora because final production and finance feedback arrives too late; later rounds "
            "must produce intermediate authorization, eligibility, provider failure, audit trail, and support handoff "
            "evidence that can trigger repair or blocking before GateKeeper can close."
        ),
        "task_scope": (
            "Scope is a refund self-service flow for customer admins: authorized admins request eligible refunds, "
            "while disputed, closed-accounting, partial-refund, and double-refund cases are controlled."
        ),
        "success_surface": (
            "Success means an eligible refund can be requested by an authorized admin, recorded with an audit trail, "
            "and traced by support or finance from durable evidence."
        ),
        "fake_done_risks": (
            "Reject pages, buttons, mocked eligibility, or happy-path-only tests that do not prove refund authorization, "
            "auditability, provider failure handling, and double-refund prevention."
        ),
        "evidence_preferences": (
            "Trusted proof is permission checks, eligibility cases, payment-provider failure behavior, audit records, "
            "support handoff artifacts, and final Proven / Weak / Unproven / Blocking / Residual risk buckets."
        ),
        "execution_strategy": (
            "First prove authorization, eligibility, audit, provider failure, and support handoff on a narrow refund path; "
            "defer UI polish or broader billing expansion until those risks have direct evidence."
        ),
        "residual_risk_policy": (
            "Rare provider edge cases may remain only when visible and assigned; unauthorized refunds, missing audit trails, "
            "silent provider failure, and double refunds must block closure."
        ),
        "judgment_tradeoffs": (
            "Prefer a rough but proven refund path over a polished billing screen; reject speed or UI completeness "
            "when it hides authorization, audit, provider, or support risk."
        ),
        "local_governance": (
            "If project-local governance markers are present, Builder reads the applicable rules before editing, "
            "Inspector verifies the related design or test obligations, and GateKeeper treats skipped local governance "
            "as Weak, Unproven, or Blocking without inventing marker contents."
        ),
        "role_posture": (
            "Builder implements refund safety, Inspector tries to disprove authorization and audit claims, "
            "Guide narrows repair if evidence is weak, and GateKeeper blocks unauthorized or double-refund risk."
        ),
        "workflow_shape": (
            "Builder -> Inspector -> Guide repair -> Builder -> GateKeeper fits because refund drift must surface "
            "through evidence before the final GateKeeper verdict, and weak proof must redirect the next pass toward "
            "evidence-first repair rather than broader implementation."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path; billing, payment, and audit code locations must be verified during the run."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }
    return payload


def alignment_chinese_refund_agreement_response() -> dict:
    payload = alignment_chinese_agreement_response()
    payload["assistant_message"] = "请确认退款自助流程工作协议；确认后我会编译授权、资格、审计和支付失败证据。"
    payload["agreement_summary"] = "围绕退款自助流程治理授权、退款资格、审计记录、支付失败、重复退款阻断和客服交接证据。"
    payload["readiness_evidence"] = {
        "loop_fit": "退款任务适合 Loopora，因为真正的生产、财务或合规反馈来得太晚；后续轮次必须产生授权、退款资格、审计记录、支付失败和客服交接等中间证据，用来提前触发修复或阻断，而不是等一次最终反馈。",
        "task_scope": "范围是客户管理员的退款自助流程：授权管理员申请符合资格的退款，并控制争议订单、已关账发票、部分退款和重复退款。",
        "success_surface": "成功意味着授权管理员能申请符合资格的退款，系统记录审计轨迹，客服或财务能追踪退款决定。",
        "fake_done_risks": "拒绝只有页面、按钮、模拟资格或 happy path 测试，却没有证明退款授权、审计、支付失败处理和重复退款防护的结果。",
        "evidence_preferences": "可信证据包括授权检查、退款资格用例、支付服务失败行为、审计记录、客服交接产物，以及最终已证明、弱证据、未证明、阻断和残余风险证据桶。",
        "execution_strategy": "先证明授权、退款资格、支付失败、审计和客服交接，再考虑扩展界面体验；证据薄弱时先收窄到可证明路径。",
        "residual_risk_policy": "少见支付服务边缘情况只有在可见并分配后才可接受；未授权退款、缺失审计、静默支付失败和重复退款必须阻断。",
        "judgment_tradeoffs": "优先选择粗糙但已证明的退款路径，而不是漂亮但未证明授权、审计、支付或客服风险的账单界面。",
        "local_governance": "若存在项目本地治理入口，Builder 先读取适用规则，Inspector 验证相关 design 或 test 义务，GateKeeper 将跳过本地治理视为弱证据、未证明或阻断，且不编造 marker 内容。",
        "role_posture": "Builder 实现退款安全，Inspector 反证授权和审计声明，Guide 在证据薄弱时收窄修复，GateKeeper 阻断未授权或重复退款风险。",
        "workflow_shape": "Builder -> Inspector -> Guide 修复 -> Builder -> GateKeeper 适合退款任务，因为退款偏差必须在最终裁决前通过证据暴露，且弱证据要把下一轮转向补证据，而不是继续铺开实现。",
        "workdir_facts": "已观察到的工作区事实只限目标路径；退款、支付、审计代码位置必须在运行中验证。",
        "open_questions": "等待用户明确确认这份工作协议。",
    }
    return payload
