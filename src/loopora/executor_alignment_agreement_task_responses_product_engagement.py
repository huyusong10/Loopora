from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _notification_subscription_deliverability_readiness_evidence,
    _schedule_timezone_recurrence_readiness_evidence,
    _support_ticket_sla_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_support_ticket_sla_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed support ticket SLA task")
    payload["assistant_message"] = (
        "Please confirm this support ticket SLA working agreement; I will compile a support-ticket contract-first workflow "
        "with parallel Lifecycle Evidence and Access Notification Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this support ticket triage / SLA escalation task through a contract-first Loop: {task}. "
        "Support Ticket Contract Inspector first freezes email/API import, dedupe/merge, queue and lifecycle state machine, claim/assign/priority/status permissions, SLA clock and breach/escalation rules, queue health, notification dedupe, audit notes, tenant isolation, PII redaction, monitoring, and governance; "
        "Ticket SLA Builder implements only from that handoff; Ticket Lifecycle Inspector and Access Notification Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on Kanban-only, manager-dashboard-only, queued/open status-only, missing import dedupe, missing lifecycle transitions, missing SLA clock or breach escalation proof, missing permission or tenant negatives, missing notification suppression, missing audit/PII proof, or skipped local governance."
    )
    payload["readiness_evidence"] = _support_ticket_sla_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_support_ticket_sla_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 support ticket SLA 任务")
    payload["assistant_message"] = (
        "请确认这份 support ticket SLA 工作协议；确认后我会生成 Support Ticket Contract Inspector 先固定工单生命周期和 SLA 契约、"
        "Ticket SLA Builder 再实现、Ticket Lifecycle Inspector 与 Access Notification Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 support ticket triage / SLA escalation 任务编排 contract-first Loop：{task}。"
        "Support Ticket Contract Inspector 先只读固定 email/API import、dedupe/merge、queue 和 lifecycle state machine、claim/assign/priority/status permissions、SLA clock 与 breach/escalation rules、queue health、notification dedupe、audit notes、tenant isolation、PII redaction、monitoring 和 governance；"
        "Ticket SLA Builder 只能基于该 handoff 实现；Ticket Lifecycle Inspector 与 Access Notification Audit Inspector 并行检查；"
        "GateKeeper 对 Kanban-only、manager-dashboard-only、queued/open status-only、import dedupe 缺失、lifecycle transitions 缺失、SLA clock 或 breach escalation proof 缺失、permission/tenant negatives 缺失、notification suppression 缺失、audit/PII proof 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _support_ticket_sla_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_support_ticket_sla_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de support ticket SLA confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de support ticket SLA; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Lifecycle Evidence y Access Notification Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de support ticket triage / SLA escalation con un Loop contract-first: {task}. "
        "Support Ticket Contract Inspector fija import email/API, dedupe/merge, queue y lifecycle state machine, permisos de claim/assign/priority/status, SLA clock, breach/escalation, queue health, notification dedupe, audit notes, tenant isolation, PII redaction, monitoring y governance; "
        "Ticket SLA Builder implementa desde ese handoff; Ticket Lifecycle Inspector y Access Notification Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante Kanban-only, manager-dashboard-only, status-only, missing dedupe, lifecycle transitions, SLA/escalation, permission or tenant negatives, notification suppression, audit/PII proof o governance omitida."
    )
    payload["readiness_evidence"] = _support_ticket_sla_readiness_evidence(task, language="es")
    return payload


def alignment_english_schedule_timezone_recurrence_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed schedule timezone recurrence task")
    payload["assistant_message"] = (
        "Please confirm this schedule timezone recurrence working agreement; I will compile a "
        "schedule-contract-first workflow with parallel Temporal Correctness and Delivery Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this weekly digest schedule / timezone recurrence task through a contract-first Loop: {task}. "
        "Schedule Contract Inspector first freezes timezone source, user timezone fallback, local Monday 09:00 semantics, DST spring-forward/fall-back samples, missed-run catch-up window, retry/provider replay idempotency, subscription/disabled/tenant/locale filters, provider delivery/failure surface, audit fields, monitoring, migration, and governance; "
        "Digest Scheduler Builder implements only from that handoff; Temporal Correctness Inspector and Delivery Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on cron-only, local-trigger-only, UTC-only, single-timezone-only, provider-accepted-only, missing DST boundary, missing catch-up/idempotency negative, missing subscription/disabled negative, missing audit/monitoring, missing migration, or skipped governance."
    )
    payload["readiness_evidence"] = _schedule_timezone_recurrence_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_schedule_timezone_recurrence_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 schedule timezone recurrence 任务")
    payload["assistant_message"] = (
        "请确认这份 schedule timezone recurrence 工作协议；确认后我会生成 Schedule Contract Inspector 先固定时间契约、"
        "Digest Scheduler Builder 再实现、Temporal Correctness Inspector 与 Delivery Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 weekly digest schedule / timezone recurrence 任务编排 contract-first Loop：{task}。"
        "Schedule Contract Inspector 先只读固定 timezone source、user timezone fallback、本地周一 09:00、DST spring-forward/fall-back 样本、missed-run catch-up window、retry/provider replay idempotency、subscription/disabled/tenant/locale filters、provider delivery/failure surface、audit fields、monitoring、migration 和 governance；"
        "Digest Scheduler Builder 只能基于该 handoff 实现；Temporal Correctness Inspector 与 Delivery Audit Inspector 并行检查；"
        "GateKeeper 对 cron-only、local-trigger-only、UTC-only、single-timezone-only、provider-accepted-only、DST boundary 缺失、catch-up/idempotency negative 缺失、subscription/disabled negative 缺失、audit/monitoring 缺失、migration 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _schedule_timezone_recurrence_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_schedule_timezone_recurrence_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de schedule timezone recurrence confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de schedule timezone recurrence; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Temporal Correctness y Delivery Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de weekly digest schedule / timezone recurrence con un Loop contract-first: {task}. "
        "Schedule Contract Inspector fija timezone source, fallback, local Monday 09:00, DST, catch-up, retry/provider replay, subscription/disabled/tenant/locale filters, provider delivery/failure, audit fields, monitoring, migration y governance; "
        "Digest Scheduler Builder implementa desde ese handoff; Temporal Correctness Inspector y Delivery Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante cron-only, local-trigger-only, UTC-only, single-timezone-only, provider-accepted-only, missing DST, catch-up/idempotency, subscription/disabled negatives, audit/monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _schedule_timezone_recurrence_readiness_evidence(task, language="es")
    return payload


def alignment_english_notification_subscription_deliverability_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed notification deliverability task")
    payload["assistant_message"] = (
        "Please confirm this notification subscription-deliverability working agreement; I will compile a "
        "notification-contract-first workflow with parallel Deliverability Evidence and Template Privacy inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this lifecycle campaign email / notification deliverability task through a contract-first Loop: {task}. "
        "Notification Contract Inspector first freezes subscription eligibility, preferences, unsubscribe, suppression, bounce/complaint/drop events, disabled-user and tenant filters, locale/templates, redaction, provider webhook replay/idempotency, retry/DLQ, delivery audit, monitoring, migration, and governance; "
        "Campaign Email Builder implements only from that handoff; Deliverability Evidence Inspector and Template Privacy Inspector inspect in parallel; "
        "GateKeeper fails closed on one-test-email, provider-accepted-only, UI-toggle-only, happy-path-send-only, docs-only unsubscribe, missing bounce/complaint proof, missing duplicate negatives, missing locale/template proof, missing redaction, missing audit reconciliation, missing monitoring, missing migration, or skipped governance."
    )
    payload["readiness_evidence"] = _notification_subscription_deliverability_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_notification_subscription_deliverability_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 notification deliverability 任务")
    payload["assistant_message"] = (
        "请确认这份 notification subscription-deliverability 工作协议；确认后我会生成 Notification Contract Inspector 先固定通知契约、"
        "Campaign Email Builder 再实现、Deliverability Evidence Inspector 与 Template Privacy Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 lifecycle campaign email / notification deliverability 任务编排 contract-first Loop：{task}。"
        "Notification Contract Inspector 先只读固定 subscription eligibility、preferences、unsubscribe、suppression、bounce/complaint/drop events、disabled-user 和 tenant filters、locale/templates、redaction、provider webhook replay/idempotency、retry/DLQ、delivery audit、monitoring、migration 和 governance；"
        "Campaign Email Builder 只能基于该 handoff 实现；Deliverability Evidence Inspector 与 Template Privacy Inspector 并行检查；"
        "GateKeeper 对 one-test-email、provider-accepted-only、UI-toggle-only、happy-path-send-only、docs-only unsubscribe、bounce/complaint proof 缺失、duplicate negatives 缺失、locale/template proof 缺失、redaction 缺失、audit reconciliation 缺失、monitoring 缺失、migration 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _notification_subscription_deliverability_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_notification_subscription_deliverability_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de notification deliverability confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de notification subscription-deliverability; después compilaré un workflow notification-contract-first "
        "con inspecciones paralelas de Deliverability Evidence y Template Privacy antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de lifecycle campaign email / notification deliverability con un Loop contract-first: {task}. "
        "Notification Contract Inspector fija subscription, preferences, unsubscribe, suppression, bounce/complaint/drop events, tenant/disabled filters, locale/templates, redaction, provider webhook replay/idempotency, retry/DLQ, audit, monitoring, migration y governance; "
        "Campaign Email Builder implementa desde ese handoff; Deliverability Evidence Inspector y Template Privacy Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante one-test-email, provider-accepted-only, UI-toggle-only, happy-path, docs-only unsubscribe, missing bounce/complaint, duplicates, locale/template, redaction, audit reconciliation, monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _notification_subscription_deliverability_readiness_evidence(task, language="es")
    return payload
