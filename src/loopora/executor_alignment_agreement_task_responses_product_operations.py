from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _analytics_experiment_instrumentation_readiness_evidence,
    _inventory_reservation_consistency_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_inventory_reservation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed inventory reservation task")
    payload["assistant_message"] = (
        "Please confirm this inventory reservation working agreement; I will compile an inventory contract-first workflow "
        "with parallel Reservation Race and Payment Ledger inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this checkout inventory reservation and oversell-prevention task through a contract-first Loop: {task}. "
        "Inventory Contract Inspector first freezes SKU stock invariants, reservation state machine, hold TTL/expiry, payment webhook ordering, release semantics for cancellation/refund/failed payment, idempotency keys, reconciliation targets, sold-out/low-stock states, audit, monitoring, and governance; "
        "Inventory Reservation Builder implements only from that handoff; Reservation Race Inspector and Payment Ledger Inspector inspect in parallel; "
        "GateKeeper fails closed on one-user checkout, UI stock decrement, DB decrement only, missing TTL expiry, missing webhook replay/order, missing release proof, missing ledger reconciliation, missing sold-out consistency, missing audit/monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _inventory_reservation_consistency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_inventory_reservation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的库存预留任务")
    payload["assistant_message"] = (
        "请确认这份 inventory reservation 工作协议；确认后我会生成 Inventory Contract Inspector 先固定库存/预留契约、"
        "Inventory Reservation Builder 再实现、Reservation Race Inspector 与 Payment Ledger Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 checkout inventory reservation 与防超卖任务编排 contract-first Loop：{task}。"
        "Inventory Contract Inspector 先只读固定 SKU stock invariants、reservation state machine、hold TTL/expiry、payment webhook ordering、取消/退款/失败支付释放语义、idempotency keys、reconciliation targets、售罄/低库存状态、audit、monitoring 和 governance；"
        "Inventory Reservation Builder 只能基于该 handoff 实现；Reservation Race Inspector 与 Payment Ledger Inspector 并行检查；"
        "GateKeeper 对 one-user checkout、UI stock decrement、DB decrement only、TTL expiry 缺失、webhook replay/order 缺失、release proof 缺失、ledger reconciliation 缺失、sold-out consistency 缺失、audit/monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _inventory_reservation_consistency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_inventory_reservation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de inventory reservation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de inventory reservation; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Reservation Race y Payment Ledger antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de checkout inventory reservation y oversell prevention con un Loop contract-first: {task}. "
        "Inventory Contract Inspector fija SKU invariants, reservation state machine, TTL/expiry, webhook ordering, release semantics, idempotency keys, reconciliation targets, sold-out/low-stock, audit, monitoring y governance; "
        "Inventory Reservation Builder implementa desde ese handoff; Reservation Race Inspector y Payment Ledger Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante one-user checkout, UI stock decrement, DB decrement only, missing TTL/webhook/release/reconciliation/sold-out/audit/monitoring proof o governance omitida."
    )
    payload["readiness_evidence"] = _inventory_reservation_consistency_readiness_evidence(task, language="es")
    return payload


def alignment_english_analytics_experiment_instrumentation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed analytics instrumentation and experiment task")
    payload["assistant_message"] = (
        "Please confirm this analytics instrumentation / experiment exposure working agreement; I will compile an "
        "instrumentation-contract-first workflow with parallel Event Integrity and Experiment Consistency inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this onboarding analytics instrumentation / A-B experiment exposure task through a contract-first Loop: {task}. "
        "Instrumentation Contract Inspector first freezes versioned event schema, identity merge, consent/PII boundaries, SDK retry/offline replay, experiment assignment/exposure/variant/holdout/reassignment, warehouse/dashboard reconciliation, monitoring, migration, and governance; "
        "Tracking Builder implements only from that handoff; Event Integrity Inspector and Experiment Consistency Inspector inspect in parallel; "
        "GateKeeper fails closed on button-click-only, console-log-only, mock-analytics-only, one-provider-accepted-event, missing warehouse reconciliation, missing consent negative, missing duplicate/offline replay negatives, experiment exposure as follow-up, missing monitoring, or skipped governance."
    )
    payload["readiness_evidence"] = _analytics_experiment_instrumentation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_analytics_experiment_instrumentation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 analytics instrumentation and experiment 任务")
    payload["assistant_message"] = (
        "请确认这份 analytics instrumentation / experiment exposure 工作协议；确认后我会生成 Instrumentation Contract Inspector 先固定埋点与实验契约、"
        "Tracking Builder 再实现、Event Integrity Inspector 与 Experiment Consistency Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 onboarding analytics instrumentation / A-B experiment exposure 任务编排 contract-first Loop：{task}。"
        "Instrumentation Contract Inspector 先只读固定 versioned event schema、identity merge、consent/PII boundaries、SDK retry/offline replay、experiment assignment/exposure/variant/holdout/reassignment、warehouse/dashboard reconciliation、monitoring、migration 和 governance；"
        "Tracking Builder 只能基于该 handoff 实现；Event Integrity Inspector 与 Experiment Consistency Inspector 并行检查；"
        "GateKeeper 对 button-click-only、console-log-only、mock-analytics-only、one-provider-accepted-event、warehouse reconciliation 缺失、consent negative 缺失、duplicate/offline replay negatives 缺失、experiment exposure 当后续、monitoring 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _analytics_experiment_instrumentation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_analytics_experiment_instrumentation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de analytics instrumentation and experiment confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de analytics instrumentation / experiment exposure; después compilaré un workflow instrumentation-contract-first "
        "con inspecciones paralelas de Event Integrity y Experiment Consistency antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de onboarding analytics instrumentation / A-B experiment exposure con un Loop contract-first: {task}. "
        "Instrumentation Contract Inspector fija event schema, identity merge, consent/PII, retry/offline replay, assignment/exposure/variant/holdout/reassignment, warehouse/dashboard reconciliation, monitoring, migration y governance; "
        "Tracking Builder implementa desde ese handoff; Event Integrity y Experiment Consistency inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante button-click-only, console-log-only, mock analytics, one provider event, missing reconciliation, consent negative, duplicate/offline replay, exposure follow-up, monitoring o governance."
    )
    payload["readiness_evidence"] = _analytics_experiment_instrumentation_readiness_evidence(task, language="es")
    return payload
