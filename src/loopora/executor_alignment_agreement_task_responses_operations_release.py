from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _cache_invalidation_consistency_readiness_evidence,
    _feature_flag_rollout_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_feature_flag_rollout_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed feature flag rollout task")
    payload["assistant_message"] = (
        "Please confirm this feature-flag rollout working agreement; I will compile a release contract-first workflow "
        "with parallel Exposure Consistency and Operational Rollback inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this release rollout safety task through a contract-first Loop: {task}. "
        "Rollout Contract Inspector first freezes default-off behavior, cohort targeting, percentage rollout math, sticky assignment, exposure logging, kill switch, rollback cleanup, monitoring/alert thresholds, audit, local governance, and local-only bypass proof targets; "
        "Rollout Builder implements only from that handoff; Exposure Consistency Inspector and Operational Rollback Inspector inspect in parallel; "
        "GateKeeper fails closed on UI-toggle-only, local-flag-only, one beta happy path, docs-only rollout, missing sticky assignment, missing kill-switch / rollback proof, missing monitoring / conversion evidence, missing audit, or missing cohort negatives."
    )
    payload["readiness_evidence"] = _feature_flag_rollout_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_feature_flag_rollout_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 feature flag rollout 任务")
    payload["assistant_message"] = (
        "请确认这份 feature-flag rollout 工作协议；确认后我会生成发布契约先行、再并行曝光一致性与运营回滚检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 release rollout safety 任务编排 contract-first Loop：{task}。"
        "Rollout Contract Inspector 先固定 default-off、cohort targeting、percentage rollout math、sticky assignment、exposure logging、kill switch、rollback cleanup、monitoring/alert thresholds、audit、local governance 和 local-only bypass proof targets；"
        "Rollout Builder 只能基于该 handoff 实现；Exposure Consistency Inspector 与 Operational Rollback Inspector 并行检查；"
        "GateKeeper 对 UI-toggle-only、local-flag-only、one beta happy path、docs-only rollout、sticky assignment 缺失、kill switch / rollback 证明缺失、monitoring / conversion 证据缺失、audit 缺失或 cohort negatives 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _feature_flag_rollout_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_feature_flag_rollout_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de feature flag rollout confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de feature-flag rollout; después compilaré un workflow release contract-first "
        "con inspecciones paralelas de Exposure Consistency y Operational Rollback antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de release rollout safety con un Loop contract-first: {task}. "
        "Rollout Contract Inspector fija default-off, cohort targeting, percentage rollout, sticky assignment, exposure logging, kill switch, rollback cleanup, monitoring/alerts, audit, governance y local-only bypass targets; "
        "Rollout Builder implementa desde ese handoff; Exposure Consistency Inspector y Operational Rollback Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante UI-toggle-only, local-flag-only, beta happy path, docs-only rollout, sticky assignment faltante, rollback débil, monitoring/conversion faltante o audit/cohort negatives faltantes."
    )
    payload["readiness_evidence"] = _feature_flag_rollout_readiness_evidence(task, language="es")
    return payload


def alignment_english_cache_invalidation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed price cache invalidation task")
    payload["assistant_message"] = (
        "Please confirm this cache invalidation working agreement; I will compile a cache contract-first workflow "
        "with parallel Stale Read Evidence and Checkout Price Integrity inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this product price cache invalidation task through a cache contract-first Loop: {task}. "
        "Cache Contract Inspector first freezes price surfaces, cache-key inventory, TTL/SLA, PDP/cart/checkout/API/CDN/Redis/read-model boundaries, stale-read behavior, region/currency key isolation, rollback cleanup, audit, monitoring, and local governance proof targets; "
        "Price Cache Builder implements only from that handoff; Stale Read Evidence Inspector and Checkout Price Integrity Inspector inspect in parallel; "
        "GateKeeper fails closed on database-update-only, manual-refresh-only, single-cache-layer purge, one happy-path PDP, docs-only TTL, missing stale-read negatives, missing checkout old-price negative, missing region/currency key isolation, missing rollback cleanup, missing audit, or missing monitoring evidence."
    )
    payload["readiness_evidence"] = _cache_invalidation_consistency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_cache_invalidation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的商品价格缓存失效任务")
    payload["assistant_message"] = (
        "请确认这份 cache invalidation 工作协议；确认后我会生成缓存契约先行、再并行 stale-read 与 checkout 价格完整性检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 product price cache invalidation 任务编排 cache contract-first Loop：{task}。"
        "Cache Contract Inspector 先固定 price surfaces、cache-key inventory、TTL/SLA、PDP/cart/checkout/API/CDN/Redis/read-model boundaries、stale-read behavior、region/currency key isolation、rollback cleanup、audit、monitoring 和 local governance proof targets；"
        "Price Cache Builder 只能基于该 handoff 实现；Stale Read Evidence Inspector 与 Checkout Price Integrity Inspector 并行检查；"
        "GateKeeper 对 database-update-only、manual-refresh-only、single-cache-layer purge、one happy-path PDP、docs-only TTL、stale-read negatives 缺失、checkout old-price negative 缺失、region/currency key isolation 缺失、rollback cleanup 缺失、audit 缺失或 monitoring 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _cache_invalidation_consistency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_cache_invalidation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de cache invalidation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de cache invalidation; después compilaré un workflow cache contract-first "
        "con inspecciones paralelas de Stale Read Evidence y Checkout Price Integrity antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de product price cache invalidation con un Loop cache contract-first: {task}. "
        "Cache Contract Inspector fija price surfaces, cache-key inventory, TTL/SLA, boundaries PDP/cart/checkout/API/CDN/Redis/read-model, stale reads, region/currency isolation, rollback, audit, monitoring y governance; "
        "Price Cache Builder implementa desde ese handoff; Stale Read Evidence Inspector y Checkout Price Integrity Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante database-update-only, manual-refresh-only, single-cache-layer purge, happy-path PDP, docs-only TTL, stale-read negatives faltantes, checkout old-price negative faltante, key isolation faltante, rollback/audit/monitoring faltante."
    )
    payload["readiness_evidence"] = _cache_invalidation_consistency_readiness_evidence(task, language="es")
    return payload
