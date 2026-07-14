from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _concurrency_conflict_resolution_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_concurrency_conflict_resolution_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed collaborative editing conflict-resolution task")
    payload["assistant_message"] = (
        "Please confirm this conflict-resolution working agreement; I will compile a conflict-contract-first workflow "
        "with parallel Conflict Evidence and Permission Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this collaborative editing conflict-resolution task through a contract-first Loop: {task}. "
        "Conflict Contract Inspector first freezes two-user same-paragraph edit fixtures, version conflict / optimistic-lock semantics, safe merge versus reject rules, offline replay, idempotency keys, permission matrix, audit fields, monitoring, and governance; "
        "Collaboration Builder implements only from that handoff; Conflict Evidence Inspector and Permission Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on single-user-save-only, last-write-wins, happy-path WebSocket-only, missing optimistic-lock proof, missing offline replay idempotency, missing both-sides-preserved proof, missing permission negative, missing audit, or skipped governance."
    )
    payload["readiness_evidence"] = _concurrency_conflict_resolution_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_concurrency_conflict_resolution_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的协作文档冲突解决任务")
    payload["assistant_message"] = (
        "请确认这份 conflict-resolution 工作协议；确认后我会生成 Conflict Contract Inspector 先固定冲突契约、"
        "Collaboration Builder 再实现、Conflict Evidence Inspector 与 Permission Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 collaborative editing conflict-resolution 任务编排 contract-first Loop：{task}。"
        "Conflict Contract Inspector 先固定 two-user same-paragraph edit fixtures、version conflict / optimistic-lock semantics、safe merge versus reject rules、offline replay、idempotency keys、permission matrix、audit fields、monitoring 和 governance；"
        "Collaboration Builder 只能基于该 handoff 实现；Conflict Evidence Inspector 与 Permission Audit Inspector 并行检查；"
        "GateKeeper 对 single-user-save-only、last-write-wins、happy-path WebSocket-only、optimistic-lock proof 缺失、offline replay idempotency 缺失、both-sides-preserved proof 缺失、permission negative 缺失、audit 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _concurrency_conflict_resolution_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_concurrency_conflict_resolution_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de conflict-resolution confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de conflict-resolution; después compilaré un workflow conflict-contract-first "
        "con inspecciones paralelas de Conflict Evidence y Permission Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de collaborative editing conflict-resolution con un Loop contract-first: {task}. "
        "Conflict Contract Inspector fija two-user fixtures, optimistic locking, safe merge/reject rules, offline replay, idempotency keys, permission matrix, audit, monitoring y governance; "
        "Collaboration Builder implementa desde ese handoff; Conflict Evidence y Permission Audit inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante single-user-save-only, last-write-wins, WebSocket-only, missing optimistic-lock, offline replay, both-sides-preserved, permission negative, audit o governance."
    )
    payload["readiness_evidence"] = _concurrency_conflict_resolution_readiness_evidence(task, language="es")
    return payload
