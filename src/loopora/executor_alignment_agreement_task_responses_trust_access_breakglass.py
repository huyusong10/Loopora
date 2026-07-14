from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import _support_impersonation_readiness_evidence
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_support_impersonation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed support impersonation task")
    payload["assistant_message"] = (
        "Please confirm this support impersonation / break-glass working agreement; I will compile a policy-inspection-first workflow "
        "before any Builder changes."
    )
    payload["agreement_summary"] = (
        f"Govern this support impersonation / break-glass access task through a policy-first Loop: {task}. "
        "Break-glass Policy Inspector first freezes approval, consent, reason, time limit, attribution, MFA/step-up, privacy, tenant negative cases, "
        "audit, revoke/expiry, monitoring, and export-attempt proof targets; Break-glass Builder implements only from that handoff; "
        "Access Evidence Inspector verifies no-ticket, expired, revoked, cross-tenant, privacy, destructive-action, export, audit-integrity, and monitoring evidence; "
        "GateKeeper fails closed on shared-token, login-as happy path, banner-only, missing approval/consent, weak privacy/tenant proof, or weak audit evidence."
    )
    payload["readiness_evidence"] = _support_impersonation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_support_impersonation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 support impersonation / break-glass 任务")
    payload["assistant_message"] = (
        "请确认这份 support impersonation / break-glass 工作协议；确认后我会生成先只读 policy inspection、再 Builder、再证据 Inspector 和 GateKeeper 的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 support impersonation / break-glass access 任务编排 policy-first Loop：{task}。"
        "Break-glass Policy Inspector 先固定 approval、consent、reason、time limit、attribution、MFA/step-up、privacy、tenant 负向、"
        "audit、revoke/expiry、monitoring 和 export-attempt proof targets；Break-glass Builder 只能基于该 handoff 实现；"
        "Access Evidence Inspector 验证 no-ticket、expired、revoked、cross-tenant、privacy、destructive action、export、audit-integrity 和 monitoring evidence；"
        "GateKeeper 对 shared-token、login-as happy path、banner-only、缺少 approval/consent、privacy/tenant 弱证据或 audit 弱证据 fail closed。"
    )
    payload["readiness_evidence"] = _support_impersonation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_support_impersonation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de support impersonation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de support impersonation / break-glass; después compilaré un workflow policy-inspection-first antes de cambios de Builder."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de support impersonation / break-glass access con un Loop policy-first: {task}. "
        "Break-glass Policy Inspector fija approval, consent, reason, time limit, attribution, MFA/step-up, privacy, tenant negatives, audit, revoke/expiry, monitoring y export-attempt; "
        "Builder implementa desde ese handoff; Evidence Inspector verifica no-ticket, expired, revoked, tenant, privacy, destructive action, export, audit-integrity y monitoring; "
        "GateKeeper falla cerrado ante shared-token, login-as happy path, banner-only o evidencia débil."
    )
    payload["readiness_evidence"] = _support_impersonation_readiness_evidence(task, language="es")
    return payload
