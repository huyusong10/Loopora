from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import _authorization_policy_readiness_evidence
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_authorization_policy_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed authorization policy task")
    payload["assistant_message"] = (
        "Please confirm this authorization-policy working agreement; I will compile one narrow Builder followed by "
        "parallel Contract and Security Evidence Inspectors before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this authorization-policy consistency task through a parallel-inspection Loop: {task}. "
        "Policy Builder implements the narrow shared-decision slice and leaves a policy trace; Contract Inspector verifies the permission matrix, "
        "policy-decision trace, rollout and compatibility contract; Security Evidence Inspector independently attacks negative authorization, "
        "tenant escalation, stale cache / revocation, exports, jobs, field leakage, and audit proof; GateKeeper reads both parallel handoffs and fails closed if either is Weak or Unproven."
    )
    payload["readiness_evidence"] = _authorization_policy_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_authorization_policy_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的授权策略一致性任务")
    payload["assistant_message"] = (
        "请确认这份 authorization policy 工作协议；确认后我会生成一个窄 Builder，然后并行 Contract Inspector 与 Security Evidence Inspector，最后由 GateKeeper 裁决。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 authorization policy consistency 任务编排并行检查 Loop：{task}。"
        "Policy Builder 实现最小共享决策切片并留下 policy trace；Contract Inspector 验证 permission matrix、policy-decision trace、rollout 和兼容契约；"
        "Security Evidence Inspector 独立攻击负向授权、跨租户提权、stale cache / revocation、export、job、field leakage 和 audit proof；"
        "GateKeeper 读取两个并行 handoff，任一检查 Weak 或 Unproven 都 fail closed。"
    )
    payload["readiness_evidence"] = _authorization_policy_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_authorization_policy_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de authorization policy confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de authorization policy; después compilaré un Builder estrecho seguido por Contract Inspector "
        "y Security Evidence Inspector en paralelo antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de authorization-policy consistency con un Loop de inspección paralela: {task}. "
        "Policy Builder implementa el corte mínimo y deja policy trace; Contract Inspector verifica matriz, decision trace, rollout y compatibilidad; "
        "Security Evidence Inspector ataca negativos, escalación entre tenants, cache/revocation, exports, jobs, field leakage y audit; "
        "GateKeeper lee ambos handoffs paralelos y falla cerrado si cualquiera queda Weak o Unproven."
    )
    payload["readiness_evidence"] = _authorization_policy_readiness_evidence(task, language="es")
    return payload
