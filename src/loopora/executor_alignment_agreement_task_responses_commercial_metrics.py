from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _metric_reporting_reconciliation_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_metric_reporting_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed revenue metric reporting task")
    payload["assistant_message"] = (
        "Please confirm this metric reporting reconciliation working agreement; I will compile a metric-contract-first "
        "workflow with parallel Metric Reconciliation and Permission Backfill inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this SaaS revenue metric reporting / MRR dashboard task through a contract-first Loop: {task}. "
        "Metric Contract Inspector first freezes metric definitions, version, edge cases, FX/cutoff/timezone, ledger/invoice/provider reconciliation, locked-month backfill, revenue segment permissions, export parity, audit, and governance; "
        "Revenue Dashboard Builder implements only from that handoff; Metric Reconciliation Inspector and Permission Backfill Inspector inspect in parallel; "
        "GateKeeper fails closed on chart-only, CSV-only, provider-total-only, missing edge-case fixture, missing ledger reconciliation, missing locked-month proof, missing permission negative, missing audit trail, missing monitoring, or skipped governance."
    )
    payload["readiness_evidence"] = _metric_reporting_reconciliation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_metric_reporting_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 revenue metric reporting 任务")
    payload["assistant_message"] = (
        "请确认这份 metric reporting reconciliation 工作协议；确认后我会生成 Metric Contract Inspector 先固定指标契约、"
        "Revenue Dashboard Builder 再实现、Metric Reconciliation Inspector 与 Permission Backfill Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 SaaS revenue metric reporting / MRR dashboard 任务编排 contract-first Loop：{task}。"
        "Metric Contract Inspector 先固定 metric definitions、version、edge cases、FX/cutoff/timezone、ledger/invoice/provider reconciliation、locked-month backfill、revenue segment permissions、export parity、audit 和 governance；"
        "Revenue Dashboard Builder 只能基于该 handoff 实现；Metric Reconciliation Inspector 与 Permission Backfill Inspector 并行检查；"
        "GateKeeper 对 chart-only、CSV-only、provider-total-only、edge-case fixture 缺失、ledger reconciliation 缺失、locked-month proof 缺失、permission negative 缺失、audit trail 缺失、monitoring 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _metric_reporting_reconciliation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_metric_reporting_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de revenue metric reporting confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de metric reporting reconciliation; después compilaré un workflow metric-contract-first "
        "con inspecciones paralelas de Metric Reconciliation y Permission Backfill antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de SaaS revenue metric reporting / MRR dashboard con un Loop contract-first: {task}. "
        "Metric Contract Inspector fija definitions, version, edge cases, FX/cutoff/timezone, ledger/invoice/provider reconciliation, locked-month backfill, permissions, export parity, audit y governance; "
        "Revenue Dashboard Builder implementa desde ese handoff; Metric Reconciliation y Permission Backfill inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante chart-only, CSV-only, provider-total-only, missing edge cases, reconciliation, locked-month proof, permission negative, audit trail, monitoring o governance."
    )
    payload["readiness_evidence"] = _metric_reporting_reconciliation_readiness_evidence(task, language="es")
    return payload
