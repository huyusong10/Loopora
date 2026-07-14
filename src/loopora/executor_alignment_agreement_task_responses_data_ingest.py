from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _data_import_validation_readiness_evidence,
    _file_upload_storage_safety_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_data_import_validation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed customer CSV import task")
    payload["assistant_message"] = (
        "Please confirm this data import working agreement; I will compile an import contract-first workflow "
        "with parallel Import Evidence and Privacy Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this customer CSV bulk import task through an import contract-first Loop: {task}. "
        "Import Contract Inspector first freezes field mapping, required/type schema validation, dry-run preview, mixed good/bad row fixtures, row-level error report shape, partial-failure isolation, idempotency key/retry semantics, external_id dedupe, PII redaction, permissions, audit batch fields, and local governance proof targets; "
        "CSV Import Builder implements only from that handoff; Import Evidence Inspector and Privacy Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on happy-path-only CSV, preview-only, all-or-nothing import, success-count-only report, missing schema validation, missing bad-row isolation, missing idempotency/dedupe, missing privacy/audit, missing permission negatives, or skipped local governance."
    )
    payload["readiness_evidence"] = _data_import_validation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_data_import_validation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 customer CSV import 任务")
    payload["assistant_message"] = "请确认这份 data import 工作协议；确认后我会生成导入契约先行、再并行导入证据与隐私审计检查、最后 GateKeeper 裁决的 Loop。"
    payload["agreement_summary"] = (
        f"围绕这条 customer CSV bulk import 任务编排 import contract-first Loop：{task}。"
        "Import Contract Inspector 先固定 field mapping、required/type schema validation、dry-run preview、好坏行混合 fixtures、row-level error report shape、partial-failure isolation、idempotency key/retry semantics、external_id dedupe、PII redaction、permissions、audit batch fields 和 local governance proof targets；"
        "CSV Import Builder 只能基于该 handoff 实现；Import Evidence Inspector 与 Privacy Audit Inspector 并行检查；"
        "GateKeeper 对 happy-path-only CSV、preview-only、all-or-nothing import、success-count-only report、schema validation 缺失、bad-row isolation 缺失、idempotency/dedupe 缺失、privacy/audit 缺失、permission negatives 缺失或跳过本地治理 fail closed。"
    )
    payload["readiness_evidence"] = _data_import_validation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_data_import_validation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de importación CSV confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de data import; después compilaré un workflow import contract-first "
        "con inspecciones paralelas de Import Evidence y Privacy Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de customer CSV bulk import con un Loop import contract-first: {task}. "
        "Import Contract Inspector fija mapping, schema required/type, dry-run preview, fixtures buenas/malas, row-level error report, partial-failure isolation, idempotency key/retry, external_id dedupe, PII redaction, permisos, audit batch fields y governance; "
        "CSV Import Builder implementa desde ese handoff; Import Evidence Inspector y Privacy Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante happy CSV only, preview-only, all-or-nothing import, success-count-only report, missing schema, bad-row isolation, idempotency/dedupe, privacy/audit, permission negatives o governance omitida."
    )
    payload["readiness_evidence"] = _data_import_validation_readiness_evidence(task, language="es")
    return payload


def alignment_english_file_upload_storage_safety_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed file upload task")
    payload["assistant_message"] = (
        "Please confirm this file upload storage-safety working agreement; I will compile an upload contract-first workflow "
        "with parallel Storage Access and Malware Cleanup inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this user file upload / object storage safety task through a contract-first Loop: {task}. "
        "Upload Storage Contract Inspector first freezes MIME/content sniffing, mismatch cases, size limits, malware fixtures, quarantine state machine, private ACL, signed URL permission/expiry, tenant key isolation, cleanup, audit, monitoring, and governance; "
        "File Upload Builder implements only from that handoff; Storage Access Inspector and Malware Cleanup Inspector inspect in parallel; "
        "GateKeeper fails closed on returned-URL-only, happy PDF only, browser-content-type-only, public bucket, scan follow-up, missing quarantine, missing tenant negatives, missing cleanup, missing audit/monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _file_upload_storage_safety_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_file_upload_storage_safety_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的文件上传任务")
    payload["assistant_message"] = (
        "请确认这份 file upload storage-safety 工作协议；确认后我会生成 Upload Storage Contract Inspector 先固定上传/存储契约、"
        "File Upload Builder 再实现、Storage Access Inspector 与 Malware Cleanup Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 user file upload / object storage safety 任务编排 contract-first Loop：{task}。"
        "Upload Storage Contract Inspector 先只读固定 MIME/content sniffing、mismatch cases、size limits、malware fixtures、quarantine state machine、private ACL、signed URL permission/expiry、tenant key isolation、cleanup、audit、monitoring 和 governance；"
        "File Upload Builder 只能基于该 handoff 实现；Storage Access Inspector 与 Malware Cleanup Inspector 并行检查；"
        "GateKeeper 对 returned-URL-only、happy PDF only、browser-content-type-only、public bucket、scan follow-up、quarantine 缺失、tenant negatives 缺失、cleanup 缺失、audit/monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _file_upload_storage_safety_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_file_upload_storage_safety_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de file upload confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de file upload storage safety; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Storage Access y Malware Cleanup antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de user file upload / object storage safety con un Loop contract-first: {task}. "
        "Upload Storage Contract Inspector fija MIME/content sniffing, mismatch cases, size limits, malware fixtures, quarantine state machine, private ACL, signed URL permission/expiry, tenant key isolation, cleanup, audit, monitoring y governance; "
        "File Upload Builder implementa desde ese handoff; Storage Access Inspector y Malware Cleanup Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante returned-URL-only, happy PDF only, browser-content-type-only, public bucket, scan follow-up, missing quarantine/tenant negatives/cleanup/audit/monitoring o governance omitida."
    )
    payload["readiness_evidence"] = _file_upload_storage_safety_readiness_evidence(task, language="es")
    return payload
