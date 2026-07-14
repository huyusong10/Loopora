from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _key_rotation_readiness_evidence,
    _prompt_asset_ownership_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_key_rotation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed API key rotation task")
    payload["assistant_message"] = (
        "Please confirm this API key / service account secret rotation working agreement; I will compile a "
        "key-rotation-contract-first workflow with parallel Rotation Lifecycle Evidence and Secret Storage Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this API key and service account secret rotation task through a contract-first Loop: {task}. "
        "Key Rotation Contract Inspector first freezes old/new overlap, zero-downtime compatibility, compromised-key revoke, revoked-key negatives, scope/tenant binding, hash/KMS storage, expiry, last-used telemetry, rollback, audit fields, and monitoring targets; "
        "Secret Rotation Builder implements only from that handoff; Rotation Lifecycle Evidence Inspector and Secret Storage Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on new-key-only UI, env-var-only, happy-path API call only, missing revoked-key negative, missing overlap proof, missing storage proof, missing audit fields, or missing monitoring proof."
    )
    payload["readiness_evidence"] = _key_rotation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_key_rotation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 API key / service account secret rotation 任务")
    payload["assistant_message"] = (
        "请确认这份 API key / service account secret rotation 工作协议；确认后我会生成 Key Rotation Contract Inspector 先固定契约、"
        "Secret Rotation Builder 再实现、Rotation Lifecycle Evidence Inspector 与 Secret Storage Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 API key 与 service account secret rotation 任务编排 contract-first Loop：{task}。"
        "Key Rotation Contract Inspector 先只读固定 old/new overlap、zero-downtime compatibility、compromised-key revoke、revoked-key negatives、scope/tenant binding、hash/KMS storage、expiry、last-used telemetry、rollback、audit fields 和 monitoring targets；"
        "Secret Rotation Builder 只能基于该 handoff 实现；Rotation Lifecycle Evidence Inspector 与 Secret Storage Audit Inspector 并行检查；"
        "GateKeeper 对 new-key-only UI、env-var-only、happy-path API call only、revoked-key negative 缺失、overlap proof 缺失、storage proof 缺失、audit fields 缺失或 monitoring proof 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _key_rotation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_key_rotation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de API key rotation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de API key / service account secret rotation; después compilaré un workflow key-rotation-contract-first con inspecciones paralelas de Rotation Lifecycle Evidence y Secret Storage Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de API key y service account secret rotation con un Loop contract-first: {task}. "
        "Key Rotation Contract Inspector fija overlap old/new, compatibilidad zero-downtime, revoke, negativos revoked-key, scope/tenant binding, hash/KMS storage, expiry, last-used telemetry, rollback, audit fields y monitoring targets; "
        "Secret Rotation Builder implementa desde ese handoff; Rotation Lifecycle Evidence Inspector y Secret Storage Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante new-key-only UI, env-var-only, happy-path-only, missing revoked-key negative, missing overlap proof, missing storage proof, missing audit fields o missing monitoring proof."
    )
    payload["readiness_evidence"] = _key_rotation_readiness_evidence(task, language="es")
    return payload


def alignment_english_prompt_asset_ownership_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed prompt asset ownership task")
    payload["assistant_message"] = (
        "Please confirm this prompt asset ownership working agreement; I will compile a contract-first workflow "
        "with parallel Prompt Asset Ownership and Runtime Prompt Rendering inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this fixed system/developer prompt decoupling task through a contract-first Loop: {task}. "
        "Prompt Surface Contract Inspector first freezes managed entries, role-agent instructions, Claude additional context, runtime prefixes, output contracts, alignment compiler prompt, shared proof/residual-risk guidance, role metadata descriptions, Strategy Source boundaries, and locale-neutral system_prompt asset rules; "
        "Prompt Asset Builder moves remaining fixed instruction bodies into assets without changing runtime semantics; Prompt Asset Ownership Inspector and Runtime Prompt Rendering Inspector inspect in parallel; "
        "GateKeeper fails closed on inline system-style instruction bodies, locale-specific system_prompt refs, weakened ownership tests, missing static asset refs, unresolved placeholders, or Strategy Source presets leaking into fixed system prompt loading."
    )
    payload["readiness_evidence"] = _prompt_asset_ownership_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_prompt_asset_ownership_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 system prompt asset ownership 任务")
    payload["assistant_message"] = (
        "请确认这份 system prompt asset ownership 工作协议；确认后我会生成 Prompt Surface Contract Inspector 先固定契约、"
        "Prompt Asset Builder 再迁移、Prompt Asset Ownership Inspector 与 Runtime Prompt Rendering Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条固定 system/developer prompt 解耦任务编排 contract-first Loop：{task}。"
        "Prompt Surface Contract Inspector 先固定 managed entries、role-agent instructions、Claude additional context、runtime prefixes、output contracts、alignment compiler prompt、shared proof/residual-risk guidance、role metadata descriptions、Strategy Source 边界和 locale-neutral system_prompt asset 规则；"
        "Prompt Asset Builder 迁移剩余固定指令体但不改变运行语义；Prompt Asset Ownership Inspector 与 Runtime Prompt Rendering Inspector 并行检查；"
        "GateKeeper 对 inline system-style instruction bodies、locale-specific system_prompt refs、弱化 ownership tests、缺少 static asset refs、unresolved placeholders 或 Strategy Source presets 泄漏到固定 system prompt loading fail closed。"
    )
    payload["readiness_evidence"] = _prompt_asset_ownership_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_prompt_asset_ownership_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de prompt asset ownership confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de prompt asset ownership; después compilaré un workflow contract-first con inspecciones paralelas de Prompt Asset Ownership y Runtime Prompt Rendering antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de desacoplar fixed system/developer prompts con un Loop contract-first: {task}. "
        "Prompt Surface Contract Inspector fija managed entries, role agents, Claude context, runtime prefixes, output contracts, alignment compiler prompt, shared guidance, role metadata, Strategy Source boundaries y reglas locale-neutral; "
        "Prompt Asset Builder migra instruction bodies sin cambiar semántica; Prompt Asset Ownership Inspector y Runtime Prompt Rendering Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante inline instruction bodies, locale-specific system_prompt refs, weakened tests, missing static refs, unresolved placeholders o Strategy Source leakage."
    )
    payload["readiness_evidence"] = _prompt_asset_ownership_readiness_evidence(task, language="es")
    return payload
