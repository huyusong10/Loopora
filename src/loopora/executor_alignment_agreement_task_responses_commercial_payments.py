from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _dispute_chargeback_lifecycle_readiness_evidence,
    _payment_webhook_ledger_readiness_evidence,
    _payout_settlement_reconciliation_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_payout_settlement_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed marketplace payout settlement task")
    payload["assistant_message"] = (
        "Please confirm this payout settlement working agreement; I will compile a payout-contract-first workflow "
        "with parallel Settlement Reconciliation and Access Idempotency inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this marketplace seller payout settlement task through a payout contract-first Loop: {task}. "
        "Payout Contract Inspector first freezes seller balance ledger semantics, captured/refunded/chargeback samples, fee/tax/adjustment/hold/reserve/negative-balance rules, batch cutoff/timezone/currency/FX policy, provider transfer and bank fixtures, KYC hold, failed payout retry, reversal idempotency, double-payout prevention, provider/local/invoice/bank reconciliation, tenant access, audit, monitoring, and local governance proof targets; "
        "Payout Settlement Builder implements only from that handoff; Settlement Reconciliation Inspector and Access Idempotency Inspector inspect in parallel; "
        "GateKeeper fails closed on dashboard-paid-only, test-payout-only, UI-balance-only, missing seller ledger proof, missing failed/reversal negative, missing double-payout negative, missing provider-bank reconciliation, missing tenant negative, missing audit trail, missing monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _payout_settlement_reconciliation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_payout_settlement_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 marketplace payout settlement 任务")
    payload["assistant_message"] = (
        "请确认这份 payout settlement 工作协议；确认后我会生成 payout 契约先行、再并行 settlement reconciliation 与 access/idempotency 检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 marketplace seller payout settlement 任务编排 payout contract-first Loop：{task}。"
        "Payout Contract Inspector 先只读固定 seller balance ledger、captured/refunded/chargeback samples、fee/tax/adjustment/hold/reserve/negative-balance rules、batch cutoff/timezone/currency/FX、provider transfer/bank fixtures、KYC hold、failed payout retry、reversal idempotency、double-payout prevention、provider/local/invoice/bank reconciliation、tenant access、audit、monitoring 和 local governance proof targets；"
        "Payout Settlement Builder 只能基于该 handoff 实现；Settlement Reconciliation Inspector 与 Access Idempotency Inspector 并行检查；"
        "GateKeeper 对 dashboard-paid-only、test-payout-only、UI-balance-only、seller ledger proof 缺失、failed/reversal negative 缺失、double-payout negative 缺失、provider-bank reconciliation 缺失、tenant negative 缺失、audit trail 缺失、monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _payout_settlement_reconciliation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_payout_settlement_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de payout settlement confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de payout settlement; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Settlement Reconciliation y Access Idempotency antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de marketplace seller payout settlement con un Loop contract-first: {task}. "
        "Payout Contract Inspector fija seller ledger, captured/refunded/chargeback samples, fee/tax/hold rules, cutoff/timezone/currency/FX, provider/bank fixtures, KYC hold, failed payout retry, reversal idempotency, double-payout prevention, reconciliation, tenant access, audit, monitoring y governance; "
        "Payout Settlement Builder implementa desde ese handoff; Settlement Reconciliation y Access Idempotency inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante dashboard-paid-only, test-payout-only, UI balance only, missing ledger, failed/reversal negative, double-payout negative, reconciliation, tenant negative, audit, monitoring o governance."
    )
    payload["readiness_evidence"] = _payout_settlement_reconciliation_readiness_evidence(task, language="es")
    return payload


def alignment_english_dispute_chargeback_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed dispute and chargeback lifecycle task")
    payload["assistant_message"] = (
        "Please confirm this dispute/chargeback working agreement; I will compile a dispute-contract-first workflow "
        "with parallel Dispute Evidence and Ledger Notification inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this dispute and chargeback lifecycle task through a contract-first Loop: {task}. "
        "Dispute Contract Inspector first freezes provider dispute fixtures, webhook signature/replay/order, retrieval request, representment evidence deadlines, reason codes, refund overlap, ledger/payout effects, notification/SLA, audit, monitoring, and governance; "
        "Chargeback Lifecycle Builder implements only from that handoff; Dispute Evidence Inspector and Ledger Notification Inspector inspect in parallel; "
        "GateKeeper fails closed on UI-status-only, dashboard-outcome-only, provider-dispute-id-only, happy-path close, missing evidence package, missing deadline proof, missing refund-overlap negative, missing ledger/payout reconciliation, missing notification/SLA, missing audit, missing monitoring, or skipped governance."
    )
    payload["readiness_evidence"] = _dispute_chargeback_lifecycle_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_dispute_chargeback_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 dispute / chargeback lifecycle 任务")
    payload["assistant_message"] = (
        "请确认这份 dispute/chargeback 工作协议；确认后我会生成 Dispute Contract Inspector 先固定契约、"
        "Chargeback Lifecycle Builder 再实现、Dispute Evidence Inspector 与 Ledger Notification Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 dispute / chargeback lifecycle 任务编排 contract-first Loop：{task}。"
        "Dispute Contract Inspector 先只读固定 provider dispute fixtures、webhook signature/replay/order、retrieval request、representment evidence deadline、reason code、refund overlap、ledger/payout、notification/SLA、audit、monitoring 和 governance；"
        "Chargeback Lifecycle Builder 只能基于该 handoff 实现；Dispute Evidence Inspector 与 Ledger Notification Inspector 并行检查；"
        "GateKeeper 对 UI-status-only、dashboard-outcome-only、provider-dispute-id-only、happy-path close、evidence package 缺失、deadline proof 缺失、refund-overlap negative 缺失、ledger/payout reconciliation 缺失、notification/SLA 缺失、audit 缺失、monitoring 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _dispute_chargeback_lifecycle_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_dispute_chargeback_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de dispute / chargeback confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de dispute/chargeback; después compilaré un workflow contract-first con inspecciones paralelas de Dispute Evidence y Ledger Notification antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea dispute / chargeback lifecycle con un Loop contract-first: {task}. "
        "Dispute Contract Inspector fija provider fixtures, webhook signature/replay/order, retrieval, representment deadlines, reason codes, refund overlap, ledger/payout, notification/SLA, audit, monitoring y governance; "
        "Chargeback Lifecycle Builder implementa desde ese handoff; Dispute Evidence Inspector y Ledger Notification Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante UI-status-only, dashboard-only, provider-dispute-id-only, happy-path close, missing package, deadline, overlap negative, ledger/payout reconciliation, notification/SLA, audit, monitoring o governance."
    )
    payload["readiness_evidence"] = _dispute_chargeback_lifecycle_readiness_evidence(task, language="es")
    return payload


def alignment_english_payment_webhook_ledger_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed payment webhook task")
    payload["assistant_message"] = (
        "Please confirm this payment webhook working agreement; I will compile a webhook-contract-first workflow "
        "with parallel Webhook Evidence and Ledger Reconciliation inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this payment provider webhook and ledger task through a contract-first Loop: {task}. "
        "Webhook Contract Inspector first freezes provider event schemas, signature/timestamp rules, replay/idempotency, ordering, retry/DLQ, ledger/dispute/payout state machines, audit/privacy, monitoring, and manual replay targets; "
        "Payment Webhook Builder implements only from that handoff; Webhook Evidence Inspector and Ledger Reconciliation Inspector inspect in parallel; "
        "GateKeeper fails closed on happy-path-webhook-only, unsigned dev-mode acceptance, provider-status-only, database-constraint-only dedupe, docs-only contract, missing replay negatives, missing ordering proof, missing ledger reconciliation, or missing monitoring/DLQ proof."
    )
    payload["readiness_evidence"] = _payment_webhook_ledger_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_payment_webhook_ledger_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 payment webhook 任务")
    payload["assistant_message"] = (
        "请确认这份 payment webhook 工作协议；确认后我会生成 Webhook Contract Inspector 先固定契约、"
        "Payment Webhook Builder 再实现、Webhook Evidence Inspector 与 Ledger Reconciliation Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 payment provider webhook 与 ledger 任务编排 contract-first Loop：{task}。"
        "Webhook Contract Inspector 先只读固定 provider event schema、signature/timestamp rules、replay/idempotency、ordering、retry/DLQ、ledger/dispute/payout state machines、audit/privacy、monitoring 和 manual replay targets；"
        "Payment Webhook Builder 只能基于该 handoff 实现；Webhook Evidence Inspector 与 Ledger Reconciliation Inspector 并行检查；"
        "GateKeeper 对 happy-path-webhook-only、unsigned dev-mode acceptance、provider-status-only、database-constraint-only dedupe、docs-only contract、replay negatives 缺失、ordering proof 缺失、ledger reconciliation 缺失或 monitoring/DLQ proof 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _payment_webhook_ledger_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_payment_webhook_ledger_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de payment webhook confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de payment webhook; después compilaré un workflow contract-first con inspecciones paralelas de Webhook Evidence y Ledger Reconciliation antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de payment provider webhook y ledger con un Loop contract-first: {task}. "
        "Webhook Contract Inspector fija schemas, signature/timestamp, replay/idempotency, ordering, retry/DLQ, ledger/dispute/payout state machines, audit/privacy, monitoring y manual replay targets; "
        "Payment Webhook Builder implementa desde ese handoff; Webhook Evidence Inspector y Ledger Reconciliation Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante happy-path-webhook-only, unsigned dev-mode, provider-status-only, database-constraint-only dedupe, docs-only contract, replay/order proof faltante, ledger reconciliation faltante o monitoring/DLQ faltante."
    )
    payload["readiness_evidence"] = _payment_webhook_ledger_readiness_evidence(task, language="es")
    return payload
