from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _subscription_entitlement_billing_readiness_evidence,
    _tax_calculation_compliance_readiness_evidence,
    _usage_quota_metering_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_usage_quota_metering_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed usage quota task")
    payload["assistant_message"] = (
        "Please confirm this usage quota metering working agreement; I will compile a quota contract-first workflow "
        "with parallel Quota Race and Billing Reconciliation inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this SaaS API usage metering / plan quota enforcement task through a contract-first Loop: {task}. "
        "Quota Contract Inspector first freezes usage event schema, idempotency keys, org/plan/quota windows, concurrency, duplicates, retries, plan changes, reset timezone, limits, permission-safe errors, ledger/invoice/provider reconciliation, audit, monitoring, migration, and governance; "
        "Usage Metering Builder implements only from that handoff; Quota Race Inspector and Billing Reconciliation Inspector inspect in parallel; "
        "GateKeeper fails closed on dashboard-only usage, single 429, cron reset only, provider total only, missing duplicate-event proof, missing concurrency proof, missing plan-change proof, missing reset timezone, missing reconciliation, missing audit/monitoring, missing migration, or skipped local governance."
    )
    payload["readiness_evidence"] = _usage_quota_metering_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_usage_quota_metering_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 usage quota 任务")
    payload["assistant_message"] = (
        "请确认这份 usage quota metering 工作协议；确认后我会生成 Quota Contract Inspector 先固定计量/限额契约、"
        "Usage Metering Builder 再实现、Quota Race Inspector 与 Billing Reconciliation Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 SaaS API usage metering / plan quota enforcement 任务编排 contract-first Loop：{task}。"
        "Quota Contract Inspector 先只读固定 usage event schema、idempotency keys、org/plan/quota windows、concurrency、duplicates、retries、plan changes、reset timezone、limits、permission-safe errors、ledger/invoice/provider reconciliation、audit、monitoring、migration 和 governance；"
        "Usage Metering Builder 只能基于该 handoff 实现；Quota Race Inspector 与 Billing Reconciliation Inspector 并行检查；"
        "GateKeeper 对 dashboard-only usage、single 429、cron reset only、provider total only、duplicate-event proof 缺失、concurrency proof 缺失、plan-change proof 缺失、reset timezone 缺失、reconciliation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _usage_quota_metering_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_usage_quota_metering_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de usage quota confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de usage quota metering; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Quota Race y Billing Reconciliation antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de SaaS API usage metering / plan quota enforcement con un Loop contract-first: {task}. "
        "Quota Contract Inspector fija usage schema, idempotency, org/plan/quota windows, concurrency, duplicates, retries, plan changes, reset timezone, limits, errors, reconciliation, audit, monitoring, migration y governance; "
        "Usage Metering Builder implementa desde ese handoff; Quota Race Inspector y Billing Reconciliation Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante dashboard-only, single 429, cron reset, provider total only, missing duplicate/concurrency/plan-change/reset/reconciliation/audit/monitoring/migration proof o governance omitida."
    )
    payload["readiness_evidence"] = _usage_quota_metering_readiness_evidence(task, language="es")
    return payload


def alignment_english_subscription_entitlement_billing_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed subscription entitlement task")
    payload["assistant_message"] = (
        "Please confirm this subscription entitlement / proration working agreement; I will compile a subscription "
        "contract-first workflow with parallel Entitlement State and Billing Proration Reconciliation inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this B2B SaaS subscription upgrade/downgrade and entitlement activation task through a contract-first Loop: {task}. "
        "Subscription Contract Inspector first freezes plan-change lifecycle, upgrade immediate effect, downgrade next-cycle effect, proration, credit memo, invoice totals, trial/grace, billing-period boundaries, provider checkout/webhook replay, duplicate-click idempotency, team-member entitlements, quota/history preservation, permissions, tenant boundaries, audit, rollback, monitoring, and governance; "
        "Entitlement Billing Builder implements only from that handoff; Entitlement State Inspector and Billing Proration Reconciliation Inspector inspect in parallel; "
        "GateKeeper fails closed on button-only, checkout-success-only, provider-total-only, happy-path plan change, missing downgrade-delayed proof, missing proration/credit memo, missing entitlement propagation, missing permission negatives, missing webhook replay/idempotency, missing reconciliation, missing rollback/monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _subscription_entitlement_billing_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_subscription_entitlement_billing_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 subscription entitlement 任务")
    payload["assistant_message"] = (
        "请确认这份 subscription entitlement / proration 工作协议；确认后我会生成 Subscription Contract Inspector 先固定订阅/权益/账单契约、"
        "Entitlement Billing Builder 再实现、Entitlement State Inspector 与 Billing Proration Reconciliation Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 B2B SaaS 订阅升级/降级和权益生效任务编排 contract-first Loop：{task}。"
        "Subscription Contract Inspector 先只读固定 plan-change lifecycle、升级立即生效、降级下个周期生效、proration、credit memo、invoice totals、试用/宽限期、billing-period boundaries、provider checkout/webhook replay、重复点击幂等、团队成员权益、quota/history preservation、权限、tenant boundaries、audit、rollback、monitoring 和 governance；"
        "Entitlement Billing Builder 只能基于该 handoff 实现；Entitlement State Inspector 与 Billing Proration Reconciliation Inspector 并行检查；"
        "GateKeeper 对 button-only、checkout-success-only、provider-total-only、happy-path plan change、降级延迟生效证明缺失、proration/credit memo 缺失、权益传播缺失、权限负向缺失、webhook replay/idempotency 缺失、对账缺失、rollback/monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _subscription_entitlement_billing_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_subscription_entitlement_billing_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de subscription entitlement confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de subscription entitlement / proration; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Entitlement State y Billing Proration Reconciliation antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea B2B SaaS subscription upgrade/downgrade y entitlement activation con un Loop contract-first: {task}. "
        "Subscription Contract Inspector fija lifecycle, immediate upgrade, next-cycle downgrade, proration, credit memo, invoice totals, trial/grace, billing boundaries, provider checkout/webhook replay, duplicate-click idempotency, team entitlements, quota/history, permissions, tenant boundaries, audit, rollback, monitoring y governance; "
        "Entitlement Billing Builder implementa desde ese handoff; Entitlement State Inspector y Billing Proration Reconciliation Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante button-only, checkout-success-only, provider-total-only, happy path, missing downgrade delay, proration/credit memo, entitlement propagation, permission negatives, webhook replay/idempotency, reconciliation, rollback/monitoring o governance omitida."
    )
    payload["readiness_evidence"] = _subscription_entitlement_billing_readiness_evidence(task, language="es")
    return payload


def alignment_english_tax_calculation_compliance_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed tax calculation task")
    payload["assistant_message"] = (
        "Please confirm this tax calculation compliance working agreement; I will compile a tax contract-first workflow "
        "with parallel Jurisdiction Rate and Invoice Reversal inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this checkout tax calculation compliance task through a contract-first Loop: {task}. "
        "Tax Contract Inspector first freezes nexus, US sales tax, EU VAT, GST, jurisdiction/address matrix, product taxability, exemptions, reverse charge, display mode, rounding, invoice/refund reversal, provider fallback/idempotency, effective dates, audit, reconciliation, migration, and governance; "
        "Tax Calculation Builder implements only from that handoff; Jurisdiction Rate Inspector and Invoice Reversal Inspector inspect in parallel; "
        "GateKeeper fails closed on one tax number, hardcoded rate, provider quote only, UI total only, missing jurisdiction matrix, missing exemption/reverse-charge, missing refund/reversal, missing rounding proof, missing reconciliation, missing audit/monitoring, missing migration, or skipped local governance."
    )
    payload["readiness_evidence"] = _tax_calculation_compliance_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_tax_calculation_compliance_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 tax calculation 任务")
    payload["assistant_message"] = (
        "请确认这份 tax calculation compliance 工作协议；确认后我会生成 Tax Contract Inspector 先固定税务计算契约、"
        "Tax Calculation Builder 再实现、Jurisdiction Rate Inspector 与 Invoice Reversal Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 checkout tax calculation compliance 任务编排 contract-first Loop：{task}。"
        "Tax Contract Inspector 先只读固定 nexus、US sales tax、EU VAT、GST、jurisdiction/address matrix、product taxability、exemptions、reverse charge、display mode、rounding、invoice/refund reversal、provider fallback/idempotency、effective dates、audit、reconciliation、migration 和 governance；"
        "Tax Calculation Builder 只能基于该 handoff 实现；Jurisdiction Rate Inspector 与 Invoice Reversal Inspector 并行检查；"
        "GateKeeper 对 one tax number、hardcoded rate、provider quote only、UI total only、jurisdiction matrix 缺失、exemption/reverse-charge 缺失、refund/reversal 缺失、rounding proof 缺失、reconciliation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _tax_calculation_compliance_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_tax_calculation_compliance_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de tax calculation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de tax calculation compliance; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Jurisdiction Rate e Invoice Reversal antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de checkout tax calculation compliance con un Loop contract-first: {task}. "
        "Tax Contract Inspector fija nexus, sales tax/VAT/GST, jurisdiction/address matrix, taxability, exemptions, reverse charge, display, rounding, invoice/refund reversal, provider fallback/idempotency, effective dates, audit, reconciliation, migration y governance; "
        "Tax Calculation Builder implementa desde ese handoff; Jurisdiction Rate Inspector e Invoice Reversal Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante one tax number, hardcoded rate, provider quote only, UI total only, missing jurisdiction, exemption, refund/reversal, rounding, reconciliation, audit/monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _tax_calculation_compliance_readiness_evidence(task, language="es")
    return payload
