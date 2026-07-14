from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _audit_log_integrity_retention_readiness_evidence,
    _backup_restore_recovery_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_backup_restore_recovery_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed backup restore recovery task")
    payload["assistant_message"] = (
        "Please confirm this backup / restore recovery working agreement; I will compile a recovery-contract-first workflow "
        "with parallel Restore Drill Evidence and Retention Security Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this production backup / restore and disaster recovery task through a contract-first Loop: {task}. "
        "Backup Recovery Contract Inspector first freezes nightly backup, PITR, cross-region snapshot, encryption key access, retention/legal hold, schema-migration restore, tenant/full database restore, RPO/RTO, integrity, monitoring, restore permission, and audit targets; "
        "Backup Restore Builder implements only from that handoff; Restore Drill Evidence Inspector and Retention Security Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on backup-job-green-only, snapshot-file-only, dashboard-green-only, missing restore drill, missing PITR, missing checksum/row count/smoke proof, missing RPO/RTO evidence, missing retention/legal-hold proof, missing permission, missing audit fields, or missing monitoring alerts."
    )
    payload["readiness_evidence"] = _backup_restore_recovery_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_backup_restore_recovery_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 backup / restore disaster recovery 任务")
    payload["assistant_message"] = (
        "请确认这份 backup / restore recovery 工作协议；确认后我会生成 Backup Recovery Contract Inspector 先固定契约、"
        "Backup Restore Builder 再实现、Restore Drill Evidence Inspector 与 Retention Security Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条生产数据库 backup / restore 和 disaster recovery 任务编排 contract-first Loop：{task}。"
        "Backup Recovery Contract Inspector 先只读固定 nightly backup、PITR、cross-region snapshot、encryption key access、retention/legal hold、schema-migration restore、tenant/full database restore、RPO/RTO、integrity、monitoring、restore permission 和 audit targets；"
        "Backup Restore Builder 只能基于该 handoff 实现；Restore Drill Evidence Inspector 与 Retention Security Audit Inspector 并行检查；"
        "GateKeeper 对 backup-job-green-only、snapshot-file-only、dashboard-green-only、restore drill 缺失、PITR 缺失、checksum/row count/smoke proof 缺失、RPO/RTO 证据缺失、retention/legal-hold proof 缺失、permission 缺失、audit fields 缺失或 monitoring alerts 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _backup_restore_recovery_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_backup_restore_recovery_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de backup restore recovery confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de backup / restore recovery; después compilaré un workflow recovery-contract-first con inspecciones paralelas de Restore Drill Evidence y Retention Security Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de production backup / restore y disaster recovery con un Loop contract-first: {task}. "
        "Backup Recovery Contract Inspector fija nightly backups, PITR, cross-region snapshots, encryption key access, retention/legal hold, schema migration restore, tenant/full DB restore, RPO/RTO, integrity, monitoring, permission y audit targets; "
        "Backup Restore Builder implementa desde ese handoff; Restore Drill Evidence Inspector y Retention Security Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante backup-job-green-only, snapshot-file-only, dashboard-green-only, missing restore drill, missing PITR, missing integrity proof, missing RPO/RTO, missing retention/legal-hold, missing permission, missing audit o missing monitoring."
    )
    payload["readiness_evidence"] = _backup_restore_recovery_readiness_evidence(task, language="es")
    return payload


def alignment_english_audit_log_integrity_retention_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed audit trail task")
    payload["assistant_message"] = (
        "Please confirm this audit log integrity/retention working agreement; I will compile an audit-contract-first workflow "
        "with parallel Audit Integrity and Retention Export inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this compliance audit trail task through a contract-first Loop: {task}. "
        "Audit Contract Inspector first freezes event matrix, required fields, redaction, append-only/hash-chain/WORM integrity, clock skew, retention/legal hold, SIEM/export reconciliation, tenant access, retry semantics, logging failure/sequence gap alerts, migration, and governance; "
        "Audit Trail Builder implements only from that handoff; Audit Integrity Inspector and Retention Export Inspector inspect in parallel; "
        "GateKeeper fails closed on database-row-only, console-log-only, UI-history-only, reviewability-only, missing tamper negative, missing retention/legal hold, missing export reconciliation, missing tenant negative, missing redaction, missing retry proof, missing monitoring, missing migration, or skipped local governance."
    )
    payload["readiness_evidence"] = _audit_log_integrity_retention_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_audit_log_integrity_retention_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 audit trail 任务")
    payload["assistant_message"] = (
        "请确认这份 audit log integrity/retention 工作协议；确认后我会生成 Audit Contract Inspector 先固定审计契约、"
        "Audit Trail Builder 再实现、Audit Integrity Inspector 与 Retention Export Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 compliance audit trail 任务编排 contract-first Loop：{task}。"
        "Audit Contract Inspector 先只读固定 event matrix、required fields、redaction、append-only/hash-chain/WORM integrity、clock skew、retention/legal hold、SIEM/export reconciliation、tenant access、retry semantics、logging failure/sequence gap alerts、migration 和 governance；"
        "Audit Trail Builder 只能基于该 handoff 实现；Audit Integrity Inspector 与 Retention Export Inspector 并行检查；"
        "GateKeeper 对 database-row-only、console-log-only、UI-history-only、reviewability-only、tamper negative 缺失、retention/legal hold 缺失、export reconciliation 缺失、tenant negative 缺失、redaction 缺失、retry proof 缺失、monitoring 缺失、migration 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _audit_log_integrity_retention_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_audit_log_integrity_retention_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de audit trail confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de audit log integrity/retention; después compilaré un workflow audit-contract-first "
        "con inspecciones paralelas de Audit Integrity y Retention Export antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de compliance audit trail con un Loop contract-first: {task}. "
        "Audit Contract Inspector fija event matrix, fields, redaction, append-only/hash-chain/WORM integrity, clock skew, retention/legal hold, export reconciliation, tenant access, retry, alerts, migration y governance; "
        "Audit Trail Builder implementa desde ese handoff; Audit Integrity Inspector y Retention Export Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante row-only, console-only, UI-history-only, reviewability-only, missing tamper, retention, export reconciliation, tenant negative, redaction, retry, monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _audit_log_integrity_retention_readiness_evidence(task, language="es")
    return payload
