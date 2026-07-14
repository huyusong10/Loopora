from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _data_residency_readiness_evidence,
    _kyc_aml_screening_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_data_residency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed data residency task")
    payload["assistant_message"] = (
        "Please confirm this data residency / regional isolation working agreement; I will compile a contract-first "
        "workflow with Residency Contract Inspector, Regional Isolation Builder, Residency Evidence Inspector, and GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this enterprise data residency / regional isolation task through a contract-first Loop: {task}. "
        "Residency Contract Inspector first freezes the EU/US data-plane inventory, tenant residency policy, routing, storage, search, "
        "cache, queues, backups, logs, analytics, processor/DPA, key-region, failover, migration/backfill, access/export/audit/trace, "
        "egress-monitoring, and wrong-region negative targets; Regional Isolation Builder implements only from that handoff; "
        "Residency Evidence Inspector verifies every regional proof and negative; GateKeeper fails closed on UI-region-only, env-var-only, "
        "tenant-field-only, one-routed-request-only, docs-only DPA, missing processor proof, missing wrong-region negatives, missing key-region proof, "
        "or missing observability / egress alerts."
    )
    payload["readiness_evidence"] = _data_residency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_data_residency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 data residency / regional isolation 任务")
    payload["assistant_message"] = (
        "请确认这份 data residency / regional isolation 工作协议；确认后我会生成 Residency Contract Inspector 先固定契约、"
        "Regional Isolation Builder 再实现、Residency Evidence Inspector 复验证据、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条企业 data residency / regional isolation 任务编排 contract-first Loop：{task}。"
        "Residency Contract Inspector 先只读固定 EU/US 数据面清单、tenant residency policy、routing、存储、search、cache、queue、"
        "backup、logs、analytics、processor/DPA、key-region、failover、migration/backfill、access/export/audit/trace、egress monitoring 和 wrong-region 负向目标；"
        "Regional Isolation Builder 只能基于该 handoff 实现；Residency Evidence Inspector 验证所有区域证明和负向证据；"
        "GateKeeper 对 UI-region-only、env-var-only、tenant-field-only、one-routed-request-only、docs-only DPA、processor proof 缺失、wrong-region 负向缺失、"
        "key-region proof 缺失或 observability / egress alert 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _data_residency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_data_residency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de data residency confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de data residency / regional isolation; después compilaré un workflow contract-first "
        "con Residency Contract Inspector, Regional Isolation Builder, Residency Evidence Inspector y GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de data residency / regional isolation con un Loop contract-first: {task}. "
        "Residency Contract Inspector fija inventario EU/US, residency policy, routing, storage, search, cache, queues, backups, logs, analytics, "
        "processor/DPA, key-region, failover, migration/backfill, access/export/audit/trace, egress monitoring y negativos wrong-region; "
        "Regional Isolation Builder implementa desde ese handoff; Residency Evidence Inspector verifica pruebas regionales y negativos; "
        "GateKeeper falla cerrado ante UI-region-only, env-var-only, tenant-field-only, one-routed-request-only, docs-only DPA, processor proof faltante, "
        "wrong-region negatives faltantes, key-region proof faltante o falta de observability / egress alerts."
    )
    payload["readiness_evidence"] = _data_residency_readiness_evidence(task, language="es")
    return payload


def alignment_english_kyc_aml_screening_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed KYC/AML screening task")
    payload["assistant_message"] = (
        "Please confirm this KYC/AML screening working agreement; I will compile a compliance-contract-first workflow "
        "with parallel Screening and Financial Controls inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this seller KYC/KYB and AML screening task through a compliance-contract-first Loop: {task}. "
        "Compliance Contract Inspector first freezes provider contracts, jurisdiction / retention rules, required KYC/KYB fields, "
        "sanctions / PEP / watchlist samples, manual-review rubric, appeal / resubmission, rescreening cadence, webhook signature / replay / order / idempotency, "
        "audit reason schema, privacy redaction, monitoring, and payout hold / release ledger proof targets; KYC/AML Builder implements only from that handoff; "
        "Screening Evidence Inspector and Financial Controls Inspector inspect in parallel; GateKeeper fails closed on sandbox-approved-only, UI-verified-only, "
        "provider-status-only, happy-path webhook, weak manual-review proof, missing sanctions negatives, or missing payout ledger proof."
    )
    payload["readiness_evidence"] = _kyc_aml_screening_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_kyc_aml_screening_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 KYC/AML screening 任务")
    payload["assistant_message"] = (
        "请确认这份 KYC/AML screening 工作协议；确认后我会生成合规契约先行、再并行筛查证据与资金控制检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 seller KYC/KYB and AML screening 任务编排 compliance-contract-first Loop：{task}。"
        "Compliance Contract Inspector 先固定 provider contract、jurisdiction / retention、KYC/KYB fields、sanctions / PEP / watchlist samples、"
        "manual-review rubric、appeal / resubmission、rescreening cadence、webhook signature / replay / order / idempotency、audit reason schema、"
        "privacy redaction、monitoring 和 payout hold / release ledger proof targets；KYC/AML Builder 只能基于该 handoff 实现；"
        "Screening Evidence Inspector 与 Financial Controls Inspector 并行检查；GateKeeper 对 sandbox-approved-only、UI-verified-only、provider-status-only、"
        "happy-path webhook、manual-review 弱证据、sanctions 负例缺失或 payout ledger proof 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _kyc_aml_screening_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_kyc_aml_screening_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de KYC/AML screening confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de KYC/AML screening; después compilaré un workflow compliance-contract-first con inspecciones paralelas de Screening y Financial Controls antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de seller KYC/KYB y AML screening con un Loop compliance-contract-first: {task}. "
        "Compliance Contract Inspector fija provider contracts, reglas de jurisdicción/retention, campos KYC/KYB, muestras sanctions/PEP/watchlist, rúbrica manual, "
        "appeal/resubmission, rescreening, webhook signature/replay/order/idempotency, audit reason schema, privacy, monitoring y payout ledger proof; "
        "KYC/AML Builder implementa desde ese handoff; Screening Evidence Inspector y Financial Controls Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante sandbox-approved-only, UI-verified-only, provider-status-only, happy-path webhook, revisión manual débil o falta de sanctions negatives / payout ledger."
    )
    payload["readiness_evidence"] = _kyc_aml_screening_readiness_evidence(task, language="es")
    return payload
