from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _incident_root_cause_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_incident_root_cause_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed incident repair task")
    payload["assistant_message"] = (
        "Please confirm this incident/root-cause working agreement; I will compile a read-only Repro Inspector first, "
        "then a root-cause Builder, Monitoring Inspector, and strict GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this incident/root-cause task through a repro-first Loop: {task}. "
        "Repro Inspector first pins reproduction evidence, trigger conditions, and failure mode without editing; "
        "Incident Builder may patch only from that handoff; Monitoring Inspector verifies the regression guard, recurrence detection, "
        "alerts, and release or rollback proof; GateKeeper fails closed on narrative-only root cause, patch evidence not tied to repro, "
        "or missing monitoring / rollback evidence."
    )
    payload["readiness_evidence"] = _incident_root_cause_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_incident_root_cause_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的事故修复任务")
    payload["assistant_message"] = "请确认这份事故 / root-cause 工作协议；确认后我会生成先只读复现检查、再根因修复、监控检查和严格 GateKeeper 的 Loop。"
    payload["agreement_summary"] = (
        f"围绕这条事故 / root-cause 任务编排 repro-first Loop：{task}。"
        "Repro Inspector 先只读固定复现证据、触发条件和 failure mode；Incident Builder 只能基于该 handoff 修 root cause；"
        "Monitoring Inspector 验证 regression guard、复发检测、告警和发布 / 回滚证据；GateKeeper 对 narrative-only root cause、"
        "patch 证据没有绑定复现链路、缺少 monitoring 或 rollback proof 时 fail closed。"
    )
    payload["readiness_evidence"] = _incident_root_cause_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_incident_root_cause_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de incidente/root cause confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de incidente/root cause; después compilaré un Loop con Repro Inspector solo lectura primero, "
        "luego Builder de root cause, Inspector de monitoring y GateKeeper estricto."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de incidente/root cause con un Loop repro-first: {task}. "
        "Repro Inspector fija evidencia de reproducción, condiciones de disparo y failure mode sin editar; "
        "Incident Builder parchea solo desde ese handoff; Monitoring Inspector verifica regresión, detección de recurrencia, alertas y release/rollback; "
        "GateKeeper falla cerrado ante root cause narrativo, patch no ligado a repro o falta de monitoring/rollback."
    )
    payload["readiness_evidence"] = _incident_root_cause_readiness_evidence(task, language="es")
    return payload
