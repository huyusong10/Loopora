from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import _refund_repair_readiness_evidence
from loopora.executor_alignment_agreement_responses import alignment_agreement_response, alignment_chinese_agreement_response


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
    payload["readiness_evidence"] = _refund_repair_readiness_evidence("", language="en")
    return payload


def alignment_chinese_refund_agreement_response() -> dict:
    payload = alignment_chinese_agreement_response()
    payload["assistant_message"] = "请确认退款自助流程工作协议；确认后我会编译授权、资格、审计和支付失败证据。"
    payload["agreement_summary"] = "围绕退款自助流程治理授权、退款资格、审计记录、支付失败、重复退款阻断和客服交接证据。"
    payload["readiness_evidence"] = _refund_repair_readiness_evidence("", language="zh")
    return payload
