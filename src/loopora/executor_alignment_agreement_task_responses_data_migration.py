from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _cdc_replication_consistency_readiness_evidence,
    _database_schema_migration_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_database_schema_migration_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed database schema migration task")
    payload["assistant_message"] = (
        "Please confirm this database schema migration / backfill working agreement; I will compile a "
        "migration-contract-first workflow with parallel Data Consistency and Operational Rollback inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this multi-tenant database schema migration / backfill task through a contract-first Loop: {task}. "
        "Migration Contract Inspector first freezes old/new schema semantics, dual-write window, reader compatibility, tenant isolation, backfill idempotency/retry, invoice reconciliation, progress monitoring, pause/resume, rollback to old readers, cleanup, compatibility, and governance; "
        "Schema Migration Builder implements only from that handoff; Data Consistency Inspector and Operational Rollback Inspector inspect in parallel; "
        "GateKeeper fails closed on table-only migration, one-happy-path-test, one-time backfill, docs-only rollback, missing old-reader parity, missing tenant negative, missing retry proof, missing invoice reconciliation, missing monitoring, or skipped governance."
    )
    payload["readiness_evidence"] = _database_schema_migration_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_database_schema_migration_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 database schema migration 任务")
    payload["assistant_message"] = (
        "请确认这份 database schema migration / backfill 工作协议；确认后我会生成 Migration Contract Inspector 先固定迁移契约、"
        "Schema Migration Builder 再实现、Data Consistency Inspector 与 Operational Rollback Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 multi-tenant database schema migration / backfill 任务编排 contract-first Loop：{task}。"
        "Migration Contract Inspector 先固定 old/new schema semantics、dual-write window、reader compatibility、tenant isolation、backfill idempotency/retry、invoice reconciliation、progress monitoring、pause/resume、rollback to old readers、cleanup、compatibility 和 governance；"
        "Schema Migration Builder 只能基于该 handoff 实现；Data Consistency Inspector 与 Operational Rollback Inspector 并行检查；"
        "GateKeeper 对 table-only migration、one-happy-path-test、one-time backfill、docs-only rollback、old-reader parity 缺失、tenant negative 缺失、retry proof 缺失、invoice reconciliation 缺失、monitoring 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _database_schema_migration_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_database_schema_migration_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de database schema migration confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de database schema migration / backfill; después compilaré un workflow migration-contract-first "
        "con inspecciones paralelas de Data Consistency y Operational Rollback antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de multi-tenant database schema migration / backfill con un Loop contract-first: {task}. "
        "Migration Contract Inspector fija old/new schema, dual-write, reader compatibility, tenant isolation, backfill idempotency/retry, invoice reconciliation, monitoring, pause/resume, rollback, cleanup, compatibility y governance; "
        "Schema Migration Builder implementa desde ese handoff; Data Consistency y Operational Rollback inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante table-only migration, one happy-path, one-time backfill, docs-only rollback, missing reader parity, tenant negative, retry, invoice reconciliation, monitoring o governance."
    )
    payload["readiness_evidence"] = _database_schema_migration_readiness_evidence(task, language="es")
    return payload


def alignment_english_cdc_replication_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed CDC replication task")
    payload["assistant_message"] = (
        "Please confirm this CDC replication consistency working agreement; I will compile a CDC-contract-first workflow "
        "with parallel Replication Evidence and Reconciliation Lag inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this CDC replication / warehouse / read-model task through a contract-first Loop: {task}. "
        "CDC Contract Inspector first freezes source event schema, ordering keys, snapshot/backfill boundaries, checkpoint replay semantics, tombstones, schema evolution, tenant filters, reconciliation queries, lag SLO/alerts, connector recovery, audit, and governance; "
        "CDC Pipeline Builder implements only from that handoff; Replication Evidence Inspector and Reconciliation Lag Inspector inspect in parallel; "
        "GateKeeper fails closed on green-sync-job-only, row-count-sample-only, dashboard-latest-only, missing out-of-order proof, missing replay duplicate negative, missing schema evolution fixture, missing tombstone proof, missing lag alert, missing connector recovery, or skipped governance."
    )
    payload["readiness_evidence"] = _cdc_replication_consistency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_cdc_replication_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 CDC replication 任务")
    payload["assistant_message"] = (
        "请确认这份 CDC replication consistency 工作协议；确认后我会生成 CDC Contract Inspector 先固定复制契约、"
        "CDC Pipeline Builder 再实现、Replication Evidence Inspector 与 Reconciliation Lag Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 CDC replication / warehouse / read-model 任务编排 contract-first Loop：{task}。"
        "CDC Contract Inspector 先固定 source event schema、ordering keys、snapshot/backfill boundaries、checkpoint replay semantics、tombstones、schema evolution、tenant filters、reconciliation queries、lag SLO/alerts、connector recovery、audit 和 governance；"
        "CDC Pipeline Builder 只能基于该 handoff 实现；Replication Evidence Inspector 与 Reconciliation Lag Inspector 并行检查；"
        "GateKeeper 对 green-sync-job-only、row-count-sample-only、dashboard-latest-only、out-of-order proof 缺失、replay duplicate negative 缺失、schema evolution fixture 缺失、tombstone proof 缺失、lag alert 缺失、connector recovery 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _cdc_replication_consistency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_cdc_replication_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de CDC replication confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de CDC replication consistency; después compilaré un workflow CDC-contract-first "
        "con inspecciones paralelas de Replication Evidence y Reconciliation Lag antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de CDC replication / warehouse / read-model con un Loop contract-first: {task}. "
        "CDC Contract Inspector fija source event schema, ordering, snapshot/backfill, checkpoint replay, tombstones, schema evolution, tenant filters, reconciliation, lag SLO/alerts, connector recovery, audit y governance; "
        "CDC Pipeline Builder implementa desde ese handoff; Replication Evidence y Reconciliation Lag inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante green-sync-only, row-count sample only, dashboard latest only, missing out-of-order, replay duplicate negative, schema evolution, tombstone, lag alert, connector recovery o governance."
    )
    payload["readiness_evidence"] = _cdc_replication_consistency_readiness_evidence(task, language="es")
    return payload
