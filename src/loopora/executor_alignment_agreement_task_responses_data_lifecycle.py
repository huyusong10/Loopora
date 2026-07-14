from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _data_lifecycle_deletion_retention_readiness_evidence,
    _dsar_data_export_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_dsar_data_export_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed DSAR data export task")
    payload["assistant_message"] = (
        "Please confirm this DSAR data export working agreement; I will compile a DSAR export contract-first workflow "
        "with parallel Export Scope and Access Retention Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this GDPR/CCPA subject access data export task through a contract-first Loop: {task}. "
        "DSAR Export Contract Inspector first freezes request intake, identity verification, requester/admin/API permission matrix, export scope inventory, tenant/user exclusion negatives, PII/secret redaction, legal hold and retention exceptions, async export job lifecycle, encrypted file delivery, signed URL expiry, expiry cleanup, download audit, notification dedupe, rate limits, monitoring, and governance; "
        "Privacy Export Builder implements only from that handoff; Export Scope Inspector and Access Retention Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on CSV-only, download-button-only, dashboard-ready-only, missing request/auth proof, missing scope coverage, missing tenant or user negatives, missing redaction, missing legal-hold exception, missing async lifecycle, missing encrypted expiring file proof, missing download audit, duplicate notifications, missing rate limit, missing monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _dsar_data_export_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_dsar_data_export_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 DSAR data export 任务")
    payload["assistant_message"] = (
        "请确认这份 DSAR data export 工作协议；确认后我会生成 DSAR Export Contract Inspector 先固定隐私导出契约、"
        "Privacy Export Builder 再实现、Export Scope Inspector 与 Access Retention Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 GDPR/CCPA subject access data export 任务编排 contract-first Loop：{task}。"
        "DSAR Export Contract Inspector 先只读固定 request intake、identity verification、requester/admin/API permission matrix、export scope inventory、tenant/user exclusion negatives、PII/secret redaction、legal hold/retention exceptions、async export job lifecycle、encrypted file delivery、signed URL expiry、expiry cleanup、download audit、notification dedupe、rate limits、monitoring 和 governance；"
        "Privacy Export Builder 只能基于该 handoff 实现；Export Scope Inspector 与 Access Retention Audit Inspector 并行检查；"
        "GateKeeper 对 CSV-only、download-button-only、dashboard-ready-only、request/auth proof 缺失、scope coverage 缺失、tenant/user negatives 缺失、redaction 缺失、legal-hold exception 缺失、async lifecycle 缺失、encrypted expiring file proof 缺失、download audit 缺失、duplicate notifications、rate limit 缺失、monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _dsar_data_export_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_dsar_data_export_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de DSAR data export confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de DSAR data export; después compilaré un workflow DSAR export contract-first "
        "con inspecciones paralelas de Export Scope y Access Retention Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea GDPR/CCPA subject access data export con un Loop contract-first: {task}. "
        "DSAR Export Contract Inspector fija intake, identity verification, permisos requester/admin/API, scope inventory, tenant/user negatives, PII/secret redaction, legal hold/retention, async export lifecycle, encrypted delivery, signed URL expiry, cleanup, download audit, notification dedupe, rate limits, monitoring y governance; "
        "Privacy Export Builder implementa desde ese handoff; Export Scope Inspector y Access Retention Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante CSV-only, download-button-only, dashboard-ready-only, missing auth, scope, tenant/user negatives, redaction, legal-hold exception, async lifecycle, encrypted expiring file, download audit, duplicate notifications, rate limit, monitoring o governance omitida."
    )
    payload["readiness_evidence"] = _dsar_data_export_readiness_evidence(task, language="es")
    return payload


def alignment_english_data_lifecycle_deletion_retention_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed data deletion and retention task")
    payload["assistant_message"] = (
        "Please confirm this data deletion / retention working agreement; I will compile a data-lifecycle "
        "contract-first workflow with parallel Privacy Deletion Evidence and Retention Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this GDPR data deletion / retention task through a contract-first Loop: {task}. "
        "Data Lifecycle Contract Inspector first freezes deletion surfaces, retention exceptions, legal hold, backup expiry, search/cache purge, analytics anonymization, export suppression, audit trail, tenant isolation, permission, and monitoring targets; "
        "Deletion Builder implements only from that handoff; Privacy Deletion Evidence Inspector and Retention Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on UI-delete-only, soft-delete-only, one-happy-path response, docs-only retention policy, missing backup-expiry proof, missing retention/legal-hold proof, missing purge/anonymization proof, missing tenant negatives, or missing audit/monitoring evidence."
    )
    payload["readiness_evidence"] = _data_lifecycle_deletion_retention_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_data_lifecycle_deletion_retention_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的数据删除与保留任务")
    payload["assistant_message"] = (
        "请确认这份 data deletion / retention 工作协议；确认后我会生成 Data Lifecycle Contract Inspector 先固定契约、"
        "Deletion Builder 再实现、Privacy Deletion Evidence Inspector 与 Retention Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 GDPR data deletion / retention 任务编排 contract-first Loop：{task}。"
        "Data Lifecycle Contract Inspector 先只读固定 deletion surfaces、retention exceptions、legal hold、backup expiry、search/cache purge、analytics anonymization、export suppression、audit trail、tenant isolation、permission 和 monitoring targets；"
        "Deletion Builder 只能基于该 handoff 实现；Privacy Deletion Evidence Inspector 与 Retention Audit Inspector 并行检查；"
        "GateKeeper 对 UI-delete-only、soft-delete-only、one happy-path response、docs-only retention policy、backup-expiry proof 缺失、retention/legal-hold proof 缺失、purge/anonymization proof 缺失、tenant negatives 缺失或 audit/monitoring evidence 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _data_lifecycle_deletion_retention_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_data_lifecycle_deletion_retention_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de data deletion / retention confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de data deletion / retention; después compilaré un workflow contract-first con inspecciones paralelas de Privacy Deletion Evidence y Retention Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea GDPR data deletion / retention con un Loop contract-first: {task}. "
        "Data Lifecycle Contract Inspector fija superficies de deletion, excepciones de retention, legal hold, backup expiry, search/cache purge, analytics anonymization, export suppression, audit, tenant isolation, permission y monitoring; "
        "Deletion Builder implementa desde ese handoff; Privacy Deletion Evidence Inspector y Retention Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante UI-delete-only, soft-delete-only, one happy path, docs-only retention, falta de backup expiry, retention/legal hold, purge/anonymization, tenant negatives o audit/monitoring."
    )
    payload["readiness_evidence"] = _data_lifecycle_deletion_retention_readiness_evidence(task, language="es")
    return payload
