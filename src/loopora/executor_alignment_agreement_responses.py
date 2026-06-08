from __future__ import annotations

import re
from collections.abc import Callable

from loopora.alignment_traceability_terms import agent_candidate_traceability_terms
from loopora.executor_alignment_readiness_responses import (
    alignment_chinese_improvement_readiness_evidence,
    alignment_chinese_readiness_evidence,
    alignment_improvement_readiness_evidence,
    alignment_readiness_evidence,
)


LocalizedAgreementFactories = tuple[Callable[[str], dict], Callable[[str], dict], Callable[[str], dict]]


def alignment_agreement_response() -> dict:
    return {
        "status": "question",
        "assistant_message": "我会按这个工作协议生成：先做聚焦实现，再收集可复现证据，最后由守门者保守裁决。请回复“确认”后我再生成 Loop 方案。",
        "needs_user_input": True,
        "decision_options": [
            {
                "id": "confirm_agreement",
                "label": "采用这个方向（推荐）",
                "description": "按这份工作协议生成 Loop 方案。",
                "recommended": True,
                "user_reply": "确认，采用这个方向。",
            },
            {
                "id": "adjust_agreement",
                "label": "我想调整",
                "description": "先修改其中一个判断，再生成方案。",
                "recommended": False,
                "user_reply": "我想调整这份工作协议：",
            },
        ],
        "bundle_yaml": "",
        "session_ref": {
            "session_id": "",
            "thread_id": "",
            "conversation_id": "",
            "provider": "fake",
            "raw_json": "",
        },
        "alignment_phase": "agreement",
        "agreement_summary": "Use a focused Builder, evidence Inspector, and strict GateKeeper.",
        "readiness_checklist": {
            "loop_fit": True,
            "task_scope": True,
            "success_surface": True,
            "fake_done_risks": True,
            "evidence_preferences": True,
            "execution_strategy": True,
            "residual_risk_policy": True,
            "judgment_tradeoffs": True,
            "local_governance": True,
            "role_posture": True,
            "workflow_shape": True,
            "explicit_confirmation": False,
        },
        "readiness_evidence": alignment_readiness_evidence(
            open_questions="Waiting for explicit user confirmation of the working agreement."
        ),
    }


def alignment_chinese_agreement_response() -> dict:
    payload = alignment_agreement_response()
    payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
    payload["readiness_evidence"] = alignment_chinese_readiness_evidence(open_questions="等待用户明确确认这份工作协议。")
    return payload


def alignment_improvement_agreement_response() -> dict:
    payload = alignment_agreement_response()
    payload["assistant_message"] = (
        "Please confirm this improvement agreement; I will preserve the stable source Loop and revise only the feedback-driven governance surfaces."
    )
    payload["agreement_summary"] = (
        "Preserve the existing Loop's stable task intent and workdir, then change the evidence, role posture, and GateKeeper strictness that feedback shows are weak."
    )
    payload["readiness_evidence"] = alignment_improvement_readiness_evidence(
        open_questions="Waiting for explicit user confirmation of the improvement agreement."
    )
    return payload


def alignment_chinese_improvement_agreement_response() -> dict:
    payload = alignment_chinese_agreement_response()
    payload["assistant_message"] = "请确认这份改进协议；我会保留既有 Loop 的稳定意图，只修订反馈指向的治理面。"
    payload["agreement_summary"] = "保留既有 Loop 的稳定任务意图和 workdir，并基于反馈改进证据、角色姿态和 GateKeeper 严格度。"
    payload["readiness_evidence"] = alignment_chinese_improvement_readiness_evidence(open_questions="等待用户明确确认这份改进协议。")
    return payload


def alignment_chinese_refactor_improvement_agreement_response(feedback_text: str) -> dict:
    payload = alignment_chinese_improvement_agreement_response()
    feedback = feedback_text or "用户要求更激进但仍任务范围内的重构改进。"
    payload["assistant_message"] = "请确认这份重构改进协议；确认后我会把重构 delta 投射到 spec、阶段角色、workflow handoff 和 GateKeeper 阻断条件。"
    payload["agreement_summary"] = (
        "保留来源 Loop 的稳定搜索目标、workdir 和 executor 默认值；只允许任务范围内的重构 delta。"
        "这次改进把过大的 Search Builder 拆成 baseline、query rewrite、retrieval、ranking、regression review 和 evidence hardening 阶段。"
        "如果复杂度只是换地方、搜索用户行为回归或证据路径仍无法复验，GateKeeper 必须阻断。"
    )
    payload["readiness_evidence"] = {
        **alignment_chinese_improvement_readiness_evidence(open_questions="等待用户明确确认这份改进协议。"),
        "task_scope": (
            "保留来源 bundle 的搜索用户目标、workdir 和 executor 默认值；只改变任务范围内的重构 delta、重构风险与阶段证据边界，"
            f"不把反馈扩展成开放式平台重写。用户反馈：{feedback}"
        ),
        "success_surface": (
            "成功意味着改进后的独立 bundle 把 search refactor delta 映射到 baseline、query rewrite、retrieval、ranking、"
            "regression review 和 evidence hardening handoff；reviewer 可以证明复杂度没有只是换地方、搜索结果没有回归、证据路径可复验。"
        ),
        "fake_done_risks": (
            "拒绝只增加角色数量、复杂度只是换地方、只写更激进文案、搜索行为回归、缺少 baseline 或缺少阶段证据路径的改进。"
        ),
        "evidence_preferences": (
            "优先使用 baseline artifact、阶段 handoff、复杂度/可维护性证据、before/after regression evidence、"
            "项目检查、命令输出、日志或 evidence id，并继续区分已证明、弱证据、未证明、阻断和残余风险。"
        ),
        "execution_strategy": (
            "先锁定 baseline 和重构边界，再分别推进 query rewrite、retrieval 和 ranking；Regression Inspector 暴露复杂度转移、"
            "行为回归或证据缺口；Evidence Hardening Builder 只补 proof，GateKeeper 汇入所有阶段 handoff 后裁决。"
        ),
        "residual_risk_policy": (
            "轻微 tuning 风险只有在标为残余风险并有 owner/follow-up 时可保留；复杂度只是换地方、用户行为回归、baseline 缺失、"
            "阶段证据路径不可复验或跳过本地治理必须 fail closed。"
        ),
        "judgment_tradeoffs": (
            "优先任务范围内可证明的重构，而不是为了显得激进而大改；当速度、范围或角色数量与重构证据冲突时，"
            "复杂度没有转移、用户行为不回归和证据可复验优先。"
        ),
        "role_posture": (
            "Baseline Inspector 固定当前行为，阶段 Builder 只负责一个重构边界，Regression Inspector 反证复杂度转移和用户行为回归，"
            "Evidence Hardening Builder 补证据，GateKeeper 对未证明重构或回归 fail closed。"
        ),
        "workflow_shape": (
            "使用 long-chain 改进 workflow，因为 baseline、query rewrite、retrieval、ranking、regression review 和 evidence hardening "
            "各自产生不同 artifact、handoff 和 proof target；GateKeeper 必须读取 baseline、review 和 hardening handoff，"
            "让弱证据、复杂度转移、行为回归或假完成在 closure 前暴露。"
        ),
    }
    return payload


def alignment_task_anchored_agreement_response(
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> dict:
    task = str(task_text or "").strip()
    for predicate, factories in _task_specific_agreement_factories():
        if predicate(task):
            return _localized_task_agreement_response(
                task,
                prefers_chinese=prefers_chinese,
                display_language=display_language,
                factories=factories,
            )
    return _localized_task_agreement_response(
        task,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
        factories=(
            alignment_chinese_task_anchored_agreement_response,
            alignment_spanish_task_anchored_agreement_response,
            alignment_english_task_anchored_agreement_response,
        ),
    )


def _task_specific_agreement_factories() -> tuple[tuple[Callable[[str], bool], LocalizedAgreementFactories], ...]:
    return (
        (
            _agreement_is_prompt_asset_ownership_task,
            (
                alignment_chinese_prompt_asset_ownership_agreement_response,
                alignment_spanish_prompt_asset_ownership_agreement_response,
                alignment_english_prompt_asset_ownership_agreement_response,
            ),
        ),
        (
            _agreement_is_backup_restore_recovery_task,
            (
                alignment_chinese_backup_restore_recovery_agreement_response,
                alignment_spanish_backup_restore_recovery_agreement_response,
                alignment_english_backup_restore_recovery_agreement_response,
            ),
        ),
        (
            _agreement_is_audit_log_integrity_retention_task,
            (
                alignment_chinese_audit_log_integrity_retention_agreement_response,
                alignment_spanish_audit_log_integrity_retention_agreement_response,
                alignment_english_audit_log_integrity_retention_agreement_response,
            ),
        ),
        (
            _agreement_is_database_schema_migration_task,
            (
                alignment_chinese_database_schema_migration_agreement_response,
                alignment_spanish_database_schema_migration_agreement_response,
                alignment_english_database_schema_migration_agreement_response,
            ),
        ),
        (
            _agreement_is_cdc_replication_consistency_task,
            (
                alignment_chinese_cdc_replication_consistency_agreement_response,
                alignment_spanish_cdc_replication_consistency_agreement_response,
                alignment_english_cdc_replication_consistency_agreement_response,
            ),
        ),
        (
            _agreement_is_metric_reporting_reconciliation_task,
            (
                alignment_chinese_metric_reporting_reconciliation_agreement_response,
                alignment_spanish_metric_reporting_reconciliation_agreement_response,
                alignment_english_metric_reporting_reconciliation_agreement_response,
            ),
        ),
        (
            _agreement_is_dispute_chargeback_lifecycle_task,
            (
                alignment_chinese_dispute_chargeback_lifecycle_agreement_response,
                alignment_spanish_dispute_chargeback_lifecycle_agreement_response,
                alignment_english_dispute_chargeback_lifecycle_agreement_response,
            ),
        ),
        (
            _agreement_is_payout_settlement_reconciliation_task,
            (
                alignment_chinese_payout_settlement_reconciliation_agreement_response,
                alignment_spanish_payout_settlement_reconciliation_agreement_response,
                alignment_english_payout_settlement_reconciliation_agreement_response,
            ),
        ),
        (
            _agreement_is_analytics_experiment_instrumentation_task,
            (
                alignment_chinese_analytics_experiment_instrumentation_agreement_response,
                alignment_spanish_analytics_experiment_instrumentation_agreement_response,
                alignment_english_analytics_experiment_instrumentation_agreement_response,
            ),
        ),
        (
            _agreement_is_schedule_phase_task,
            (
                alignment_chinese_schedule_timezone_recurrence_agreement_response,
                alignment_spanish_schedule_timezone_recurrence_agreement_response,
                alignment_english_schedule_timezone_recurrence_agreement_response,
            ),
        ),
        (
            _agreement_is_dsar_data_export_task,
            (
                alignment_chinese_dsar_data_export_agreement_response,
                alignment_spanish_dsar_data_export_agreement_response,
                alignment_english_dsar_data_export_agreement_response,
            ),
        ),
        (
            _agreement_is_support_ticket_sla_task,
            (
                alignment_chinese_support_ticket_sla_agreement_response,
                alignment_spanish_support_ticket_sla_agreement_response,
                alignment_english_support_ticket_sla_agreement_response,
            ),
        ),
        (
            _agreement_is_subscription_entitlement_billing_task,
            (
                alignment_chinese_subscription_entitlement_billing_agreement_response,
                alignment_spanish_subscription_entitlement_billing_agreement_response,
                alignment_english_subscription_entitlement_billing_agreement_response,
            ),
        ),
        (
            _agreement_is_notification_subscription_deliverability_task,
            (
                alignment_chinese_notification_subscription_deliverability_agreement_response,
                alignment_spanish_notification_subscription_deliverability_agreement_response,
                alignment_english_notification_subscription_deliverability_agreement_response,
            ),
        ),
        (
            _agreement_is_data_lifecycle_deletion_retention_task,
            (
                alignment_chinese_data_lifecycle_deletion_retention_agreement_response,
                alignment_spanish_data_lifecycle_deletion_retention_agreement_response,
                alignment_english_data_lifecycle_deletion_retention_agreement_response,
            ),
        ),
        (
            _agreement_is_feature_flag_rollout_task,
            (
                alignment_chinese_feature_flag_rollout_agreement_response,
                alignment_spanish_feature_flag_rollout_agreement_response,
                alignment_english_feature_flag_rollout_agreement_response,
            ),
        ),
        (
            _agreement_is_cache_invalidation_consistency_task,
            (
                alignment_chinese_cache_invalidation_consistency_agreement_response,
                alignment_spanish_cache_invalidation_consistency_agreement_response,
                alignment_english_cache_invalidation_consistency_agreement_response,
            ),
        ),
        (
            _agreement_is_data_import_validation_task,
            (
                alignment_chinese_data_import_validation_agreement_response,
                alignment_spanish_data_import_validation_agreement_response,
                alignment_english_data_import_validation_agreement_response,
            ),
        ),
        (
            _agreement_is_concurrency_conflict_resolution_task,
            (
                alignment_chinese_concurrency_conflict_resolution_agreement_response,
                alignment_spanish_concurrency_conflict_resolution_agreement_response,
                alignment_english_concurrency_conflict_resolution_agreement_response,
            ),
        ),
        (
            _agreement_is_usage_quota_metering_task,
            (
                alignment_chinese_usage_quota_metering_agreement_response,
                alignment_spanish_usage_quota_metering_agreement_response,
                alignment_english_usage_quota_metering_agreement_response,
            ),
        ),
        (
            _agreement_is_tax_calculation_compliance_task,
            (
                alignment_chinese_tax_calculation_compliance_agreement_response,
                alignment_spanish_tax_calculation_compliance_agreement_response,
                alignment_english_tax_calculation_compliance_agreement_response,
            ),
        ),
        (
            _agreement_is_inventory_reservation_consistency_task,
            (
                alignment_chinese_inventory_reservation_consistency_agreement_response,
                alignment_spanish_inventory_reservation_consistency_agreement_response,
                alignment_english_inventory_reservation_consistency_agreement_response,
            ),
        ),
        (
            _agreement_is_file_upload_storage_safety_task,
            (
                alignment_chinese_file_upload_storage_safety_agreement_response,
                alignment_spanish_file_upload_storage_safety_agreement_response,
                alignment_english_file_upload_storage_safety_agreement_response,
            ),
        ),
        (
            _agreement_is_auth_session_token_lifecycle_task,
            (
                alignment_chinese_auth_session_token_lifecycle_agreement_response,
                alignment_spanish_auth_session_token_lifecycle_agreement_response,
                alignment_english_auth_session_token_lifecycle_agreement_response,
            ),
        ),
        (
            _agreement_is_data_residency_task,
            (
                alignment_chinese_data_residency_agreement_response,
                alignment_spanish_data_residency_agreement_response,
                alignment_english_data_residency_agreement_response,
            ),
        ),
        (
            _agreement_is_support_impersonation_task,
            (
                alignment_chinese_support_impersonation_agreement_response,
                alignment_spanish_support_impersonation_agreement_response,
                alignment_english_support_impersonation_agreement_response,
            ),
        ),
        (
            _agreement_is_kyc_aml_screening_task,
            (
                alignment_chinese_kyc_aml_screening_agreement_response,
                alignment_spanish_kyc_aml_screening_agreement_response,
                alignment_english_kyc_aml_screening_agreement_response,
            ),
        ),
        (
            _agreement_is_identity_sso_task,
            (
                alignment_chinese_identity_sso_agreement_response,
                alignment_spanish_identity_sso_agreement_response,
                alignment_english_identity_sso_agreement_response,
            ),
        ),
        (
            _agreement_is_key_rotation_task,
            (
                alignment_chinese_key_rotation_agreement_response,
                alignment_spanish_key_rotation_agreement_response,
                alignment_english_key_rotation_agreement_response,
            ),
        ),
        (
            _agreement_is_payment_webhook_ledger_task,
            (
                alignment_chinese_payment_webhook_ledger_agreement_response,
                alignment_spanish_payment_webhook_ledger_agreement_response,
                alignment_english_payment_webhook_ledger_agreement_response,
            ),
        ),
        (
            _agreement_is_rag_long_chain_task,
            (
                alignment_chinese_rag_long_chain_agreement_response,
                alignment_spanish_rag_long_chain_agreement_response,
                alignment_english_rag_long_chain_agreement_response,
            ),
        ),
        (
            _agreement_is_authorization_policy_task,
            (
                alignment_chinese_authorization_policy_agreement_response,
                alignment_spanish_authorization_policy_agreement_response,
                alignment_english_authorization_policy_agreement_response,
            ),
        ),
        (
            _agreement_is_incident_root_cause_task,
            (
                alignment_chinese_incident_root_cause_agreement_response,
                alignment_spanish_incident_root_cause_agreement_response,
                alignment_english_incident_root_cause_agreement_response,
            ),
        ),
        (
            _agreement_is_search_index_consistency_task,
            (
                alignment_chinese_search_index_consistency_agreement_response,
                alignment_spanish_search_index_consistency_agreement_response,
                alignment_english_search_index_consistency_agreement_response,
            ),
        ),
        (
            _agreement_is_search_quality_task,
            (
                alignment_chinese_search_quality_agreement_response,
                alignment_spanish_search_quality_agreement_response,
                alignment_english_search_quality_agreement_response,
            ),
        ),
    )


def _localized_task_agreement_response(
    task: str,
    *,
    prefers_chinese: bool,
    display_language: str,
    factories: LocalizedAgreementFactories,
) -> dict:
    chinese_factory, spanish_factory, english_factory = factories
    if prefers_chinese:
        return chinese_factory(task)
    if str(display_language or "").strip().lower() == "es":
        return spanish_factory(task)
    return english_factory(task)


def alignment_english_search_index_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed search index consistency task")
    payload["assistant_message"] = (
        "Please confirm this search-index consistency working agreement; I will compile a search-index-contract-first "
        "workflow with parallel Index Consistency and Access Freshness inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this knowledge-base search-index consistency task through a contract-first Loop: {task}. "
        "Search Index Contract Inspector first freezes document event schema, create/update/delete semantics, tenant ACL and permission-change rules, index alias/versioning, reindex/backfill cursor and idempotency, watermark recovery, lag SLO/alerts, pagination/sort stability samples, audit fields, retry/DLQ behavior, and governance; "
        "Search Index Builder implements only from that handoff; Index Consistency Inspector and Access Freshness Inspector inspect in parallel; "
        "GateKeeper fails closed on local-search-only, green-index-job-only, row-count-sample-only, dashboard-latest-only, missing ACL negatives, missing deleted-document proof, missing reindex idempotency, missing cursor recovery, missing lag alert, missing audit, or skipped governance."
    )
    payload["readiness_evidence"] = _search_index_consistency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_search_index_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 search index consistency 任务")
    payload["assistant_message"] = (
        "请确认这份 search-index consistency 工作协议；确认后我会生成 Search Index Contract Inspector 先固定索引契约、"
        "Search Index Builder 再实现、Index Consistency Inspector 与 Access Freshness Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 knowledge-base search-index consistency 任务编排 contract-first Loop：{task}。"
        "Search Index Contract Inspector 先固定 document event schema、create/update/delete 语义、tenant ACL 与 permission-change rules、index alias/versioning、reindex/backfill cursor 与 idempotency、watermark recovery、lag SLO/alerts、pagination/sort stability samples、audit fields、retry/DLQ behavior 和 governance；"
        "Search Index Builder 只能基于该 handoff 实现；Index Consistency Inspector 与 Access Freshness Inspector 并行检查；"
        "GateKeeper 对 local-search-only、green-index-job-only、row-count-sample-only、dashboard-latest-only、ACL negatives 缺失、deleted-document proof 缺失、reindex idempotency 缺失、cursor recovery 缺失、lag alert 缺失、audit 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _search_index_consistency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_search_index_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de search index consistency confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de search-index consistency; después compilaré un workflow search-index-contract-first "
        "con inspecciones paralelas de Index Consistency y Access Freshness antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de knowledge-base search-index consistency con un Loop contract-first: {task}. "
        "Search Index Contract Inspector fija event schema, create/update/delete, tenant ACL, permission changes, alias/versioning, reindex/backfill cursor e idempotency, watermark recovery, lag alerts, pagination/sort samples, audit, retry/DLQ y governance; "
        "Search Index Builder implementa desde ese handoff; Index Consistency y Access Freshness inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante local-search-only, green-index-job-only, row-count-sample-only, dashboard-latest-only, missing ACL negatives, deleted-document proof, reindex idempotency, cursor recovery, lag alert, audit o governance."
    )
    payload["readiness_evidence"] = _search_index_consistency_readiness_evidence(task, language="es")
    return payload


def alignment_english_search_quality_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed search-quality task")
    payload["assistant_message"] = (
        "Please confirm this search-quality working agreement; I will compile a workflow that freezes the eval baseline before any search/ranking changes."
    )
    payload["agreement_summary"] = (
        f"Govern this search-quality task through an eval-first Loop: {task}. "
        "Evaluation Baseline Inspector freezes eval set, negative queries, regression samples, Top-5 baseline, and human-review rubric; "
        "Search Quality Builder changes retrieval/ranking from that handoff; Quality Evidence Inspector compares before/after and human quality records; "
        "GateKeeper fails closed on demo-query-only, single-score-only, or cherry-picked progress."
    )
    payload["readiness_evidence"] = _search_quality_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_search_quality_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 search quality 任务")
    payload["assistant_message"] = "请确认这份 search quality 工作协议；确认后我会生成先冻结 eval baseline、再改检索/排序、最后由 GateKeeper 裁决的 Loop。"
    payload["agreement_summary"] = (
        f"围绕这条 search quality 任务编排 eval-first Loop：{task}。"
        "Evaluation Baseline Inspector 先固定 eval set、负向查询、回归样本、Top-5 baseline 和人工评审 rubric；"
        "Search Quality Builder 只基于 baseline handoff 改检索/排序；Quality Evidence Inspector 比较 before/after 和人工质量记录；"
        "GateKeeper 对 demo-query-only、single-score-only 或 cherry-picked progress fail closed。"
    )
    payload["readiness_evidence"] = _search_quality_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_search_quality_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de search quality confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de search quality; después compilaré un Loop que congela eval baseline antes de cambiar retrieval/ranking."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de search quality con un Loop eval-first: {task}. "
        "Evaluation Baseline Inspector congela eval set, negativos, regresión, Top-5 baseline y rúbrica humana; "
        "Search Quality Builder cambia retrieval/ranking desde ese handoff; Quality Evidence Inspector compara before/after y revisión humana; "
        "GateKeeper falla cerrado ante demo-query-only o single-score-only."
    )
    payload["readiness_evidence"] = _search_quality_readiness_evidence(task, language="es")
    return payload


def alignment_english_rag_long_chain_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed RAG grounding task")
    payload["assistant_message"] = (
        "Please confirm this RAG grounding long-chain working agreement; I will compile a workflow with contract inspection, "
        "corpus ingestion, retrieval ACL, answer/tool gating, evaluation inspection, evidence hardening, and GateKeeper fan-in."
    )
    payload["agreement_summary"] = (
        f"Govern this enterprise RAG support chatbot grounding task through a long-chain Loop: {task}. "
        "RAG Contract Inspector first freezes document-version, source-span, retrieval ACL, tenant filtering, prompt-injection, tool allowlist, PII redaction, fallback/no-answer, eval, human-review, monitoring, and governance proof targets; "
        "Corpus Ingestion Builder, Retrieval ACL Builder, and Answer Tooling Builder create narrow staged handoffs; "
        "RAG Evaluation Inspector reads all three builder handoffs; Evidence Hardening Builder only repairs Weak, Unproven, or Blocking proof gaps from evaluation; "
        "RAG GateKeeper reads contract, evaluation, and hardening handoffs and fails closed on demo-only, plausible-answer-only, embedding-search-only, UI-citation-only, missing source spans, missing permission/tenant negatives, missing prompt-injection negatives, missing tool-safety, missing privacy redaction, missing eval/human-review/monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _rag_long_chain_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_rag_long_chain_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 RAG grounding 任务")
    payload["assistant_message"] = (
        "请确认这份 RAG grounding 长链工作协议；确认后我会生成先 contract inspection，再分阶段 ingestion、retrieval ACL、"
        "answer/tool gating、evaluation inspection、evidence hardening，最后 GateKeeper 汇总裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条企业 RAG support chatbot grounding 任务编排 long-chain Loop：{task}。"
        "RAG Contract Inspector 先只读固定 document-version、source-span、retrieval ACL、tenant filtering、prompt-injection、tool allowlist、PII redaction、fallback/no-answer、eval、human-review、monitoring 和 governance proof targets；"
        "Corpus Ingestion Builder、Retrieval ACL Builder 与 Answer Tooling Builder 生成窄阶段 handoff；"
        "RAG Evaluation Inspector 读取三个 builder handoff；Evidence Hardening Builder 只修 evaluation 点名的 Weak、Unproven 或 Blocking proof gaps；"
        "RAG GateKeeper 读取 contract、evaluation 和 hardening handoff，并对 demo-only、plausible-answer-only、embedding-search-only、UI-citation-only、source span 缺失、permission/tenant negatives 缺失、prompt-injection negatives 缺失、tool-safety 缺失、privacy redaction 缺失、eval/human-review/monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _rag_long_chain_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_rag_long_chain_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea RAG grounding confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo RAG grounding long-chain; después compilaré contract inspection, ingestion, retrieval ACL, "
        "answer/tool gating, evaluation, evidence hardening y GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea enterprise RAG support chatbot grounding con un Loop long-chain: {task}. "
        "RAG Contract Inspector fija document version, source spans, retrieval ACL, tenant filtering, prompt injection, tool allowlist, redaction, fallback/no-answer, eval, human review, monitoring y governance; "
        "Corpus Ingestion Builder, Retrieval ACL Builder y Answer Tooling Builder producen handoffs estrechos; "
        "RAG Evaluation Inspector lee los tres handoffs; Evidence Hardening Builder repara solo gaps Weak/Unproven/Blocking; "
        "RAG GateKeeper lee contract, evaluation y hardening y falla cerrado ante demo-only, plausible answer, embedding-search-only, UI-citation-only, missing permissions, tool safety, privacy, eval, monitoring o governance."
    )
    payload["readiness_evidence"] = _rag_long_chain_readiness_evidence(task, language="es")
    return payload


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
    payload["assistant_message"] = "请确认这份 feature-flag rollout 工作协议；确认后我会生成发布契约先行、再并行曝光一致性与运营回滚检查、最后 GateKeeper 裁决的 Loop。"
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
    payload["assistant_message"] = "请确认这份 cache invalidation 工作协议；确认后我会生成缓存契约先行、再并行 stale-read 与 checkout 价格完整性检查、最后 GateKeeper 裁决的 Loop。"
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


def alignment_english_inventory_reservation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed inventory reservation task")
    payload["assistant_message"] = (
        "Please confirm this inventory reservation working agreement; I will compile an inventory contract-first workflow "
        "with parallel Reservation Race and Payment Ledger inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this checkout inventory reservation and oversell-prevention task through a contract-first Loop: {task}. "
        "Inventory Contract Inspector first freezes SKU stock invariants, reservation state machine, hold TTL/expiry, payment webhook ordering, release semantics for cancellation/refund/failed payment, idempotency keys, reconciliation targets, sold-out/low-stock states, audit, monitoring, and governance; "
        "Inventory Reservation Builder implements only from that handoff; Reservation Race Inspector and Payment Ledger Inspector inspect in parallel; "
        "GateKeeper fails closed on one-user checkout, UI stock decrement, DB decrement only, missing TTL expiry, missing webhook replay/order, missing release proof, missing ledger reconciliation, missing sold-out consistency, missing audit/monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _inventory_reservation_consistency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_inventory_reservation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的库存预留任务")
    payload["assistant_message"] = (
        "请确认这份 inventory reservation 工作协议；确认后我会生成 Inventory Contract Inspector 先固定库存/预留契约、"
        "Inventory Reservation Builder 再实现、Reservation Race Inspector 与 Payment Ledger Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 checkout inventory reservation 与防超卖任务编排 contract-first Loop：{task}。"
        "Inventory Contract Inspector 先只读固定 SKU stock invariants、reservation state machine、hold TTL/expiry、payment webhook ordering、取消/退款/失败支付释放语义、idempotency keys、reconciliation targets、售罄/低库存状态、audit、monitoring 和 governance；"
        "Inventory Reservation Builder 只能基于该 handoff 实现；Reservation Race Inspector 与 Payment Ledger Inspector 并行检查；"
        "GateKeeper 对 one-user checkout、UI stock decrement、DB decrement only、TTL expiry 缺失、webhook replay/order 缺失、release proof 缺失、ledger reconciliation 缺失、sold-out consistency 缺失、audit/monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _inventory_reservation_consistency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_inventory_reservation_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de inventory reservation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de inventory reservation; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Reservation Race y Payment Ledger antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de checkout inventory reservation y oversell prevention con un Loop contract-first: {task}. "
        "Inventory Contract Inspector fija SKU invariants, reservation state machine, TTL/expiry, webhook ordering, release semantics, idempotency keys, reconciliation targets, sold-out/low-stock, audit, monitoring y governance; "
        "Inventory Reservation Builder implementa desde ese handoff; Reservation Race Inspector y Payment Ledger Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante one-user checkout, UI stock decrement, DB decrement only, missing TTL/webhook/release/reconciliation/sold-out/audit/monitoring proof o governance omitida."
    )
    payload["readiness_evidence"] = _inventory_reservation_consistency_readiness_evidence(task, language="es")
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


def alignment_english_usage_quota_metering_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed usage quota task")
    payload["assistant_message"] = (
        "Please confirm this usage quota metering working agreement; I will compile a quota contract-first workflow "
        "with parallel Quota Race and Billing Reconciliation inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this SaaS API usage metering / plan quota enforcement task through a contract-first Loop: {task}. "
        "Quota Contract Inspector first freezes usage event schema, idempotency keys, org/plan/quota windows, concurrency, duplicates, retries, plan changes, reset timezone, limits, permission-safe errors, ledger/invoice/provider reconciliation, audit, monitoring, migration, and governance; "
        "Usage Metering Builder implements only from that handoff; Quota Race Inspector and Billing Reconciliation Inspector inspect in parallel; "
        "GateKeeper fails closed on dashboard-only usage, single 429, cron reset only, provider total only, missing duplicate-event proof, missing concurrency proof, missing plan-change proof, missing reset timezone, missing reconciliation, missing audit/monitoring, missing migration, or skipped local governance."
    )
    payload["readiness_evidence"] = _usage_quota_metering_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_usage_quota_metering_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 usage quota 任务")
    payload["assistant_message"] = (
        "请确认这份 usage quota metering 工作协议；确认后我会生成 Quota Contract Inspector 先固定计量/限额契约、"
        "Usage Metering Builder 再实现、Quota Race Inspector 与 Billing Reconciliation Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 SaaS API usage metering / plan quota enforcement 任务编排 contract-first Loop：{task}。"
        "Quota Contract Inspector 先只读固定 usage event schema、idempotency keys、org/plan/quota windows、concurrency、duplicates、retries、plan changes、reset timezone、limits、permission-safe errors、ledger/invoice/provider reconciliation、audit、monitoring、migration 和 governance；"
        "Usage Metering Builder 只能基于该 handoff 实现；Quota Race Inspector 与 Billing Reconciliation Inspector 并行检查；"
        "GateKeeper 对 dashboard-only usage、single 429、cron reset only、provider total only、duplicate-event proof 缺失、concurrency proof 缺失、plan-change proof 缺失、reset timezone 缺失、reconciliation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _usage_quota_metering_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_usage_quota_metering_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de usage quota confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de usage quota metering; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Quota Race y Billing Reconciliation antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de SaaS API usage metering / plan quota enforcement con un Loop contract-first: {task}. "
        "Quota Contract Inspector fija usage schema, idempotency, org/plan/quota windows, concurrency, duplicates, retries, plan changes, reset timezone, limits, errors, reconciliation, audit, monitoring, migration y governance; "
        "Usage Metering Builder implementa desde ese handoff; Quota Race Inspector y Billing Reconciliation Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante dashboard-only, single 429, cron reset, provider total only, missing duplicate/concurrency/plan-change/reset/reconciliation/audit/monitoring/migration proof o governance omitida."
    )
    payload["readiness_evidence"] = _usage_quota_metering_readiness_evidence(task, language="es")
    return payload


def alignment_english_subscription_entitlement_billing_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed subscription entitlement task")
    payload["assistant_message"] = (
        "Please confirm this subscription entitlement / proration working agreement; I will compile a subscription "
        "contract-first workflow with parallel Entitlement State and Billing Proration Reconciliation inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this B2B SaaS subscription upgrade/downgrade and entitlement activation task through a contract-first Loop: {task}. "
        "Subscription Contract Inspector first freezes plan-change lifecycle, upgrade immediate effect, downgrade next-cycle effect, proration, credit memo, invoice totals, trial/grace, billing-period boundaries, provider checkout/webhook replay, duplicate-click idempotency, team-member entitlements, quota/history preservation, permissions, tenant boundaries, audit, rollback, monitoring, and governance; "
        "Entitlement Billing Builder implements only from that handoff; Entitlement State Inspector and Billing Proration Reconciliation Inspector inspect in parallel; "
        "GateKeeper fails closed on button-only, checkout-success-only, provider-total-only, happy-path plan change, missing downgrade-delayed proof, missing proration/credit memo, missing entitlement propagation, missing permission negatives, missing webhook replay/idempotency, missing reconciliation, missing rollback/monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _subscription_entitlement_billing_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_subscription_entitlement_billing_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 subscription entitlement 任务")
    payload["assistant_message"] = (
        "请确认这份 subscription entitlement / proration 工作协议；确认后我会生成 Subscription Contract Inspector 先固定订阅/权益/账单契约、"
        "Entitlement Billing Builder 再实现、Entitlement State Inspector 与 Billing Proration Reconciliation Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 B2B SaaS 订阅升级/降级和权益生效任务编排 contract-first Loop：{task}。"
        "Subscription Contract Inspector 先只读固定 plan-change lifecycle、升级立即生效、降级下个周期生效、proration、credit memo、invoice totals、试用/宽限期、billing-period boundaries、provider checkout/webhook replay、重复点击幂等、团队成员权益、quota/history preservation、权限、tenant boundaries、audit、rollback、monitoring 和 governance；"
        "Entitlement Billing Builder 只能基于该 handoff 实现；Entitlement State Inspector 与 Billing Proration Reconciliation Inspector 并行检查；"
        "GateKeeper 对 button-only、checkout-success-only、provider-total-only、happy-path plan change、降级延迟生效证明缺失、proration/credit memo 缺失、权益传播缺失、权限负向缺失、webhook replay/idempotency 缺失、对账缺失、rollback/monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _subscription_entitlement_billing_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_subscription_entitlement_billing_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de subscription entitlement confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de subscription entitlement / proration; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Entitlement State y Billing Proration Reconciliation antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea B2B SaaS subscription upgrade/downgrade y entitlement activation con un Loop contract-first: {task}. "
        "Subscription Contract Inspector fija lifecycle, immediate upgrade, next-cycle downgrade, proration, credit memo, invoice totals, trial/grace, billing boundaries, provider checkout/webhook replay, duplicate-click idempotency, team entitlements, quota/history, permissions, tenant boundaries, audit, rollback, monitoring y governance; "
        "Entitlement Billing Builder implementa desde ese handoff; Entitlement State Inspector y Billing Proration Reconciliation Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante button-only, checkout-success-only, provider-total-only, happy path, missing downgrade delay, proration/credit memo, entitlement propagation, permission negatives, webhook replay/idempotency, reconciliation, rollback/monitoring o governance omitida."
    )
    payload["readiness_evidence"] = _subscription_entitlement_billing_readiness_evidence(task, language="es")
    return payload


def alignment_english_support_ticket_sla_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed support ticket SLA task")
    payload["assistant_message"] = (
        "Please confirm this support ticket SLA working agreement; I will compile a support-ticket contract-first workflow "
        "with parallel Lifecycle Evidence and Access Notification Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this support ticket triage / SLA escalation task through a contract-first Loop: {task}. "
        "Support Ticket Contract Inspector first freezes email/API import, dedupe/merge, queue and lifecycle state machine, claim/assign/priority/status permissions, SLA clock and breach/escalation rules, queue health, notification dedupe, audit notes, tenant isolation, PII redaction, monitoring, and governance; "
        "Ticket SLA Builder implements only from that handoff; Ticket Lifecycle Inspector and Access Notification Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on Kanban-only, manager-dashboard-only, queued/open status-only, missing import dedupe, missing lifecycle transitions, missing SLA clock or breach escalation proof, missing permission or tenant negatives, missing notification suppression, missing audit/PII proof, or skipped local governance."
    )
    payload["readiness_evidence"] = _support_ticket_sla_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_support_ticket_sla_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 support ticket SLA 任务")
    payload["assistant_message"] = (
        "请确认这份 support ticket SLA 工作协议；确认后我会生成 Support Ticket Contract Inspector 先固定工单生命周期和 SLA 契约、"
        "Ticket SLA Builder 再实现、Ticket Lifecycle Inspector 与 Access Notification Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 support ticket triage / SLA escalation 任务编排 contract-first Loop：{task}。"
        "Support Ticket Contract Inspector 先只读固定 email/API import、dedupe/merge、queue 和 lifecycle state machine、claim/assign/priority/status permissions、SLA clock 与 breach/escalation rules、queue health、notification dedupe、audit notes、tenant isolation、PII redaction、monitoring 和 governance；"
        "Ticket SLA Builder 只能基于该 handoff 实现；Ticket Lifecycle Inspector 与 Access Notification Audit Inspector 并行检查；"
        "GateKeeper 对 Kanban-only、manager-dashboard-only、queued/open status-only、import dedupe 缺失、lifecycle transitions 缺失、SLA clock 或 breach escalation proof 缺失、permission/tenant negatives 缺失、notification suppression 缺失、audit/PII proof 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _support_ticket_sla_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_support_ticket_sla_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de support ticket SLA confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de support ticket SLA; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Lifecycle Evidence y Access Notification Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de support ticket triage / SLA escalation con un Loop contract-first: {task}. "
        "Support Ticket Contract Inspector fija import email/API, dedupe/merge, queue y lifecycle state machine, permisos de claim/assign/priority/status, SLA clock, breach/escalation, queue health, notification dedupe, audit notes, tenant isolation, PII redaction, monitoring y governance; "
        "Ticket SLA Builder implementa desde ese handoff; Ticket Lifecycle Inspector y Access Notification Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante Kanban-only, manager-dashboard-only, status-only, missing dedupe, lifecycle transitions, SLA/escalation, permission or tenant negatives, notification suppression, audit/PII proof o governance omitida."
    )
    payload["readiness_evidence"] = _support_ticket_sla_readiness_evidence(task, language="es")
    return payload


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


def alignment_english_tax_calculation_compliance_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed tax calculation task")
    payload["assistant_message"] = (
        "Please confirm this tax calculation compliance working agreement; I will compile a tax contract-first workflow "
        "with parallel Jurisdiction Rate and Invoice Reversal inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this checkout tax calculation compliance task through a contract-first Loop: {task}. "
        "Tax Contract Inspector first freezes nexus, US sales tax, EU VAT, GST, jurisdiction/address matrix, product taxability, exemptions, reverse charge, display mode, rounding, invoice/refund reversal, provider fallback/idempotency, effective dates, audit, reconciliation, migration, and governance; "
        "Tax Calculation Builder implements only from that handoff; Jurisdiction Rate Inspector and Invoice Reversal Inspector inspect in parallel; "
        "GateKeeper fails closed on one tax number, hardcoded rate, provider quote only, UI total only, missing jurisdiction matrix, missing exemption/reverse-charge, missing refund/reversal, missing rounding proof, missing reconciliation, missing audit/monitoring, missing migration, or skipped local governance."
    )
    payload["readiness_evidence"] = _tax_calculation_compliance_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_tax_calculation_compliance_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 tax calculation 任务")
    payload["assistant_message"] = (
        "请确认这份 tax calculation compliance 工作协议；确认后我会生成 Tax Contract Inspector 先固定税务计算契约、"
        "Tax Calculation Builder 再实现、Jurisdiction Rate Inspector 与 Invoice Reversal Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 checkout tax calculation compliance 任务编排 contract-first Loop：{task}。"
        "Tax Contract Inspector 先只读固定 nexus、US sales tax、EU VAT、GST、jurisdiction/address matrix、product taxability、exemptions、reverse charge、display mode、rounding、invoice/refund reversal、provider fallback/idempotency、effective dates、audit、reconciliation、migration 和 governance；"
        "Tax Calculation Builder 只能基于该 handoff 实现；Jurisdiction Rate Inspector 与 Invoice Reversal Inspector 并行检查；"
        "GateKeeper 对 one tax number、hardcoded rate、provider quote only、UI total only、jurisdiction matrix 缺失、exemption/reverse-charge 缺失、refund/reversal 缺失、rounding proof 缺失、reconciliation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _tax_calculation_compliance_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_tax_calculation_compliance_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de tax calculation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de tax calculation compliance; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Jurisdiction Rate e Invoice Reversal antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de checkout tax calculation compliance con un Loop contract-first: {task}. "
        "Tax Contract Inspector fija nexus, sales tax/VAT/GST, jurisdiction/address matrix, taxability, exemptions, reverse charge, display, rounding, invoice/refund reversal, provider fallback/idempotency, effective dates, audit, reconciliation, migration y governance; "
        "Tax Calculation Builder implementa desde ese handoff; Jurisdiction Rate Inspector e Invoice Reversal Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante one tax number, hardcoded rate, provider quote only, UI total only, missing jurisdiction, exemption, refund/reversal, rounding, reconciliation, audit/monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _tax_calculation_compliance_readiness_evidence(task, language="es")
    return payload


def alignment_english_auth_session_token_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed auth session task")
    payload["assistant_message"] = (
        "Please confirm this auth session/token lifecycle working agreement; I will compile a session-token contract-first "
        "workflow with parallel Token Misuse and Session Revocation Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this auth session/token lifecycle task through a contract-first Loop: {task}. "
        "Session Token Contract Inspector first freezes access/refresh expiry, refresh rotation, reuse detection, logout/all-device revocation, password reset and MFA invalidation, cookie flags, CSRF/API token boundaries, audit fields, monitoring, migration, and governance; "
        "Session Token Builder implements only from that handoff; Token Misuse Inspector and Session Revocation Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on login/logout happy path, frontend-only clear, framework defaults, short-expiry-only, missing revoked/stolen/expired token negatives, missing refresh reuse proof, missing session invalidation, missing audit/monitoring, missing migration, or skipped local governance."
    )
    payload["readiness_evidence"] = _auth_session_token_lifecycle_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_auth_session_token_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 auth session 任务")
    payload["assistant_message"] = (
        "请确认这份 auth session/token lifecycle 工作协议；确认后我会生成 Session Token Contract Inspector 先固定 token/session 契约、"
        "Session Token Builder 再实现、Token Misuse Inspector 与 Session Revocation Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 auth session/token lifecycle 任务编排 contract-first Loop：{task}。"
        "Session Token Contract Inspector 先只读固定 access/refresh expiry、refresh rotation、reuse detection、logout/all-device revocation、password reset/MFA invalidation、cookie flags、CSRF/API token boundaries、audit fields、monitoring、migration 和 governance；"
        "Session Token Builder 只能基于该 handoff 实现；Token Misuse Inspector 与 Session Revocation Audit Inspector 并行检查；"
        "GateKeeper 对 login/logout happy path、frontend-only clear、framework defaults、short-expiry-only、revoked/stolen/expired token negatives 缺失、refresh reuse proof 缺失、session invalidation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _auth_session_token_lifecycle_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_auth_session_token_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de auth session confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de auth session/token lifecycle; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Token Misuse y Session Revocation Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de auth session/token lifecycle con un Loop contract-first: {task}. "
        "Session Token Contract Inspector fija expiry access/refresh, refresh rotation, reuse detection, revocation, password reset/MFA invalidation, cookie flags, CSRF/API boundaries, audit, monitoring, migration y governance; "
        "Session Token Builder implementa desde ese handoff; Token Misuse Inspector y Session Revocation Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante login/logout happy path, frontend-only clear, framework defaults, short-expiry-only, missing token negatives, refresh reuse proof, session invalidation, audit/monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _auth_session_token_lifecycle_readiness_evidence(task, language="es")
    return payload


def alignment_english_data_residency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed data residency task")
    payload["assistant_message"] = (
        "Please confirm this data residency / regional isolation working agreement; I will compile a contract-first "
        "workflow with Residency Contract Inspector, Regional Isolation Builder, Residency Evidence Inspector, and GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this enterprise data residency / regional isolation task through a contract-first Loop: {task}. "
        "Residency Contract Inspector first freezes the EU/US data-plane inventory, tenant residency policy, routing, storage, search, "
        "cache, queues, backups, logs, analytics, processor/DPA, key-region, failover, migration/backfill, access/export/audit/trace, "
        "egress-monitoring, and wrong-region negative targets; Regional Isolation Builder implements only from that handoff; "
        "Residency Evidence Inspector verifies every regional proof and negative; GateKeeper fails closed on UI-region-only, env-var-only, "
        "tenant-field-only, one-routed-request-only, docs-only DPA, missing processor proof, missing wrong-region negatives, missing key-region proof, "
        "or missing observability / egress alerts."
    )
    payload["readiness_evidence"] = _data_residency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_data_residency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 data residency / regional isolation 任务")
    payload["assistant_message"] = (
        "请确认这份 data residency / regional isolation 工作协议；确认后我会生成 Residency Contract Inspector 先固定契约、"
        "Regional Isolation Builder 再实现、Residency Evidence Inspector 复验证据、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条企业 data residency / regional isolation 任务编排 contract-first Loop：{task}。"
        "Residency Contract Inspector 先只读固定 EU/US 数据面清单、tenant residency policy、routing、存储、search、cache、queue、"
        "backup、logs、analytics、processor/DPA、key-region、failover、migration/backfill、access/export/audit/trace、egress monitoring 和 wrong-region 负向目标；"
        "Regional Isolation Builder 只能基于该 handoff 实现；Residency Evidence Inspector 验证所有区域证明和负向证据；"
        "GateKeeper 对 UI-region-only、env-var-only、tenant-field-only、one-routed-request-only、docs-only DPA、processor proof 缺失、wrong-region 负向缺失、"
        "key-region proof 缺失或 observability / egress alert 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _data_residency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_data_residency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de data residency confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de data residency / regional isolation; después compilaré un workflow contract-first "
        "con Residency Contract Inspector, Regional Isolation Builder, Residency Evidence Inspector y GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de data residency / regional isolation con un Loop contract-first: {task}. "
        "Residency Contract Inspector fija inventario EU/US, residency policy, routing, storage, search, cache, queues, backups, logs, analytics, "
        "processor/DPA, key-region, failover, migration/backfill, access/export/audit/trace, egress monitoring y negativos wrong-region; "
        "Regional Isolation Builder implementa desde ese handoff; Residency Evidence Inspector verifica pruebas regionales y negativos; "
        "GateKeeper falla cerrado ante UI-region-only, env-var-only, tenant-field-only, one-routed-request-only, docs-only DPA, processor proof faltante, "
        "wrong-region negatives faltantes, key-region proof faltante o falta de observability / egress alerts."
    )
    payload["readiness_evidence"] = _data_residency_readiness_evidence(task, language="es")
    return payload


def alignment_english_support_impersonation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed support impersonation task")
    payload["assistant_message"] = (
        "Please confirm this support impersonation / break-glass working agreement; I will compile a policy-inspection-first workflow "
        "before any Builder changes."
    )
    payload["agreement_summary"] = (
        f"Govern this support impersonation / break-glass access task through a policy-first Loop: {task}. "
        "Break-glass Policy Inspector first freezes approval, consent, reason, time limit, attribution, MFA/step-up, privacy, tenant negative cases, "
        "audit, revoke/expiry, monitoring, and export-attempt proof targets; Break-glass Builder implements only from that handoff; "
        "Access Evidence Inspector verifies no-ticket, expired, revoked, cross-tenant, privacy, destructive-action, export, audit-integrity, and monitoring evidence; "
        "GateKeeper fails closed on shared-token, login-as happy path, banner-only, missing approval/consent, weak privacy/tenant proof, or weak audit evidence."
    )
    payload["readiness_evidence"] = _support_impersonation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_support_impersonation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 support impersonation / break-glass 任务")
    payload["assistant_message"] = "请确认这份 support impersonation / break-glass 工作协议；确认后我会生成先只读 policy inspection、再 Builder、再证据 Inspector 和 GateKeeper 的 Loop。"
    payload["agreement_summary"] = (
        f"围绕这条 support impersonation / break-glass access 任务编排 policy-first Loop：{task}。"
        "Break-glass Policy Inspector 先固定 approval、consent、reason、time limit、attribution、MFA/step-up、privacy、tenant 负向、"
        "audit、revoke/expiry、monitoring 和 export-attempt proof targets；Break-glass Builder 只能基于该 handoff 实现；"
        "Access Evidence Inspector 验证 no-ticket、expired、revoked、cross-tenant、privacy、destructive action、export、audit-integrity 和 monitoring evidence；"
        "GateKeeper 对 shared-token、login-as happy path、banner-only、缺少 approval/consent、privacy/tenant 弱证据或 audit 弱证据 fail closed。"
    )
    payload["readiness_evidence"] = _support_impersonation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_support_impersonation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de support impersonation confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de support impersonation / break-glass; después compilaré un workflow policy-inspection-first antes de cambios de Builder."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de support impersonation / break-glass access con un Loop policy-first: {task}. "
        "Break-glass Policy Inspector fija approval, consent, reason, time limit, attribution, MFA/step-up, privacy, tenant negatives, audit, revoke/expiry, monitoring y export-attempt; "
        "Builder implementa desde ese handoff; Evidence Inspector verifica no-ticket, expired, revoked, tenant, privacy, destructive action, export, audit-integrity y monitoring; "
        "GateKeeper falla cerrado ante shared-token, login-as happy path, banner-only o evidencia débil."
    )
    payload["readiness_evidence"] = _support_impersonation_readiness_evidence(task, language="es")
    return payload


def alignment_english_kyc_aml_screening_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed KYC/AML screening task")
    payload["assistant_message"] = (
        "Please confirm this KYC/AML screening working agreement; I will compile a compliance-contract-first workflow "
        "with parallel Screening and Financial Controls inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this seller KYC/KYB and AML screening task through a compliance-contract-first Loop: {task}. "
        "Compliance Contract Inspector first freezes provider contracts, jurisdiction / retention rules, required KYC/KYB fields, "
        "sanctions / PEP / watchlist samples, manual-review rubric, appeal / resubmission, rescreening cadence, webhook signature / replay / order / idempotency, "
        "audit reason schema, privacy redaction, monitoring, and payout hold / release ledger proof targets; KYC/AML Builder implements only from that handoff; "
        "Screening Evidence Inspector and Financial Controls Inspector inspect in parallel; GateKeeper fails closed on sandbox-approved-only, UI-verified-only, "
        "provider-status-only, happy-path webhook, weak manual-review proof, missing sanctions negatives, or missing payout ledger proof."
    )
    payload["readiness_evidence"] = _kyc_aml_screening_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_kyc_aml_screening_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 KYC/AML screening 任务")
    payload["assistant_message"] = "请确认这份 KYC/AML screening 工作协议；确认后我会生成合规契约先行、再并行筛查证据与资金控制检查、最后 GateKeeper 裁决的 Loop。"
    payload["agreement_summary"] = (
        f"围绕这条 seller KYC/KYB and AML screening 任务编排 compliance-contract-first Loop：{task}。"
        "Compliance Contract Inspector 先固定 provider contract、jurisdiction / retention、KYC/KYB fields、sanctions / PEP / watchlist samples、"
        "manual-review rubric、appeal / resubmission、rescreening cadence、webhook signature / replay / order / idempotency、audit reason schema、"
        "privacy redaction、monitoring 和 payout hold / release ledger proof targets；KYC/AML Builder 只能基于该 handoff 实现；"
        "Screening Evidence Inspector 与 Financial Controls Inspector 并行检查；GateKeeper 对 sandbox-approved-only、UI-verified-only、provider-status-only、"
        "happy-path webhook、manual-review 弱证据、sanctions 负例缺失或 payout ledger proof 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _kyc_aml_screening_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_kyc_aml_screening_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de KYC/AML screening confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de KYC/AML screening; después compilaré un workflow compliance-contract-first con inspecciones paralelas de Screening y Financial Controls antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de seller KYC/KYB y AML screening con un Loop compliance-contract-first: {task}. "
        "Compliance Contract Inspector fija provider contracts, reglas de jurisdicción/retention, campos KYC/KYB, muestras sanctions/PEP/watchlist, rúbrica manual, "
        "appeal/resubmission, rescreening, webhook signature/replay/order/idempotency, audit reason schema, privacy, monitoring y payout ledger proof; "
        "KYC/AML Builder implementa desde ese handoff; Screening Evidence Inspector y Financial Controls Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante sandbox-approved-only, UI-verified-only, provider-status-only, happy-path webhook, revisión manual débil o falta de sanctions negatives / payout ledger."
    )
    payload["readiness_evidence"] = _kyc_aml_screening_readiness_evidence(task, language="es")
    return payload


def alignment_english_identity_sso_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed enterprise SSO task")
    payload["assistant_message"] = (
        "Please confirm this enterprise SSO working agreement; I will compile an identity-contract-first workflow "
        "with parallel SSO Assertion Evidence and Provisioning Mapping inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this enterprise SAML/OIDC SSO and provisioning task through a contract-first Loop: {task}. "
        "Identity Contract Inspector first freezes IdP metadata, issuer/audience, signed assertion, tenant domain binding, replay/expiry, role/group mapping, SCIM/JIT provisioning, deprovisioning, password-login compatibility, audit, and monitoring proof targets; "
        "SSO Builder implements only from that handoff; SSO Assertion Evidence Inspector and Provisioning Mapping Inspector inspect in parallel; "
        "GateKeeper fails closed on Okta-happy-path-only, SAML-library-only, UI-enabled-only, admin-only mapping, missing forged assertion negatives, missing tenant-binding proof, missing deprovisioning proof, or missing audit/monitoring proof."
    )
    payload["readiness_evidence"] = _identity_sso_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_identity_sso_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的企业 SSO 任务")
    payload["assistant_message"] = (
        "请确认这份 enterprise SSO 工作协议；确认后我会生成 Identity Contract Inspector 先固定身份契约、"
        "SSO Builder 再实现、SSO Assertion Evidence Inspector 与 Provisioning Mapping Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条企业 SAML/OIDC SSO 与 provisioning 任务编排 contract-first Loop：{task}。"
        "Identity Contract Inspector 先只读固定 IdP metadata、issuer/audience、signed assertion、tenant domain binding、replay/expiry、role/group mapping、"
        "SCIM/JIT provisioning、deprovisioning、password-login compatibility、audit 和 monitoring proof targets；"
        "SSO Builder 只能基于该 handoff 实现；SSO Assertion Evidence Inspector 与 Provisioning Mapping Inspector 并行检查；"
        "GateKeeper 对 Okta-happy-path-only、SAML-library-only、UI-enabled-only、admin-only mapping、forged assertion 负向缺失、tenant-binding proof 缺失、deprovisioning proof 缺失或 audit/monitoring proof 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _identity_sso_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_identity_sso_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de enterprise SSO confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de enterprise SSO; después compilaré un workflow identity-contract-first con inspecciones paralelas de SSO Assertion Evidence y Provisioning Mapping antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de SAML/OIDC SSO y provisioning con un Loop contract-first: {task}. "
        "Identity Contract Inspector fija IdP metadata, issuer/audience, signed assertion, tenant domain binding, replay/expiry, role/group mapping, SCIM/JIT provisioning, deprovisioning, password-login compatibility, audit y monitoring targets; "
        "SSO Builder implementa desde ese handoff; SSO Assertion Evidence Inspector y Provisioning Mapping Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante Okta-happy-path-only, SAML-library-only, UI-enabled-only, admin-only mapping, forged assertion negatives faltantes, tenant-binding proof faltante, deprovisioning proof faltante o audit/monitoring faltante."
    )
    payload["readiness_evidence"] = _identity_sso_readiness_evidence(task, language="es")
    return payload


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


def alignment_english_payout_settlement_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed marketplace payout settlement task")
    payload["assistant_message"] = (
        "Please confirm this payout settlement working agreement; I will compile a payout-contract-first workflow "
        "with parallel Settlement Reconciliation and Access Idempotency inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this marketplace seller payout settlement task through a payout contract-first Loop: {task}. "
        "Payout Contract Inspector first freezes seller balance ledger semantics, captured/refunded/chargeback samples, fee/tax/adjustment/hold/reserve/negative-balance rules, batch cutoff/timezone/currency/FX policy, provider transfer and bank fixtures, KYC hold, failed payout retry, reversal idempotency, double-payout prevention, provider/local/invoice/bank reconciliation, tenant access, audit, monitoring, and local governance proof targets; "
        "Payout Settlement Builder implements only from that handoff; Settlement Reconciliation Inspector and Access Idempotency Inspector inspect in parallel; "
        "GateKeeper fails closed on dashboard-paid-only, test-payout-only, UI-balance-only, missing seller ledger proof, missing failed/reversal negative, missing double-payout negative, missing provider-bank reconciliation, missing tenant negative, missing audit trail, missing monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _payout_settlement_reconciliation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_payout_settlement_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 marketplace payout settlement 任务")
    payload["assistant_message"] = "请确认这份 payout settlement 工作协议；确认后我会生成 payout 契约先行、再并行 settlement reconciliation 与 access/idempotency 检查、最后 GateKeeper 裁决的 Loop。"
    payload["agreement_summary"] = (
        f"围绕这条 marketplace seller payout settlement 任务编排 payout contract-first Loop：{task}。"
        "Payout Contract Inspector 先只读固定 seller balance ledger、captured/refunded/chargeback samples、fee/tax/adjustment/hold/reserve/negative-balance rules、batch cutoff/timezone/currency/FX、provider transfer/bank fixtures、KYC hold、failed payout retry、reversal idempotency、double-payout prevention、provider/local/invoice/bank reconciliation、tenant access、audit、monitoring 和 local governance proof targets；"
        "Payout Settlement Builder 只能基于该 handoff 实现；Settlement Reconciliation Inspector 与 Access Idempotency Inspector 并行检查；"
        "GateKeeper 对 dashboard-paid-only、test-payout-only、UI-balance-only、seller ledger proof 缺失、failed/reversal negative 缺失、double-payout negative 缺失、provider-bank reconciliation 缺失、tenant negative 缺失、audit trail 缺失、monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _payout_settlement_reconciliation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_payout_settlement_reconciliation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de payout settlement confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de payout settlement; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Settlement Reconciliation y Access Idempotency antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de marketplace seller payout settlement con un Loop contract-first: {task}. "
        "Payout Contract Inspector fija seller ledger, captured/refunded/chargeback samples, fee/tax/hold rules, cutoff/timezone/currency/FX, provider/bank fixtures, KYC hold, failed payout retry, reversal idempotency, double-payout prevention, reconciliation, tenant access, audit, monitoring y governance; "
        "Payout Settlement Builder implementa desde ese handoff; Settlement Reconciliation y Access Idempotency inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante dashboard-paid-only, test-payout-only, UI balance only, missing ledger, failed/reversal negative, double-payout negative, reconciliation, tenant negative, audit, monitoring o governance."
    )
    payload["readiness_evidence"] = _payout_settlement_reconciliation_readiness_evidence(task, language="es")
    return payload


def alignment_english_analytics_experiment_instrumentation_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed analytics instrumentation and experiment task")
    payload["assistant_message"] = (
        "Please confirm this analytics instrumentation / experiment exposure working agreement; I will compile an "
        "instrumentation-contract-first workflow with parallel Event Integrity and Experiment Consistency inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this onboarding analytics instrumentation / A-B experiment exposure task through a contract-first Loop: {task}. "
        "Instrumentation Contract Inspector first freezes versioned event schema, identity merge, consent/PII boundaries, SDK retry/offline replay, experiment assignment/exposure/variant/holdout/reassignment, warehouse/dashboard reconciliation, monitoring, migration, and governance; "
        "Tracking Builder implements only from that handoff; Event Integrity Inspector and Experiment Consistency Inspector inspect in parallel; "
        "GateKeeper fails closed on button-click-only, console-log-only, mock-analytics-only, one-provider-accepted-event, missing warehouse reconciliation, missing consent negative, missing duplicate/offline replay negatives, experiment exposure as follow-up, missing monitoring, or skipped governance."
    )
    payload["readiness_evidence"] = _analytics_experiment_instrumentation_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_analytics_experiment_instrumentation_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 analytics instrumentation and experiment 任务")
    payload["assistant_message"] = (
        "请确认这份 analytics instrumentation / experiment exposure 工作协议；确认后我会生成 Instrumentation Contract Inspector 先固定埋点与实验契约、"
        "Tracking Builder 再实现、Event Integrity Inspector 与 Experiment Consistency Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 onboarding analytics instrumentation / A-B experiment exposure 任务编排 contract-first Loop：{task}。"
        "Instrumentation Contract Inspector 先只读固定 versioned event schema、identity merge、consent/PII boundaries、SDK retry/offline replay、experiment assignment/exposure/variant/holdout/reassignment、warehouse/dashboard reconciliation、monitoring、migration 和 governance；"
        "Tracking Builder 只能基于该 handoff 实现；Event Integrity Inspector 与 Experiment Consistency Inspector 并行检查；"
        "GateKeeper 对 button-click-only、console-log-only、mock-analytics-only、one-provider-accepted-event、warehouse reconciliation 缺失、consent negative 缺失、duplicate/offline replay negatives 缺失、experiment exposure 当后续、monitoring 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _analytics_experiment_instrumentation_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_analytics_experiment_instrumentation_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de analytics instrumentation and experiment confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de analytics instrumentation / experiment exposure; después compilaré un workflow instrumentation-contract-first "
        "con inspecciones paralelas de Event Integrity y Experiment Consistency antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de onboarding analytics instrumentation / A-B experiment exposure con un Loop contract-first: {task}. "
        "Instrumentation Contract Inspector fija event schema, identity merge, consent/PII, retry/offline replay, assignment/exposure/variant/holdout/reassignment, warehouse/dashboard reconciliation, monitoring, migration y governance; "
        "Tracking Builder implementa desde ese handoff; Event Integrity y Experiment Consistency inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante button-click-only, console-log-only, mock analytics, one provider event, missing reconciliation, consent negative, duplicate/offline replay, exposure follow-up, monitoring o governance."
    )
    payload["readiness_evidence"] = _analytics_experiment_instrumentation_readiness_evidence(task, language="es")
    return payload


def alignment_english_schedule_timezone_recurrence_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed schedule timezone recurrence task")
    payload["assistant_message"] = (
        "Please confirm this schedule timezone recurrence working agreement; I will compile a "
        "schedule-contract-first workflow with parallel Temporal Correctness and Delivery Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this weekly digest schedule / timezone recurrence task through a contract-first Loop: {task}. "
        "Schedule Contract Inspector first freezes timezone source, user timezone fallback, local Monday 09:00 semantics, DST spring-forward/fall-back samples, missed-run catch-up window, retry/provider replay idempotency, subscription/disabled/tenant/locale filters, provider delivery/failure surface, audit fields, monitoring, migration, and governance; "
        "Digest Scheduler Builder implements only from that handoff; Temporal Correctness Inspector and Delivery Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on cron-only, local-trigger-only, UTC-only, single-timezone-only, provider-accepted-only, missing DST boundary, missing catch-up/idempotency negative, missing subscription/disabled negative, missing audit/monitoring, missing migration, or skipped governance."
    )
    payload["readiness_evidence"] = _schedule_timezone_recurrence_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_schedule_timezone_recurrence_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 schedule timezone recurrence 任务")
    payload["assistant_message"] = (
        "请确认这份 schedule timezone recurrence 工作协议；确认后我会生成 Schedule Contract Inspector 先固定时间契约、"
        "Digest Scheduler Builder 再实现、Temporal Correctness Inspector 与 Delivery Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 weekly digest schedule / timezone recurrence 任务编排 contract-first Loop：{task}。"
        "Schedule Contract Inspector 先只读固定 timezone source、user timezone fallback、本地周一 09:00、DST spring-forward/fall-back 样本、missed-run catch-up window、retry/provider replay idempotency、subscription/disabled/tenant/locale filters、provider delivery/failure surface、audit fields、monitoring、migration 和 governance；"
        "Digest Scheduler Builder 只能基于该 handoff 实现；Temporal Correctness Inspector 与 Delivery Audit Inspector 并行检查；"
        "GateKeeper 对 cron-only、local-trigger-only、UTC-only、single-timezone-only、provider-accepted-only、DST boundary 缺失、catch-up/idempotency negative 缺失、subscription/disabled negative 缺失、audit/monitoring 缺失、migration 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _schedule_timezone_recurrence_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_schedule_timezone_recurrence_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de schedule timezone recurrence confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de schedule timezone recurrence; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Temporal Correctness y Delivery Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de weekly digest schedule / timezone recurrence con un Loop contract-first: {task}. "
        "Schedule Contract Inspector fija timezone source, fallback, local Monday 09:00, DST, catch-up, retry/provider replay, subscription/disabled/tenant/locale filters, provider delivery/failure, audit fields, monitoring, migration y governance; "
        "Digest Scheduler Builder implementa desde ese handoff; Temporal Correctness Inspector y Delivery Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante cron-only, local-trigger-only, UTC-only, single-timezone-only, provider-accepted-only, missing DST, catch-up/idempotency, subscription/disabled negatives, audit/monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _schedule_timezone_recurrence_readiness_evidence(task, language="es")
    return payload


def alignment_english_notification_subscription_deliverability_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed notification deliverability task")
    payload["assistant_message"] = (
        "Please confirm this notification subscription-deliverability working agreement; I will compile a "
        "notification-contract-first workflow with parallel Deliverability Evidence and Template Privacy inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this lifecycle campaign email / notification deliverability task through a contract-first Loop: {task}. "
        "Notification Contract Inspector first freezes subscription eligibility, preferences, unsubscribe, suppression, bounce/complaint/drop events, disabled-user and tenant filters, locale/templates, redaction, provider webhook replay/idempotency, retry/DLQ, delivery audit, monitoring, migration, and governance; "
        "Campaign Email Builder implements only from that handoff; Deliverability Evidence Inspector and Template Privacy Inspector inspect in parallel; "
        "GateKeeper fails closed on one-test-email, provider-accepted-only, UI-toggle-only, happy-path-send-only, docs-only unsubscribe, missing bounce/complaint proof, missing duplicate negatives, missing locale/template proof, missing redaction, missing audit reconciliation, missing monitoring, missing migration, or skipped governance."
    )
    payload["readiness_evidence"] = _notification_subscription_deliverability_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_notification_subscription_deliverability_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 notification deliverability 任务")
    payload["assistant_message"] = (
        "请确认这份 notification subscription-deliverability 工作协议；确认后我会生成 Notification Contract Inspector 先固定通知契约、"
        "Campaign Email Builder 再实现、Deliverability Evidence Inspector 与 Template Privacy Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 lifecycle campaign email / notification deliverability 任务编排 contract-first Loop：{task}。"
        "Notification Contract Inspector 先只读固定 subscription eligibility、preferences、unsubscribe、suppression、bounce/complaint/drop events、disabled-user 和 tenant filters、locale/templates、redaction、provider webhook replay/idempotency、retry/DLQ、delivery audit、monitoring、migration 和 governance；"
        "Campaign Email Builder 只能基于该 handoff 实现；Deliverability Evidence Inspector 与 Template Privacy Inspector 并行检查；"
        "GateKeeper 对 one-test-email、provider-accepted-only、UI-toggle-only、happy-path-send-only、docs-only unsubscribe、bounce/complaint proof 缺失、duplicate negatives 缺失、locale/template proof 缺失、redaction 缺失、audit reconciliation 缺失、monitoring 缺失、migration 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _notification_subscription_deliverability_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_notification_subscription_deliverability_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de notification deliverability confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de notification subscription-deliverability; después compilaré un workflow notification-contract-first "
        "con inspecciones paralelas de Deliverability Evidence y Template Privacy antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de lifecycle campaign email / notification deliverability con un Loop contract-first: {task}. "
        "Notification Contract Inspector fija subscription, preferences, unsubscribe, suppression, bounce/complaint/drop events, tenant/disabled filters, locale/templates, redaction, provider webhook replay/idempotency, retry/DLQ, audit, monitoring, migration y governance; "
        "Campaign Email Builder implementa desde ese handoff; Deliverability Evidence Inspector y Template Privacy Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante one-test-email, provider-accepted-only, UI-toggle-only, happy-path, docs-only unsubscribe, missing bounce/complaint, duplicates, locale/template, redaction, audit reconciliation, monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _notification_subscription_deliverability_readiness_evidence(task, language="es")
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


def alignment_english_dispute_chargeback_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed dispute and chargeback lifecycle task")
    payload["assistant_message"] = (
        "Please confirm this dispute/chargeback working agreement; I will compile a dispute-contract-first workflow "
        "with parallel Dispute Evidence and Ledger Notification inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this dispute and chargeback lifecycle task through a contract-first Loop: {task}. "
        "Dispute Contract Inspector first freezes provider dispute fixtures, webhook signature/replay/order, retrieval request, representment evidence deadlines, reason codes, refund overlap, ledger/payout effects, notification/SLA, audit, monitoring, and governance; "
        "Chargeback Lifecycle Builder implements only from that handoff; Dispute Evidence Inspector and Ledger Notification Inspector inspect in parallel; "
        "GateKeeper fails closed on UI-status-only, dashboard-outcome-only, provider-dispute-id-only, happy-path close, missing evidence package, missing deadline proof, missing refund-overlap negative, missing ledger/payout reconciliation, missing notification/SLA, missing audit, missing monitoring, or skipped governance."
    )
    payload["readiness_evidence"] = _dispute_chargeback_lifecycle_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_dispute_chargeback_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 dispute / chargeback lifecycle 任务")
    payload["assistant_message"] = (
        "请确认这份 dispute/chargeback 工作协议；确认后我会生成 Dispute Contract Inspector 先固定契约、"
        "Chargeback Lifecycle Builder 再实现、Dispute Evidence Inspector 与 Ledger Notification Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 dispute / chargeback lifecycle 任务编排 contract-first Loop：{task}。"
        "Dispute Contract Inspector 先只读固定 provider dispute fixtures、webhook signature/replay/order、retrieval request、representment evidence deadline、reason code、refund overlap、ledger/payout、notification/SLA、audit、monitoring 和 governance；"
        "Chargeback Lifecycle Builder 只能基于该 handoff 实现；Dispute Evidence Inspector 与 Ledger Notification Inspector 并行检查；"
        "GateKeeper 对 UI-status-only、dashboard-outcome-only、provider-dispute-id-only、happy-path close、evidence package 缺失、deadline proof 缺失、refund-overlap negative 缺失、ledger/payout reconciliation 缺失、notification/SLA 缺失、audit 缺失、monitoring 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _dispute_chargeback_lifecycle_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_dispute_chargeback_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de dispute / chargeback confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de dispute/chargeback; después compilaré un workflow contract-first con inspecciones paralelas de Dispute Evidence y Ledger Notification antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea dispute / chargeback lifecycle con un Loop contract-first: {task}. "
        "Dispute Contract Inspector fija provider fixtures, webhook signature/replay/order, retrieval, representment deadlines, reason codes, refund overlap, ledger/payout, notification/SLA, audit, monitoring y governance; "
        "Chargeback Lifecycle Builder implementa desde ese handoff; Dispute Evidence Inspector y Ledger Notification Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante UI-status-only, dashboard-only, provider-dispute-id-only, happy-path close, missing package, deadline, overlap negative, ledger/payout reconciliation, notification/SLA, audit, monitoring o governance."
    )
    payload["readiness_evidence"] = _dispute_chargeback_lifecycle_readiness_evidence(task, language="es")
    return payload


def alignment_english_payment_webhook_ledger_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed payment webhook task")
    payload["assistant_message"] = (
        "Please confirm this payment webhook working agreement; I will compile a webhook-contract-first workflow "
        "with parallel Webhook Evidence and Ledger Reconciliation inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this payment provider webhook and ledger task through a contract-first Loop: {task}. "
        "Webhook Contract Inspector first freezes provider event schemas, signature/timestamp rules, replay/idempotency, ordering, retry/DLQ, ledger/dispute/payout state machines, audit/privacy, monitoring, and manual replay targets; "
        "Payment Webhook Builder implements only from that handoff; Webhook Evidence Inspector and Ledger Reconciliation Inspector inspect in parallel; "
        "GateKeeper fails closed on happy-path-webhook-only, unsigned dev-mode acceptance, provider-status-only, database-constraint-only dedupe, docs-only contract, missing replay negatives, missing ordering proof, missing ledger reconciliation, or missing monitoring/DLQ proof."
    )
    payload["readiness_evidence"] = _payment_webhook_ledger_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_payment_webhook_ledger_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 payment webhook 任务")
    payload["assistant_message"] = (
        "请确认这份 payment webhook 工作协议；确认后我会生成 Webhook Contract Inspector 先固定契约、"
        "Payment Webhook Builder 再实现、Webhook Evidence Inspector 与 Ledger Reconciliation Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 payment provider webhook 与 ledger 任务编排 contract-first Loop：{task}。"
        "Webhook Contract Inspector 先只读固定 provider event schema、signature/timestamp rules、replay/idempotency、ordering、retry/DLQ、ledger/dispute/payout state machines、audit/privacy、monitoring 和 manual replay targets；"
        "Payment Webhook Builder 只能基于该 handoff 实现；Webhook Evidence Inspector 与 Ledger Reconciliation Inspector 并行检查；"
        "GateKeeper 对 happy-path-webhook-only、unsigned dev-mode acceptance、provider-status-only、database-constraint-only dedupe、docs-only contract、replay negatives 缺失、ordering proof 缺失、ledger reconciliation 缺失或 monitoring/DLQ proof 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _payment_webhook_ledger_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_payment_webhook_ledger_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de payment webhook confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de payment webhook; después compilaré un workflow contract-first con inspecciones paralelas de Webhook Evidence y Ledger Reconciliation antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de payment provider webhook y ledger con un Loop contract-first: {task}. "
        "Webhook Contract Inspector fija schemas, signature/timestamp, replay/idempotency, ordering, retry/DLQ, ledger/dispute/payout state machines, audit/privacy, monitoring y manual replay targets; "
        "Payment Webhook Builder implementa desde ese handoff; Webhook Evidence Inspector y Ledger Reconciliation Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante happy-path-webhook-only, unsigned dev-mode, provider-status-only, database-constraint-only dedupe, docs-only contract, replay/order proof faltante, ledger reconciliation faltante o monitoring/DLQ faltante."
    )
    payload["readiness_evidence"] = _payment_webhook_ledger_readiness_evidence(task, language="es")
    return payload


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
    payload["assistant_message"] = "请确认这份 authorization policy 工作协议；确认后我会生成一个窄 Builder，然后并行 Contract Inspector 与 Security Evidence Inspector，最后由 GateKeeper 裁决。"
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


def alignment_english_task_anchored_agreement_response(task_text: str) -> dict:
    payload = alignment_agreement_response()
    task = task_text or "the user-confirmed task"
    anchors = _task_anchor_terms_text(task_text)
    payload["assistant_message"] = (
        "Please confirm this task-specific working agreement; I will preserve the task anchor across spec, roles, "
        "workflow handoffs, repair guidance, and the final GateKeeper evidence verdict."
    )
    payload["agreement_summary"] = (
        f"Govern this task anchor through an evidence-first repair Loop: {task}. "
        "A narrow Builder proves the smallest real loop, Inspector tries to disprove the task-specific claims, "
        "Guide turns weak proof into repair, Repair Builder closes named gaps, and GateKeeper fails closed when proof is weak."
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because important risk is not settled by one Agent pass or one demo. "
            "Later rounds must create Builder handoffs, negative evidence, audit or reconciliation artifacts when relevant, "
            "Guide repair direction, and a GateKeeper verdict that can be reused as an auditable contract."
        ),
        "task_scope": (
            f"Scope stays on the concrete user task: {task}. The Loop should prove the smallest task-specific closed path "
            "and avoid broad platform rewrite, generic starter work, or unrelated polish."
        ),
        "success_surface": _task_success_surface_evidence(task, anchors=anchors, prefers_chinese=False),
        "fake_done_risks": _task_fake_done_risk_evidence(task, prefers_chinese=False),
        "evidence_preferences": (
            "Prefer project-owned checks, command output, provider fixture or API proof when relevant, audit logs, "
            "reconciliation artifacts, provider failure / timeout / retry / fallback evidence when relevant, "
            "role handoffs, and explicit Proven / Weak / Unproven / Blocking / Residual risk buckets."
        ),
        "execution_strategy": (
            "Build the smallest real task loop first; inspect negative paths, boundary consistency, audit or reconciliation "
            "claims, and fake-done risk; route weak proof through Guide; repair named gaps only; then GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Core task claims, negative evidence, boundary consistency, audit or reconciliation proof, and local-governance gaps fail closed. "
            "Only out-of-scope risks that are visible, named, and owned by follow-up may remain as Residual risk."
        ),
        "judgment_tradeoffs": (
            "Prefer a narrow proven loop over broader or prettier work with weak proof. Speed loses to task-anchor traceability, "
            "negative evidence, auditability, boundary isolation, and GateKeeper blocking."
        ),
        "local_governance": (
            "If project-local governance markers are present, Builder reads the applicable rules before editing, Inspector verifies "
            "the related design or test obligations, and GateKeeper treats skipped local governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Builder constructs the task slice, Inspector tries to disprove task-specific claims, Guide narrows repair from Weak / "
            "Unproven / Blocking evidence, Repair Builder fixes named gaps, and GateKeeper closes only from direct proof."
        ),
        "workflow_shape": (
            "Use Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper. Inspector reads Builder handoff and Builder evidence; "
            "Guide reads Inspector findings; Repair Builder reads Guide and inspection handoffs; GateKeeper reads every upstream handoff "
            "and queries Builder, Inspector, and Guide evidence before finishing."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Stack, test runner, and existing implementation details "
            "must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }
    return payload


def alignment_chinese_task_anchored_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_agreement_response()
    task = task_text or "用户确认的任务"
    anchors = _task_anchor_terms_text(task_text)
    payload["assistant_message"] = "请确认这份任务专属工作协议；确认后我会把任务锚点贯穿到 spec、roles、workflow、修复 handoff 和 GateKeeper 证据裁决里。"
    payload["agreement_summary"] = (
        f"围绕这条任务锚点编排证据优先的修复 Loop：{task}。"
        "先由 Builder 证明最小真实闭环，再由 Inspector 反证任务声明，Guide 把弱证据收窄成修复，"
        "Repair Builder 补被点名缺口，GateKeeper 在证据薄弱时 fail closed。"
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            f"任务锚点（{task}）适合 Loopora，因为关键风险不能靠一次 Agent pass 或一次 demo 裁决。"
            "后续轮次需要产生 Builder handoff、负向证据、相关审计或对账 artifact、Guide 修复方向，以及可复用、可审计的 GateKeeper verdict。"
        ),
        "task_scope": (
            f"范围固定在这条具体用户任务：{task}。Loop 只证明最小任务闭环，不扩展成宽泛平台改造、泛化 starter work 或无关 polish。"
        ),
        "success_surface": _task_success_surface_evidence(task, anchors=anchors, prefers_chinese=True),
        "fake_done_risks": _task_fake_done_risk_evidence(task, prefers_chinese=True),
        "evidence_preferences": (
            "优先项目内检查、命令输出、相关 provider fixture 或 API 证据、审计日志、对账 artifact、角色 handoff，"
            "涉及 provider failure 时还要有 timeout、retry/backoff 或 fallback 证据，并明确区分 Proven、Weak、Unproven、Blocking 和 Residual risk。"
        ),
        "execution_strategy": (
            "先构建最小真实任务闭环；再检查负向路径、边界一致性、审计或对账声明和假完成风险；"
            "弱证据进入 Guide；Repair Builder 只补被点名缺口；最后 GateKeeper 从所有 handoff 裁决。"
        ),
        "residual_risk_policy": (
            "核心任务声明、负向证据、边界一致性、审计或对账证据、本地治理处理不足时必须 fail closed。"
            "只有超出本轮范围且已点名、可见、有人接手 follow-up 的风险可作为 Residual risk 保留。"
        ),
        "judgment_tradeoffs": (
            "优先小而可证明的闭环，而不是更宽或更漂亮但证据薄弱的实现。速度不能覆盖任务锚点 traceability、负向证据、审计性、边界隔离或 GateKeeper 阻断。"
        ),
        "local_governance": (
            "若存在项目本地治理入口，Builder 先读取适用规则，Inspector 验证相关 design 或 test 义务，GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
        ),
        "role_posture": (
            "Builder 构建任务切片，Inspector 反证任务声明，Guide 根据 Weak / Unproven / Blocking 证据收窄修复，"
            "Repair Builder 修复被点名缺口，GateKeeper 只按直接证据收束。"
        ),
        "workflow_shape": (
            "采用 Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper。Inspector 读取 Builder handoff 和证据；"
            "Guide 读取 Inspector 发现；Repair Builder 读取 Guide 与检查 handoff；GateKeeper 读取全部上游 handoff 并查询 Builder、Inspector、Guide 证据后才能 finish。"
        ),
        "workdir_facts": (
            "已观察事实只限目标路径和 Workdir Snapshot；技术栈、测试 runner 和既有实现位置必须在运行中验证后才能声称。"
        ),
        "open_questions": "等待用户明确确认这份工作协议。",
    }
    return payload


def alignment_spanish_task_anchored_agreement_response(task_text: str) -> dict:
    payload = alignment_agreement_response()
    task = task_text or "la tarea confirmada por el usuario"
    anchors = _task_anchor_terms_text(task_text)
    payload["assistant_message"] = (
        "Confirma este acuerdo de trabajo específico de la tarea; después preservaré el ancla de tarea en spec, roles, "
        "workflow, handoffs de reparación y veredicto de evidencia de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta ancla de tarea con un Loop de reparación guiado por evidencia: {task}. "
        "Builder prueba el cierre real mínimo, Inspector intenta refutar las afirmaciones específicas, Guide convierte "
        "evidencia débil en reparación, Repair Builder cierra brechas nombradas y GateKeeper falla cerrado cuando la evidencia es débil."
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            f"La ancla de tarea ({task}) encaja con Loopora porque el riesgo importante no se resuelve con una sola pasada del Agent "
            "ni una demo. Rondas posteriores deben crear handoffs de Builder, evidencia negativa, auditoría o reconciliación cuando aplique, "
            "dirección de reparación de Guide y un veredicto auditable de GateKeeper."
        ),
        "task_scope": (
            f"El alcance queda limitado a la tarea concreta del usuario: {task}. El Loop debe probar el camino mínimo específico "
            "y evitar una reescritura amplia, trabajo inicial genérico o pulido sin evidencia."
        ),
        "success_surface": _task_success_surface_evidence(task, anchors=anchors, prefers_chinese=False, display_language="es"),
        "fake_done_risks": _task_fake_done_risk_evidence(task, prefers_chinese=False, display_language="es"),
        "evidence_preferences": (
            "Preferir pruebas del proyecto, salida de comandos, evidencia de fixture o API del provider cuando aplique, logs de auditoría, "
            "artefactos de reconciliación, evidencia de timeout/retry/fallback si hay fallo de provider, handoffs de roles y buckets Proven, Weak, Unproven, Blocking y Residual risk."
        ),
        "execution_strategy": (
            "Construir primero el cierre real mínimo de la tarea; inspeccionar rutas negativas, consistencia de límites, auditoría o reconciliación "
            "y riesgos de falso terminado; enviar evidencia débil a Guide; reparar solo brechas nombradas; luego GateKeeper juzga desde todos los handoffs."
        ),
        "residual_risk_policy": (
            "Afirmaciones centrales, evidencia negativa, consistencia de límites, auditoría o reconciliación y gobernanza local deben fallar cerrados si no están probados. "
            "Solo riesgos fuera de alcance que sean visibles, nombrados y con follow-up dueño pueden quedar como Residual risk."
        ),
        "judgment_tradeoffs": (
            "Preferir un cierre pequeño y probado sobre trabajo más amplio o pulido con evidencia débil. La velocidad pierde frente a trazabilidad, evidencia negativa, auditoría, aislamiento de límites y bloqueo de GateKeeper."
        ),
        "local_governance": (
            "Si hay marcadores de gobernanza local del proyecto, Builder lee las reglas aplicables antes de editar, Inspector verifica obligaciones de diseño o pruebas, "
            "y GateKeeper trata gobernanza omitida como Weak, Unproven o Blocking."
        ),
        "role_posture": (
            "Builder construye el corte de tarea, Inspector refuta afirmaciones específicas, Guide acota reparación desde evidencia Weak, Unproven o Blocking, "
            "Repair Builder corrige brechas nombradas y GateKeeper cierra solo con evidencia directa."
        ),
        "workflow_shape": (
            "El flujo de ejecución usa Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper como secuencia de decisión. "
            "Inspector lee handoff y evidencia de auditoría de Builder; Guide lee hallazgos de Inspector; Repair Builder lee handoffs de Guide e Inspector; "
            "GateKeeper consulta toda la evidencia antes de cerrar."
        ),
        "workdir_facts": (
            "Los hechos del proyecto observados se limitan al path objetivo y snapshot; stack, runner de pruebas e implementación existente deben verificarse durante la ejecución antes de reclamarlos como evidencia."
        ),
        "open_questions": "Esperando confirmación explícita del usuario sobre el acuerdo de trabajo.",
    }
    return payload


def _identity_sso_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 enterprise SSO 风险会在 IdP metadata、issuer/audience、assertion signature、tenant binding、SCIM/JIT lifecycle、role mapping、session expiry、audit 和 monitoring 中分阶段暴露；"
                "一次 Okta happy path、UI enabled 状态或最终人工 review 会太晚发现跨租户断言、伪造断言、role drift 或 deprovisioning 缺口。"
            ),
            "task_scope": f"范围固定为企业 SAML/OIDC SSO、SCIM/JIT provisioning、role mapping、tenant binding、session/audit/monitoring 和 password-login compatibility：{task}。不扩展成通用身份平台重写或无关 authorization policy refactor。",
            "success_surface": (
                "成功意味着 IdP metadata signature、issuer/audience、assertion signature、tenant domain binding、replay/expired assertion negatives、JIT/SCIM create/update/deactivate、owner/admin/member role/group mapping、role downgrade/deprovisioning、logout/session expiry、password-login compatibility、forged/failed assertion audit 和 monitoring alerts 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断一个 Okta 用户能登录、SAML library happy path、UI 显示 SSO enabled、admin-only role mapping、缺少 forged assertion negatives、缺少 cross-tenant binding proof、缺少 deprovisioning/downgrade proof、缺少 password-login compatibility 或 audit/monitoring proof。"
            ),
            "evidence_preferences": (
                "优先 IdP metadata fixtures、signed/forged/expired/replayed assertion negatives、issuer/audience negatives、cross-tenant assertion samples、SCIM/JIT lifecycle fixtures、role/group mapping matrix、deprovision/downgrade proof、session expiry/logout checks、password-login compatibility proof、audit refs 和 monitoring alerts；每条 claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "先由 Identity Contract Inspector 固定 IdP metadata、assertion、tenant binding、SCIM/JIT、role mapping、session、audit、monitoring 和 compatibility proof targets；"
                "SSO Builder 读取 contract handoff 后实现；SSO Assertion Evidence Inspector 与 Provisioning Mapping Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 copy、IdP vendor polish 或非关键 setup documentation 可作为 Residual risk 留下并指定 owner/follow-up；缺少 assertion、tenant binding、provisioning/deprovisioning、role mapping、session expiry、audit/monitoring、compatibility 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "严格身份契约、负向断言和 provisioning lifecycle 证据优先于快速接通登录；速度不能覆盖跨租户、伪造断言、role drift、deprovisioning 或 audit 缺口。",
            "local_governance": (
                "若存在项目本地治理入口，Identity Contract Inspector 与 SSO Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/security 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Identity Contract Inspector 固定 identity contract 与 proof targets；SSO Builder 只基于 handoff 实现；SSO Assertion Evidence Inspector 反证 metadata/signature/issuer/audience/replay/tenant/session；"
                "Provisioning Mapping Inspector 验证 SCIM/JIT、role mapping、deprovisioning、downgrade、compatibility、audit 和 monitoring；GateKeeper 对 happy-path-only 或 weak proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Identity Contract Inspector -> SSO Builder -> [SSO Assertion Evidence Inspector + Provisioning Mapping Inspector] -> Identity SSO GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 sso-assertion、identity-provisioning、tenant-isolation、permission-auth、session-lifecycle、audit-log、monitoring、backward-compatibility、migration-rollback 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；IdP、SAML/OIDC、SCIM、session、audit、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque SSO se prueba con metadata, issuer/audience, assertion signature, tenant binding, SCIM/JIT lifecycle, role mapping, sessions, audit y monitoring.",
            "task_scope": f"Alcance limitado a SAML/OIDC SSO, SCIM/JIT provisioning, role mapping, tenant binding, sessions, audit, monitoring y compatibilidad: {task}.",
            "success_surface": "Éxito significa metadata/signature, issuer/audience, tenant binding, replay/expired negatives, SCIM/JIT lifecycle, role mapping, logout/session expiry, compatibility, audit y monitoring probados.",
            "fake_done_risks": "Bloquear Okta-happy-path-only, SAML-library-only, UI-enabled-only, admin-only mapping, missing forged assertion negatives, missing tenant binding, missing deprovisioning o missing audit/monitoring.",
            "evidence_preferences": "Preferir IdP fixtures, signed/forged/expired/replayed assertions, issuer/audience negatives, cross-tenant samples, SCIM/JIT fixtures, role matrix, session checks, compatibility, audit refs y alerts.",
            "execution_strategy": "Identity Contract Inspector fija targets; SSO Builder implementa desde handoff; SSO Assertion Evidence y Provisioning Mapping Inspectors inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de assertion, tenant binding, provisioning/deprovisioning, role mapping, sessions, audit/monitoring, compatibility o governance fail closed.",
            "judgment_tradeoffs": "Identity contract, negative assertions, and provisioning lifecycle proof beats fast login progress.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Assertion Inspector refuta identity claims; Provisioning Inspector verifica lifecycle; GateKeeper falla cerrado.",
            "workflow_shape": "Identity Contract Inspector -> SSO Builder -> [SSO Assertion Evidence Inspector + Provisioning Mapping Inspector] -> Identity SSO GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; IdP, SAML/OIDC, SCIM, session, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because enterprise SSO risk is proven through IdP metadata, issuer/audience, assertion signature, tenant binding, SCIM/JIT lifecycle, role mapping, session expiry, audit, and monitoring over staged evidence. "
            "One Okta happy path, UI-enabled status, SAML-library acceptance, or final human review arrives too late to catch cross-tenant assertions, forged assertions, role drift, or deprovisioning gaps."
        ),
        "task_scope": (
            f"Scope stays on enterprise SAML/OIDC SSO, SCIM/JIT provisioning, role mapping, tenant binding, session/audit/monitoring, and password-login compatibility: {task}. The Loop should not expand into a broad identity-platform rewrite or unrelated authorization-policy refactor."
        ),
        "success_surface": (
            "Success means IdP metadata signature, issuer/audience checks, assertion signature validation, tenant domain binding, replay/expired assertion negatives, JIT/SCIM create/update/deactivate, owner/admin/member role/group mapping, role downgrade/deprovisioning, logout/session expiry, password-login compatibility, forged/failed assertion audit, and monitoring alerts are auditable."
        ),
        "fake_done_risks": (
            "Block one Okta user login, SAML-library happy path, UI-enabled-only, admin-only role mapping, missing forged assertion negatives, missing cross-tenant binding proof, missing deprovisioning/downgrade proof, missing password-login compatibility, or missing audit/monitoring proof."
        ),
        "evidence_preferences": (
            "Prefer IdP metadata fixtures, signed/forged/expired/replayed assertion negatives, issuer/audience negatives, cross-tenant assertion samples, SCIM/JIT lifecycle fixtures, role/group mapping matrix, deprovision/downgrade proof, session expiry/logout checks, password-login compatibility proof, audit refs, and monitoring alerts. "
            "Classify each identity and provisioning claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Identity Contract Inspector first freezes IdP metadata, assertion, tenant binding, SCIM/JIT, role mapping, session, audit, monitoring, and compatibility proof targets; SSO Builder implements from that handoff; SSO Assertion Evidence Inspector and Provisioning Mapping Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor copy, IdP vendor polish, or non-critical setup documentation may remain only with owner/follow-up; missing assertion, tenant binding, provisioning/deprovisioning, role mapping, session expiry, audit/monitoring, compatibility, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Strict identity contract, negative assertion, and provisioning lifecycle proof beats fast login progress; speed cannot hide cross-tenant, forged assertion, role drift, deprovisioning, or audit gaps."
        ),
        "local_governance": (
            "If project-local governance markers are present, Identity Contract Inspector and SSO Builder read applicable rules, both parallel Inspectors verify related design/test/security obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Identity Contract Inspector freezes identity contract and proof targets; SSO Builder implements only from that handoff; SSO Assertion Evidence Inspector refutes metadata/signature/issuer/audience/replay/tenant/session claims; Provisioning Mapping Inspector verifies SCIM/JIT, role mapping, deprovisioning, downgrade, compatibility, audit, and monitoring; GateKeeper fails closed on happy-path-only or weak proof."
        ),
        "workflow_shape": (
            "Use Identity Contract Inspector -> SSO Builder -> [SSO Assertion Evidence Inspector + Provisioning Mapping Inspector] -> Identity SSO GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries sso-assertion, identity-provisioning, tenant-isolation, permission-auth, session-lifecycle, audit-log, monitoring, backward-compatibility, migration-rollback, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. IdP, SAML/OIDC, SCIM, session, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _key_rotation_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 API key / service account secret rotation 的风险会在 overlap、zero-downtime、revoke、revoked-key negative、scope/tenant binding、secret storage、telemetry、rollback、audit 和 monitoring 中分阶段暴露；"
                "一次 new-key UI、env var 更新、happy-path API call 或最终人工 review 会太晚发现 revoked key 仍可用、plaintext secret、租户串用或回滚重启 revoked key。"
            ),
            "task_scope": f"范围固定为客户 API key / service account secret rotation lifecycle：{task}。不扩展成通用权限平台、全凭据系统重写或无关 auth/session reset。",
            "success_surface": (
                "成功意味着 old/new key overlap window、zero-downtime rotation、compromised-key revoke、revoked-key denial、scope / tenant binding、hash 或 KMS encrypted storage、rotation schedule、expiry、last-used telemetry、rollback safety、rotation failure / stale-key monitoring 和 key id / actor / scope / tenant / created/rotated/revoked/failed reason audit 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断 UI 显示新 key、env var 更新、一次 happy-path API call、docs-only rotation、缺少 overlap proof、缺少 revoked-key negative、缺少 tenant/scope negative、缺少 hash/KMS storage proof、缺少 rollback proof、缺少 audit fields 或缺少 monitoring alerts。"
            ),
            "evidence_preferences": (
                "优先 old/new key API calls、revoked-key negative calls、compromised-key revoke proof、scope/tenant negative samples、hash/KMS storage inspection、expiry and last-used telemetry、rollback safety proof、rotation failure / stale-key alerts、redacted audit refs 和 local-governance evidence；每条 claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "先由 Key Rotation Contract Inspector 固定 overlap、revoke、scope/tenant、storage、expiry、telemetry、rollback、audit 和 monitoring proof targets；"
                "Secret Rotation Builder 读取 contract handoff 后实现；Rotation Lifecycle Evidence Inspector 与 Secret Storage Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 UI copy、vendor-specific docs 或非关键 setup polish 可作为 Residual risk 留下并指定 owner/follow-up；缺少 overlap、revoked-key denial、tenant/scope binding、storage, telemetry、rollback、audit、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "严格 key lifecycle、storage 和 audit proof 优先于快速展示新 key；速度不能覆盖 revoked-key、tenant binding、plaintext secret、rollback 或 stale-key monitoring 缺口。",
            "local_governance": (
                "若存在项目本地治理入口，Key Rotation Contract Inspector 与 Secret Rotation Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/security 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Key Rotation Contract Inspector 固定 lifecycle contract 与 proof targets；Secret Rotation Builder 只基于 handoff 实现；Rotation Lifecycle Evidence Inspector 反证 overlap/revoke/scope/tenant/expiry/rollback/monitoring；"
                "Secret Storage Audit Inspector 验证 hash/KMS storage、plaintext leak negatives、audit fields、privacy redaction 和 local governance；GateKeeper 对 new-key-only 或 weak proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Key Rotation Contract Inspector -> Secret Rotation Builder -> [Rotation Lifecycle Evidence Inspector + Secret Storage Audit Inspector] -> Key Rotation GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 key-rotation、privacy-redaction、permission-auth、audit-log、monitoring、backward-compatibility、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；API key store、KMS/hash、auth enforcement、audit、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque key rotation se prueba con overlap, zero-downtime, revoke, revoked-key negatives, scope/tenant binding, storage, telemetry, rollback, audit y monitoring.",
            "task_scope": f"Alcance limitado al lifecycle de API key / service account secret rotation: {task}; sin rewrite amplio.",
            "success_surface": "Éxito significa overlap old/new, zero-downtime, revoke, revoked-key denial, scope/tenant binding, hash/KMS storage, schedule, expiry, telemetry, rollback, monitoring y audit probados.",
            "fake_done_risks": "Bloquear new-key UI, env var, happy-path API call, docs-only rotation, missing overlap, missing revoked-key negative, missing storage, missing audit fields o missing monitoring.",
            "evidence_preferences": "Preferir old/new key calls, revoked-key negatives, revoke proof, scope/tenant negatives, hash/KMS inspection, expiry/telemetry, rollback, alerts, redacted audit refs y governance.",
            "execution_strategy": "Key Rotation Contract Inspector fija targets; Builder implementa desde handoff; Rotation Lifecycle Evidence y Secret Storage Audit Inspectors inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de overlap, revoked-key denial, tenant/scope binding, storage, telemetry, rollback, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Key lifecycle, storage, and audit proof beats fast new-key progress.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Lifecycle Inspector refuta key behavior; Storage Audit Inspector verifica storage/audit; GateKeeper falla cerrado.",
            "workflow_shape": "Key Rotation Contract Inspector -> Secret Rotation Builder -> [Rotation Lifecycle Evidence Inspector + Secret Storage Audit Inspector] -> Key Rotation GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; key store, KMS/hash, auth enforcement, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because API key / service account secret rotation risk is proven through overlap, zero-downtime compatibility, revoke, revoked-key negatives, scope/tenant binding, secret storage, telemetry, rollback, audit, and monitoring over staged evidence. "
            "One new-key UI, env-var update, happy-path API call, docs-only rotation, or final human review arrives too late to catch revoked keys still working, plaintext secrets, cross-tenant use, or rollback re-enabling revoked keys."
        ),
        "task_scope": (
            f"Scope stays on customer API key / service account secret rotation lifecycle: {task}. The Loop should not expand into a broad authorization platform, credential-system rewrite, or unrelated auth/session reset."
        ),
        "success_surface": (
            "Success means old/new key overlap window, zero-downtime rotation, compromised-key revoke, revoked-key denial, scope / tenant binding, hash or KMS encrypted storage, rotation schedule, expiry, last-used telemetry, rollback safety, rotation failure / stale-key monitoring, and key id / actor / scope / tenant / created/rotated/revoked/failed reason audit are auditable."
        ),
        "fake_done_risks": (
            "Block new-key UI, env-var update, one happy-path API call, docs-only rotation, missing overlap proof, missing revoked-key negative, missing tenant/scope negative, missing hash/KMS storage proof, missing rollback proof, missing audit fields, or missing monitoring alerts."
        ),
        "evidence_preferences": (
            "Prefer old/new key API calls, revoked-key negative calls, compromised-key revoke proof, scope/tenant negative samples, hash/KMS storage inspection, expiry and last-used telemetry, rollback safety proof, rotation failure / stale-key alerts, redacted audit refs, and local-governance evidence. "
            "Classify each key lifecycle and storage claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Key Rotation Contract Inspector first freezes overlap, revoke, scope/tenant, storage, expiry, telemetry, rollback, audit, and monitoring proof targets; Secret Rotation Builder implements from that handoff; Rotation Lifecycle Evidence Inspector and Secret Storage Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor UI copy, vendor-specific docs, or non-critical setup polish may remain only with owner/follow-up; missing overlap, revoked-key denial, tenant/scope binding, storage, telemetry, rollback, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Strict key lifecycle, storage, and audit proof beats fast new-key progress; speed cannot hide revoked-key, tenant-binding, plaintext-secret, rollback, or stale-key monitoring gaps."
        ),
        "local_governance": (
            "If project-local governance markers are present, Key Rotation Contract Inspector and Secret Rotation Builder read applicable rules, both parallel Inspectors verify related design/test/security obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Key Rotation Contract Inspector freezes lifecycle contract and proof targets; Secret Rotation Builder implements only from that handoff; Rotation Lifecycle Evidence Inspector refutes overlap/revoke/scope/tenant/expiry/rollback/monitoring claims; Secret Storage Audit Inspector verifies hash/KMS storage, plaintext leak negatives, audit fields, privacy redaction, and local governance; GateKeeper fails closed on new-key-only or weak proof."
        ),
        "workflow_shape": (
            "Use Key Rotation Contract Inspector -> Secret Rotation Builder -> [Rotation Lifecycle Evidence Inspector + Secret Storage Audit Inspector] -> Key Rotation GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries key-rotation, privacy-redaction, permission-auth, audit-log, monitoring, backward-compatibility, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. API key store, KMS/hash, auth enforcement, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _dispute_chargeback_lifecycle_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 dispute / chargeback 风险会在 provider dispute lifecycle、webhook ordering、deadline/package、refund overlap、ledger/payout、notification/SLA、audit、monitoring 和 governance 中逐步暴露；一次 UI status、dashboard won/lost、provider dispute id 或 happy-path close 会太晚发现证据缺口。"
            ),
            "task_scope": f"范围固定为 dispute / chargeback lifecycle：{task}。不扩展成 notification subscription-deliverability、payout settlement 主任务、payment webhook 平台重写或无关 UI polish。",
            "success_surface": (
                "成功意味着 provider dispute.created/updated/closed、retrieval request、representment evidence deadline、issuer/acquirer reason code、provisional credit/debit、fee、win/loss、partial/duplicate dispute、refund overlap、order fulfillment evidence、customer notification、merchant response SLA、ledger entries、invoice/balance adjustment、payout hold/release、audit trail 和 monitoring 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断 UI-status-only、Stripe dashboard won/lost-only、provider dispute id-only、happy-path close、evidence package 缺失、deadline proof 缺失、refund-overlap negative 缺失、ledger/payout reconciliation 缺失、notification/SLA 缺失、audit trail 缺失、monitoring 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 provider fixture contract、signature/replay/out-of-order webhook cases、deadline scheduler proof、evidence package artifact、ledger/payout reconciliation、refund/chargeback overlap negatives、notification delivery proof、merchant SLA cases、audit reason refs、failed/stale dispute alerts、command output 和 durable artifacts；每条 claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "先由 Dispute Contract Inspector 固定 provider fixtures、webhook ordering、deadline、reason code、refund overlap、ledger/payout、notification/SLA、audit、monitoring 和 governance targets；"
                "Chargeback Lifecycle Builder 读取 contract handoff 后实现；Dispute Evidence Inspector 与 Ledger Notification Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 dashboard/report polish 或额外 provider sample 可作为 Residual risk 留下并指定 owner/follow-up；缺少 deadline/package、refund overlap、ledger/payout、notification/SLA、audit、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "严格 dispute lifecycle 证据优先于务实进度；宁可先交窄而可复验的 deadline/package、overlap、ledger 和 notification proof，也不要 happy-path 状态更新掩盖争议处理风险。",
            "local_governance": (
                "若存在项目本地治理入口，Dispute Contract Inspector 和 Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/payment/audit/notification 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Dispute Contract Inspector 固定 provider contract 与 proof targets；Chargeback Lifecycle Builder 只基于 handoff 实现；Dispute Evidence Inspector 反证 webhook/deadline/package/overlap；"
                "Ledger Notification Inspector 验证 ledger/payout/notification/SLA/audit/privacy/monitoring；GateKeeper 对 UI-status-only 或 weak proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Dispute Contract Inspector -> Chargeback Lifecycle Builder -> [Dispute Evidence Inspector + Ledger Notification Inspector] -> Dispute Chargeback GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 dispute-chargeback、webhook-ordering、provider-contract、evidence-deadline、reason-code、ledger-reconciliation、payout-settlement、payment-refund-billing、message-delivery、audit-log、privacy-redaction、monitoring 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；provider、webhook、deadline scheduler、ledger、notification、audit、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque dispute/chargeback risk se prueba con lifecycle, ordering, deadlines, package, ledger/payout, notification/SLA, audit, monitoring y governance.",
            "task_scope": f"Alcance limitado a dispute / chargeback lifecycle: {task}; sin convertirlo en notification deliverability, payout settlement principal o rewrite amplio.",
            "success_surface": "Éxito significa dispute events, retrieval, representment deadline, reason codes, credits/debits, outcomes, overlap, fulfillment evidence, notification/SLA, ledger/payout, audit y monitoring probados.",
            "fake_done_risks": "Bloquear UI-status-only, dashboard-only, provider-id-only, happy-path close, missing package, deadline, overlap negative, ledger/payout reconciliation, notification/SLA, audit, monitoring o governance.",
            "evidence_preferences": "Preferir provider fixtures, signed/replay/out-of-order webhooks, deadline proof, package artifacts, ledger/payout reconciliation, overlap negatives, notification delivery, SLA, audit refs y alerts; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Dispute Contract Inspector fija targets; Builder implementa desde handoff; Dispute Evidence y Ledger Notification Inspectors inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de package/deadline, overlap, ledger/payout, notification/SLA, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Dispute lifecycle proof beats pragmatic progress.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Dispute Evidence refuta lifecycle; Ledger Notification verifica ledger/SLA/audit; GateKeeper falla cerrado.",
            "workflow_shape": "Dispute Contract Inspector -> Chargeback Lifecycle Builder -> [Dispute Evidence Inspector + Ledger Notification Inspector] -> Dispute Chargeback GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; provider, webhook, deadline scheduler, ledger, notification, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because dispute / chargeback risk is proven through provider dispute lifecycle, webhook ordering, deadline/package evidence, refund overlap negatives, ledger/payout reconciliation, notification/SLA, audit, monitoring, and governance over staged evidence. "
            "One UI status change, dashboard won/lost outcome, stored provider dispute id, or happy-path close arrives too late to catch missing lifecycle proof."
        ),
        "task_scope": (
            f"Scope stays on dispute / chargeback lifecycle: {task}. The Loop should not become notification subscription-deliverability, payout settlement as the main task, a broad payment webhook rewrite, or unrelated UI polish."
        ),
        "success_surface": (
            "Success means provider dispute.created/updated/closed, retrieval request, representment evidence submission deadline, issuer/acquirer reason code, provisional credit/debit, fee, win/loss, partial dispute, duplicate dispute, refund overlap, order fulfillment evidence, customer notification, merchant response SLA, ledger entries, invoice/balance adjustment, payout hold/release, audit trail, and monitoring are auditable."
        ),
        "fake_done_risks": (
            "Block UI-status-only, Stripe dashboard won/lost-only, provider-dispute-id-only, happy-path close, missing evidence package, missing deadline proof, missing refund-overlap negative, missing ledger/payout reconciliation, missing notification/SLA, missing audit trail, missing monitoring, or skipped governance."
        ),
        "evidence_preferences": (
            "Prefer provider fixture contract, signature/replay/out-of-order webhook cases, deadline scheduler proof, evidence package artifact, ledger/payout reconciliation, refund/chargeback overlap negatives, notification delivery proof, merchant SLA cases, audit reason refs, failed/stale dispute alerts, command output, and durable artifacts. "
            "Classify each lifecycle claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Dispute Contract Inspector first freezes provider fixtures, webhook ordering, deadlines, reason codes, refund overlap, ledger/payout, notification/SLA, audit, monitoring, and governance targets; Chargeback Lifecycle Builder implements from that handoff; Dispute Evidence Inspector and Ledger Notification Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard/report polish or additional provider samples may remain only with owner/follow-up; missing deadline/package, refund overlap, ledger/payout, notification/SLA, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Strict dispute lifecycle proof beats pragmatic progress; prefer a narrow verifiable deadline/package, overlap, ledger, and notification proof slice over a faster status update that hides dispute handling risk."
        ),
        "local_governance": (
            "If project-local governance markers are present, Dispute Contract Inspector and Builder read applicable rules, both parallel Inspectors verify related design/test/payment/audit/notification obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Dispute Contract Inspector freezes provider contract and proof targets; Chargeback Lifecycle Builder implements only from that handoff; Dispute Evidence Inspector refutes webhook/deadline/package/overlap claims; Ledger Notification Inspector verifies ledger/payout/notification/SLA/audit/privacy/monitoring; GateKeeper fails closed on UI-status-only or weak proof."
        ),
        "workflow_shape": (
            "Use Dispute Contract Inspector -> Chargeback Lifecycle Builder -> [Dispute Evidence Inspector + Ledger Notification Inspector] -> Dispute Chargeback GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries dispute-chargeback, webhook-ordering, provider-contract, evidence-deadline, reason-code, ledger-reconciliation, payout-settlement, payment-refund-billing, message-delivery, audit-log, privacy-redaction, monitoring, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Provider, webhook, deadline scheduler, ledger, notification, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _payment_webhook_ledger_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 payment webhook 风险会在 signature/timestamp、replay/idempotency、ordering、retry/DLQ、"
                "ledger/dispute/payout reconciliation、audit/privacy、manual replay 和 monitoring 中逐步暴露；一次 happy-path webhook、provider status 或最终人工 review 会太晚发现重复入账、乱序状态或对账缺口。"
            ),
            "task_scope": f"范围固定为 payment provider webhook ingestion 与 ledger reconciliation：{task}。不扩展成全支付平台重写、通用账务系统或无关结账 UI polish。",
            "success_surface": (
                "成功意味着 provider contract fixtures、signature verification、timestamp tolerance、replay protection、idempotency key、duplicate prevention、out-of-order delivery、event version compatibility、ledger reconciliation、payout settlement、dispute lifecycle、retry/backoff、DLQ、audit log、privacy redaction、monitoring alerts 和 manual replay tooling 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断一个 checkout.session.completed happy path、dev mode 接收 unsigned event、只存 provider status、只靠数据库 unique constraint 去重、docs-only provider contract、缺少 replay negatives、缺少 ordering proof、缺少 ledger reconciliation 或缺少 monitoring/DLQ proof。"
            ),
            "evidence_preferences": (
                "优先 signed fixture corpus、invalid signature negatives、stale timestamp negatives、replay/duplicate negatives、out-of-order sequences、idempotency ledger checks、provider retry/failure proof、DLQ proof、manual replay proof、audit refs、monitoring alerts 和 reconciliation reports；每条 claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "先由 Webhook Contract Inspector 固定 provider schema、signature/timestamp、idempotency、ordering、retry/DLQ、ledger/dispute/payout state machines、audit/privacy、monitoring 和 replay targets；"
                "Payment Webhook Builder 读取 contract handoff 后实现；Webhook Evidence Inspector 与 Ledger Reconciliation Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 dashboard/report polish 或 provider fixture coverage 扩展可作为 Residual risk 留下并指定 owner/follow-up；缺少 signature/replay/order/idempotency、retry/DLQ、ledger/dispute/payout reconciliation、audit/privacy、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "严格 webhook 与账务证据优先于务实进度；宁可先交窄而可复验的签名、乱序、重放和 ledger proof，也不要 happy-path 状态更新掩盖账务风险。",
            "local_governance": (
                "若存在项目本地治理入口，Webhook Contract Inspector 和 Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/payment 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Webhook Contract Inspector 固定 provider contract 与 proof targets；Payment Webhook Builder 只基于 handoff 实现；Webhook Evidence Inspector 反证 signature/replay/order/retry/DLQ；"
                "Ledger Reconciliation Inspector 验证 ledger/dispute/payout/audit/privacy/monitoring；GateKeeper 对 happy-path-only 或 weak proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Webhook Contract Inspector -> Payment Webhook Builder -> [Webhook Evidence Inspector + Ledger Reconciliation Inspector] -> Payment Webhook GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 webhook-ordering、ledger-reconciliation、payout-settlement、dispute-chargeback、payment-refund-billing、provider-contract、idempotency、retry-timeout、queue-recovery、audit-log、privacy-redaction、monitoring 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；provider、webhook、ledger、queue、audit、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque webhook risk se prueba con signature/timestamp, replay/idempotency, ordering, retry/DLQ, ledger/dispute/payout reconciliation, audit/privacy, manual replay y monitoring.",
            "task_scope": f"Alcance limitado a payment provider webhook ingestion y ledger reconciliation: {task}; sin rewrite amplio.",
            "success_surface": "Éxito significa provider fixtures, signatures, timestamp tolerance, replay, idempotency, duplicates, ordering, version compatibility, ledger, payouts, disputes, retry/DLQ, audit, privacy, monitoring y manual replay probados.",
            "fake_done_risks": "Bloquear happy-path webhook, unsigned dev-mode, provider-status-only, database-constraint-only dedupe, docs-only contract, replay/order proof faltante, ledger reconciliation faltante o monitoring/DLQ faltante.",
            "evidence_preferences": "Preferir signed fixtures, invalid signatures, stale timestamps, replay/duplicate negatives, out-of-order sequences, idempotency ledger checks, retry/failure, DLQ, manual replay, audit refs, alerts y reconciliation reports.",
            "execution_strategy": "Webhook Contract Inspector fija targets; Builder implementa desde handoff; Webhook Evidence y Ledger Reconciliation Inspectors inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de signature/replay/order/idempotency, retry/DLQ, ledger/dispute/payout reconciliation, audit/privacy, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Webhook and ledger proof beats pragmatic progress.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Webhook Evidence refuta eventos; Ledger Inspector verifica contabilidad; GateKeeper falla cerrado.",
            "workflow_shape": "Webhook Contract Inspector -> Payment Webhook Builder -> [Webhook Evidence Inspector + Ledger Reconciliation Inspector] -> Payment Webhook GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; provider, webhook, ledger, queue, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because payment webhook risk is proven through signature/timestamp validation, replay/idempotency, ordering, retry/DLQ, ledger/dispute/payout reconciliation, audit/privacy, manual replay, and monitoring over staged evidence. "
            "One happy-path webhook, stored provider status, database-only dedupe, docs-only contract, or final human review arrives too late to catch duplicate ledger effects, out-of-order states, or reconciliation gaps."
        ),
        "task_scope": (
            f"Scope stays on payment provider webhook ingestion and ledger reconciliation: {task}. The Loop should not expand into a broad payment-platform rewrite, general accounting system, or unrelated checkout UI polish."
        ),
        "success_surface": (
            "Success means provider contract fixtures, signature verification, timestamp tolerance, replay protection, idempotency key handling, duplicate prevention, out-of-order delivery, event version compatibility, ledger reconciliation, payout settlement reconciliation, dispute lifecycle state transitions, retry/backoff, dead-letter queue, audit log, privacy redaction, monitoring alerts, and manual replay tooling are auditable."
        ),
        "fake_done_risks": (
            "Block one checkout.session.completed happy path, unsigned dev-mode acceptance, provider-status-only storage, database-constraint-only dedupe, docs-only provider contract, missing replay negatives, missing ordering proof, missing ledger reconciliation, or missing monitoring/DLQ proof."
        ),
        "evidence_preferences": (
            "Prefer signed fixture corpus, invalid signature negatives, stale timestamp negatives, replay and duplicate event negatives, out-of-order sequences, idempotency ledger checks, provider retry/failure proof, DLQ proof, manual replay proof, audit refs, monitoring alerts, and reconciliation reports. "
            "Classify each webhook and ledger claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Webhook Contract Inspector first freezes provider schemas, signature/timestamp rules, idempotency, ordering, retry/DLQ, ledger/dispute/payout state machines, audit/privacy, monitoring, and replay targets; Payment Webhook Builder implements from that handoff; Webhook Evidence Inspector and Ledger Reconciliation Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard/report polish or provider fixture coverage expansion may remain only with owner/follow-up; missing signature/replay/order/idempotency, retry/DLQ, ledger/dispute/payout reconciliation, audit/privacy, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Strict webhook and ledger proof beats pragmatic progress; prefer a narrow verifiable signature, ordering, replay, and ledger proof slice over a faster happy-path status update that hides accounting risk."
        ),
        "local_governance": (
            "If project-local governance markers are present, Webhook Contract Inspector and Builder read applicable rules, both parallel Inspectors verify related design/test/payment obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Webhook Contract Inspector freezes provider contract and proof targets; Payment Webhook Builder implements only from that handoff; Webhook Evidence Inspector refutes signature/replay/order/retry/DLQ claims; Ledger Reconciliation Inspector verifies ledger/dispute/payout/audit/privacy/monitoring; GateKeeper fails closed on happy-path-only or weak proof."
        ),
        "workflow_shape": (
            "Use Webhook Contract Inspector -> Payment Webhook Builder -> [Webhook Evidence Inspector + Ledger Reconciliation Inspector] -> Payment Webhook GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries webhook-ordering, ledger-reconciliation, payout-settlement, dispute-chargeback, payment-refund-billing, provider-contract, idempotency, retry-timeout, queue-recovery, audit-log, privacy-redaction, monitoring, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Provider, webhook, ledger, queue, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _data_residency_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 data residency / regional isolation 的真实风险分布在 DB、object storage、search、cache、queue、"
                "backup、logs、analytics、processor/DPA、key-region、failover、migration、access/export/audit/trace 和 egress monitoring；"
                "一次 Agent pass、一个 routed request、UI region 或最终人工 review 会太晚发现错区写入、跨区复制、处理方不匹配或观测缺口。"
            ),
            "task_scope": (
                f"范围固定为企业 SaaS EU/US tenant data residency / regional isolation：{task}。不扩展成普通 regional dashboard、"
                "全平台数据仓库重写、泛化权限系统或非驻留报表 polish。"
            ),
            "success_surface": (
                "成功意味着 tenant residency policy、EU/US routing、primary DB、object storage、search index、cache、queue、backups、logs、"
                "analytics export、processor/subprocessor allowlist、DPA、encryption key region、failover、migration/backfill、support/admin access、data export、"
                "audit log、observability trace、cross-region egress monitoring 和 wrong-region write/read/export negatives 都有可审计区域证明。"
            ),
            "fake_done_risks": (
                "必须阻断 UI 显示 region=EU、env var、tenant table region 字段、一个 routed request、docs-only DPA、dashboard filter、"
                "processor proof 缺失、wrong-region negatives 缺失、key-region proof 缺失或 observability / egress alerts 缺失的通过。"
            ),
            "evidence_preferences": (
                "优先 regional data-flow inventory、processor contract fixtures、wrong-region write/read/export negatives、cross-region egress alert proof、"
                "key-region proof、failover proof、migration/backfill proof、backup/search/analytics/log region proof、support/admin access proof、"
                "audit refs、observability traces 和 monitoring alerts，并把每条 claim 分类为 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "先由 Residency Contract Inspector 只读固定数据面、处理方、failover、migration、access/export/audit/trace 和监控证明目标；"
                "Regional Isolation Builder 读取 contract handoff 后才实现；Residency Evidence Inspector 验证区域证明、错区负向、processor/DPA、key、failover、migration、"
                "access/export/audit/trace 和 alerts；GateKeeper 从所有 handoff 与 evidence_query 裁决。"
            ),
            "residual_risk_policy": (
                "轻微 dashboard/report polish 只有在可见、点名且有 owner/follow-up 时可作为 Residual risk；缺少数据面区域证明、processor/DPA、"
                "wrong-region negatives、key-region、failover、migration/backfill、backup/search/analytics/log region proof、access/export/audit/trace、monitoring 或本地治理证据时必须 fail closed。"
            ),
            "judgment_tradeoffs": (
                "严格驻留证据和错区反证优先于快速展示 region selector；速度不能覆盖 processor contract、DPA、key-region、failover、migration、访问导出、审计追踪或 egress alert 缺口。"
            ),
            "local_governance": (
                "若存在项目本地治理入口，Residency Contract Inspector 与 Builder 必须读取适用规则，Residency Evidence Inspector 验证相关 design/test/compliance 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Residency Contract Inspector 固定 EU/US 数据面和负向样本；Regional Isolation Builder 只实现这些边界；"
                "Residency Evidence Inspector 反证区域、处理方、访问、导出、审计、trace 和 monitoring claims；GateKeeper 对 UI/env/tenant-field-only 或 weak proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Residency Contract Inspector -> Regional Isolation Builder -> Residency Evidence Inspector -> Residency GateKeeper。"
                "Builder 必须读取 contract handoff；Evidence Inspector 读取 contract 与 builder handoff；GateKeeper 读取 contract、builder、evidence handoff 并查询 regional-isolation、tenant-isolation、"
                "provider-contract、backup、search、analytics、privacy、data-export、monitoring、audit、migration、permission 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；数据面、processor、region routing、key、failover、migration、audit、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": (
                f"La ancla ({task}) encaja con Loopora porque data residency se prueba con DB, storage, search, cache, queue, backups, logs, analytics, processors, keys, failover, migration, access/export/audit/traces y egress monitoring, no con una sola pasada."
            ),
            "task_scope": f"Alcance limitado a EU/US tenant data residency / regional isolation: {task}; sin dashboard regional ni rewrite amplio.",
            "success_surface": (
                "Éxito significa policy, routing, DB, object storage, search, cache, queue, backups, logs, analytics, processor/subprocessor, DPA, key region, failover, migration, access, export, audit, traces, egress alerts y negativos wrong-region probados."
            ),
            "fake_done_risks": "Bloquear UI region=EU, env var, tenant region field, one routed request, docs-only DPA, processor proof faltante, negativos wrong-region faltantes, key-region proof faltante o falta de egress alerts.",
            "evidence_preferences": (
                "Preferir data-flow inventory, processor contract fixtures, wrong-region write/read/export negatives, egress alerts, key-region, failover, migration/backfill, backup/search/analytics/log region proof, access/export/audit/traces y monitoring; clasificar claims como Proven, Weak, Unproven, Blocking o Residual risk."
            ),
            "execution_strategy": "Residency Contract Inspector fija targets; Regional Isolation Builder implementa desde ese handoff; Residency Evidence Inspector verifica pruebas y negativos; GateKeeper decide desde handoffs y evidence_query.",
            "residual_risk_policy": "Faltas de data-plane, processor/DPA, wrong-region negatives, key-region, failover, migration, access/export/audit/trace, monitoring o governance fail closed; solo polish con owner/follow-up puede quedar.",
            "judgment_tradeoffs": "Preferir evidencia estricta de residencia y negativos sobre un selector de región rápido.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; Evidence Inspector verifica obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela inventario y negativos; Builder implementa límites; Evidence Inspector refuta claims; GateKeeper falla cerrado ante weak proof.",
            "workflow_shape": "Residency Contract Inspector -> Regional Isolation Builder -> Residency Evidence Inspector -> Residency GateKeeper con handoffs explícitos.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; data-plane, processors, routing, keys, failover, migration, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because data residency / regional isolation risk spans DB, object storage, search, cache, queue, backups, logs, analytics, processor/DPA, key-region, failover, migration, access/export/audit/trace, and egress monitoring. "
            "One Agent pass, one routed request, UI region, env var, tenant field, or final human review arrives too late to catch wrong-region writes, cross-region replication, processor mismatch, or missing observability."
        ),
        "task_scope": (
            f"Scope stays on enterprise SaaS EU/US tenant data residency / regional isolation: {task}. The Loop should not expand into a regional dashboard, data-warehouse rewrite, broad permission-system rewrite, or unrelated report polish."
        ),
        "success_surface": (
            "Success means tenant residency policy, EU/US routing, primary DB, object storage, search index, cache, queue, backups, logs, analytics export, processor/subprocessor allowlist, DPA, encryption key region, failover, migration/backfill, support/admin access, data export, audit log, observability trace, cross-region egress monitoring, and wrong-region write/read/export negatives are auditable."
        ),
        "fake_done_risks": (
            "Block UI region=EU, env var, tenant table region field, one routed request, docs-only DPA, dashboard filter, missing processor proof, missing wrong-region negatives, missing key-region proof, or missing observability / egress alerts."
        ),
        "evidence_preferences": (
            "Prefer regional data-flow inventory, processor contract fixtures, wrong-region write/read/export negatives, cross-region egress alert proof, key-region proof, failover proof, migration/backfill proof, backup/search/analytics/log region proof, support/admin access proof, audit refs, observability traces, and monitoring alerts. "
            "Classify each residency claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Residency Contract Inspector first freezes data-plane, processor, failover, migration, access/export/audit/trace, and monitoring proof targets read-only; Regional Isolation Builder implements only after that contract handoff; Residency Evidence Inspector verifies regional proof, wrong-region negatives, processor/DPA, key, failover, migration, access/export/audit/trace, and alerts; GateKeeper judges from all handoffs and evidence_query."
        ),
        "residual_risk_policy": (
            "Minor dashboard/report polish may remain only when visible, named, and owned by follow-up; missing data-plane region proof, processor/DPA, wrong-region negatives, key-region, failover, migration/backfill, backup/search/analytics/log region proof, access/export/audit/trace, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Strict residency proof and wrong-region negatives beat faster region-selector progress. Speed cannot hide processor contract, DPA, key-region, failover, migration, access/export, audit/trace, or egress-alert gaps."
        ),
        "local_governance": (
            "If project-local governance markers are present, Residency Contract Inspector and Builder read applicable rules, Residency Evidence Inspector verifies related design/test/compliance obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Residency Contract Inspector freezes EU/US data-plane and negative samples; Regional Isolation Builder implements only those boundaries; Residency Evidence Inspector disproves region, processor, access, export, audit, trace, and monitoring claims; GateKeeper fails closed on UI/env/tenant-field-only or weak proof."
        ),
        "workflow_shape": (
            "Use Residency Contract Inspector -> Regional Isolation Builder -> Residency Evidence Inspector -> Residency GateKeeper. Builder reads the contract handoff; Evidence Inspector reads contract plus builder handoffs; GateKeeper reads contract, builder, and evidence handoffs and queries regional-isolation, tenant-isolation, provider-contract, backup, search, analytics, privacy, data-export, monitoring, audit, migration, permission, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Data-plane, processors, region routing, keys, failover, migration, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _search_index_consistency_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为全文搜索索引一致性不能靠一次 Agent pass、一个本地搜索结果、green index job 或 dashboard latest 裁决。"
                "后续轮次必须分阶段产生 document event schema、create/update/delete 增量同步、tenant ACL / permission-change negative、reindex/backfill idempotency、cursor recovery、lag alert、audit、retry/DLQ 和 governance 证据。"
            ),
            "task_scope": f"范围固定为 knowledge-base search-index consistency：{task}。不扩展成 search quality eval、RAG answer grounding、通用搜索体验 polish 或只做本地搜索框。",
            "success_surface": (
                "成功意味着 document create/update/delete 会增量同步到 search index；tenant ACL 和 permission revocation 立即过滤结果；已删除或无权限文档有负向搜索样本；"
                "reindex/backfill 可重跑且幂等；watermark/cursor 失败后可恢复；index lag / stale index 有 SLO、监控和告警；pagination/sort 稳定；audit log 覆盖 reindex run、watermark/cursor、失败重试和 governance。"
            ),
            "fake_done_risks": (
                "必须阻断 local-search-only、green-index-job-only、row-count-sample-only、dashboard-latest-only、ACL negatives 缺失、deleted-document proof 缺失、reindex idempotency 缺失、cursor recovery 缺失、lag alert 缺失、audit 缺失、retry/DLQ proof 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 search index contract、document event fixtures、create/update/delete sync proof、tenant ACL / permission revocation negatives、deleted-document negative search、cross-tenant negatives、reindex/backfill idempotent reruns、watermark/cursor recovery artifact、lag/stale monitoring alerts、pagination/sort samples、audit refs、retry/DLQ evidence 和 local-governance evidence。每条 search-index claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Search Index Contract Inspector 先固定 proof targets；Search Index Builder 读取 contract handoff 后实现；"
                "Index Consistency Inspector 与 Access Freshness Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 relevance tuning、额外 query 覆盖或 UI polish 可作为 Residual risk 留下并指定 owner/follow-up；缺少 event sync、ACL/revocation negatives、deleted-document negatives、idempotent reindex、cursor recovery、lag alert、audit、retry/DLQ 或 governance 证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "索引一致性、权限新鲜度、删除反证、重建幂等、cursor recovery、lag alert 和 audit 证据优先于快速看到一个搜索结果。",
            "local_governance": (
                "若存在项目本地治理入口，Search Index Contract Inspector 与 Search Index Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/security/data/monitoring/audit 义务，GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Search Index Contract Inspector 固定 event schema、ACL、alias/versioning、reindex/cursor、lag/audit/retry targets；Search Index Builder 只基于 handoff 实现；Index Consistency Inspector 反证 create/update/delete、deleted-doc、reindex、cursor、lag 和 pagination；Access Freshness Inspector 反证 ACL/revocation、cross-tenant、audit、retry/DLQ、monitoring 和 governance；GateKeeper 对浅层搜索 proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Search Index Contract Inspector -> Search Index Builder -> [Index Consistency Inspector + Access Freshness Inspector] -> Search Index GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 search-index、permission-auth、tenant-isolation、idempotency、monitoring、audit-log、queue-recovery、retry-timeout、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；搜索引擎、索引 schema、document event source、tenant/ACL model、queue/backfill worker、monitoring、audit 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque search-index consistency requiere evidencia por fases, no un resultado local, green job o dashboard latest.",
            "task_scope": f"Alcance limitado a knowledge-base search-index consistency: {task}; sin search quality eval, RAG grounding ni UI-only search.",
            "success_surface": "Éxito significa create/update/delete sync, tenant ACL y permission revocation filtering, deleted/unauthorized negatives, idempotent reindex/backfill, watermark/cursor recovery, lag/stale alerts, stable pagination/sort, audit, retry/DLQ y governance.",
            "fake_done_risks": "Bloquear local-search-only, green-index-job-only, row-count-sample-only, dashboard-latest-only, missing ACL negatives, deleted-document proof, reindex idempotency, cursor recovery, lag alert, audit, retry/DLQ o governance.",
            "evidence_preferences": "Preferir event fixtures, index sync proof, ACL/revocation negatives, deleted-document and cross-tenant negatives, idempotent reindex reruns, cursor recovery, lag alerts, pagination/sort samples, audit, retry/DLQ y governance.",
            "execution_strategy": "Search Index Contract Inspector fija targets; Search Index Builder implementa; Index Consistency y Access Freshness inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de sync, ACL negatives, deleted negatives, idempotent reindex, cursor recovery, lag alert, audit, retry/DLQ o governance fail closed.",
            "judgment_tradeoffs": "Index consistency, access freshness, deletion proof, idempotent reindex, cursor recovery, lag alert and audit beat fast local search.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Index Consistency refuta sync/reindex/cursor/lag/pagination; Access Freshness refuta ACL, tenant, audit, retry/DLQ y monitoring.",
            "workflow_shape": "Search Index Contract Inspector -> Search Index Builder -> [Index Consistency Inspector + Access Freshness Inspector] -> Search Index GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; engine, schema, events, ACL, queue/backfill, monitoring, audit y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because full-text search index consistency cannot be judged from one Agent pass, one local search result, a green index job, sampled row count, or dashboard latest. "
            "Later rounds must produce staged evidence for document event schema, create/update/delete incremental sync, tenant ACL and permission-change negatives, reindex/backfill idempotency, cursor recovery, lag alerting, audit, retry/DLQ, and governance."
        ),
        "task_scope": (
            f"Scope stays on knowledge-base search-index consistency: {task}. The Loop should not expand into search quality evaluation, RAG answer grounding, broad search UX polish, or merely a local search box."
        ),
        "success_surface": (
            "Success means document create/update/delete events incrementally sync to the search index; tenant ACL and permission revocation filter results immediately; deleted and unauthorized documents have negative search samples; reindex/backfill reruns are idempotent; watermark/cursor recovery works after failure; index lag / stale index SLOs, monitoring, and alerts exist; pagination and sorting are stable; audit logs cover reindex runs, watermark/cursor, failed retries, and governance."
        ),
        "fake_done_risks": (
            "Block local-search-only, green-index-job-only, row-count-sample-only, dashboard-latest-only, missing ACL negatives, missing deleted-document proof, missing reindex idempotency, missing cursor recovery, missing lag alert, missing audit, missing retry/DLQ proof, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer search index contract proof, document event fixtures, create/update/delete sync proof, tenant ACL and permission revocation negatives, deleted-document negative search, cross-tenant negatives, reindex/backfill idempotent reruns, watermark/cursor recovery artifact, lag/stale monitoring alerts, pagination/sort samples, audit refs, retry/DLQ evidence, and local-governance evidence. "
            "Classify each search-index claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Search Index Contract Inspector first freezes proof targets; Search Index Builder implements from that handoff; Index Consistency Inspector and Access Freshness Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor relevance tuning, extra query coverage, or UI polish may remain only with owner/follow-up; missing event sync, ACL/revocation negatives, deleted-document negatives, idempotent reindex, cursor recovery, lag alert, audit, retry/DLQ, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Index consistency, access freshness, deleted-document proof, idempotent reindex, cursor recovery, lag alerts, and audit evidence beat quickly seeing one search result."
        ),
        "local_governance": (
            "If project-local governance markers are present, Search Index Contract Inspector and Search Index Builder read applicable rules, both parallel Inspectors verify related design/test/security/data/monitoring/audit obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Search Index Contract Inspector freezes event schema, ACL, alias/versioning, reindex/cursor, lag/audit/retry targets; Search Index Builder implements only from that handoff; Index Consistency Inspector refutes create/update/delete, deleted-document, reindex, cursor, lag, and pagination gaps; Access Freshness Inspector refutes ACL/revocation, cross-tenant, audit, retry/DLQ, monitoring, and governance gaps; GateKeeper fails closed on shallow search proof."
        ),
        "workflow_shape": (
            "Use Search Index Contract Inspector -> Search Index Builder -> [Index Consistency Inspector + Access Freshness Inspector] -> Search Index GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries search-index, permission-auth, tenant-isolation, idempotency, monitoring, audit-log, queue-recovery, retry-timeout, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Search engine, index schema, document event source, tenant/ACL model, queue/backfill worker, monitoring, audit, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _search_quality_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为搜索质量不能靠一次 Agent pass、一个 demo query、一个单点 benchmark 或最终人工 review 裁决。"
                "后续轮次会产生 baseline handoff、before/after 结果 artifact、人工评审记录、回归样本证据和 GateKeeper verdict。"
            ),
            "task_scope": f"范围固定为这条 search quality 任务：{task}。不扩展成宽泛搜索平台重写、聊天体验 polish 或无关 RAG 工具链。",
            "success_surface": (
                "成功意味着 Top-5 search quality 在真实查询、负向查询和回归样本上可审计地提升，并且人工评审记录覆盖 relevance、groundedness 和 hallucination risk。"
            ),
            "fake_done_risks": (
                "必须拒绝一个 demo query 看起来更好、单个 benchmark 分数上涨、cherry-picked query、平均分上涨但负例退化、没有人工评审或缺少回归样本。"
            ),
            "evidence_preferences": (
                "优先 eval set artifact、真实查询/负向查询/回归样本、before/after Top-5 输出、人工 review record、benchmark delta、回归检查和角色 handoff，"
                "并把每条质量声明分到 Proven、Weak、Unproven、Blocking 或 Residual risk 证据桶。"
            ),
            "execution_strategy": (
                "先冻结 eval set、baseline、负向查询、回归样本和人工评审 rubric；再让 Builder 改检索/排序；"
                "随后 Quality Evidence Inspector 比较 before/after 和质量风险；最后 GateKeeper 从 handoff 与 evidence_query 裁决。"
            ),
            "residual_risk_policy": (
                "轻微 query coverage 扩展或 review rubric 打磨可作为 Residual risk 留下，但必须有 owner/follow-up；"
                "eval-set coverage、human-review quality、search relevance、regression safety 或本地治理缺口必须 fail closed。"
            ),
            "judgment_tradeoffs": (
                "优先跨真实查询和负例可复查的质量提升，而不是更快交付一个 demo query 或单点分数上涨；速度不能覆盖 regression safety、人工质量记录、groundedness 或 hallucination risk。"
            ),
            "local_governance": (
                "若存在项目本地治理入口，Builder 先读取适用规则，Inspector 验证相关 design/test 义务，GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Evaluation Baseline Inspector 冻结证据标准，Search Quality Builder 只改检索/排序，Quality Evidence Inspector 反证质量和回归，"
                "GateKeeper 对 demo-query-only、single-score-only、cherry-picked-query 或弱证据 fail closed。"
            ),
            "workflow_shape": (
                "采用 Evaluation Baseline Inspector -> Search Quality Builder -> Quality Evidence Inspector -> Search Quality GateKeeper。"
                "Builder 必须读取 baseline handoff；Quality Inspector 读取 baseline 和 Builder handoff；GateKeeper 读取 baseline、builder、quality handoff 并查询 eval-set、human-review、search-index、negative evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；搜索栈、索引结构、embedding 模型和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": (
                f"La ancla ({task}) encaja con Loopora porque search quality no se decide con una pasada, un demo query, un score aislado o review final."
            ),
            "task_scope": f"Alcance limitado a esta tarea de search quality: {task}; sin reescritura amplia ni polish no relacionado.",
            "success_surface": (
                "Éxito significa mejora auditable de Top-5 en consultas reales, negativas y regresión, con revisión humana de relevance, groundedness y hallucination risk."
            ),
            "fake_done_risks": "Bloquear demo-query-only, single-score-only, cherry-picked query, promedio mejor con negativos peor, sin review humana o sin regresión.",
            "evidence_preferences": (
                "Preferir eval set artifact, consultas reales/negativas/regresión, before/after Top-5, review records, benchmark delta y handoffs, "
                "clasificando cada afirmación como Proven, Weak, Unproven, Blocking o Residual risk."
            ),
            "execution_strategy": (
                "Congelar eval set, baseline, negativos, regresión y rúbrica; Builder cambia retrieval/ranking; Quality Inspector compara before/after; GateKeeper decide desde handoffs y evidence_query."
            ),
            "residual_risk_policy": "Faltas de eval-set, human-review, relevance, regression safety o governance fail closed; solo riesgos visibles con owner/follow-up pueden quedar.",
            "judgment_tradeoffs": "Preferir mejora revisable sobre demo query o score aislado.",
            "local_governance": "Builder lee reglas locales, Inspector verifica design/test obligations, GateKeeper bloquea governance omitida.",
            "role_posture": "Baseline Inspector congela evidencia, Builder cambia ranking, Quality Inspector refuta calidad, GateKeeper bloquea evidencia débil.",
            "workflow_shape": "Evaluation Baseline Inspector -> Search Quality Builder -> Quality Evidence Inspector -> Search Quality GateKeeper con handoffs explícitos.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; stack e índice deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because search quality cannot be judged by one Agent pass, one demo query, one isolated benchmark score, or final human review alone. "
            "Later rounds create baseline handoff, before/after artifacts, human-review records, regression evidence, and a GateKeeper verdict."
        ),
        "task_scope": f"Scope stays on this search-quality task: {task}. The Loop should not expand into broad search-platform rewrite, chat polish, or unrelated RAG tooling.",
        "success_surface": (
            "Success means Top-5 search quality improves auditably across real queries, negative queries, and regression samples, with human-review records for relevance, groundedness, and hallucination risk."
        ),
        "fake_done_risks": (
            "Reject one better demo query, one benchmark score increase, cherry-picked queries, average-score improvement hiding negative regressions, no human review, or missing regression samples."
        ),
        "evidence_preferences": (
            "Prefer eval set artifacts, real/negative/regression query sets, before/after Top-5 outputs, human-review records, benchmark deltas, regression checks, and role handoffs, "
            "classifying each quality claim into Proven, Weak, Unproven, Blocking, or Residual risk evidence buckets."
        ),
        "execution_strategy": (
            "Freeze eval set, baseline, negative queries, regression samples, and human-review rubric first; let Builder change retrieval/ranking; "
            "then Quality Evidence Inspector compares before/after and quality risks; GateKeeper judges from handoffs and evidence_query."
        ),
        "residual_risk_policy": (
            "Minor query coverage or review-rubric polishing may remain only with owner/follow-up; eval-set coverage, human-review quality, search relevance, regression safety, or local-governance gaps fail closed."
        ),
        "judgment_tradeoffs": (
            "Prefer reviewable quality improvement across real and negative queries over faster demo-query or isolated-score progress. Speed cannot hide regression safety, human quality records, groundedness, or hallucination risk."
        ),
        "local_governance": (
            "If project-local governance markers are present, Builder reads applicable rules, Inspector verifies related design/test obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Evaluation Baseline Inspector freezes the evidence standard, Search Quality Builder changes retrieval/ranking, Quality Evidence Inspector tries to disprove quality and regression claims, "
            "and GateKeeper fails closed on demo-query-only, single-score-only, cherry-picked-query, or weak evidence."
        ),
        "workflow_shape": (
            "Use Evaluation Baseline Inspector -> Search Quality Builder -> Quality Evidence Inspector -> Search Quality GateKeeper. Builder reads baseline handoff; "
            "Quality Inspector reads baseline and Builder handoffs; GateKeeper reads baseline, builder, and quality handoffs and queries eval-set, human-review, search-index, negative evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Search stack, index shape, embedding model, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _rag_long_chain_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 RAG support chatbot 的真实完成需要 ingestion、retrieval ACL、answer/tool gating、eval review、evidence hardening 和 GateKeeper 分阶段产生不同 proof 与 handoff；"
                "one Agent pass、直接聊天、demo question、embedding search 或 UI citation 太晚发现 source-span、permission、prompt-injection、tool-safety、privacy、eval 或 monitoring 缺口。"
            ),
            "task_scope": f"范围固定为企业 RAG support chatbot grounding：{task}。不扩展成普通 search quality、search-index consistency、宽泛聊天 UI polish、authorization rewrite 或 prompt asset ownership。",
            "success_surface": (
                "成功意味着 answer grounded in retrieved source chunks，citation/source spans 可回到 document versions，retrieval ACL 与 tenant filtering 正确，prompt-injection documents 不能泄露 system prompt 或调用 unauthorized tools，PII/secrets 已 redacted，hallucination 有 fallback/handoff，top-k recall、faithfulness、citation precision、no-answer、multilingual eval、human review 和 monitoring 都可复验。"
            ),
            "fake_done_risks": (
                "必须阻断 demo-question-only、plausible-answer-only、embedding-search-only、UI-citation-only、source-span proof 缺失、permission/tenant negatives 缺失、prompt-injection negatives 缺失、tool allowlist proof 缺失、PII leak tests 缺失、eval/human-review/monitoring 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 golden Q&A eval set、citation-span verification、permission-filtered retrieval cases、negative prompt-injection docs、tool-call allowlist proof、PII leak tests、fallback/no-answer samples、human review rubric、regression monitoring 和 local-governance evidence。"
                "每条 RAG grounding claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "RAG Contract Inspector 先固定 proof targets；Corpus Ingestion Builder、Retrieval ACL Builder 与 Answer Tooling Builder 分阶段留下窄 handoff；"
                "RAG Evaluation Inspector 读取三个 builder handoff；Evidence Hardening Builder 只补 evaluation 点名缺口；RAG GateKeeper 读取 contract、evaluation 和 hardening handoff 后裁决。"
            ),
            "residual_risk_policy": (
                "轻微 answer-quality tuning、额外 multilingual query coverage 或非关键 UI copy 可作为 Residual risk 留下并指定 owner/follow-up；缺少 source-span、permission/tenant、prompt-injection、tool safety、privacy redaction、eval/human-review、monitoring 或 local-governance evidence 必须 fail closed。"
            ),
            "judgment_tradeoffs": "grounding、permission、privacy、tool safety、eval 和 monitoring 证据优先于快速 demo；速度不能覆盖 plausible answer、embedding-search-only 或 UI-citation-only 证明。",
            "local_governance": (
                "若存在 AGENTS.md、design/README.md、design/、tests/ 或其它项目本地治理入口，RAG Contract Inspector 读取适用规则，各 Builder 读取并遵循适用规则后再改动，RAG Evaluation Inspector 验证相关 design/test/privacy/permission/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "RAG Contract Inspector 固定 document/version/source-span/permission/tool/privacy/eval/monitoring targets；Corpus Ingestion Builder 只构建 document/version/source artifacts；"
                "Retrieval ACL Builder 只构建 permission-filtered retrieval 与 tenant proof；Answer Tooling Builder 只构建 grounded answer、citation、tool gating、redaction 和 fallback；"
                "RAG Evaluation Inspector 反证核心证据；Evidence Hardening Builder 只补缺口；RAG GateKeeper 对浅层 RAG demo fail closed。"
            ),
            "workflow_shape": (
                "采用 RAG Contract Inspector -> Corpus Ingestion Builder -> Retrieval ACL Builder -> Answer Tooling Builder -> RAG Evaluation Inspector -> Evidence Hardening Builder -> RAG GateKeeper。"
                "GateKeeper 查询 rag-grounding、tool-safety、permission-auth、privacy-redaction、eval-set、human-review、monitoring 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；document store、retrieval stack、permission model、tool integration、redaction layer、eval runner、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque RAG grounding se prueba por ingestion, retrieval ACL, answer/tool gating, eval review, evidence hardening y GateKeeper.",
            "task_scope": f"Alcance limitado a enterprise RAG support chatbot grounding: {task}; sin search quality, search-index, chat UI polish, authorization rewrite ni prompt assets.",
            "success_surface": "Éxito significa source chunks/versiones, ACL/tenant filtering, prompt-injection negatives, tool allowlist, redaction, fallback/no-answer, eval, human review y monitoring probados.",
            "fake_done_risks": "Bloquear demo-only, plausible answer, embedding search only, UI citations only, missing source spans, permissions, prompt-injection negatives, tool proof, PII tests, eval/human-review/monitoring o governance.",
            "evidence_preferences": "Preferir golden Q&A, citation-span verification, permission-filtered retrieval, negative prompt-injection docs, tool allowlist, PII tests, fallback samples, human rubric, monitoring y governance.",
            "execution_strategy": "Contract Inspector fija targets; Ingestion, Retrieval ACL y Answer Tooling Builders producen handoffs; Evaluation Inspector revisa; Evidence Hardening repara gaps; GateKeeper decide.",
            "residual_risk_policy": "Missing source-span, permission/tenant, prompt injection, tool safety, privacy, eval/human review, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Grounding, permission, privacy, tool safety, eval and monitoring proof beat a fast demo.",
            "local_governance": "Si existen AGENTS.md, design/README.md, design/, tests/ u otras reglas locales, Contract Inspector las lee; cada Builder lee y respeta reglas aplicables antes de editar; Evaluation Inspector verifica obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract congela targets; Builders producen handoffs; Evaluation refuta evidencia; Hardening repara gaps; GateKeeper falla cerrado.",
            "workflow_shape": "RAG Contract Inspector -> Corpus Ingestion Builder -> Retrieval ACL Builder -> Answer Tooling Builder -> RAG Evaluation Inspector -> Evidence Hardening Builder -> RAG GateKeeper.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; document store, retrieval stack, permisos, tools, redaction, eval, monitoring y runner deben verificarse.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because RAG support chatbot completion is proven through ingestion, retrieval ACL, answer/tool gating, eval review, evidence hardening, and GateKeeper handoffs. "
            "One Agent pass, direct chat, a demo question, embedding search, or UI citations arrive too late to catch source-span, permission, prompt-injection, tool-safety, privacy, eval, or monitoring gaps."
        ),
        "task_scope": (
            f"Scope stays on enterprise RAG support chatbot grounding: {task}. The Loop should not expand into search quality, search-index consistency, broad chat UI polish, authorization rewrite, or prompt asset ownership."
        ),
        "success_surface": (
            "Success means answers are grounded in retrieved source chunks, citation/source spans trace to document versions, retrieval ACL and tenant filtering are correct, prompt-injection documents cannot leak system prompts or call unauthorized tools, PII/secrets are redacted, hallucination has fallback/handoff, and top-k recall, faithfulness, citation precision, no-answer behavior, multilingual eval, human review, and monitoring are reviewable."
        ),
        "fake_done_risks": (
            "Block demo-question-only, plausible-answer-only, embedding-search-only, UI-citation-only, missing source-span proof, missing permission/tenant negatives, missing prompt-injection negatives, missing tool allowlist proof, missing PII leak tests, missing eval/human-review/monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer golden Q&A eval sets, citation-span verification, permission-filtered retrieval cases, negative prompt-injection docs, tool-call allowlist proof, PII leak tests, fallback/no-answer samples, human review rubric, regression monitoring, and local-governance evidence. "
            "Classify each RAG grounding claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "RAG Contract Inspector first freezes proof targets; Corpus Ingestion Builder, Retrieval ACL Builder, and Answer Tooling Builder leave narrow staged handoffs; "
            "RAG Evaluation Inspector reads all three builder handoffs; Evidence Hardening Builder only repairs evaluation-named gaps; RAG GateKeeper judges from contract, evaluation, and hardening handoffs."
        ),
        "residual_risk_policy": (
            "Minor answer-quality tuning, extra multilingual query coverage, or non-critical UI copy may remain only with owner/follow-up; missing source-span, permission/tenant, prompt-injection, tool-safety, privacy redaction, eval/human-review, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Grounding, permission, privacy, tool safety, eval, and monitoring proof beats fast demo progress; speed cannot hide plausible-answer, embedding-search-only, or UI-citation-only proof."
        ),
        "local_governance": (
            "If AGENTS.md, design/README.md, design/, tests/, or other project-local governance markers are present, RAG Contract Inspector reads applicable rules, each Builder reads and follows applicable rules before edits, RAG Evaluation Inspector verifies related design/test/privacy/permission/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "RAG Contract Inspector freezes document/version/source-span/permission/tool/privacy/eval/monitoring targets; Corpus Ingestion Builder builds document/version/source artifacts; Retrieval ACL Builder builds permission-filtered retrieval and tenant proof; Answer Tooling Builder builds grounded answers, citations, tool gating, redaction, and fallback; RAG Evaluation Inspector disproves core evidence; Evidence Hardening Builder patches only gaps; RAG GateKeeper fails closed on shallow RAG demos."
        ),
        "workflow_shape": (
            "Use RAG Contract Inspector -> Corpus Ingestion Builder -> Retrieval ACL Builder -> Answer Tooling Builder -> RAG Evaluation Inspector -> Evidence Hardening Builder -> RAG GateKeeper. GateKeeper queries rag-grounding, tool-safety, permission-auth, privacy-redaction, eval-set, human-review, monitoring, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Document store, retrieval stack, permission model, tool integration, redaction layer, eval runner, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _incident_root_cause_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为事故修复的真实反馈通常太晚；一次 patch、一次现有测试通过或一次 happy path "
                "不能证明复现链路、root cause、回归防护、监控和回滚路径都成立。后续轮次必须先产生只读复现 handoff，再产生根因修复、监控检查和 GateKeeper verdict。"
            ),
            "task_scope": f"范围固定为这条事故 / root-cause 任务：{task}。不扩展成宽泛 checkout、billing 或平台重写。",
            "success_surface": (
                "成功意味着复现或触发条件、failure mode、root-cause 证据、regression guard、复发监控 / 告警以及发布 / 回滚路径都可被审计。"
            ),
            "fake_done_risks": (
                "必须阻断只打 patch、现有测试通过、happy-path checkout、root cause 只有叙述、patch 证据没有绑定复现链路、缺少监控或缺少回滚 proof。"
            ),
            "evidence_preferences": (
                "优先复现 artifact、触发条件、failure mode 记录、root-cause 到 patch 的因果链、regression test、监控 / 告警输出、发布 / 回滚 handoff、"
                "项目内检查和角色 handoff，并把每条事故声明分到 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "先只读：Repro Inspector 固定复现证据、触发条件和 proof targets；Incident Builder 只能基于该 handoff 修 root cause；"
                "Monitoring Inspector 验证 regression guard、复发检测、告警和回滚路径；GateKeeper 从完整 handoff 与 evidence_query 裁决。"
            ),
            "residual_risk_policy": (
                "复现 / 触发条件、root-cause proof、patch-to-repro traceability、regression guard、monitoring、rollback 或本地治理缺口必须 fail closed；"
                "只有已点名、可见且有 owner/follow-up 的非核心风险可保留。"
            ),
            "judgment_tradeoffs": "优先可复查的事故因果链和复发防护，而不是更快合入补丁。速度不能覆盖叙述式 root cause、弱复现或无监控发布。",
            "local_governance": (
                "若存在项目本地治理入口，Incident Builder 改代码前读取适用规则，Monitoring Inspector 验证相关 design/test/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Repro Inspector 只读冻结复现与触发条件；Incident Builder 修最小 root cause 并绑定复现证据；"
                "Monitoring Inspector 反证 regression、recurrence detection 和 rollback；GateKeeper 对弱证据 fail closed。"
            ),
            "workflow_shape": (
                "采用 Repro Inspector -> Incident Builder -> Monitoring Inspector -> GateKeeper。Builder 必须读取 repro handoff；"
                "Monitoring Inspector 读取 repro 和 builder handoff；GateKeeper 查询 root-cause-repro、monitoring、negative evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；checkout、payment、ledger、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": (
                f"La ancla ({task}) encaja con Loopora porque el feedback real de incidente llega tarde; un patch o pruebas existentes no prueban repro, root cause, regresión, monitoring y rollback."
            ),
            "task_scope": f"Alcance limitado a esta tarea de incidente/root cause: {task}; sin reescritura amplia.",
            "success_surface": "Éxito significa evidencia auditable de reproducción o trigger, failure mode, root cause, regression guard, monitoring/alerts y release/rollback.",
            "fake_done_risks": "Bloquear patch-only, existing-tests-only, happy path, root cause narrativo, patch no ligado a repro, sin monitoring o sin rollback proof.",
            "evidence_preferences": "Preferir repro artifacts, trigger conditions, failure mode, causal chain root-cause-to-patch, regression tests, monitoring/alerts, rollback handoff y buckets de evidencia.",
            "execution_strategy": "Primero solo lectura: Repro Inspector fija repro y proof targets; Builder parchea desde ese handoff; Monitoring Inspector verifica regresión, recurrencia, alertas y rollback; GateKeeper decide.",
            "residual_risk_policy": "Repro, root-cause proof, patch-to-repro traceability, regression guard, monitoring, rollback y governance faltante fail closed.",
            "judgment_tradeoffs": "Preferir cadena causal revisable y protección de recurrencia sobre un patch rápido.",
            "local_governance": "Builder lee reglas locales antes de editar, Monitoring Inspector verifica obligaciones y GateKeeper bloquea governance omitida.",
            "role_posture": "Repro Inspector congela evidencia, Builder corrige root cause, Monitoring Inspector refuta regresión/recurrencia/rollback, GateKeeper falla cerrado.",
            "workflow_shape": "Repro Inspector -> Incident Builder -> Monitoring Inspector -> GateKeeper con handoffs explícitos.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; checkout, payment, ledger, monitoring y test runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because real incident feedback arrives too late; one patch, existing tests passing, or a happy path "
            "does not prove reproduction, root cause, regression guard, monitoring, and rollback. Later rounds must first create a read-only repro handoff, "
            "then root-cause repair evidence, monitoring inspection, and a GateKeeper verdict."
        ),
        "task_scope": f"Scope stays on this incident/root-cause task: {task}. The Loop should not expand into broad checkout, billing, or platform rewrite.",
        "success_surface": (
            "Success means reproduction or trigger conditions, failure mode, root-cause evidence, regression guard, recurrence monitoring / alerts, and release / rollback path are auditable."
        ),
        "fake_done_risks": (
            "Block patch-only, existing-tests-only, happy-path checkout, narrative-only root cause, patch evidence not tied to repro, missing monitoring, or missing rollback proof."
        ),
        "evidence_preferences": (
            "Prefer repro artifacts, trigger conditions, failure-mode records, root-cause-to-patch causal chain, regression tests, monitoring / alert output, "
            "release / rollback handoff, project-owned checks, and role handoffs, with each incident claim classified as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Start read-only: Repro Inspector pins reproduction evidence, trigger conditions, and proof targets; Incident Builder may patch only from that handoff; "
            "Monitoring Inspector verifies regression guard, recurrence detection, alerts, and rollback path; GateKeeper judges from complete handoffs and evidence_query."
        ),
        "residual_risk_policy": (
            "Repro / trigger conditions, root-cause proof, patch-to-repro traceability, regression guard, monitoring, rollback, and local-governance gaps fail closed. "
            "Only non-core risks that are named, visible, and owned by follow-up may remain."
        ),
        "judgment_tradeoffs": (
            "Prefer a reviewable incident causal chain and recurrence protection over a faster patch. Speed cannot hide narrative root cause, weak repro, or unmonitored release."
        ),
        "local_governance": (
            "If project-local governance markers are present, Incident Builder reads applicable rules before editing, Monitoring Inspector verifies related design/test/monitoring obligations, "
            "and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Repro Inspector freezes repro and trigger evidence read-only; Incident Builder fixes the smallest root cause tied to repro; "
            "Monitoring Inspector disproves regression, recurrence detection, and rollback claims; GateKeeper fails closed on weak evidence."
        ),
        "workflow_shape": (
            "Use Repro Inspector -> Incident Builder -> Monitoring Inspector -> GateKeeper. Builder must read the repro handoff; "
            "Monitoring Inspector reads repro and builder handoffs; GateKeeper queries root-cause-repro, monitoring, negative evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Checkout, payment, ledger, monitoring, and test runner details must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _support_impersonation_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 break-glass access 的真实风险会在审批、同意、会话归因、隐私遮蔽、租户负向、"
                "审计不可篡改、撤销/过期和异常监控中逐步暴露；一次 Agent pass、login-as demo、banner-only 或最终人工 review 会太晚发现共享 token、越权或审计缺口。"
            ),
            "task_scope": f"范围固定为这条 support impersonation / break-glass access 任务：{task}。不扩展成普通客服工单、客户资料编辑或全平台 RBAC 重写。",
            "success_surface": (
                "成功意味着 approved ticket、customer consent、reason code、supervisor approval、time-bound session、actor/acting_as/on_behalf_of attribution、"
                "MFA/step-up、PII masking、tenant isolation、tamper-evident audit refs、revoke、expiry、monitoring 和 export-attempt proof 都可审计。"
            ),
            "fake_done_risks": (
                "必须阻断只实现 impersonate button、feature flag、shared admin token、login-as happy path 或 UI banner，"
                "但没有审批、同意、归因、MFA、隐私、租户、撤销、过期、审计和监控负例证据的通过。"
            ),
            "evidence_preferences": (
                "优先 approval/consent fixtures、reason-code and supervisor-approval cases、time-bound session checks、actor/acting_as/on_behalf_of traces、"
                "MFA/step-up negatives、PII masking tests、tenant isolation negatives、tamper-evident audit refs、revoke/expiry cases、export/download attempts 和 anomaly-monitoring artifacts。"
                "每条 break-glass 声明必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk 证据桶。"
            ),
            "execution_strategy": (
                "先由 Break-glass Policy Inspector 只读固定 approval、consent、session、privacy、tenant、audit、revoke、expiry、monitoring 和 export proof targets；"
                "Break-glass Builder 读取该 handoff 后只实现可审计路径；Access Evidence Inspector 验证负向、隐私、租户、撤销、过期、审计和监控证据；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 monitoring threshold tuning 只有在标为 Residual risk 且有 owner/follow-up 时才可保留；缺少 approval、consent、reason、supervisor approval、"
                "attribution、MFA/step-up、PII masking、tenant isolation、audit immutability、revoke、expiry、export attempt、monitoring 或本地治理 evidence 时必须 fail closed。"
            ),
            "judgment_tradeoffs": "严格阻断优先于快速放出代理登录；宁可先交窄而可审计的 break-glass flow，也不要宽泛 login-as demo 掩盖隐私、权限或审计风险。",
            "local_governance": (
                "若存在项目本地治理入口，Policy Inspector 和 Builder 必须读取适用规则，Access Evidence Inspector 验证相关 design/test/security 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Break-glass Policy Inspector 固定 approval/consent/session/audit/privacy/tenant proof targets；Break-glass Builder 只实现这些治理边界；"
                "Access Evidence Inspector 验证负向、撤销、过期、隐私、租户和审计证据；GateKeeper 对 shared-token、banner-only 或 weak-proof 状态 fail closed。"
            ),
            "workflow_shape": (
                "采用 Break-glass Policy Inspector -> Break-glass Builder -> Access Evidence Inspector -> Break-glass GateKeeper。"
                "Builder 必须读取 policy handoff；Evidence Inspector 读取 policy 与 builder handoff；GateKeeper 查询 support-impersonation、permission、tenant、privacy、session、audit、monitoring、export 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；support、RBAC、audit、session、tenant、export、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque break-glass risk se prueba en approval, consent, attribution, privacy, tenant, audit, revoke, expiry y monitoring, no con login-as demo.",
            "task_scope": f"Alcance limitado a support impersonation / break-glass access: {task}; sin reescritura amplia de RBAC.",
            "success_surface": "Éxito significa approval, consent, reason, supervisor approval, time-bound session, attribution, MFA/step-up, PII masking, tenant isolation, audit, revoke, expiry, monitoring y export proof.",
            "fake_done_risks": "Bloquear impersonate button, feature flag, shared admin token, login-as happy path o UI banner sin aprobación, privacidad, tenant, revoke, audit y monitoring.",
            "evidence_preferences": "Preferir approval/consent fixtures, reason/supervisor cases, attribution traces, MFA/step-up negatives, PII masking, tenant negatives, audit refs, revoke/expiry, export attempts y monitoring; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Policy Inspector fija proof targets; Builder implementa desde ese handoff; Evidence Inspector verifica negativos, privacy, tenant, revoke, audit y monitoring; GateKeeper decide.",
            "residual_risk_policy": "Faltas de approval, consent, attribution, MFA, PII masking, tenant, audit, revoke, expiry, export, monitoring o governance fail closed; solo threshold tuning menor puede quedar con owner/follow-up.",
            "judgment_tradeoffs": "Bloqueo estricto antes que login-as rápido.",
            "local_governance": "Policy Inspector y Builder leen reglas locales; Evidence Inspector verifica obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Policy Inspector congela targets; Builder implementa límites; Evidence Inspector ataca negativos; GateKeeper falla cerrado ante weak proof.",
            "workflow_shape": "Break-glass Policy Inspector -> Break-glass Builder -> Access Evidence Inspector -> Break-glass GateKeeper con handoffs explícitos.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; support, RBAC, audit, session, tenant, export, monitoring y test runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because break-glass access risk is proven through approval, consent, attribution, privacy masking, tenant negatives, "
            "tamper-evident audit, revoke/expiry, and anomaly monitoring over multiple rounds; one Agent pass, login-as demo, banner-only state, or final human review arrives too late."
        ),
        "task_scope": f"Scope stays on this support impersonation / break-glass access task: {task}. The Loop should not expand into general support tickets, customer-profile editing, or broad RBAC rewrite.",
        "success_surface": (
            "Success means approved ticket, customer consent, reason code, supervisor approval, time-bound session, actor/acting_as/on_behalf_of attribution, "
            "MFA/step-up, PII masking, tenant isolation, tamper-evident audit refs, revoke, expiry, monitoring, and export-attempt proof are auditable."
        ),
        "fake_done_risks": (
            "Block impersonate button, feature flag, shared admin token, login-as happy path, or UI banner without approval, consent, attribution, MFA, privacy, tenant, revoke, expiry, audit, and monitoring negatives."
        ),
        "evidence_preferences": (
            "Prefer approval/consent fixtures, reason-code and supervisor-approval cases, time-bound session checks, actor/acting_as/on_behalf_of traces, "
            "MFA/step-up negatives, PII masking tests, tenant isolation negatives, tamper-evident audit refs, revoke/expiry cases, export/download attempts, and anomaly-monitoring artifacts. "
            "Classify each break-glass claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Break-glass Policy Inspector first freezes approval, consent, session, privacy, tenant, audit, revoke, expiry, monitoring, and export proof targets read-only; "
            "Break-glass Builder implements only from that handoff; Access Evidence Inspector verifies negative, privacy, tenant, revoke, expiry, audit, and monitoring evidence; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor monitoring-threshold tuning may remain only when labeled Residual risk with owner/follow-up; missing approval, consent, reason, supervisor approval, attribution, MFA/step-up, "
            "PII masking, tenant isolation, audit immutability, revoke, expiry, export attempt, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Strict blocking beats fast impersonation release; prefer a narrow auditable break-glass flow over a broad login-as demo that hides privacy, permission, or audit risk."
        ),
        "local_governance": (
            "If project-local governance markers are present, Policy Inspector and Builder read applicable rules, Access Evidence Inspector verifies related design/test/security obligations, "
            "and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Break-glass Policy Inspector freezes approval/consent/session/audit/privacy/tenant proof targets; Break-glass Builder implements only those governance boundaries; "
            "Access Evidence Inspector verifies negatives, revoke, expiry, privacy, tenant, and audit evidence; GateKeeper fails closed on shared-token, banner-only, or weak-proof states."
        ),
        "workflow_shape": (
            "Use Break-glass Policy Inspector -> Break-glass Builder -> Access Evidence Inspector -> Break-glass GateKeeper. Builder must read the policy handoff; "
            "Evidence Inspector reads policy and builder handoffs; GateKeeper queries support-impersonation, permission, tenant, privacy, session, audit, monitoring, export, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Support, RBAC, audit, session, tenant, export, monitoring, and test runner details must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _kyc_aml_screening_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 seller KYC/KYB 与 AML screening 的真实风险会在 provider contract、sanctions 负例、"
                "人工审核、webhook 顺序、payout ledger、rescreening、privacy / retention 和 monitoring 中逐步暴露；一次 provider approved、UI verified、"
                "stored provider status 或最终人工 review 会太晚发现合规、资金或审计缺口。"
            ),
            "task_scope": f"范围固定为这条 marketplace seller onboarding KYC/KYB and AML sanctions screening 任务：{task}。不扩展成全 marketplace、支付系统或通用合规平台重写。",
            "success_surface": (
                "成功意味着 identity verification、business registry、beneficial owner、document OCR/liveness、address verification、sanctions/PEP/adverse-media/watchlist、"
                "risk score、manual review、appeal/resubmission、periodic rescreening、webhook signature/replay/order/idempotency、region retention、audit reason、"
                "payout hold/release、privacy redaction 和 monitoring 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断 provider sandbox approved、UI verified、stored provider status、one happy-path webhook、manual review 弱证据、sanctions 负例缺失、"
                "fraud document 负例缺失、payout ledger proof 缺失、privacy / retention 缺失或 monitoring 缺失的通过。"
            ),
            "evidence_preferences": (
                "优先 provider contract fixtures、golden approved/rejected/manual-review cases、false positive 和 false negative sanctions samples、expired/fraudulent document negatives、"
                "manual review rubric、decision reason audit trail、webhook signature/replay/order proof、rescreening job proof、payout hold ledger reconciliation、"
                "privacy redaction、region retention 和 monitoring alerts。每条 KYC/AML 声明必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk 证据桶。"
            ),
            "execution_strategy": (
                "先由 Compliance Contract Inspector 只读固定 provider、jurisdiction/retention、KYC/KYB fields、sanctions samples、manual review、appeal、rescreening、webhook、"
                "audit reason、privacy、monitoring 和 payout ledger proof targets；KYC/AML Builder 读取该 handoff 后实现；"
                "Screening Evidence Inspector 与 Financial Controls Inspector 并行检查筛查证据和资金/隐私/监控证据；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 monitoring threshold 或 rubric tuning 只有在标为 Residual risk 且有 owner/follow-up 时才可保留；缺少 KYC/KYB、sanctions / PEP / watchlist、"
                "manual review、fraud document negatives、webhook order/idempotency、rescreening、retention/privacy、audit reason、payout ledger、monitoring 或本地治理证据时必须 fail closed。"
            ),
            "judgment_tradeoffs": "优先合规证据、负向筛查样本和 payout safety，而不是更快让 seller onboarding 显示 verified。",
            "local_governance": (
                "若存在项目本地治理入口，Compliance Contract Inspector 和 Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/compliance 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Compliance Contract Inspector 固定合规与 proof targets；KYC/AML Builder 只基于 handoff 实现；"
                "Screening Evidence Inspector 反证筛查、证件、webhook 与 provider failure；Financial Controls Inspector 验证 payout、ledger、retention、privacy、audit 和 monitoring；"
                "GateKeeper 对假完成或弱证据 fail closed。"
            ),
            "workflow_shape": (
                "采用 Compliance Contract Inspector -> KYC/AML Builder -> [Screening Evidence Inspector + Financial Controls Inspector] -> KYC/AML GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 kyc-aml-screening、provider-contract、webhook-ordering、"
                "payout-settlement、ledger-reconciliation、privacy-redaction、human-review、monitoring、audit-log 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；provider、KYC/KYB、sanctions、manual review、webhook、ledger、privacy、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque KYC/KYB y AML screening se prueban con provider contracts, sanctions negatives, manual review, webhooks, payout ledger, rescreening, privacy/retention y monitoring.",
            "task_scope": f"Alcance limitado a marketplace seller onboarding KYC/KYB and AML sanctions screening: {task}; sin reescritura amplia.",
            "success_surface": "Éxito significa identity/business verification, beneficial owners, OCR/liveness, address, sanctions/PEP/watchlist, risk score, manual review, appeal, rescreening, webhooks, retention, audit reasons, payout hold/release, privacy y monitoring.",
            "fake_done_risks": "Bloquear provider sandbox approved, UI verified, provider status, happy-path webhook, manual-review débil, falta de sanctions negatives, fraudulent docs, payout ledger, privacy/retention o monitoring.",
            "evidence_preferences": "Preferir provider fixtures, golden approved/rejected/manual-review, false positives/negatives, expired/fraud docs, rubric, audit trail, webhook proof, rescreening job, payout ledger reconciliation, privacy, retention y alerts; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Compliance Contract Inspector fija proof targets; KYC/AML Builder implementa desde ese handoff; Screening Evidence Inspector y Financial Controls Inspector inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de KYC/KYB, sanctions/PEP/watchlist, manual review, fraud negatives, webhook ordering, rescreening, retention/privacy, audit reason, payout ledger, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Preferir compliance evidence y payout safety sobre onboarding rápido.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Screening Inspector refuta screening/provider/webhooks; Financial Controls Inspector verifica payout, ledger, retention, privacy, audit y monitoring; GateKeeper falla cerrado.",
            "workflow_shape": "Compliance Contract Inspector -> KYC/AML Builder -> [Screening Evidence Inspector + Financial Controls Inspector] -> KYC/AML GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; provider, KYC/KYB, sanctions, manual review, webhook, ledger, privacy, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because seller KYC/KYB and AML screening risk is proven through provider contracts, sanctions negatives, manual review, "
            "webhook ordering, payout ledger, rescreening, privacy / retention, and monitoring across staged evidence; one provider-approved response, UI verified state, stored provider status, "
            "or final human review arrives too late."
        ),
        "task_scope": f"Scope stays on this marketplace seller onboarding KYC/KYB and AML sanctions screening task: {task}. The Loop should not expand into a broad marketplace, payments, or compliance-platform rewrite.",
        "success_surface": (
            "Success means identity verification, business registry, beneficial owner checks, document OCR/liveness, address verification, sanctions / PEP / adverse-media / watchlist screening, "
            "risk score, manual review, appeal/resubmission, periodic rescreening, webhook signature/replay/order/idempotency, region retention, audit reason codes, payout hold/release, privacy redaction, and monitoring are auditable."
        ),
        "fake_done_risks": (
            "Block provider sandbox approved, UI verified, stored provider status, one happy-path webhook, weak manual-review proof, missing sanctions negatives, missing fraud-document negatives, "
            "missing payout ledger proof, missing privacy / retention, or missing monitoring."
        ),
        "evidence_preferences": (
            "Prefer provider contract fixtures, golden approved/rejected/manual-review cases, false positive and false negative sanctions samples, expired/fraudulent document negatives, "
            "manual review rubric, decision reason audit trail, webhook signature/replay/order proof, rescreening job proof, payout hold ledger reconciliation, privacy redaction, region retention, and monitoring alerts. "
            "Classify each KYC/AML claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Compliance Contract Inspector first freezes provider, jurisdiction/retention, KYC/KYB field, sanctions sample, manual review, appeal, rescreening, webhook, audit reason, privacy, monitoring, "
            "and payout ledger proof targets read-only; KYC/AML Builder implements from that handoff; Screening Evidence Inspector and Financial Controls Inspector inspect screening and financial/privacy/monitoring evidence in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor monitoring-threshold or rubric tuning may remain only when labeled Residual risk with owner/follow-up; missing KYC/KYB, sanctions / PEP / watchlist, manual review, fraud-document negatives, "
            "webhook ordering/idempotency, rescreening, retention/privacy, audit reason, payout ledger, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": "Prefer compliance evidence, negative screening samples, and payout safety over faster seller-onboarding verified status.",
        "local_governance": (
            "If project-local governance markers are present, Compliance Contract Inspector and Builder read applicable rules, both parallel Inspectors verify related design/test/compliance obligations, "
            "and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Compliance Contract Inspector freezes compliance proof targets; KYC/AML Builder implements only from that handoff; Screening Evidence Inspector refutes screening, document, webhook, and provider-failure claims; "
            "Financial Controls Inspector verifies payout, ledger, retention, privacy, audit, and monitoring; GateKeeper fails closed on fake-done or weak-proof states."
        ),
        "workflow_shape": (
            "Use Compliance Contract Inspector -> KYC/AML Builder -> [Screening Evidence Inspector + Financial Controls Inspector] -> KYC/AML GateKeeper. "
            "Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries kyc-aml-screening, provider-contract, webhook-ordering, payout-settlement, ledger-reconciliation, privacy-redaction, human-review, monitoring, audit-log, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Provider, KYC/KYB, sanctions, manual review, webhook, ledger, privacy, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _authorization_policy_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为授权策略一致性不能靠一次 Agent pass、隐藏按钮、一个 middleware 或一个 admin happy path 裁决。"
                "后续轮次需要一个 Builder handoff，以及 Contract Inspector 和 Security Evidence Inspector 的并行独立证据，最后由 GateKeeper 汇总阻断。"
            ),
            "task_scope": f"范围固定为这条 authorization policy consistency 任务：{task}。不扩展成全平台身份系统重写或无关管理后台 polish。",
            "success_surface": (
                "成功意味着同一 policy decision 在 API、UI、background jobs、export/report、cache invalidation、audit log、role hierarchy、"
                "field-level permissions、SCIM/SSO mapping、temporary access 和 tenant boundary 上都有一致证据。"
            ),
            "fake_done_risks": (
                "必须阻断只隐藏按钮、只加 middleware、只测 admin happy path、只覆盖 API、把 cache revocation/export/job/audit 留给 follow-up、"
                "或缺少 cross-tenant / field-level / stale-cache 负向证据。"
            ),
            "evidence_preferences": (
                "优先 permission matrix contract、policy decision trace、negative authorization cases、cross-tenant escalation attempts、"
                "stale cache / revocation proof、export/report/job enforcement、field-level leakage checks、audit refs、version rollout 和 backward compatibility proof。"
                "每条授权一致性声明必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk 证据桶。"
            ),
            "execution_strategy": (
                "先由 Policy Builder 构建最小共享策略决策切片；随后 Contract Inspector 与 Security Evidence Inspector 并行读取同一 Builder handoff，"
                "一个验证契约矩阵和 rollout/compat，一个攻击安全负例和审计证据；GateKeeper 读取两个并行 handoff 后裁决。"
            ),
            "residual_risk_policy": (
                "authorization-policy、tenant-isolation、negative authorization、cache revocation、export/job/audit、field-level leakage 或本地治理缺口必须 fail closed；"
                "只有可见、点名且有 owner/follow-up 的非核心 rollout polish 可保留。"
            ),
            "judgment_tradeoffs": (
                "优先同一 policy decision 的可审计一致性和负向安全证据，而不是更快合入局部权限补丁。速度不能覆盖跨边界漂移、缓存撤销、导出/job 绕过或审计缺口。"
            ),
            "local_governance": (
                "若存在项目本地治理入口，Policy Builder 改代码前读取适用规则，两个 Inspector 分别验证 design/test/security 义务，GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Policy Builder 构建最小共享决策切片；Contract Inspector 固定并验证权限矩阵、decision trace、rollout 和 compat；"
                "Security Evidence Inspector 独立攻击越权、串租户、缓存、导出、job、字段泄露和审计；GateKeeper 对任一弱证据 fail closed。"
            ),
            "workflow_shape": (
                "采用 Policy Builder -> [Contract Inspector + Security Evidence Inspector] -> Authorization GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取同一个 Builder handoff；GateKeeper 读取两个并行 handoff 并查询 authorization-policy、tenant-isolation、permission、cache、export、audit 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；policy engine、API、UI、job、export、cache、audit 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque authorization consistency no se decide con botones ocultos, middleware o un admin happy path.",
            "task_scope": f"Alcance limitado a esta tarea de authorization policy consistency: {task}; sin reescritura amplia.",
            "success_surface": "Éxito significa una misma policy decision probada en API, UI, jobs, export/report, cache, audit, roles, field permissions, SCIM/SSO y tenants.",
            "fake_done_risks": "Bloquear hidden-buttons-only, middleware-only, admin happy path, API-only, cache/export/job/audit follow-up o falta de negativos.",
            "evidence_preferences": "Preferir permission matrix, policy decision trace, negativos, tenant escalation, cache/revocation, exports/jobs, field leakage, audit refs, rollout y compat; cada claim se clasifica como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Policy Builder construye el corte; Contract Inspector y Security Evidence Inspector inspeccionan en paralelo el mismo handoff; GateKeeper decide desde ambos.",
            "residual_risk_policy": "Authorization, tenant isolation, negative auth, cache revocation, export/job/audit, field leakage y governance faltante fail closed.",
            "judgment_tradeoffs": "Preferir consistencia auditable y negativos de seguridad sobre un patch rápido.",
            "local_governance": "Builder lee reglas locales, ambos Inspectors verifican obligaciones y GateKeeper bloquea governance omitida.",
            "role_posture": "Builder construye decisión compartida; Contract Inspector verifica matriz/trace/rollout/compat; Security Inspector ataca bypasses; GateKeeper falla cerrado.",
            "workflow_shape": "Policy Builder -> [Contract Inspector + Security Evidence Inspector] -> Authorization GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; engine, API, UI, jobs, exports, cache, audit y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because authorization consistency cannot be judged by one Agent pass, hidden buttons, one middleware check, or one admin happy path. "
            "Later rounds need one Builder handoff plus independent parallel Contract Inspector and Security Evidence Inspector proof before GateKeeper closure."
        ),
        "task_scope": f"Scope stays on this authorization policy consistency task: {task}. The Loop should not expand into broad identity-system rewrite or unrelated admin polish.",
        "success_surface": (
            "Success means one policy decision is consistently proven across API, UI, background jobs, export/report, cache invalidation, audit log, role hierarchy, "
            "field-level permissions, SCIM/SSO mapping, temporary access, and tenant boundaries."
        ),
        "fake_done_risks": (
            "Block hidden-buttons-only, middleware-only, admin-happy-path-only, API-only proof, cache revocation/export/job/audit deferred to follow-up, "
            "or missing cross-tenant / field-level / stale-cache negative evidence."
        ),
        "evidence_preferences": (
            "Prefer permission matrix contract, policy decision trace, negative authorization cases, cross-tenant escalation attempts, stale cache / revocation proof, "
            "export/report/job enforcement, field-level leakage checks, audit refs, version rollout, and backward compatibility proof."
            " Classify each authorization-consistency claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Policy Builder first builds the narrow shared-policy-decision slice; then Contract Inspector and Security Evidence Inspector inspect the same Builder handoff in parallel, "
            "one verifying matrix and rollout/compat contracts while the other attacks security negatives and audit proof; GateKeeper reads both parallel handoffs."
        ),
        "residual_risk_policy": (
            "Authorization-policy, tenant-isolation, negative authorization, cache revocation, export/job/audit, field-level leakage, or local-governance gaps fail closed. "
            "Only non-core rollout polish that is visible, named, and owned by follow-up may remain."
        ),
        "judgment_tradeoffs": (
            "Prefer auditable consistency of one policy decision and negative security evidence over a faster local permission patch. Speed cannot hide cross-boundary drift, cache revocation, export/job bypass, or audit gaps."
        ),
        "local_governance": (
            "If project-local governance markers are present, Policy Builder reads applicable rules before editing, both Inspectors verify related design/test/security obligations, "
            "and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Policy Builder builds the smallest shared-decision slice; Contract Inspector verifies permission matrix, decision trace, rollout, and compatibility; "
            "Security Evidence Inspector independently attacks authorization bypass, tenant isolation, stale cache, export/job, field leakage, and audit proof; GateKeeper fails closed on either weak handoff."
        ),
        "workflow_shape": (
            "Use Policy Builder -> [Contract Inspector + Security Evidence Inspector] -> Authorization GateKeeper. Both Inspectors share one parallel_group and read the same Builder handoff; "
            "GateKeeper reads both parallel handoffs and queries authorization-policy, tenant-isolation, permission, cache, export, audit, and local-governance evidence."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Policy engine, API, UI, jobs, exports, cache, audit, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _prompt_asset_ownership_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为固定 system/developer prompt 解耦会跨 managed entries、role agents、runtime prompts、alignment compiler、shared guidance、role metadata 和 Strategy Source 边界产生多处证据；"
                "一次迁移、单个测试或人工 review 太容易漏掉 inline 指令体、locale-specific system_prompt refs、placeholder 渲染和 preset 边界回归。"
            ),
            "task_scope": f"范围固定为固定 system/developer prompt body 与 role metadata instruction 的资产归属：{task}。不把用户可编辑 Strategy Source preset、UI 文案或诊断消息误迁成 system prompt。",
            "success_surface": (
                "成功意味着 Agent Native managed entries、role-agent instructions、Claude session additional context、runtime role prefixes、output contracts、alignment compiler main prompt、shared proof/residual-risk guidance 和 role descriptions 都通过 system_prompt assets 加载；"
                "system_prompts 树不按用户语言分支，Python 只选择 asset refs 并传结构化值。"
            ),
            "fake_done_risks": (
                "必须阻断只迁移一个 prompt、description/dispatch snippet 仍 inline、system_prompts 下出现 .zh/.en 等 locale refs、测试被弱化、静态 asset refs 缺失、placeholder 未解析或 Strategy Source preset 泄漏到固定 system prompt loader。"
            ),
            "evidence_preferences": (
                "优先 design/contracts.md prompt ownership 边界、system_prompt_assets.py loader proof、AST long-instruction scan、static asset ref existence、rendered managed entry/role/runtime/alignment prompt snapshots、unresolved placeholder rejection 和 Strategy Source boundary tests；"
                "每条 prompt surface claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Prompt Surface Contract Inspector 先固定 prompt surfaces 与非契约边界；Prompt Asset Builder 只按 handoff 迁移固定 instruction body；"
                "Prompt Asset Ownership Inspector 与 Runtime Prompt Rendering Inspector 并行读取 contract 和 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 asset 文件命名或非固定 UI copy 可作为 Residual risk 留下并指定 owner/follow-up；inline system-style prompt body、locale-specific system prompt branch、弱化测试、缺少 asset ref proof 或 placeholder 漏洞必须 fail closed。"
            ),
            "judgment_tradeoffs": "资产归属和渲染兼容证据优先于快速清理字符串；速度不能覆盖系统提示词语言分支、role metadata prompt、runtime rendering 或 Strategy Source 边界缺口。",
            "local_governance": (
                "Prompt Surface Contract Inspector 与 Builder 必须读取 design/contracts.md prompt asset ownership 边界和适用 tests；两个并行 Inspector 验证相关 design/test 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Prompt Surface Contract Inspector 固定 surfaces 与非 prompt 边界；Prompt Asset Builder 迁移固定指令体但不改变语义；Prompt Asset Ownership Inspector 反证 Python inline body、locale ref 和测试弱化；"
                "Runtime Prompt Rendering Inspector 验证 managed entries、role agents、runtime/alignment/shared prompt 渲染、placeholder 和 Strategy Source 边界；GateKeeper 对 weak ownership 或 rendering proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Prompt Surface Contract Inspector -> Prompt Asset Builder -> [Prompt Asset Ownership Inspector + Runtime Prompt Rendering Inspector] -> Prompt Asset GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 prompt-asset-ownership、system-prompt-loading、locale-neutrality、runtime-rendering、placeholder-safety、strategy-source-boundary 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；prompt surfaces、asset loader、tests 和 rendered outputs 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque prompt ownership cruza managed entries, role agents, runtime prompts, alignment compiler, shared guidance, metadata y Strategy Source boundaries.",
            "task_scope": f"Alcance limitado a fixed system/developer prompt bodies y role metadata instructions: {task}; no migrar UI copy, diagnostics o presets editables como system prompts.",
            "success_surface": "Éxito significa managed entries, role agents, Claude context, runtime prefixes, output contracts, alignment compiler prompt, shared guidance y role descriptions cargados desde assets sin locale-specific refs.",
            "fake_done_risks": "Bloquear one-prompt-only, inline descriptions/dispatch snippets, .zh/.en refs, weakened tests, missing static refs, unresolved placeholders o Strategy Source leakage.",
            "evidence_preferences": "Preferir design contract, loader proof, AST long-instruction scan, static ref checks, rendered prompt snapshots, placeholder rejection y Strategy Source boundary tests.",
            "execution_strategy": "Prompt Surface Contract Inspector fija surfaces; Builder migra desde handoff; Ownership y Rendering Inspectors inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Inline prompt bodies, locale branches, weakened tests, missing refs o placeholder gaps fail closed.",
            "judgment_tradeoffs": "Asset ownership and rendering compatibility proof beats fast string cleanup.",
            "local_governance": "Inspector y Builder leen design/tests; Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector fija surfaces; Builder migra; Ownership Inspector refuta inline/locale/test gaps; Rendering Inspector verifica outputs; GateKeeper falla cerrado.",
            "workflow_shape": "Prompt Surface Contract Inspector -> Prompt Asset Builder -> [Prompt Asset Ownership Inspector + Runtime Prompt Rendering Inspector] -> Prompt Asset GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; surfaces, loader, tests y rendered outputs deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because fixed system/developer prompt decoupling spans managed entries, role agents, runtime prompts, alignment compiler prompts, shared guidance, role metadata descriptions, and Strategy Source boundaries. "
            "One migration pass, one test, or final review can easily miss inline instruction bodies, locale-specific system_prompt refs, placeholder rendering, or preset-boundary regressions."
        ),
        "task_scope": (
            f"Scope stays on fixed system/developer prompt bodies and role metadata instructions: {task}. The Loop should not misclassify user-editable Strategy Source presets, UI copy, diagnostics, regex patterns, or structured field labels as fixed system prompts."
        ),
        "success_surface": (
            "Success means Agent Native managed entries, role-agent instructions, Claude session additional context, runtime role prefixes, output contracts, alignment compiler main prompt, shared proof/residual-risk guidance, and role descriptions load through system_prompt assets; "
            "the system_prompts tree has no user-language-specific refs, and Python only selects asset refs plus structured runtime values."
        ),
        "fake_done_risks": (
            "Block one-prompt-only migration, inline descriptions or dispatch snippets, .zh/.en locale refs under system_prompts, weakened tests, missing static asset refs, unresolved placeholders, or Strategy Source presets leaking into fixed system prompt loading."
        ),
        "evidence_preferences": (
            "Prefer the design/contracts.md prompt ownership boundary, system_prompt_assets.py loader proof, AST long-instruction scans, static asset ref existence checks, rendered managed entry / role / runtime / alignment prompt snapshots, unresolved-placeholder rejection, and Strategy Source boundary tests. "
            "Classify each prompt-surface claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Prompt Surface Contract Inspector first freezes prompt surfaces and non-contract boundaries; Prompt Asset Builder migrates fixed instruction bodies only from that handoff; Prompt Asset Ownership Inspector and Runtime Prompt Rendering Inspector inspect contract plus builder handoffs in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor asset file naming or non-fixed UI copy may remain only with owner/follow-up; inline system-style prompt bodies, locale-specific system prompt branches, weakened tests, missing asset-ref proof, or placeholder gaps must fail closed."
        ),
        "judgment_tradeoffs": (
            "Asset ownership and rendering compatibility proof beats fast string cleanup; speed cannot hide language-branching system prompts, role metadata prompt gaps, runtime rendering drift, or Strategy Source boundary leaks."
        ),
        "local_governance": (
            "Prompt Surface Contract Inspector and Prompt Asset Builder read the design/contracts.md prompt asset ownership boundary and applicable tests; both parallel Inspectors verify related design/test obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Prompt Surface Contract Inspector freezes surfaces and non-prompt boundaries; Prompt Asset Builder migrates fixed instruction bodies without semantic drift; Prompt Asset Ownership Inspector refutes Python inline bodies, locale refs, and weakened tests; Runtime Prompt Rendering Inspector verifies managed entries, role agents, runtime/alignment/shared prompts, placeholder safety, and Strategy Source boundaries; GateKeeper fails closed on weak ownership or rendering proof."
        ),
        "workflow_shape": (
            "Use Prompt Surface Contract Inspector -> Prompt Asset Builder -> [Prompt Asset Ownership Inspector + Runtime Prompt Rendering Inspector] -> Prompt Asset GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries prompt-asset-ownership, system-prompt-loading, locale-neutrality, runtime-rendering, placeholder-safety, strategy-source-boundary, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Prompt surfaces, asset loader, tests, and rendered outputs must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _backup_restore_recovery_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 backup / restore disaster recovery 的真实风险会在 PITR、cross-region restore、schema migration restore、tenant/full restore、RPO/RTO、integrity、retention/legal hold、permission、audit 和 monitoring 证据中分阶段暴露；"
                "backup job 绿色、一个 snapshot 文件或最终人工 review 太晚发现无法恢复、数据损坏、密钥不可用、权限绕过或告警缺失。"
            ),
            "task_scope": f"范围固定为生产数据库 backup / restore 与 disaster recovery readiness：{task}。不扩展成通用数据平台迁移、全监控平台或无关数据驻留重写。",
            "success_surface": (
                "成功意味着 nightly backup、point-in-time recovery、cross-region snapshot restore、encryption key access、retention policy、legal hold、schema migration restore、isolated tenant restore、full database restore、checksum、row count、application smoke test、RPO/RTO timing、backup/restore failure alerts、restore permission 和 audit backup/snapshot/restore/key/operator/failure reason 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断 backup job green、one snapshot file、dashboard green、缺少 restore drill、缺少 PITR、缺少 tenant/full restore、缺少 checksum/row count/smoke proof、缺少 RPO/RTO evidence、缺少 retention/legal hold、缺少 encryption key access、缺少 restore permission、缺少 audit fields 或缺少 monitoring alerts。"
            ),
            "evidence_preferences": (
                "优先 restore drill output、PITR restore、cross-region snapshot restore、schema migration restore、isolated tenant/full database restore、checksum/row count/application smoke tests、RPO/RTO timing、encryption key access、retention/legal hold behavior、failed/expired/lagging backup alerts、restore permission proof、redacted audit refs 和 local-governance evidence；每条 recovery claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "先由 Backup Recovery Contract Inspector 固定 recovery surface 与 proof targets；Backup Restore Builder 读取 contract handoff 后实现；"
                "Restore Drill Evidence Inspector 与 Retention Security Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 dashboard copy、非关键 runbook polish 或额外 provider fixture coverage 可作为 Residual risk 留下并指定 owner/follow-up；缺少 PITR、restore drill、RPO/RTO、integrity、retention/legal hold、permission、audit、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "可恢复性、完整性和审计证据优先于快速显示 backup 绿色；速度不能覆盖无法恢复、数据损坏、密钥不可用、权限绕过、保留策略错误或告警缺口。",
            "local_governance": (
                "若存在项目本地治理入口，Backup Recovery Contract Inspector 与 Backup Restore Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/security/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Backup Recovery Contract Inspector 固定 recovery contract 与 proof targets；Backup Restore Builder 只基于 handoff 实现；Restore Drill Evidence Inspector 反证 restore drill、PITR、cross-region、schema migration、tenant/full restore、integrity 和 RPO/RTO；"
                "Retention Security Audit Inspector 验证 retention/legal hold、encryption key access、permission、audit fields、monitoring alerts 和 local governance；GateKeeper 对 green-only 或 weak proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Backup Recovery Contract Inspector -> Backup Restore Builder -> [Restore Drill Evidence Inspector + Retention Security Audit Inspector] -> Backup Recovery GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 backup-restore、migration-rollback、monitoring、audit-log、permission-auth、data-integrity、retention-policy、security-key-access、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；数据库、backup provider、storage、KMS/key、monitoring、audit 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque recovery se prueba por PITR, cross-region restore, restore drills, RPO/RTO, integrity, retention, permission, audit y monitoring.",
            "task_scope": f"Alcance limitado a production database backup / restore disaster recovery readiness: {task}; sin rewrite amplio.",
            "success_surface": "Éxito significa nightly backup, PITR, cross-region restore, key access, retention/legal hold, migration restore, tenant/full restore, checksum, row count, smoke, RPO/RTO, alerts, permission y audit probados.",
            "fake_done_risks": "Bloquear backup job green, one snapshot file, dashboard green, missing restore drill, PITR, integrity, RPO/RTO, retention/legal hold, permission, audit o monitoring.",
            "evidence_preferences": "Preferir restore drill, PITR, cross-region restore, migration restore, tenant/full restore, checksum/row count/smoke, timing, key access, retention/legal hold, alerts, permission, audit refs y governance.",
            "execution_strategy": "Backup Recovery Contract Inspector fija targets; Builder implementa desde handoff; Restore Drill Evidence y Retention Security Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de PITR, restore drill, RPO/RTO, integrity, retention, permission, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Recovery and integrity proof beats fast green backup status.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Restore Drill Inspector refuta recovery; Retention Security Audit verifica retention, permission, audit y monitoring; GateKeeper falla cerrado.",
            "workflow_shape": "Backup Recovery Contract Inspector -> Backup Restore Builder -> [Restore Drill Evidence Inspector + Retention Security Audit Inspector] -> Backup Recovery GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; DB, provider, storage, KMS, monitoring, audit y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because backup / restore disaster recovery risk is proven through PITR, cross-region restore, schema-migration restore, tenant/full restore, RPO/RTO, integrity, retention/legal hold, permission, audit, and monitoring over staged evidence. "
            "One green backup job, one snapshot file, dashboard green, or final human review arrives too late to catch unrecoverable backups, corrupt restores, unavailable keys, permission bypass, or missing alerts."
        ),
        "task_scope": (
            f"Scope stays on production database backup / restore and disaster recovery readiness: {task}. The Loop should not expand into a broad data-platform migration, monitoring-platform rewrite, or unrelated data residency project."
        ),
        "success_surface": (
            "Success means nightly backup, point-in-time recovery, cross-region snapshot restore, encryption key access, retention policy, legal hold, schema migration restore, isolated tenant restore, full database restore, checksum, row count, application smoke test, RPO/RTO timing, backup/restore failure alerts, restore permission, and audit backup/snapshot/restore/key/operator/failure reason are auditable."
        ),
        "fake_done_risks": (
            "Block backup job green, one snapshot file, dashboard green, missing restore drill, missing PITR, missing tenant/full restore, missing checksum/row count/smoke proof, missing RPO/RTO evidence, missing retention/legal hold, missing encryption key access, missing restore permission, missing audit fields, or missing monitoring alerts."
        ),
        "evidence_preferences": (
            "Prefer restore drill output, PITR restore, cross-region snapshot restore, schema migration restore, isolated tenant/full database restore, checksum/row count/application smoke tests, RPO/RTO timing, encryption key access, retention/legal hold behavior, failed/expired/lagging backup alerts, restore permission proof, redacted audit refs, and local-governance evidence. "
            "Classify each recovery claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Backup Recovery Contract Inspector first freezes recovery surface and proof targets; Backup Restore Builder implements from that handoff; Restore Drill Evidence Inspector and Retention Security Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard copy, non-critical runbook polish, or additional provider fixture coverage may remain only with owner/follow-up; missing PITR, restore drill, RPO/RTO, integrity, retention/legal hold, permission, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Recovery, integrity, and audit proof beats fast green backup status; speed cannot hide unrecoverable backups, corrupt data, unavailable keys, permission bypass, retention mistakes, or missing alerts."
        ),
        "local_governance": (
            "If project-local governance markers are present, Backup Recovery Contract Inspector and Backup Restore Builder read applicable rules, both parallel Inspectors verify related design/test/security/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Backup Recovery Contract Inspector freezes recovery contract and proof targets; Backup Restore Builder implements only from that handoff; Restore Drill Evidence Inspector refutes restore drill, PITR, cross-region, schema migration, tenant/full restore, integrity, and RPO/RTO claims; Retention Security Audit Inspector verifies retention/legal hold, encryption key access, permission, audit fields, monitoring alerts, and local governance; GateKeeper fails closed on green-only or weak proof."
        ),
        "workflow_shape": (
            "Use Backup Recovery Contract Inspector -> Backup Restore Builder -> [Restore Drill Evidence Inspector + Retention Security Audit Inspector] -> Backup Recovery GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries backup-restore, migration-rollback, monitoring, audit-log, permission-auth, data-integrity, retention-policy, security-key-access, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Database, backup provider, storage, KMS/key, monitoring, audit, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _audit_log_integrity_retention_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 compliance audit trail 的真实完成要通过 event matrix、required fields、redaction、append-only/hash-chain/WORM integrity、clock skew、retention/legal hold、SIEM/export reconciliation、tenant access、retry、logging failure、stale exporter、sequence gap monitoring、migration 和 governance 证据分阶段证明；"
                "database row、console log、UI history 或 reviewability-only 太晚发现可篡改日志、漏记/重复、跨租户访问、留存失效或导出不可对账。"
            ),
            "task_scope": f"范围固定为 admin compliance audit trail integrity and retention：{task}。不扩展成 GDPR deletion/retention、通用数据生命周期、普通日志平台或安全监控重写。",
            "success_surface": (
                "成功意味着 create/update/delete、permission change、failed attempt 都写入 append-only audit log，actor/subject/tenant/request id/IP/user agent/before-after diff/reason code/timestamp/sequence fields 完整，PII/token redaction、timestamp monotonic/clock skew、tamper-evident hash chain 或 WORM、retention/legal hold、SIEM/export reconciliation、tenant isolation、retry no-miss/no-duplicate、logging failure/stale exporter/sequence gap alerts、migration 和 local governance 都可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 database-row-only、console-log-only、UI-history-only、audit-reviewability-only、tamper negative 缺失、retention/legal hold 缺失、export reconciliation 缺失、tenant negative 缺失、redaction 缺失、retry proof 缺失、monitoring 缺失、migration 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 operation/failed-attempt fixtures、required field assertions、PII/token redaction checks、tamper negative checks、hash-chain/WORM proof、clock skew proof、retention/legal hold proof、SIEM/export reconciliation artifacts、tenant negative access samples、retry no-miss/no-duplicate proof、logging failure/stale exporter/sequence gap alerts、migration compatibility 和 local-governance evidence。"
                "每条 audit integrity claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Audit Contract Inspector 先固定 audit proof targets；Audit Trail Builder 读取 contract handoff 后实现；"
                "Audit Integrity Inspector 与 Retention Export Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 UI copy、额外 event type coverage 或非关键 runbook polish 可作为 Residual risk 留下并指定 owner/follow-up；缺少 tamper evidence、required fields、redaction、retention/legal hold、export reconciliation、tenant negative、retry、monitoring、migration 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "审计完整性、防篡改、留存/法务保留、租户隔离、脱敏、重试正确性和监控证据优先于快速写一行日志；速度不能覆盖 row-only、console-only、UI-history-only 或不可对账导出。",
            "local_governance": (
                "若存在项目本地治理入口，Audit Contract Inspector 与 Audit Trail Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/security/compliance/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Audit Contract Inspector 固定 event matrix、fields、redaction、integrity、retention/export、tenant、retry、monitoring proof targets；Audit Trail Builder 只基于 handoff 实现；"
                "Audit Integrity Inspector 反证 operation fixtures、fields、redaction、timestamp、tamper、sequence、retry 和 tenant negatives；Retention Export Inspector 验证 retention/legal hold、WORM/hash-chain、export reconciliation、alerts、access、migration 和 governance；GateKeeper 对浅层 audit 证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Audit Contract Inspector -> Audit Trail Builder -> [Audit Integrity Inspector + Retention Export Inspector] -> Audit Compliance GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 audit-integrity、audit-log、permission-auth、tenant-isolation、privacy-redaction、idempotency、monitoring、data-export、retention-policy、backward-compatibility、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；audit writer、storage/integrity layer、exporter、retention/legal hold policy、tenant/access model、monitoring、migration path 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque audit integrity se prueba por event matrix, fields, redaction, append-only/hash-chain/WORM, retention/legal hold, export reconciliation, tenant access, retry, alerts, migration y governance.",
            "task_scope": f"Alcance limitado a admin compliance audit trail integrity and retention: {task}; sin GDPR deletion/retention ni logging platform amplio.",
            "success_surface": "Éxito significa operation/failed writes, required fields, redaction, monotonic timestamps, tamper evidence, retention/legal hold, SIEM/export reconciliation, tenant isolation, retry no-miss/no-duplicate, alerts, migration y governance probados.",
            "fake_done_risks": "Bloquear row-only, console-only, UI-history-only, reviewability-only, missing tamper, retention/legal hold, export reconciliation, tenant negatives, redaction, retry, monitoring, migration o governance.",
            "evidence_preferences": "Preferir fixtures, field assertions, redaction, tamper negatives, WORM/hash-chain proof, clock skew, retention/legal hold, export reconciliation, tenant negatives, retry proof, alerts, migration y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Audit Contract Inspector fija targets; Audit Trail Builder implementa desde handoff; Audit Integrity y Retention Export inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de tamper evidence, fields, redaction, retention/legal hold, export reconciliation, tenant negative, retry, monitoring, migration o governance fail closed.",
            "judgment_tradeoffs": "Audit integrity, tamper evidence, retention/export, tenant isolation, redaction and retry proof beats quickly writing one log row.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Audit Integrity refuta fixtures/fields/redaction/tamper/sequence/retry/tenant; Retention Export verifica retention/export/alerts/access/migration; GateKeeper falla cerrado.",
            "workflow_shape": "Audit Contract Inspector -> Audit Trail Builder -> [Audit Integrity Inspector + Retention Export Inspector] -> Audit Compliance GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; writer, storage/integrity, exporter, retention policy, access model, monitoring, migration y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because compliance audit trail integrity is proven through event matrix, required fields, redaction, append-only/hash-chain/WORM integrity, clock skew, retention/legal hold, SIEM/export reconciliation, tenant access, retry semantics, logging failure, stale exporter, sequence gap monitoring, migration, and governance evidence over staged handoffs. "
            "A database row, console log, UI history row, or reviewability-only audit arrives too late to catch mutable logs, missed/duplicate entries, cross-tenant access, failed retention, or unreconciled exports."
        ),
        "task_scope": (
            f"Scope stays on admin compliance audit trail integrity and retention: {task}. The Loop should not expand into GDPR deletion/retention, a broad data lifecycle task, generic logging platform, or security monitoring rewrite."
        ),
        "success_surface": (
            "Success means create/update/delete, permission changes, and failed attempts write append-only audit log entries; actor/subject/tenant/request id/IP/user agent/before-after diff/reason code/timestamp/sequence fields are complete; PII/tokens are redacted; timestamps are monotonic and handle clock skew; tamper-evident hash chain or WORM storage, retention/legal hold, SIEM/export reconciliation, tenant isolation, retry no-miss/no-duplicate, logging failure/stale exporter/sequence gap alerts, migration, and local governance are reviewable."
        ),
        "fake_done_risks": (
            "Block database-row-only, console-log-only, UI-history-only, audit-reviewability-only, missing tamper negative, missing retention/legal hold, missing export reconciliation, missing tenant negative, missing redaction, missing retry proof, missing monitoring, missing migration, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer operation/failed-attempt fixtures, required-field assertions, PII/token redaction checks, tamper negative checks, hash-chain/WORM proof, clock-skew proof, retention/legal-hold proof, SIEM/export reconciliation artifacts, tenant negative access samples, retry no-miss/no-duplicate proof, logging failure/stale exporter/sequence gap alerts, migration compatibility, and local-governance evidence. "
            "Classify each audit integrity claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Audit Contract Inspector first freezes audit proof targets; Audit Trail Builder implements from that handoff; Audit Integrity Inspector and Retention Export Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor UI copy, extra event type coverage, or non-critical runbook polish may remain only with owner/follow-up; missing tamper evidence, required fields, redaction, retention/legal hold, export reconciliation, tenant negative, retry, monitoring, migration, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Audit integrity, tamper evidence, retention/legal hold, tenant isolation, redaction, retry correctness, and monitoring proof beats quickly writing one log row; speed cannot hide row-only, console-only, UI-history-only, or unreconciled exports."
        ),
        "local_governance": (
            "If project-local governance markers are present, Audit Contract Inspector and Audit Trail Builder read applicable rules, both parallel Inspectors verify related design/test/security/compliance/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Audit Contract Inspector freezes event matrix, fields, redaction, integrity, retention/export, tenant, retry, and monitoring proof targets; Audit Trail Builder implements only from that handoff; Audit Integrity Inspector refutes operation fixtures, fields, redaction, timestamp, tamper, sequence, retry, and tenant negatives; Retention Export Inspector verifies retention/legal hold, WORM/hash-chain, export reconciliation, alerts, access, migration, and governance; GateKeeper fails closed on shallow audit proof."
        ),
        "workflow_shape": (
            "Use Audit Contract Inspector -> Audit Trail Builder -> [Audit Integrity Inspector + Retention Export Inspector] -> Audit Compliance GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries audit-integrity, audit-log, permission-auth, tenant-isolation, privacy-redaction, idempotency, monitoring, data-export, retention-policy, backward-compatibility, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Audit writer, storage/integrity layer, exporter, retention/legal hold policy, tenant/access model, monitoring, migration path, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _database_schema_migration_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 database schema migration / backfill 的真实完成要通过 schema contract、dual-write、old/new reader parity、tenant isolation、backfill retry/idempotency、invoice reconciliation、monitoring、rollback 和 governance 证据分阶段证明；"
                "一次 Agent 执行、table-only migration、one-time backfill 或 docs-only rollback 太晚发现账单漂移、租户串读或无法回滚。"
            ),
            "task_scope": f"范围固定为 multi-tenant database schema migration / backfill：{task}。不扩展成泛化数据平台、backup restore、data residency 或只建一张表。",
            "success_surface": (
                "成功意味着 old/new schema semantics 明确；dual-write 与 old/new readers 兼容；mixed migrated/unmigrated tenants 读写一致；tenant isolation 负向通过；backfill cursor/retry/idempotency 可恢复；invoice reconciliation 证明 no drift；progress monitoring/alerts、pause/resume、rollback to old readers、cleanup、compatibility 和 local governance 都有证据。"
            ),
            "fake_done_risks": "必须阻断 table-only migration、one happy-path test、one-time backfill、docs-only rollback、old-reader parity 缺失、tenant negative 缺失、retry proof 缺失、invoice reconciliation 缺失、monitoring 缺失或本地治理跳过。",
            "evidence_preferences": (
                "优先 migration contract、old/new reader parity fixtures、mixed migrated/unmigrated tenant cases、cross-tenant negatives、dual-write/read-after-write proof、backfill retry/idempotency/failed-batch recovery、invoice reconciliation/no-drift artifacts、rollback switch proof、progress metrics/alerts、pause/resume、cleanup、compatibility 和 local-governance evidence。每条 migration claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Migration Contract Inspector 先固定 proof targets；Schema Migration Builder 读取 contract handoff 后实现；"
                "Data Consistency Inspector 与 Operational Rollback Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微 cleanup polish、额外 migration fixture 或非关键 dashboard polish 可作为 Residual risk 留下并指定 owner/follow-up；缺少 schema、dual-write、reader parity、tenant isolation、backfill retry、invoice reconciliation、rollback、monitoring、compatibility 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "数据一致性、租户隔离、账单对账、回填幂等、回滚和监控证据优先于快速改 schema；速度不能覆盖 table-only、schema-only 或 docs-only rollback。",
            "local_governance": (
                "若存在项目本地治理入口，Migration Contract Inspector 与 Schema Migration Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/data/migration/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Migration Contract Inspector 固定 schema、dual-write、readers、tenants、backfill、reconciliation、rollback 和 monitoring targets；Schema Migration Builder 只基于 handoff 实现；Data Consistency Inspector 反证 reader parity、dual-write、tenant isolation、backfill retry 和 invoice drift；Operational Rollback Inspector 验证 rollback、monitoring、failed batch recovery、pause/resume、cleanup 和 compatibility；GateKeeper 对浅层 migration proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Migration Contract Inspector -> Schema Migration Builder -> [Data Consistency Inspector + Operational Rollback Inspector] -> Migration GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 schema-migration、dual-write、reader-compatibility、tenant-isolation、backfill-idempotency、invoice-reconciliation、monitoring、rollback-recovery、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；database schema、readers/writers、backfill job、billing invoices、monitoring、rollback path 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque migration/backfill se prueba con schema contract, dual-write, reader parity, tenant isolation, backfill retry, invoice reconciliation, monitoring, rollback y governance.",
            "task_scope": f"Alcance limitado a multi-tenant database schema migration / backfill: {task}; sin broad data platform ni table-only migration.",
            "success_surface": "Éxito significa old/new schema semantics, dual-write compatibility, mixed tenants, tenant negatives, backfill idempotency/retry, invoice reconciliation/no drift, monitoring, pause/resume, rollback, cleanup, compatibility y governance probados.",
            "fake_done_risks": "Bloquear table-only migration, one happy-path, one-time backfill, docs-only rollback, missing reader parity, tenant negative, retry, invoice reconciliation, monitoring o governance.",
            "evidence_preferences": "Preferir migration contract, reader parity fixtures, mixed tenants, cross-tenant negatives, dual-write proof, backfill retry/recovery, invoice reconciliation, rollback, monitoring, pause/resume, cleanup, compatibility y governance.",
            "execution_strategy": "Migration Contract Inspector fija targets; Schema Migration Builder implementa; Data Consistency y Operational Rollback inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de schema, dual-write, reader parity, tenant isolation, backfill retry, reconciliation, rollback, monitoring, compatibility o governance fail closed.",
            "judgment_tradeoffs": "Consistency, tenant isolation, invoice reconciliation, idempotent backfill, rollback and monitoring beat fast schema changes.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Data Consistency refuta parity/dual-write/tenant/backfill/reconciliation; Operational Rollback verifica rollback/monitoring/recovery; GateKeeper falla cerrado.",
            "workflow_shape": "Migration Contract Inspector -> Schema Migration Builder -> [Data Consistency Inspector + Operational Rollback Inspector] -> Migration GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; schema, readers/writers, backfill job, invoices, monitoring, rollback path y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because database schema migration / backfill readiness is proven through schema contract, dual-write compatibility, old/new reader parity, tenant isolation, backfill retry/idempotency, invoice reconciliation, monitoring, rollback, and governance evidence over staged handoffs. "
            "One Agent pass, table-only migration, one-time backfill, or docs-only rollback arrive too late to catch invoice drift, tenant leakage, or unrecoverable rollback."
        ),
        "task_scope": (
            f"Scope stays on multi-tenant database schema migration / backfill: {task}. The Loop should not expand into a broad data platform, backup restore, data residency, or merely creating a new table."
        ),
        "success_surface": (
            "Success means old/new schema semantics are frozen; dual-write and old/new readers stay compatible; mixed migrated/unmigrated tenants read and write consistently; tenant-isolation negatives pass; backfill cursor/retry/idempotency recovers from failures; invoice reconciliation proves no drift; progress monitoring/alerts, pause/resume, rollback to old readers, cleanup, compatibility, and local governance all have evidence."
        ),
        "fake_done_risks": (
            "Block table-only migration, one happy-path test, one-time backfill, docs-only rollback, missing old-reader parity, missing tenant negative, missing retry proof, missing invoice reconciliation, missing monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer migration contract proof, old/new reader parity fixtures, mixed migrated/unmigrated tenant cases, cross-tenant negatives, dual-write/read-after-write proof, backfill retry/idempotency/failed-batch recovery, invoice reconciliation/no-drift artifacts, rollback switch proof, progress metrics/alerts, pause/resume, cleanup, compatibility, and local-governance evidence. "
            "Classify each migration claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Migration Contract Inspector first freezes proof targets; Schema Migration Builder implements from that handoff; Data Consistency Inspector and Operational Rollback Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor cleanup polish, extra migration fixtures, or non-critical dashboard polish may remain only with owner/follow-up; missing schema, dual-write, reader parity, tenant isolation, backfill retry, invoice reconciliation, rollback, monitoring, compatibility, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Data consistency, tenant isolation, invoice reconciliation, idempotent backfill, rollback, and monitoring proof beats quick schema changes; speed cannot hide table-only, schema-only, or docs-only rollback evidence."
        ),
        "local_governance": (
            "If project-local governance markers are present, Migration Contract Inspector and Schema Migration Builder read applicable rules, both parallel Inspectors verify related design/test/data/migration/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Migration Contract Inspector freezes schema, dual-write, readers, tenants, backfill, reconciliation, rollback, and monitoring targets; Schema Migration Builder implements only from that handoff; Data Consistency Inspector refutes reader parity, dual-write, tenant isolation, backfill retry, and invoice drift; Operational Rollback Inspector verifies rollback, monitoring, failed batch recovery, pause/resume, cleanup, and compatibility; GateKeeper fails closed on shallow migration proof."
        ),
        "workflow_shape": (
            "Use Migration Contract Inspector -> Schema Migration Builder -> [Data Consistency Inspector + Operational Rollback Inspector] -> Migration GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries schema-migration, dual-write, reader-compatibility, tenant-isolation, backfill-idempotency, invoice-reconciliation, monitoring, rollback-recovery, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Database schema, readers/writers, backfill job, billing invoices, monitoring, rollback path, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _cdc_replication_consistency_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 CDC replication / warehouse / read-model 同步的真实完成要通过 source event schema、ordering、checkpoint replay、idempotency、snapshot/backfill、tombstone、schema evolution、tenant isolation、reconciliation、lag monitoring、connector recovery、audit 和 governance 证据分阶段证明；"
                "一次 Agent 执行、green sync job、抽样 row count 或 dashboard latest 太晚发现丢重、乱序、回放重复、schema/tombstone 漏处理、租户串读或目标漂移。"
            ),
            "task_scope": f"范围固定为 CDC replication consistency：{task}。不扩展成 payment webhook、billing ledger、通用数据平台、backup restore 或只做同步状态 UI。",
            "success_surface": (
                "成功意味着 source event schema 与 ordering keys 明确；snapshot/backfill 和 streaming replication 不丢不重；LSN/watermark/checkpoint 正确推进并可 replay；duplicate/out-of-order events 幂等；delete/tombstone 与 schema evolution/column rename/additive change 可处理；tenant filters 和 cross-tenant negatives 通过；warehouse/read-model row count、checksum、event count 与 aggregate reconciliation 一致；lag/stale checkpoint/DLQ/poison/sync failure monitoring 和 connector recovery 可证明；audit 与 local governance 都有证据。"
            ),
            "fake_done_risks": "必须阻断 green-sync-job-only、row-count-sample-only、dashboard-latest-only、out-of-order proof 缺失、replay duplicate negative 缺失、schema evolution fixture 缺失、tombstone proof 缺失、tenant negative 缺失、warehouse/read-model reconciliation 缺失、lag alert 缺失、connector recovery 缺失或本地治理跳过。",
            "evidence_preferences": (
                "优先 CDC contract、source event schema fixtures、out-of-order and duplicate replay negatives、checkpoint replay proof、snapshot/backfill with concurrent writes、delete/tombstone fixtures、schema-version / column rename fixtures、tenant isolation negatives、warehouse/read-model row/checksum/event/aggregate reconciliation queries、lag/stale checkpoint/DLQ/poison/failure alerts、connector restart/recovery artifacts、audit refs 和 local-governance evidence。每条 CDC claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "CDC Contract Inspector 先固定 proof targets；CDC Pipeline Builder 读取 contract handoff 后实现；"
                "Replication Evidence Inspector 与 Reconciliation Lag Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微 dashboard polish、额外表覆盖或非关键 provider/connector sample 可作为 Residual risk 留下并指定 owner/follow-up；缺少 ordering、checkpoint replay、idempotency、backfill、schema/tombstone、tenant isolation、reconciliation、lag alert、connector recovery、audit 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "复制一致性、回放幂等、租户隔离、目标对账、延迟告警和恢复证据优先于快速看到同步绿色；速度不能覆盖 dashboard-latest-only 或 row-count-sample-only。",
            "local_governance": (
                "若存在项目本地治理入口，CDC Contract Inspector 与 CDC Pipeline Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/data/operations/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "CDC Contract Inspector 固定 schema、ordering、checkpoint、backfill、schema/tombstone、tenant、reconciliation、lag、recovery、audit 和 governance targets；CDC Pipeline Builder 只基于 handoff 实现；Replication Evidence Inspector 反证乱序、重复回放、schema/tombstone、tenant 和 audit；Reconciliation Lag Inspector 验证对账、并发回填、lag/DLQ/target drift、connector recovery 和 monitoring；GateKeeper 对浅层 CDC proof fail closed。"
            ),
            "workflow_shape": (
                "采用 CDC Contract Inspector -> CDC Pipeline Builder -> [Replication Evidence Inspector + Reconciliation Lag Inspector] -> CDC Replication GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 cdc-replication、event-ordering、idempotency、schema-evolution、backfill-consistency、delete-tombstone、tenant-isolation、warehouse-reconciliation、monitoring、connector-recovery、audit-log、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；source database、CDC connector、event schema、warehouse/read model、tenant model、monitoring、audit 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque CDC replication consistency se prueba con schema, ordering, checkpoint replay, idempotency, backfill, tombstones, schema evolution, tenant isolation, reconciliation, lag monitoring, connector recovery, audit y governance.",
            "task_scope": f"Alcance limitado a CDC replication consistency: {task}; sin payment webhook, billing ledger, broad data platform ni sync-status UI.",
            "success_surface": "Éxito significa source event schema y ordering claros, snapshot/backfill y streaming sin loss/duplicates, checkpoint replay, idempotency, tombstones, schema evolution, tenant negatives, warehouse/read-model reconciliation, lag/DLQ/failure alerts, connector recovery, audit y governance probados.",
            "fake_done_risks": "Bloquear green-sync-job-only, row-count-sample-only, dashboard-latest-only, missing out-of-order, replay duplicate negative, schema evolution fixture, tombstone proof, tenant negative, reconciliation, lag alert, connector recovery o governance.",
            "evidence_preferences": "Preferir CDC contract, event fixtures, out-of-order/duplicate replay negatives, checkpoint replay, concurrent-write backfill, tombstones, schema-version fixtures, tenant negatives, reconciliation queries, lag/DLQ alerts, connector recovery, audit y governance.",
            "execution_strategy": "CDC Contract Inspector fija targets; CDC Pipeline Builder implementa; Replication Evidence y Reconciliation Lag inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de ordering, replay, idempotency, backfill, schema/tombstone, tenant isolation, reconciliation, lag alert, connector recovery, audit o governance fail closed.",
            "judgment_tradeoffs": "Replication consistency, replay idempotency, tenant isolation, reconciliation, lag alerts and recovery proof beat fast green sync.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Replication Evidence refuta ordering/replay/schema/tombstone/tenant/audit; Reconciliation Lag verifica reconciliation/backfill/lag/recovery; GateKeeper falla cerrado.",
            "workflow_shape": "CDC Contract Inspector -> CDC Pipeline Builder -> [Replication Evidence Inspector + Reconciliation Lag Inspector] -> CDC Replication GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; source database, CDC connector, event schema, warehouse/read model, tenant model, monitoring, audit y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because CDC replication / warehouse / read-model sync readiness is proven through source event schema, ordering, checkpoint replay, idempotency, snapshot/backfill, tombstones, schema evolution, tenant isolation, reconciliation, lag monitoring, connector recovery, audit, and governance evidence over staged handoffs. "
            "One Agent pass, a green sync job, sampled row count, or dashboard latest arrives too late to catch loss/duplicates, out-of-order handling gaps, replay duplication, schema/tombstone misses, tenant leakage, or target drift."
        ),
        "task_scope": (
            f"Scope stays on CDC replication consistency: {task}. The Loop should not expand into payment webhook, billing ledger, a broad data platform, backup restore, or merely a sync status UI."
        ),
        "success_surface": (
            "Success means source event schema and ordering keys are clear; snapshot/backfill and streaming replication avoid loss and duplicates; LSN/watermark/checkpoint advance correctly and support replay; duplicate and out-of-order events are idempotent; delete/tombstone and schema evolution/column rename/additive change are handled; tenant filters and cross-tenant negatives pass; warehouse/read-model row count, checksum, event count, and aggregate reconciliation match; lag, stale checkpoint, DLQ, poison event, sync failure monitoring, connector recovery, audit, and local governance all have evidence."
        ),
        "fake_done_risks": (
            "Block green-sync-job-only, row-count-sample-only, dashboard-latest-only, missing out-of-order proof, missing replay duplicate negative, missing schema evolution fixture, missing tombstone proof, missing tenant negative, missing warehouse/read-model reconciliation, missing lag alert, missing connector recovery, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer CDC contract proof, source event schema fixtures, out-of-order and duplicate replay negatives, checkpoint replay proof, snapshot/backfill with concurrent writes, delete/tombstone fixtures, schema-version / column rename fixtures, tenant isolation negatives, warehouse/read-model row/checksum/event/aggregate reconciliation queries, lag/stale checkpoint/DLQ/poison/failure alerts, connector restart/recovery artifacts, audit refs, and local-governance evidence. "
            "Classify each CDC claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "CDC Contract Inspector first freezes proof targets; CDC Pipeline Builder implements from that handoff; Replication Evidence Inspector and Reconciliation Lag Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard polish, extra table coverage, or non-critical provider/connector samples may remain only with owner/follow-up; missing ordering, checkpoint replay, idempotency, backfill, schema/tombstone, tenant isolation, reconciliation, lag alert, connector recovery, audit, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Replication consistency, replay idempotency, tenant isolation, target reconciliation, lag alerting, and recovery proof beats quickly seeing a green sync; speed cannot hide dashboard-latest-only or row-count-sample-only evidence."
        ),
        "local_governance": (
            "If project-local governance markers are present, CDC Contract Inspector and CDC Pipeline Builder read applicable rules, both parallel Inspectors verify related design/test/data/operations/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "CDC Contract Inspector freezes schema, ordering, checkpoint, backfill, schema/tombstone, tenant, reconciliation, lag, recovery, audit, and governance targets; CDC Pipeline Builder implements only from that handoff; Replication Evidence Inspector refutes out-of-order, duplicate replay, schema/tombstone, tenant, and audit gaps; Reconciliation Lag Inspector verifies reconciliation, concurrent-write backfill, lag/DLQ/target drift, connector recovery, and monitoring; GateKeeper fails closed on shallow CDC proof."
        ),
        "workflow_shape": (
            "Use CDC Contract Inspector -> CDC Pipeline Builder -> [Replication Evidence Inspector + Reconciliation Lag Inspector] -> CDC Replication GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries cdc-replication, event-ordering, idempotency, schema-evolution, backfill-consistency, delete-tombstone, tenant-isolation, warehouse-reconciliation, monitoring, connector-recovery, audit-log, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Source database, CDC connector, event schema, warehouse/read model, tenant model, monitoring, audit, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _metric_reporting_reconciliation_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 SaaS revenue metric reporting / MRR dashboard 的真实完成要通过 metric definition version、edge-case aggregation、FX/cutoff/timezone、billing ledger/invoice/provider reconciliation、locked-month backfill、permission segment、export parity、audit、monitoring 和 governance 证据分阶段证明；"
                "一次 Agent 执行、chart-only、CSV-only 或 provider-total-only 太晚发现指标口径漂移、旧月重写、权限越界或账务对不上。"
            ),
            "task_scope": f"范围固定为 revenue metric reporting reconciliation：{task}。不扩展成泛化 BI 平台、analytics experiment、payment webhook 或只做 dashboard polish。",
            "success_surface": (
                "成功意味着 MRR/ARR/churn/expansion/contraction/NRR definitions 和 metric definition version 固定；trial/coupon/discount/refund/proration/downgrade/upgrade/paused-subscription edge cases 正确；currency/FX-date、month cutoff 和 timezone 一致；billing ledger/invoice/subscription provider reconciliation 通过；dashboard/export parity 一致；historical backfill 不重写 locked months；revenue segment permission negatives 通过；metric definition version、backfill run、actor 和 reason audit 可追踪；monitoring 能发现 drift/reconciliation mismatch。"
            ),
            "fake_done_risks": "必须阻断 chart-only、CSV-only、provider-total-only、edge-case fixture 缺失、FX/cutoff/timezone proof 缺失、ledger/invoice/provider reconciliation 缺失、locked-month backfill proof 缺失、permission negative 缺失、audit trail 缺失、monitoring 缺失或本地治理跳过。",
            "evidence_preferences": (
                "优先 metric contract、metric definition version、MRR/ARR edge-case fixtures、FX-date/cutoff/timezone cases、billing ledger/invoice/provider reconciliation queries、dashboard/export parity checks、locked-month no-rewrite proof、backfill idempotency/rerun artifacts、revenue segment permission negatives、metric-version/backfill-run audit logs、drift alerts 和 local-governance evidence。每条 metric reporting claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Metric Contract Inspector 先固定 proof targets；Revenue Dashboard Builder 读取 contract handoff 后实现；"
                "Metric Reconciliation Inspector 与 Permission Backfill Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微 dashboard polish、额外指标覆盖或非关键 export 格式可作为 Residual risk 留下并指定 owner/follow-up；缺少 metric definition、edge fixtures、FX/cutoff/timezone、ledger reconciliation、locked-month backfill、permission negatives、audit、monitoring 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "指标口径、边界样本、账务对账、锁账回填、权限和审计证据优先于快速显示图表；速度不能覆盖 chart-only、CSV-only 或 provider-total-only。",
            "local_governance": (
                "若存在项目本地治理入口，Metric Contract Inspector 与 Revenue Dashboard Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/billing/reporting/permission/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Metric Contract Inspector 固定 definitions、edge cases、FX/cutoff/timezone、reconciliation、locked backfill、permission、export、audit 和 governance targets；Revenue Dashboard Builder 只基于 handoff 实现；Metric Reconciliation Inspector 反证 edge aggregation、FX/cutoff/timezone、ledger/provider reconciliation、export parity 和 drift；Permission Backfill Inspector 验证 segment negatives、locked-month no-rewrite、backfill idempotency 和 audit；GateKeeper 对浅层 reporting proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Metric Contract Inspector -> Revenue Dashboard Builder -> [Metric Reconciliation Inspector + Permission Backfill Inspector] -> Metric Reporting GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 metric-reconciliation、ledger-reconciliation、metric-definition、edge-case-aggregation、fx-cutoff-timezone、locked-backfill、permission-auth、tenant-isolation、data-export、audit-log、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；billing ledger、invoice/subscription provider、metrics store、dashboard/export layer、permission model、audit、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque revenue metric reporting se prueba con metric version, edge cases, FX/cutoff/timezone, ledger/provider reconciliation, locked backfill, permissions, exports, audit, monitoring y governance.",
            "task_scope": f"Alcance limitado a revenue metric reporting reconciliation: {task}; sin broad BI platform, analytics experiment, payment webhook ni dashboard polish.",
            "success_surface": "Éxito significa definitions/version, edge cases, FX-date, cutoff/timezone, ledger/invoice/provider reconciliation, dashboard/export parity, locked-month backfill, permission negatives, audit y drift monitoring probados.",
            "fake_done_risks": "Bloquear chart-only, CSV-only, provider-total-only, missing edge cases, FX/cutoff/timezone, reconciliation, locked-month backfill, permission negative, audit, monitoring o governance.",
            "evidence_preferences": "Preferir metric contract, version, edge fixtures, FX/cutoff/timezone, reconciliation queries, export parity, locked-month proof, backfill idempotency, permission negatives, audit logs, drift alerts y governance.",
            "execution_strategy": "Metric Contract Inspector fija targets; Revenue Dashboard Builder implementa; Metric Reconciliation y Permission Backfill inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de definitions, edge fixtures, FX/cutoff, reconciliation, locked backfill, permissions, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Metric definitions, edge cases, reconciliation, locked backfill, permissions and audit beat fast charts.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Metric Reconciliation refuta edge/reconciliation/export/drift; Permission Backfill verifica permissions/backfill/audit; GateKeeper falla cerrado.",
            "workflow_shape": "Metric Contract Inspector -> Revenue Dashboard Builder -> [Metric Reconciliation Inspector + Permission Backfill Inspector] -> Metric Reporting GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; ledger, provider, metrics store, dashboard/export layer, permissions, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because SaaS revenue metric reporting / MRR dashboard readiness is proven through metric definition version, edge-case aggregation, FX/cutoff/timezone, billing ledger/invoice/provider reconciliation, locked-month backfill, permission segments, export parity, audit, monitoring, and governance evidence over staged handoffs. "
            "One Agent pass, chart-only, CSV-only, or provider-total-only proof arrives too late to catch metric-definition drift, locked-month rewrites, permission leakage, or unreconciled revenue."
        ),
        "task_scope": (
            f"Scope stays on revenue metric reporting reconciliation: {task}. The Loop should not expand into a broad BI platform, analytics experiment, payment webhook, or merely dashboard polish."
        ),
        "success_surface": (
            "Success means MRR/ARR/churn/expansion/contraction/NRR definitions and metric definition version are fixed; trial/coupon/discount/refund/proration/downgrade/upgrade/paused-subscription edge cases are correct; currency/FX-date, month cutoff, and timezone are consistent; billing ledger/invoice/subscription provider reconciliation passes; dashboard/export parity holds; historical backfill does not rewrite locked months; revenue segment permission negatives pass; metric definition version, backfill run, actor, and reason audit are traceable; monitoring detects drift and reconciliation mismatch."
        ),
        "fake_done_risks": (
            "Block chart-only, CSV-only, provider-total-only, missing edge-case fixture, missing FX/cutoff/timezone proof, missing ledger/invoice/provider reconciliation, missing locked-month backfill proof, missing permission negative, missing audit trail, missing monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer metric contract proof, metric definition version, MRR/ARR edge-case fixtures, FX-date/cutoff/timezone cases, billing ledger/invoice/provider reconciliation queries, dashboard/export parity checks, locked-month no-rewrite proof, backfill idempotency/rerun artifacts, revenue segment permission negatives, metric-version/backfill-run audit logs, drift alerts, and local-governance evidence. "
            "Classify each metric reporting claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Metric Contract Inspector first freezes proof targets; Revenue Dashboard Builder implements from that handoff; Metric Reconciliation Inspector and Permission Backfill Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard polish, extra metric coverage, or non-critical export formatting may remain only with owner/follow-up; missing metric definition, edge fixtures, FX/cutoff/timezone, ledger reconciliation, locked-month backfill, permission negatives, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Metric definitions, edge fixtures, revenue reconciliation, locked backfill, permissions, and audit proof beats quickly showing charts; speed cannot hide chart-only, CSV-only, or provider-total-only evidence."
        ),
        "local_governance": (
            "If project-local governance markers are present, Metric Contract Inspector and Revenue Dashboard Builder read applicable rules, both parallel Inspectors verify related design/test/billing/reporting/permission/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Metric Contract Inspector freezes definitions, edge cases, FX/cutoff/timezone, reconciliation, locked backfill, permission, export, audit, and governance targets; Revenue Dashboard Builder implements only from that handoff; Metric Reconciliation Inspector refutes edge aggregation, FX/cutoff/timezone, ledger/provider reconciliation, export parity, and drift; Permission Backfill Inspector verifies segment negatives, locked-month no-rewrite, backfill idempotency, and audit; GateKeeper fails closed on shallow reporting proof."
        ),
        "workflow_shape": (
            "Use Metric Contract Inspector -> Revenue Dashboard Builder -> [Metric Reconciliation Inspector + Permission Backfill Inspector] -> Metric Reporting GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries metric-reconciliation, ledger-reconciliation, metric-definition, edge-case-aggregation, fx-cutoff-timezone, locked-backfill, permission-auth, tenant-isolation, data-export, audit-log, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Billing ledger, invoice/subscription provider, metrics store, dashboard/export layer, permission model, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _payout_settlement_reconciliation_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 marketplace seller payout settlement 的真实完成要通过 seller ledger、fee/tax/hold 计算、batch cutoff/FX、provider/bank reconciliation、failed payout/reversal/double-payout idempotency、tenant access、audit、monitoring 和 governance 证据分阶段证明；"
                "一次 Agent 执行、dashboard paid、一笔 test payout 或 UI balance decrease 太晚发现重复打款、账务不平、租户串数或审计缺口。"
            ),
            "task_scope": f"范围固定为 payout settlement reconciliation：{task}。不扩展成 KYC/KYB onboarding、dispute lifecycle、payment webhook 或只做 payout UI polish。",
            "success_surface": (
                "成功意味着 captured/refunded/chargeback orders 都进入 seller balance ledger；platform fee、tax、adjustment、hold/reserve、negative balance 正确；payout batch cutoff、timezone、currency、FX rounding 一致；provider transfer id、bank account、KYC hold、failed payout retry、reversal 和 double-payout prevention 幂等；provider payout report、本地 ledger、invoice、bank statement 可对账；seller/tenant access 隔离；audit records 含 payout batch id、ledger entry id、provider transfer id、actor、failure reason；monitoring 能发现 stuck payout、failed transfer 和 reconciliation mismatch。"
            ),
            "fake_done_risks": "必须阻断 dashboard-paid-only、test-payout-only、UI-balance-only、seller ledger proof 缺失、failed/reversal negative 缺失、double-payout negative 缺失、provider-bank reconciliation 缺失、tenant negative 缺失、audit trail 缺失、monitoring 缺失或本地治理跳过。",
            "evidence_preferences": (
                "优先 payout contract、seller ledger fixtures、fee/tax/hold calculation cases、batch cutoff/timezone/currency/FX cases、provider payout report/local ledger/invoice/bank statement reconciliation、failed payout retry/reversal artifacts、double-payout negatives、tenant access negatives、audit records、monitoring alerts 和 local-governance evidence。每条 payout settlement claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Payout Contract Inspector 先固定 proof targets；Payout Settlement Builder 读取 contract handoff 后实现；"
                "Settlement Reconciliation Inspector 与 Access Idempotency Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微 payout UI polish、额外 provider sample 或非核心报表格式可作为 Residual risk 留下并指定 owner/follow-up；缺少 seller ledger、failed/reversal negatives、double-payout negatives、provider-bank reconciliation、tenant negatives、audit、monitoring 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "seller ledger、provider/bank reconciliation、double-payout prevention、tenant isolation、audit 和 monitoring 证据优先于快速显示 payout paid。",
            "local_governance": (
                "若存在项目本地治理入口，Payout Contract Inspector 与 Payout Settlement Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/payments/ledger/permission/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Payout Contract Inspector 固定 seller ledger、batch、provider/bank reconciliation、idempotency、tenant、audit 和 governance targets；Payout Settlement Builder 只基于 handoff 实现；Settlement Reconciliation Inspector 反证 ledger/calculation/cutoff/FX/provider-bank/alerts；Access Idempotency Inspector 验证 tenant negatives、retry/reversal/double-payout、KYC hold 和 audit；GateKeeper 对浅层 payout proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Payout Contract Inspector -> Payout Settlement Builder -> [Settlement Reconciliation Inspector + Access Idempotency Inspector] -> Payout Settlement GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 payout-settlement、ledger-reconciliation、provider-bank-reconciliation、idempotency、double-payout、tenant-isolation、audit-log、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；payout provider、seller ledger、invoice、bank statement、tenant model、audit、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque payout settlement se prueba con seller ledger, cutoff/FX, provider/bank reconciliation, retry/reversal, double-payout negatives, tenant access, audit, monitoring y governance.",
            "task_scope": f"Alcance limitado a payout settlement reconciliation: {task}; sin KYC onboarding, dispute lifecycle, payment webhook ni UI polish.",
            "success_surface": "Éxito significa seller ledger, fee/tax/hold, cutoff/timezone/currency/FX, provider transfer/bank reconciliation, retry/reversal/double-payout, tenant isolation, audit y monitoring probados.",
            "fake_done_risks": "Bloquear dashboard-paid-only, test-payout-only, UI-balance-only, missing seller ledger, failed/reversal negative, double-payout negative, reconciliation, tenant negative, audit, monitoring o governance.",
            "evidence_preferences": "Preferir payout contract, ledger fixtures, calculation cases, cutoff/FX cases, reconciliation, retry/reversal artifacts, double-payout negatives, tenant negatives, audit logs, alerts y governance.",
            "execution_strategy": "Payout Contract Inspector fija targets; Payout Settlement Builder implementa; Settlement Reconciliation y Access Idempotency inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de ledger, failed/reversal, double-payout, reconciliation, tenant, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Ledger, bank/provider reconciliation, double-payout prevention, tenant isolation, audit y monitoring superan payout paid rápido.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Reconciliation refuta ledger/cutoff/reconciliation; Access Idempotency verifica tenant/retry/reversal/audit; GateKeeper falla cerrado.",
            "workflow_shape": "Payout Contract Inspector -> Payout Settlement Builder -> [Settlement Reconciliation Inspector + Access Idempotency Inspector] -> Payout Settlement GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; provider, ledger, invoices, bank statements, tenants, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because marketplace seller payout settlement readiness is proven through seller balance ledger, fee/tax/hold calculation, batch cutoff/FX, provider/bank reconciliation, failed payout retry, reversal idempotency, double-payout prevention, tenant access, audit, monitoring, and governance evidence over staged handoffs. "
            "One Agent pass, dashboard paid, one test payout, or UI balance decrease arrives too late to catch double payouts, unreconciled money movement, tenant leakage, or missing auditability."
        ),
        "task_scope": (
            f"Scope stays on payout settlement reconciliation: {task}. The Loop should not expand into KYC/KYB onboarding, dispute lifecycle, payment webhook, or payout UI polish."
        ),
        "success_surface": (
            "Success means captured/refunded/chargeback orders enter the seller balance ledger; platform fee, tax, adjustment, hold/reserve, and negative balance rules are correct; payout batch cutoff, timezone, currency, and FX rounding are consistent; provider transfer id, bank account, KYC hold, failed payout retry, reversal, and double-payout prevention are idempotent; provider payout report, local ledger, invoice, and bank statement reconcile; seller/tenant access is isolated; audit records include payout batch id, ledger entry id, provider transfer id, actor, and failure reason; monitoring detects stuck payout, failed transfer, and reconciliation mismatch."
        ),
        "fake_done_risks": (
            "Block dashboard-paid-only, test-payout-only, UI-balance-only, missing seller ledger proof, missing failed/reversal negative, missing double-payout negative, missing provider-bank reconciliation, missing tenant negative, missing audit trail, missing monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer payout contract proof, seller ledger fixtures, fee/tax/hold calculation cases, batch cutoff/timezone/currency/FX cases, provider payout report/local ledger/invoice/bank statement reconciliation, failed payout retry/reversal artifacts, double-payout negatives, tenant access negatives, audit records, monitoring alerts, and local-governance evidence. "
            "Classify each payout settlement claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Payout Contract Inspector first freezes proof targets; Payout Settlement Builder implements from that handoff; Settlement Reconciliation Inspector and Access Idempotency Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor payout UI polish, extra provider samples, or non-critical report formatting may remain only with owner/follow-up; missing seller ledger, failed/reversal negatives, double-payout negatives, provider-bank reconciliation, tenant negatives, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Seller ledger, provider/bank reconciliation, double-payout prevention, tenant isolation, audit, and monitoring proof beats quickly showing payout paid."
        ),
        "local_governance": (
            "If project-local governance markers are present, Payout Contract Inspector and Payout Settlement Builder read applicable rules, both parallel Inspectors verify related design/test/payments/ledger/permission/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Payout Contract Inspector freezes seller ledger, batch, provider/bank reconciliation, idempotency, tenant, audit, and governance targets; Payout Settlement Builder implements only from that handoff; Settlement Reconciliation Inspector refutes ledger, calculation, cutoff/FX, provider-bank reconciliation, and alerts; Access Idempotency Inspector verifies tenant negatives, failed payout retry, reversal idempotency, double-payout prevention, KYC hold, and audit; GateKeeper fails closed on shallow payout proof."
        ),
        "workflow_shape": (
            "Use Payout Contract Inspector -> Payout Settlement Builder -> [Settlement Reconciliation Inspector + Access Idempotency Inspector] -> Payout Settlement GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries payout-settlement, ledger-reconciliation, provider-bank-reconciliation, idempotency, double-payout, tenant-isolation, audit-log, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Payout provider, seller ledger, invoices, bank statements, tenant model, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _analytics_experiment_instrumentation_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 analytics instrumentation / A-B experiment exposure 的真实完成要通过 event schema、identity merge、dedupe/offline replay、consent/PII、experiment assignment/exposure、warehouse/dashboard reconciliation、monitoring、migration 和 governance 证据分阶段证明；"
                "一次 Agent 执行、button-click-only、console-log-only 或 mock analytics call 太晚发现重复上报、实验污染、PII 泄露或数仓对不上。"
            ),
            "task_scope": f"范围固定为 analytics instrumentation / experiment exposure：{task}。不扩展成 notification deliverability、feature-flag rollout、宽泛 analytics platform 或只发一个事件。",
            "success_surface": (
                "成功意味着 signup funnel events 符合 versioned schema；anonymous/logged-in identity merge 不重复计数；retry、refresh、offline replay 和 SDK callbacks 不重复上报；consent denial 抑制 PII/tracking；experiment assignment、exposure、variant、holdout 和 reassignment 行为一致；warehouse/dashboard queries 与 raw events 和 assignment logs 可对账；monitoring 能发现 event drift、missing exposure、duplicate spikes 和 schema mismatch。"
            ),
            "fake_done_risks": "必须阻断 button-click-only、console-log-only、mock analytics call、one provider accepted event、warehouse reconciliation 缺失、consent negative 缺失、duplicate/offline replay negative 缺失、experiment exposure 当后续、monitoring 缺失或本地治理跳过。",
            "evidence_preferences": (
                "优先 versioned event schema fixtures、real payload assertions、identity merge/double-count negatives、retry/refresh/offline replay/SDK callback duplicate negatives、consent-denied PII suppression、assignment/exposure/variant/holdout proofs、raw-event warehouse/dashboard reconciliation、drift/missing exposure/duplicate spike/schema mismatch alerts、migration compatibility 和 local-governance evidence。每条 analytics / experiment claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Instrumentation Contract Inspector 先固定 proof targets；Tracking Builder 读取 contract handoff 后实现；"
                "Event Integrity Inspector 与 Experiment Consistency Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微 dashboard polish、额外事件覆盖或非关键 provider sample 可作为 Residual risk 留下并指定 owner/follow-up；缺少 schema、identity、dedupe、consent、experiment exposure、reconciliation、monitoring、migration 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "事件完整性、实验一致性、去重反证、隐私/consent、数仓对账和监控证据优先于快速打点；速度不能覆盖 console.log、mock analytics 或 provider-accepted-only。",
            "local_governance": (
                "若存在项目本地治理入口，Instrumentation Contract Inspector 与 Tracking Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/privacy/analytics/i18n/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Instrumentation Contract Inspector 固定 schema、identity、consent、retry/offline、experiment 和 reconciliation targets；Tracking Builder 只基于 handoff 实现；Event Integrity Inspector 反证 payload/schema/dedupe/identity/consent/reconciliation；Experiment Consistency Inspector 验证 assignment/exposure/variant/holdout/restart-device/reassignment/alerts；GateKeeper 对浅层 analytics proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Instrumentation Contract Inspector -> Tracking Builder -> [Event Integrity Inspector + Experiment Consistency Inspector] -> Analytics Experiment GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 event-integrity、experiment-assignment、idempotency、identity-merge、privacy-redaction、warehouse-reconciliation、monitoring、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；analytics SDK、event pipeline、warehouse/dashboard、experiment store、consent layer、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque instrumentation y experiment exposure se prueban con schema, identity merge, dedupe/offline replay, consent/PII, assignment/exposure, reconciliation, monitoring, migration y governance.",
            "task_scope": f"Alcance limitado a analytics instrumentation / experiment exposure: {task}; sin notification deliverability ni broad analytics platform.",
            "success_surface": "Éxito significa event schema versionado, identity merge sin double count, retry/offline replay sin duplicados, consent/PII suppression, assignment/exposure/variant/holdout consistency, warehouse/dashboard reconciliation y monitoring probados.",
            "fake_done_risks": "Bloquear button-click-only, console-log-only, mock analytics, one provider event, missing reconciliation, consent negative, duplicate/offline replay negative, exposure follow-up, monitoring o governance.",
            "evidence_preferences": "Preferir schema fixtures, payload assertions, identity/dedupe negatives, consent PII suppression, assignment/exposure proofs, raw-event reconciliation, alerts, migration y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Instrumentation Contract Inspector fija targets; Tracking Builder implementa; Event Integrity y Experiment Consistency inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de schema, identity, dedupe, consent, exposure, reconciliation, monitoring, migration o governance fail closed.",
            "judgment_tradeoffs": "Event integrity, experiment consistency, dedupe, consent/privacy, warehouse reconciliation and monitoring beat fast event sending.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Event Integrity refuta payload/schema/dedupe/identity/consent/reconciliation; Experiment Consistency verifica assignment/exposure; GateKeeper falla cerrado.",
            "workflow_shape": "Instrumentation Contract Inspector -> Tracking Builder -> [Event Integrity Inspector + Experiment Consistency Inspector] -> Analytics Experiment GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; SDK, pipeline, warehouse, experiment store, consent, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because analytics instrumentation / A-B experiment exposure is proven through event schema, identity merge, dedupe/offline replay, consent/PII boundaries, experiment assignment/exposure, raw-event warehouse/dashboard reconciliation, monitoring, migration, and governance evidence over staged handoffs. "
            "One Agent pass, button-click-only, console-log-only, or mock analytics calls arrive too late to catch duplicate reporting, experiment pollution, PII leaks, or unreconciled warehouse data."
        ),
        "task_scope": (
            f"Scope stays on analytics instrumentation / experiment exposure: {task}. The Loop should not expand into notification deliverability, feature-flag rollout, a broad analytics platform, or merely sending one event."
        ),
        "success_surface": (
            "Success means signup funnel events match a versioned schema; anonymous/logged-in identities merge without double counting; retries, refreshes, offline replay, and SDK callbacks do not duplicate events; consent denial suppresses PII/tracking; experiment assignment, exposure, variant, holdout, and reassignment behavior are consistent; warehouse/dashboard queries reconcile with raw events and assignment logs; monitoring detects event drift, missing exposure, duplicate spikes, and schema version mismatch."
        ),
        "fake_done_risks": (
            "Block button-click-only, console-log-only, mock analytics calls, one provider accepted event, missing warehouse reconciliation, missing consent negative, missing duplicate/offline replay negative, experiment exposure as follow-up, missing monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer versioned event schema fixtures, real payload assertions, identity merge and double-count negatives, retry/refresh/offline replay/SDK callback duplicate negatives, consent-denied PII suppression, assignment/exposure/variant/holdout proofs, raw-event warehouse/dashboard reconciliation, drift/missing exposure/duplicate spike/schema mismatch alerts, migration compatibility, and local-governance evidence. "
            "Classify each analytics / experiment claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Instrumentation Contract Inspector first freezes proof targets; Tracking Builder implements from that handoff; Event Integrity Inspector and Experiment Consistency Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard polish, additional event coverage, or non-critical provider samples may remain only with owner/follow-up; missing schema, identity, dedupe, consent, experiment exposure, reconciliation, monitoring, migration, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Event integrity, experiment consistency, duplicate negatives, privacy/consent, warehouse reconciliation, and monitoring proof beats quickly firing events; speed cannot hide console.log, mock analytics, or provider-accepted-only evidence."
        ),
        "local_governance": (
            "If project-local governance markers are present, Instrumentation Contract Inspector and Tracking Builder read applicable rules, both parallel Inspectors verify related design/test/privacy/analytics/i18n/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Instrumentation Contract Inspector freezes schema, identity, consent, retry/offline, experiment, and reconciliation targets; Tracking Builder implements only from that handoff; Event Integrity Inspector refutes payload/schema/dedupe/identity/consent/reconciliation; Experiment Consistency Inspector verifies assignment/exposure/variant/holdout/restart-device/reassignment/alerts; GateKeeper fails closed on shallow analytics proof."
        ),
        "workflow_shape": (
            "Use Instrumentation Contract Inspector -> Tracking Builder -> [Event Integrity Inspector + Experiment Consistency Inspector] -> Analytics Experiment GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries event-integrity, experiment-assignment, idempotency, identity-merge, privacy-redaction, warehouse-reconciliation, monitoring, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Analytics SDK, event pipeline, warehouse/dashboard, experiment store, consent layer, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _schedule_timezone_recurrence_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 weekly digest schedule / timezone recurrence 的真实完成要通过 timezone conversion、DST boundary、missed-run catch-up、retry/provider replay idempotency、subscription/disabled/tenant/locale filtering、provider delivery reconciliation、audit fields、monitoring、migration 和 governance 证据分阶段证明；"
                "cron expression、本地触发一次、UTC-only 或 provider accepted 太晚发现错时发送、漏补、重复发送、退订误发或不可审计调度。"
            ),
            "task_scope": f"范围固定为 weekly digest schedule/timezone recurrence：{task}。不扩展成普通 notification deliverability、usage quota reset、宽泛 queue platform 或只配置 cron。",
            "success_surface": (
                "成功意味着每个用户按自己的 timezone 本地周一 09:00 收到；DST spring-forward/fall-back 前后不提前不延后；missed-run catch-up 只补一次；retry/provider replay 不重复发送；unsubscribe、disabled user、tenant 和 locale filters 不误发；provider accepted/delivered/failure 与本地 audit 可对账；scheduled_at、due_at、sent_at、skipped_reason、timezone_version、job_run_id、monitoring、migration 和 local governance 可审计。"
            ),
            "fake_done_risks": "必须阻断 cron expression only、本地触发一次、UTC-only、single-timezone-only、provider-accepted-only、DST boundary 缺失、catch-up/idempotency negative 缺失、unsubscribe/disabled negative 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过。",
            "evidence_preferences": (
                "优先 multi-timezone fixtures、DST spring-forward/fall-back boundary cases、missed-run catch-up artifacts、retry/provider replay duplicate negatives、timezone database/version drift proof、unsubscribe/disabled/tenant/locale negatives、provider delivery/failure reconciliation、audit field samples、monitoring alerts、migration compatibility 和 local-governance evidence。每条 schedule claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Schedule Contract Inspector 先固定 proof targets；Digest Scheduler Builder 读取 contract handoff 后实现；"
                "Temporal Correctness Inspector 与 Delivery Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微 digest copy、额外 locale coverage 或非关键 provider sample 可作为 Residual risk 留下并指定 owner/follow-up；缺少 timezone/DST、catch-up、idempotency、subscription/disabled negative、provider reconciliation、audit、monitoring、migration 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "时间语义、DST/catch-up 正确性、重复发送反证、退订/禁用保护、审计和监控证据优先于快速配置 cron；速度不能覆盖 UTC-only、single-timezone-only 或 provider-accepted-only。",
            "local_governance": (
                "若存在项目本地治理入口，Schedule Contract Inspector 与 Digest Scheduler Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/timezone/i18n/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Schedule Contract Inspector 固定 timezone、DST、catch-up、idempotency、filter、provider、audit、monitoring 和 migration targets；Digest Scheduler Builder 只基于 handoff 实现；Temporal Correctness Inspector 反证 timezone/DST/catch-up/replay；Delivery Audit Inspector 验证 subscription/provider/audit/monitoring/compatibility/governance；GateKeeper 对浅层 schedule 证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Schedule Contract Inspector -> Digest Scheduler Builder -> [Temporal Correctness Inspector + Delivery Audit Inspector] -> Schedule GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 timezone-recurrence、subscription-deliverability、message-delivery、provider-contract、idempotency、retry-timeout、queue-recovery、locale-i18n、audit-log、monitoring、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；scheduler、timezone library/database、queue/provider、subscription store、audit writer、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque schedule/timezone recurrence se prueba por timezone, DST, catch-up, idempotency, filters, provider reconciliation, audit, monitoring, migration y governance.",
            "task_scope": f"Alcance limitado a weekly digest schedule/timezone recurrence: {task}; sin notification genérica, quota reset ni solo cron.",
            "success_surface": "Éxito significa local Monday 09:00 por timezone, DST correcto, catch-up una vez, replay sin duplicados, filtros subscription/disabled/tenant/locale, provider/local audit reconciliation, audit fields, monitoring, migration y governance probados.",
            "fake_done_risks": "Bloquear cron-only, local-trigger-only, UTC-only, single-timezone-only, provider-accepted-only, missing DST, catch-up/idempotency, subscription negatives, audit/monitoring, migration o governance.",
            "evidence_preferences": "Preferir fixtures multi-timezone, DST, catch-up, replay duplicate negatives, timezone version drift, filter negatives, provider reconciliation, audit samples, alerts, migration y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Schedule Contract Inspector fija targets; Digest Scheduler Builder implementa; Temporal Correctness y Delivery Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de timezone/DST, catch-up, idempotency, filter negatives, reconciliation, audit, monitoring, migration o governance fail closed.",
            "judgment_tradeoffs": "Time semantics, DST/catch-up correctness, duplicate negatives, filtering, audit and monitoring beat fast cron setup.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Temporal refuta timezone/DST/catch-up/replay; Delivery Audit verifica filters/provider/audit/monitoring; GateKeeper falla cerrado.",
            "workflow_shape": "Schedule Contract Inspector -> Digest Scheduler Builder -> [Temporal Correctness Inspector + Delivery Audit Inspector] -> Schedule GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; scheduler, timezone DB, queue/provider, subscriptions, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because weekly digest schedule / timezone recurrence readiness is proven through timezone conversion, DST boundaries, missed-run catch-up, retry/provider replay idempotency, subscription/disabled/tenant/locale filtering, provider delivery reconciliation, audit fields, monitoring, migration, and governance evidence over staged handoffs. "
            "A cron expression, one local trigger, UTC-only proof, or provider accepted status arrives too late to catch wrong local-time sends, missed catch-up, duplicate sends, unsubscribed delivery, or unauditable scheduling."
        ),
        "task_scope": (
            f"Scope stays on weekly digest schedule/timezone recurrence: {task}. The Loop should not expand into generic notification deliverability, usage quota reset, broad queue-platform work, or merely configuring cron."
        ),
        "success_surface": (
            "Success means each user receives at local Monday 09:00 in their timezone; DST spring-forward/fall-back boundaries are not early or late; missed-run catch-up happens once; retry/provider replay does not duplicate sends; unsubscribe, disabled-user, tenant, and locale filters suppress correctly; provider accepted/delivered/failure events reconcile with local audit; scheduled_at, due_at, sent_at, skipped_reason, timezone_version, job_run_id, monitoring, migration, and local governance are reviewable."
        ),
        "fake_done_risks": (
            "Block cron-expression-only, local-trigger-only, UTC-only, single-timezone-only, provider-accepted-only, missing DST boundary, missing catch-up/idempotency negative, missing unsubscribe/disabled negative, missing audit/monitoring, missing migration, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer multi-timezone fixtures, DST spring-forward/fall-back boundary cases, missed-run catch-up artifacts, retry/provider replay duplicate negatives, timezone database/version drift proof, unsubscribe/disabled/tenant/locale negatives, provider delivery/failure reconciliation, audit field samples, monitoring alerts, migration compatibility, and local-governance evidence. "
            "Classify each schedule claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Schedule Contract Inspector first freezes proof targets; Digest Scheduler Builder implements from that handoff; Temporal Correctness Inspector and Delivery Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor digest copy, extra locale coverage, or non-critical provider samples may remain only with owner/follow-up; missing timezone/DST, catch-up, idempotency, subscription/disabled negatives, provider reconciliation, audit, monitoring, migration, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Time semantics, DST/catch-up correctness, duplicate-send negatives, unsubscribe/disabled protection, audit, and monitoring proof beats quickly configuring cron; speed cannot hide UTC-only, single-timezone-only, or provider-accepted-only evidence."
        ),
        "local_governance": (
            "If project-local governance markers are present, Schedule Contract Inspector and Digest Scheduler Builder read applicable rules, both parallel Inspectors verify related design/test/timezone/i18n/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Schedule Contract Inspector freezes timezone, DST, catch-up, idempotency, filter, provider, audit, monitoring, and migration targets; Digest Scheduler Builder implements only from that handoff; Temporal Correctness Inspector refutes timezone/DST/catch-up/replay; Delivery Audit Inspector verifies subscription/provider/audit/monitoring/compatibility/governance; GateKeeper fails closed on shallow schedule proof."
        ),
        "workflow_shape": (
            "Use Schedule Contract Inspector -> Digest Scheduler Builder -> [Temporal Correctness Inspector + Delivery Audit Inspector] -> Schedule GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries timezone-recurrence, subscription-deliverability, message-delivery, provider-contract, idempotency, retry-timeout, queue-recovery, locale-i18n, audit-log, monitoring, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Scheduler, timezone library/database, queue/provider, subscription store, audit writer, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _notification_subscription_deliverability_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 lifecycle campaign email / notification deliverability 的真实完成要通过 subscription eligibility、unsubscribe/preference suppression、bounce/complaint/drop events、provider delivery audit reconciliation、duplicate retry/replay negatives、locale/template safety、PII/token redaction、monitoring、migration 和 governance 证据分阶段证明；"
                "one test email、provider accepted、UI toggle 或 docs-only unsubscribe 太晚发现错发、重复发送、退订失效、PII 泄露或不可对账投递。"
            ),
            "task_scope": f"范围固定为 notification subscription-deliverability：{task}。不扩展成 usage/quota metering、普通 webhook 接入、宽泛 provider platform 或只发一封邮件。",
            "success_surface": (
                "成功意味着只有 subscribed eligible users 收到 campaign；unsubscribe 和 preference center 生效；suppression list、bounce、complaint、drop、disabled user、tenant 和 locale filters 正确；retry/provider replay 不重复发送；provider accepted/delivered/bounced/complained/dropped events 与本地 delivery audit 可对账；English/Chinese template variables 安全渲染且 PII/tokens 不泄露；rate limit、retry/backoff、DLQ/manual replay、monitoring、audit reason codes、migration 和 local governance 都可审计。"
            ),
            "fake_done_risks": "必须阻断 one-test-email、provider-accepted-only、UI-toggle-only、happy-path-send-only、docs-only unsubscribe、bounce/complaint proof 缺失、duplicate negative 缺失、locale/template proof 缺失、PII redaction 缺失、audit reconciliation 缺失、monitoring 缺失、migration 缺失或本地治理跳过。",
            "evidence_preferences": (
                "优先 subscription/preference/unsubscribe/suppression fixtures、bounce/complaint/drop provider events、本地 delivery audit reconciliation、duplicate retry/replay negatives、disabled-user/tenant negatives、English/Chinese template fallback、PII/token redaction checks、DLQ/manual replay、monitoring alerts、migration compatibility 和 local-governance evidence。每条 notification deliverability claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Notification Contract Inspector 先固定 proof targets；Campaign Email Builder 读取 contract handoff 后实现；"
                "Deliverability Evidence Inspector 与 Template Privacy Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微 copy、额外 template coverage 或非关键 provider sample 可作为 Residual risk 留下并指定 owner/follow-up；缺少 subscription、suppression、bounce/complaint、duplicate、locale/template、redaction、audit reconciliation、monitoring、migration 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "订阅正确性、退订保护、投递对账、模板隐私、重复发送反证和监控证据优先于快速发出一封邮件；速度不能覆盖 provider-accepted-only 或 happy-path-send-only。",
            "local_governance": (
                "若存在项目本地治理入口，Notification Contract Inspector 与 Campaign Email Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/privacy/i18n/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Notification Contract Inspector 固定 subscription、preference、provider event、locale、privacy、retry/DLQ、audit、monitoring targets；Campaign Email Builder 只基于 handoff 实现；Deliverability Evidence Inspector 反证 subscription/suppression/provider reconciliation/duplicate replay；Template Privacy Inspector 验证 locale/template/redaction/audit/compatibility/governance；GateKeeper 对浅层投递证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Notification Contract Inspector -> Campaign Email Builder -> [Deliverability Evidence Inspector + Template Privacy Inspector] -> Notification Deliverability GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 subscription-deliverability、message-delivery、provider-contract、idempotency、retry-timeout、queue-recovery、privacy-redaction、locale-i18n、audit-log、monitoring、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；mailer/provider、subscription store、template/i18n layer、audit writer、queue/DLQ、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque notification deliverability se prueba por subscription, unsubscribe/preference, suppression, provider events, duplicate replay, locale/templates, redaction, audit reconciliation, monitoring, migration y governance.",
            "task_scope": f"Alcance limitado a notification subscription-deliverability: {task}; sin usage/quota ni provider platform amplio.",
            "success_surface": "Éxito significa subscribed eligibility, unsubscribe/preferences, suppression, bounce/complaint/drop, provider/local audit reconciliation, duplicate replay negatives, locale/templates, redaction, retry/DLQ, monitoring, migration y governance probados.",
            "fake_done_risks": "Bloquear one-test-email, provider-accepted-only, UI-toggle-only, happy-path, docs-only unsubscribe, missing bounce/complaint, duplicate, locale/template, redaction, audit reconciliation, monitoring, migration o governance.",
            "evidence_preferences": "Preferir subscription fixtures, provider events, audit reconciliation, duplicate replay negatives, tenant/disabled negatives, locale templates, redaction, DLQ/manual replay, monitoring, migration y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Notification Contract Inspector fija targets; Campaign Email Builder implementa; Deliverability Evidence y Template Privacy inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de subscription, suppression, bounce/complaint, duplicate, locale/template, redaction, audit reconciliation, monitoring, migration o governance fail closed.",
            "judgment_tradeoffs": "Subscription correctness, unsubscribe protection, reconciliation, template privacy, duplicate negatives and monitoring beat fast one-email sending.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Deliverability refuta subscription/provider/duplicate; Template Privacy verifica locale/redaction/audit; GateKeeper falla cerrado.",
            "workflow_shape": "Notification Contract Inspector -> Campaign Email Builder -> [Deliverability Evidence Inspector + Template Privacy Inspector] -> Notification Deliverability GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; provider, subscription store, templates, audit, queue/DLQ, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because lifecycle campaign email / notification deliverability is proven through subscription eligibility, unsubscribe/preference suppression, bounce/complaint/drop events, provider delivery audit reconciliation, duplicate retry/replay negatives, locale/template safety, PII/token redaction, monitoring, migration, and governance evidence over staged handoffs. "
            "One test email, provider accepted status, a UI toggle, or docs-only unsubscribe arrives too late to catch wrong recipients, duplicate sends, broken unsubscribe, PII leakage, or unreconciled delivery."
        ),
        "task_scope": (
            f"Scope stays on notification subscription-deliverability: {task}. The Loop should not expand into usage/quota metering, generic webhook integration, broad provider platform work, or merely sending one email."
        ),
        "success_surface": (
            "Success means only subscribed eligible users receive the campaign; unsubscribe and preference center choices suppress sends; suppression list, bounce, complaint, drop, disabled-user, tenant, and locale filters work; retry/provider replay does not duplicate sends; provider accepted/delivered/bounced/complained/dropped events reconcile with local delivery audit; English/Chinese template variables render safely without PII/tokens leaking; rate limits, retry/backoff, DLQ/manual replay, monitoring, audit reason codes, migration, and local governance are reviewable."
        ),
        "fake_done_risks": (
            "Block one-test-email, provider-accepted-only, UI-toggle-only, happy-path-send-only, docs-only unsubscribe, missing bounce/complaint proof, missing duplicate negative, missing locale/template proof, missing PII redaction, missing audit reconciliation, missing monitoring, missing migration, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer subscription/preference/unsubscribe/suppression fixtures, bounce/complaint/drop provider events, local delivery audit reconciliation, duplicate retry/replay negatives, disabled-user/tenant negatives, English/Chinese template fallback, PII/token redaction checks, DLQ/manual replay, monitoring alerts, migration compatibility, and local-governance evidence. "
            "Classify each notification deliverability claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Notification Contract Inspector first freezes proof targets; Campaign Email Builder implements from that handoff; Deliverability Evidence Inspector and Template Privacy Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor copy, additional template coverage, or non-critical provider samples may remain only with owner/follow-up; missing subscription, suppression, bounce/complaint, duplicate, locale/template, redaction, audit reconciliation, monitoring, migration, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Subscription correctness, unsubscribe protection, delivery reconciliation, template privacy, duplicate-send negatives, and monitoring proof beats quickly sending one email; speed cannot hide provider-accepted-only or happy-path-send-only evidence."
        ),
        "local_governance": (
            "If project-local governance markers are present, Notification Contract Inspector and Campaign Email Builder read applicable rules, both parallel Inspectors verify related design/test/privacy/i18n/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Notification Contract Inspector freezes subscription, preference, provider event, locale, privacy, retry/DLQ, audit, and monitoring targets; Campaign Email Builder implements only from that handoff; Deliverability Evidence Inspector refutes subscription/suppression/provider reconciliation/duplicate replay; Template Privacy Inspector verifies locale/template/redaction/audit/compatibility/governance; GateKeeper fails closed on shallow delivery proof."
        ),
        "workflow_shape": (
            "Use Notification Contract Inspector -> Campaign Email Builder -> [Deliverability Evidence Inspector + Template Privacy Inspector] -> Notification Deliverability GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries subscription-deliverability, message-delivery, provider-contract, idempotency, retry-timeout, queue-recovery, privacy-redaction, locale-i18n, audit-log, monitoring, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Mailer/provider, subscription store, template/i18n layer, audit writer, queue/DLQ, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _data_lifecycle_deletion_retention_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 deletion / retention 风险会在删除面、retention exception、legal hold、backup expiry、search/cache purge、analytics anonymization、export suppression、tenant isolation、audit 和 monitoring 证据中分阶段暴露；"
                "UI 删除按钮、soft-delete flag 或 docs-only policy 太晚发现数据残留、误删保留数据、错删租户、审计不可追踪或告警缺失。"
            ),
            "task_scope": f"范围固定为 GDPR/account data deletion 与 retention readiness：{task}。不扩展成通用数据平台迁移、普通 data residency 重写或全合规模块。",
            "success_surface": (
                "成功意味着 account deletion、billing-record retention exceptions、legal hold、backup expiry handling、search index purge、cache purge、analytics anonymization、data export suppression、audit trail retention、tenant isolation、permission 和 monitoring alerts 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断 UI-delete-only、soft-delete-only、one happy-path API response、docs-only retention policy、缺少 backup expiry proof、缺少 retention/legal-hold proof、缺少 search/cache purge、缺少 analytics anonymization、缺少 export suppression、缺少 tenant negatives、缺少 audit trail 或缺少 monitoring alerts。"
            ),
            "evidence_preferences": (
                "优先 contract inventory、negative cases、billing retention exception proof、legal hold behavior、backup expiry proof、search/cache purge evidence、analytics anonymization evidence、export suppression evidence、tenant isolation negatives、permission proof、audit refs、monitoring alerts 和 local-governance evidence；每条 lifecycle claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Data Lifecycle Contract Inspector 先固定 deletion/retention proof targets；Deletion Builder 读取 contract handoff 后实现；"
                "Privacy Deletion Evidence Inspector 与 Retention Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 UI copy、非关键 runbook polish 或额外 fixture coverage 可作为 Residual risk 留下并指定 owner/follow-up；缺少删除证明、保留/legal hold、backup expiry、purge/anonymization、tenant negative、audit、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "数据消除、保留例外、租户隔离和审计证据优先于快速显示删除成功；速度不能覆盖残留数据、误删保留数据、soft-delete-only、错租户访问或告警缺口。",
            "local_governance": (
                "若存在项目本地治理入口，Data Lifecycle Contract Inspector 与 Deletion Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/privacy/security/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Data Lifecycle Contract Inspector 固定删除与保留契约；Deletion Builder 只基于 handoff 实现；Privacy Deletion Evidence Inspector 反证 account deletion、tombstone、search/cache purge、analytics anonymization、export suppression 和 tenant negatives；"
                "Retention Audit Inspector 验证 billing retention、legal hold、backup expiry、permission、audit trail、monitoring 和 local governance；GateKeeper 对 shallow proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Data Lifecycle Contract Inspector -> Deletion Builder -> [Privacy Deletion Evidence Inspector + Retention Audit Inspector] -> Data Lifecycle GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 deletion-retention、tenant-isolation、privacy-redaction、audit-log、permission-auth、monitoring、backup-restore、cache-invalidation、data-export、event-integrity、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；数据库、搜索/cache、analytics、backup/storage、audit、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque deletion/retention se prueba por superficies de borrado, excepciones, legal hold, backup expiry, purge, anonymization, tenant negatives, audit y monitoring.",
            "task_scope": f"Alcance limitado a GDPR/account data deletion y retention readiness: {task}; sin rewrite amplio.",
            "success_surface": "Éxito significa account deletion, retention exceptions, legal hold, backup expiry, search/cache purge, analytics anonymization, export suppression, audit, tenant isolation, permission y monitoring probados.",
            "fake_done_risks": "Bloquear UI-delete-only, soft-delete-only, one happy path, docs-only retention, missing backup expiry, retention/legal hold, purge/anonymization, tenant negatives, audit o monitoring.",
            "evidence_preferences": "Preferir contract inventory, negativos, retention/legal hold, backup expiry, purge, anonymization, export suppression, tenant negatives, permission, audit refs, alerts y governance.",
            "execution_strategy": "Data Lifecycle Contract Inspector fija targets; Deletion Builder implementa desde handoff; Privacy Deletion Evidence y Retention Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de deletion proof, retention/legal hold, backup expiry, purge/anonymization, tenant negative, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Deletion, retention exceptions, tenant isolation and audit proof beat fast delete status.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Privacy Inspector refuta deletion/purge/anonymization; Retention Audit verifica retention, legal hold, backup, audit y monitoring; GateKeeper falla cerrado.",
            "workflow_shape": "Data Lifecycle Contract Inspector -> Deletion Builder -> [Privacy Deletion Evidence Inspector + Retention Audit Inspector] -> Data Lifecycle GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; DB, search/cache, analytics, backup/storage, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because data deletion / retention risk is proven through deletion surfaces, retention exceptions, legal hold, backup expiry, search/cache purge, analytics anonymization, export suppression, tenant isolation, audit, and monitoring over staged evidence. "
            "A UI delete button, soft-delete flag, one happy-path response, or docs-only retention policy arrives too late to catch retained data, over-deletion, tenant leakage, unauditable action, or missing alerts."
        ),
        "task_scope": (
            f"Scope stays on GDPR/account data deletion and retention readiness: {task}. The Loop should not expand into a broad data-platform migration, general data-residency rewrite, or unrelated compliance module."
        ),
        "success_surface": (
            "Success means account deletion, billing-record retention exceptions, legal hold, backup expiry handling, search index purge, cache purge, analytics anonymization, data export suppression, audit trail retention, tenant isolation, permission, and monitoring alerts are auditable."
        ),
        "fake_done_risks": (
            "Block UI-delete-only, soft-delete-only, one happy-path API response, docs-only retention policy, missing backup expiry proof, missing retention/legal-hold proof, missing search/cache purge, missing analytics anonymization, missing export suppression, missing tenant negatives, missing audit trail, or missing monitoring alerts."
        ),
        "evidence_preferences": (
            "Prefer contract inventory, negative cases, billing retention exception proof, legal hold behavior, backup expiry proof, search/cache purge evidence, analytics anonymization evidence, export suppression evidence, tenant isolation negatives, permission proof, audit refs, monitoring alerts, and local-governance evidence. "
            "Classify each lifecycle claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Data Lifecycle Contract Inspector first freezes deletion/retention proof targets; Deletion Builder implements from that handoff; Privacy Deletion Evidence Inspector and Retention Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor UI copy, non-critical runbook polish, or additional fixture coverage may remain only with owner/follow-up; missing deletion proof, retention/legal hold, backup expiry, purge/anonymization, tenant negative, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Deletion, retention-exception, tenant-isolation, and audit proof beats fast delete status; speed cannot hide retained data, over-deletion, soft-delete-only implementation, tenant leakage, or missing alerts."
        ),
        "local_governance": (
            "If project-local governance markers are present, Data Lifecycle Contract Inspector and Deletion Builder read applicable rules, both parallel Inspectors verify related design/test/privacy/security/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Data Lifecycle Contract Inspector freezes deletion and retention contract targets; Deletion Builder implements only from that handoff; Privacy Deletion Evidence Inspector refutes account deletion, tombstone, search/cache purge, analytics anonymization, export suppression, and tenant negative claims; Retention Audit Inspector verifies billing retention, legal hold, backup expiry, permission, audit trail, monitoring, and local governance; GateKeeper fails closed on shallow proof."
        ),
        "workflow_shape": (
            "Use Data Lifecycle Contract Inspector -> Deletion Builder -> [Privacy Deletion Evidence Inspector + Retention Audit Inspector] -> Data Lifecycle GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries deletion-retention, tenant-isolation, privacy-redaction, audit-log, permission-auth, monitoring, backup-restore, cache-invalidation, data-export, event-integrity, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Database, search/cache, analytics, backup/storage, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _feature_flag_rollout_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 feature-flag rollout 风险会在 default-off、cohort targeting、percentage rollout、sticky assignment、exposure logging、kill switch、rollback cleanup、monitoring、audit 和 local-only bypass 证据中分阶段暴露；"
                "UI toggle、local flag、one beta happy path 或 docs-only rollout 太晚发现曝光漂移、灰度串组、无法回滚、监控缺失或审计不可追踪。"
            ),
            "task_scope": f"范围固定为 checkout feature flag / release rollout safety：{task}。不扩展成完整实验平台、泛化配置系统或无关支付重写。",
            "success_surface": (
                "成功意味着 default-off behavior、beta cohort targeting、stable percentage rollout、sticky session exposure、exposure logging、kill switch immediate rollback、rollback cleanup、error-rate monitoring、payment-conversion guard、audit log 和 local-only bypass prevention 都有可审计证据。"
            ),
            "fake_done_risks": (
                "必须阻断 UI-toggle-only、local-flag-only、one beta happy path、docs-only rollout、monitoring left as follow-up、缺少 cohort negatives、缺少 percentage boundary cases、缺少 sticky assignment、缺少 kill switch、缺少 rollback cleanup、缺少 conversion/error monitoring、缺少 audit 或缺少 local-only bypass 反证。"
            ),
            "evidence_preferences": (
                "优先 default-off proof、cohort negative cases、percentage boundary cases、sticky session assignment checks、exposure log evidence、kill switch proof、rollback cleanup proof、conversion/error monitoring、audit reviewability、local-only bypass prevention 和 local-governance evidence；每条 rollout claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Rollout Contract Inspector 先固定 rollout proof targets；Rollout Builder 读取 contract handoff 后实现；"
                "Exposure Consistency Inspector 与 Operational Rollback Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 copy、非关键 dashboard polish 或额外 cohort fixture coverage 可作为 Residual risk 留下并指定 owner/follow-up；缺少 default-off、cohort/percentage/sticky exposure、kill switch、rollback cleanup、monitoring/conversion、audit、local-only bypass 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "发布安全、曝光一致性、回滚能力和审计证据优先于快速打开新版 checkout；速度不能覆盖错误 cohort、session bouncing、无法熔断、脏回滚、告警缺失或不可审计 flag change。",
            "local_governance": (
                "若存在项目本地治理入口，Rollout Contract Inspector 与 Rollout Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/release/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Rollout Contract Inspector 固定 release contract 与 proof targets；Rollout Builder 只基于 handoff 实现；Exposure Consistency Inspector 反证 cohort targeting、percentage boundary、sticky assignment、exposure log 和 local-only bypass；"
                "Operational Rollback Inspector 验证 default-off、kill switch、rollback cleanup、monitoring/conversion、audit 和 governance；GateKeeper 对 shallow rollout proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Rollout Contract Inspector -> Rollout Builder -> [Exposure Consistency Inspector + Operational Rollback Inspector] -> Release Rollout GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 rollout-safety、experiment-assignment、monitoring、audit-log、payment-refund-billing、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；flag provider、cohort data、checkout flow、monitoring、audit 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque rollout se prueba por default-off, cohort targeting, percentage rollout, sticky assignment, exposure logging, kill switch, rollback, monitoring, audit y local bypass negatives.",
            "task_scope": f"Alcance limitado a checkout feature flag / release rollout safety: {task}; sin rewrite amplio.",
            "success_surface": "Éxito significa default-off, beta cohort, percentage rollout, sticky exposure, exposure logs, kill switch, rollback cleanup, monitoring/conversion, audit y local-only bypass prevention probados.",
            "fake_done_risks": "Bloquear UI-toggle-only, local-flag-only, beta happy path, docs-only rollout, monitoring follow-up, missing cohort negatives, sticky assignment, rollback, monitoring, audit o local bypass proof.",
            "evidence_preferences": "Preferir default-off proof, cohort negatives, percentage boundaries, sticky assignment, exposure logs, kill switch, rollback cleanup, conversion/error monitoring, audit, local bypass y governance.",
            "execution_strategy": "Rollout Contract Inspector fija targets; Builder implementa desde handoff; Exposure Consistency y Operational Rollback inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de default-off, cohort/percentage/sticky exposure, kill switch, rollback, monitoring/conversion, audit, local bypass o governance fail closed.",
            "judgment_tradeoffs": "Release safety, exposure consistency, rollback and audit proof beats fast checkout enablement.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Exposure Inspector refuta targeting/sticky/logs/bypass; Rollback Inspector verifica kill switch, rollback, monitoring y audit; GateKeeper falla cerrado.",
            "workflow_shape": "Rollout Contract Inspector -> Rollout Builder -> [Exposure Consistency Inspector + Operational Rollback Inspector] -> Release Rollout GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; flag provider, cohorts, checkout, monitoring, audit y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because feature-flag rollout risk is proven through default-off behavior, cohort targeting, percentage rollout, sticky assignment, exposure logging, kill switch, rollback cleanup, monitoring, audit, and local-only bypass evidence over staged evidence. "
            "A UI toggle, local flag, one beta happy path, or docs-only rollout plan arrives too late to catch exposure drift, wrong cohorts, failed rollback, missing alerts, or unauditable flag changes."
        ),
        "task_scope": (
            f"Scope stays on checkout feature flag / release rollout safety: {task}. The Loop should not expand into a full experimentation platform, generic configuration system, or unrelated payment rewrite."
        ),
        "success_surface": (
            "Success means default-off behavior, beta cohort targeting, stable percentage rollout, sticky session exposure, exposure logging, immediate kill switch rollback, rollback cleanup, error-rate monitoring, payment-conversion guard, audit log, and local-only bypass prevention are auditable."
        ),
        "fake_done_risks": (
            "Block UI-toggle-only, local-flag-only, one beta happy path, docs-only rollout, monitoring left as follow-up, missing cohort negatives, missing percentage boundary cases, missing sticky assignment, missing kill switch, missing rollback cleanup, missing conversion/error monitoring, missing audit, or missing local-only bypass negatives."
        ),
        "evidence_preferences": (
            "Prefer default-off proof, cohort negative cases, percentage boundary cases, sticky session assignment checks, exposure log evidence, kill switch proof, rollback cleanup proof, conversion/error monitoring, audit reviewability, local-only bypass prevention, and local-governance evidence. "
            "Classify each rollout claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Rollout Contract Inspector first freezes rollout proof targets; Rollout Builder implements from that handoff; Exposure Consistency Inspector and Operational Rollback Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor copy, non-critical dashboard polish, or additional cohort fixture coverage may remain only with owner/follow-up; missing default-off, cohort/percentage/sticky exposure, kill switch, rollback cleanup, monitoring/conversion, audit, local-only bypass, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Release safety, exposure consistency, rollback ability, and audit proof beats quickly enabling new checkout; speed cannot hide wrong cohorts, session bouncing, missing kill switch, dirty rollback, missing alerts, or unauditable flag changes."
        ),
        "local_governance": (
            "If project-local governance markers are present, Rollout Contract Inspector and Rollout Builder read applicable rules, both parallel Inspectors verify related design/test/release/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Rollout Contract Inspector freezes release contract and proof targets; Rollout Builder implements only from that handoff; Exposure Consistency Inspector refutes cohort targeting, percentage boundary, sticky assignment, exposure log, and local-only bypass claims; Operational Rollback Inspector verifies default-off, kill switch, rollback cleanup, monitoring/conversion, audit, and governance; GateKeeper fails closed on shallow rollout proof."
        ),
        "workflow_shape": (
            "Use Rollout Contract Inspector -> Rollout Builder -> [Exposure Consistency Inspector + Operational Rollback Inspector] -> Release Rollout GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries rollout-safety, experiment-assignment, monitoring, audit-log, payment-refund-billing, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Flag provider, cohort data, checkout flow, monitoring, audit, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _cache_invalidation_consistency_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为商品改价后的缓存一致性会在 PDP、购物车、checkout、API、CDN、Redis、read-model、TTL、stale-read、cache-key isolation、rollback、audit 和 monitoring 证据中分阶段暴露；"
                "数据库更新成功、手动刷新看到新价、只清一层缓存或单个 PDP happy path 太晚发现旧价下单、跨地区/货币串 key、回滚脏缓存或不可审计失效事件。"
            ),
            "task_scope": f"范围固定为商品价格更新后的 cache invalidation / stale-read consistency：{task}。不扩展成完整价格系统重写、通用缓存平台或无关 checkout 改造。",
            "success_surface": (
                "成功意味着管理员改价后 PDP、购物车、checkout、public API、CDN、Redis 和 read-model 都在约定 TTL 内刷新；stale cache / stale read 会回源或失效；旧价格不能 checkout；region/currency cache key 隔离；rollback 恢复旧价并清理新缓存；audit 与 monitoring 可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 database-update-only、manual-refresh-only、single-cache-layer purge、one happy-path PDP、docs-only TTL、缺少 stale-read negatives、缺少 checkout old-price negative、缺少 region/currency key isolation、缺少 rollback cleanup、缺少 audit 或缺少 monitoring。"
            ),
            "evidence_preferences": (
                "优先 cache-key inventory、TTL boundary checks、stale-read negatives、CDN/Redis/read-model invalidation proof、PDP/cart/checkout/API old-price negatives、region/currency key isolation、rollback cleanup、audit reviewability、monitoring alerts 和 local-governance evidence；每条 cache claim 进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Cache Contract Inspector 先固定 price/cache proof targets；Price Cache Builder 读取 contract handoff 后实现；"
                "Stale Read Evidence Inspector 与 Checkout Price Integrity Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微额外 cache fixture coverage、非关键 dashboard polish 或超出范围的压测样本可作为 Residual risk 留下并指定 owner/follow-up；缺少 stale-read negative、checkout old-price negative、key isolation、rollback cleanup、audit、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "价格正确性、旧价下单阻断、缓存边界一致性、回滚清理和审计证据优先于快速上线改价；速度不能覆盖旧缓存、串 key、单层 purge、脏回滚、告警缺失或不可审计 invalidation。",
            "local_governance": (
                "若存在项目本地治理入口，Cache Contract Inspector 与 Price Cache Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/cache/checkout/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Cache Contract Inspector 固定 price surfaces、cache-key inventory、TTL/SLA 和 proof targets；Price Cache Builder 只基于 handoff 实现；"
                "Stale Read Evidence Inspector 反证 CDN/Redis/read-model stale read、TTL、refetch/invalidate、region/currency key isolation 和 rollback cleanup；"
                "Checkout Price Integrity Inspector 验证 PDP/cart/checkout/API old-price negatives、payment/checkout blocking、audit、monitoring 和 governance；GateKeeper 对浅层缓存证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Cache Contract Inspector -> Price Cache Builder -> [Stale Read Evidence Inspector + Checkout Price Integrity Inspector] -> Cache Consistency GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 cache-invalidation、payment-refund-billing、audit-log、monitoring、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；价格源、PDP/cart/checkout/API、CDN、Redis、read-model、audit、monitoring 和测试 runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque la consistencia de cache de precio se prueba por PDP, carrito, checkout, API, CDN, Redis, read-model, TTL, stale reads, key isolation, rollback, audit y monitoring.",
            "task_scope": f"Alcance limitado a cache invalidation / stale-read consistency para precio de producto: {task}; sin rewrite amplio.",
            "success_surface": "Éxito significa PDP, cart, checkout, API, CDN, Redis y read-model frescos dentro de TTL; stale reads refetch/invalidate; old price no puede checkout; keys por región/moneda aisladas; rollback limpia cache; audit y monitoring probados.",
            "fake_done_risks": "Bloquear database-update-only, manual-refresh-only, single-cache-layer purge, happy-path PDP, docs-only TTL, missing stale-read negatives, missing old-price checkout negative, missing key isolation, rollback, audit o monitoring.",
            "evidence_preferences": "Preferir cache-key inventory, TTL boundaries, stale-read negatives, CDN/Redis/read-model proof, PDP/cart/checkout/API old-price negatives, key isolation, rollback cleanup, audit, monitoring y governance.",
            "execution_strategy": "Cache Contract Inspector fija targets; Price Cache Builder implementa desde handoff; Stale Read Evidence y Checkout Price Integrity inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de stale-read negatives, checkout old-price negative, key isolation, rollback, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Price correctness, old-price checkout blocking, cache-boundary consistency, rollback cleanup and audit proof beats fast price update launch.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Stale Read Inspector refuta stale cache/TTL/key isolation/rollback; Checkout Inspector verifica old-price negatives, payment blocking, audit y monitoring; GateKeeper falla cerrado.",
            "workflow_shape": "Cache Contract Inspector -> Price Cache Builder -> [Stale Read Evidence Inspector + Checkout Price Integrity Inspector] -> Cache Consistency GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; price source, PDP/cart/checkout/API, CDN, Redis, read-model, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because product price cache consistency is proven through PDP, cart, checkout, API, CDN, Redis, read-model, TTL, stale-read, cache-key isolation, rollback, audit, and monitoring evidence over staged handoffs. "
            "Database update success, a manual refresh, one cache-layer purge, or one PDP happy path arrives too late to catch old-price checkout, region/currency key contamination, dirty rollback caches, or unauditable invalidation events."
        ),
        "task_scope": (
            f"Scope stays on product price cache invalidation / stale-read consistency: {task}. The Loop should not expand into a full pricing-system rewrite, generic cache platform, or unrelated checkout redesign."
        ),
        "success_surface": (
            "Success means PDP, cart, checkout, public API, CDN, Redis, and read-model caches refresh within the agreed TTL after admin price update; stale cache / stale read refetches or invalidates; users cannot checkout with old price; region/currency cache keys are isolated; rollback restores old price and clears new cache entries; audit and monitoring are reviewable."
        ),
        "fake_done_risks": (
            "Block database-update-only, manual-refresh-only, single-cache-layer purge, one happy-path PDP, docs-only TTL, missing stale-read negatives, missing checkout old-price negative, missing region/currency key isolation, missing rollback cleanup, missing audit, or missing monitoring."
        ),
        "evidence_preferences": (
            "Prefer cache-key inventory, TTL boundary checks, stale-read negatives, CDN/Redis/read-model invalidation proof, PDP/cart/checkout/API old-price negatives, region/currency key isolation, rollback cleanup proof, audit reviewability, monitoring alerts, and local-governance evidence. "
            "Classify each cache claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Cache Contract Inspector first freezes price/cache proof targets; Price Cache Builder implements from that handoff; Stale Read Evidence Inspector and Checkout Price Integrity Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor additional cache fixture coverage, non-critical dashboard polish, or out-of-scope load samples may remain only with owner/follow-up; missing stale-read negative, checkout old-price negative, key isolation, rollback cleanup, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Price correctness, old-price checkout blocking, cache-boundary consistency, rollback cleanup, and audit proof beats quickly launching price updates; speed cannot hide stale cache, key contamination, one-layer purge, dirty rollback, missing alerts, or unauditable invalidation."
        ),
        "local_governance": (
            "If project-local governance markers are present, Cache Contract Inspector and Price Cache Builder read applicable rules, both parallel Inspectors verify related design/test/cache/checkout/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Cache Contract Inspector freezes price surfaces, cache-key inventory, TTL/SLA, and proof targets; Price Cache Builder implements only from that handoff; Stale Read Evidence Inspector refutes CDN/Redis/read-model stale reads, TTL, refetch/invalidate behavior, region/currency key isolation, and rollback cleanup; Checkout Price Integrity Inspector verifies PDP/cart/checkout/API old-price negatives, payment/checkout blocking, audit, monitoring, and governance; GateKeeper fails closed on shallow cache proof."
        ),
        "workflow_shape": (
            "Use Cache Contract Inspector -> Price Cache Builder -> [Stale Read Evidence Inspector + Checkout Price Integrity Inspector] -> Cache Consistency GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries cache-invalidation, payment-refund-billing, audit-log, monitoring, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Price source, PDP/cart/checkout/API, CDN, Redis, read-model, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _data_import_validation_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 customer CSV bulk import 的真实完成要通过 field mapping、required/type schema validation、dry-run、好坏行混合、row-level errors、partial failure、idempotent retry、external_id dedupe、PII redaction、permissions、audit batch 和 monitoring 证据分阶段证明；"
                "happy CSV、preview-only、success-count-only 或一次性全量成功太晚发现坏行污染、重复导入、PII 泄漏或不可审计批次。"
            ),
            "task_scope": f"范围固定为 customer CSV bulk import validation / idempotent retry / auditability：{task}。不扩展成通用 ETL 平台、完整 CRM 重写或无关报表导出。",
            "success_surface": (
                "成功意味着字段映射、必填/类型校验、dry-run preview、mixed good/bad row fixtures、坏行隔离、row-level error report、幂等重试、external_id 去重、PII 安全日志、权限、audit batch fields 和 monitoring 都可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 happy-path-only CSV、preview-only、all-or-nothing import、success-count-only report、schema validation 缺失、bad-row isolation 缺失、row-level report 缺失、idempotency/dedupe 缺失、PII/audit 缺失、permission negatives 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 mixed-row fixtures、schema/type validation output、dry-run artifact、row-level error report artifact、partial-failure isolation proof、idempotency retry proof、external_id dedupe proof、PII redaction checks、permission negatives、audit batch actor/source/counts/reason/status、monitoring 和 local-governance evidence。"
                "每条导入 claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Import Contract Inspector 先固定导入契约与 proof targets；CSV Import Builder 读取 contract handoff 后实现；"
                "Import Evidence Inspector 与 Privacy Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微额外 fixture 覆盖、非关键导入 UI polish 或超出本轮的性能样本可作为 Residual risk 留下并指定 owner/follow-up；缺少 schema、坏行隔离、row-level report、幂等去重、PII、权限、审计或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "数据正确性、坏行隔离、可重试幂等、去重、隐私和审计证据优先于快速上线导入入口；速度不能覆盖重复客户、静默丢行、PII 泄漏、不可审计 batch 或跳过权限负例。",
            "local_governance": (
                "若存在项目本地治理入口，Import Contract Inspector 与 CSV Import Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/privacy/security/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Import Contract Inspector 固定 mapping/schema/dry-run/error/idempotency/dedupe/privacy/audit proof targets；CSV Import Builder 只基于 handoff 实现；"
                "Import Evidence Inspector 反证 mixed-row、坏行隔离、row-level report、retry 和 external_id dedupe；Privacy Audit Inspector 验证 PII、permission、audit batch、cleanup、monitoring 和 governance；GateKeeper 对浅层导入证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Import Contract Inspector -> CSV Import Builder -> [Import Evidence Inspector + Privacy Audit Inspector] -> Import Validation GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 data-import-validation、idempotency、privacy-redaction、permission-auth、audit-log、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；CSV parser、customer model、validation runner、storage/audit/logging、permission system、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque import se prueba por mapping, schema, dry-run, filas buenas/malas, row-level errors, partial failure, idempotent retry, dedupe, privacy, permisos, audit y monitoring.",
            "task_scope": f"Alcance limitado a customer CSV bulk import validation / idempotent retry / auditability: {task}; sin ETL platform amplio.",
            "success_surface": "Éxito significa mapping, required/type validation, dry-run, mixed rows, bad-row isolation, row-level report, retry, external_id dedupe, PII-safe logs, permisos, audit batch y monitoring probados.",
            "fake_done_risks": "Bloquear happy CSV only, preview-only, all-or-nothing, success-count-only, missing schema, bad-row isolation, row report, idempotency/dedupe, privacy/audit, permissions o governance.",
            "evidence_preferences": "Preferir mixed-row fixtures, validation output, dry-run artifact, row-level report, partial failure proof, retry/dedupe proof, PII checks, permission negatives, audit batch fields, monitoring y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Import Contract Inspector fija targets; CSV Import Builder implementa desde handoff; Import Evidence y Privacy Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de schema, bad-row isolation, row-level report, idempotency/dedupe, privacy, permission, audit o governance fail closed.",
            "judgment_tradeoffs": "Data correctness, bad-row isolation, retry/dedupe, privacy and audit proof beats fast import UI.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Import Evidence refuta mixed rows, bad-row isolation, row reports, retry y dedupe; Privacy Audit verifica PII, permissions, audit, cleanup, monitoring; GateKeeper falla cerrado.",
            "workflow_shape": "Import Contract Inspector -> CSV Import Builder -> [Import Evidence Inspector + Privacy Audit Inspector] -> Import Validation GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; parser, model, validation runner, audit/logging, permissions, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because customer CSV bulk import completion is proven through field mapping, required/type schema validation, dry-run preview, mixed good/bad rows, row-level errors, partial-failure isolation, idempotent retry, external_id dedupe, PII redaction, permissions, audit batch, and monitoring evidence over staged handoffs. "
            "A happy CSV, preview-only path, success-count-only report, or one full-import success arrives too late to catch bad-row contamination, duplicate imports, PII leakage, or unauditable batches."
        ),
        "task_scope": (
            f"Scope stays on customer CSV bulk import validation / idempotent retry / auditability: {task}. The Loop should not expand into a generic ETL platform, full CRM rewrite, or unrelated reporting export."
        ),
        "success_surface": (
            "Success means field mapping, required/type validation, dry-run preview, mixed good/bad row fixtures, bad-row isolation, row-level error report, idempotent retry, external_id dedupe, PII-safe logs, permissions, audit batch fields, and monitoring are auditable."
        ),
        "fake_done_risks": (
            "Block happy-path-only CSV, preview-only, all-or-nothing import, success-count-only report, missing schema validation, missing bad-row isolation, missing row-level report, missing idempotency/dedupe, missing privacy/audit, missing permission negatives, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer mixed-row fixtures, schema/type validation output, dry-run artifacts, row-level error report artifacts, partial-failure isolation proof, idempotent retry proof, external_id dedupe proof, PII redaction checks, permission negatives, audit batch actor/source/counts/reason/status, monitoring, and local-governance evidence."
            " Classify each import claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Import Contract Inspector first freezes import contract proof targets; CSV Import Builder implements from that handoff; Import Evidence Inspector and Privacy Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor extra fixture coverage, non-critical import UI polish, or out-of-scope performance samples may remain only with owner/follow-up; missing schema, bad-row isolation, row-level report, idempotency/dedupe, privacy, permission, audit, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Data correctness, bad-row isolation, retry idempotency, dedupe, privacy, and audit proof beats quickly shipping an import entry point; speed cannot hide duplicate customers, silently dropped rows, PII leakage, unauditable batches, or skipped permission negatives."
        ),
        "local_governance": (
            "If project-local governance markers are present, Import Contract Inspector and CSV Import Builder read applicable rules, both parallel Inspectors verify related design/test/privacy/security/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Import Contract Inspector freezes mapping, schema, dry-run, error, idempotency, dedupe, privacy, and audit proof targets; CSV Import Builder implements only from that handoff; Import Evidence Inspector refutes mixed-row, bad-row isolation, row-level report, retry, and external_id dedupe claims; Privacy Audit Inspector verifies PII, permission, audit batch, cleanup, monitoring, and governance; GateKeeper fails closed on shallow import proof."
        ),
        "workflow_shape": (
            "Use Import Contract Inspector -> CSV Import Builder -> [Import Evidence Inspector + Privacy Audit Inspector] -> Import Validation GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries data-import-validation, idempotency, privacy-redaction, permission-auth, audit-log, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. CSV parser, customer model, validation runner, storage/audit/logging, permission system, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _concurrency_conflict_resolution_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为协作文档冲突解决不能靠一次 Agent pass、单人保存成功、WebSocket happy path 或最后人工 review 裁决。"
                "后续轮次必须分阶段产生双用户并发、optimistic locking、safe merge/reject、offline replay idempotency、permission negatives、audit、monitoring 和 governance 证据。"
            ),
            "task_scope": f"范围固定为 collaborative editing conflict resolution：{task}。不扩展成通用编辑器重写、库存/usage 并发、WebSocket polish 或单人保存体验。",
            "success_surface": (
                "成功意味着两个用户同时编辑同一段不会 silent overwrite；version conflict / optimistic locking 会提示冲突或安全 merge/reject；"
                "离线编辑恢复后的 replay 幂等；冲突解决保留两边内容；低权限或权限撤销用户不能覆盖别人改动；audit log 记录 base_version、resolved_by、merge outcome、retry/replay 和 permission denial。"
            ),
            "fake_done_risks": (
                "必须阻断 single-user-save-only、last-write-wins、happy-path WebSocket-only、optimistic-lock proof 缺失、offline replay idempotency 缺失、both-sides-preserved proof 缺失、permission negative 缺失、audit 缺失、monitoring 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 two-user same-paragraph fixtures、lost-update negative、version conflict UI/API response、optimistic-lock checks、safe merge/reject artifact、both-sides-preserved evidence、offline replay idempotency、retry/replay proof、permission matrix negatives、audit refs、monitoring alerts 和 local-governance evidence。每条 conflict claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Conflict Contract Inspector 先固定 proof targets；Collaboration Builder 读取 contract handoff 后实现；"
                "Conflict Evidence Inspector 与 Permission Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": "轻微编辑器 UI polish、额外冲突样本或非关键协作 presence 可作为 Residual risk 留下并指定 owner/follow-up；缺少 lost-update prevention、optimistic locking、offline replay、both-sides-preserved、permission negative、audit、monitoring 或 governance 证据必须 fail closed。",
            "judgment_tradeoffs": "冲突正确性、幂等 replay、权限反证、审计和监控优先于快速看到两个用户都能保存。",
            "local_governance": (
                "若存在项目本地治理入口，Conflict Contract Inspector 与 Collaboration Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/access/audit/monitoring 义务，GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Conflict Contract Inspector 固定并发、版本、merge/reject、offline replay、权限、audit/monitoring targets；Collaboration Builder 只基于 handoff 实现；Conflict Evidence Inspector 反证 lost update、last-write-wins、offline replay 和 both-sides-preserved；Permission Audit Inspector 验证 permission negatives、audit、monitoring 和 governance；GateKeeper 对浅层协作 proof fail closed。"
            ),
            "workflow_shape": (
                "采用 Conflict Contract Inspector -> Collaboration Builder -> [Conflict Evidence Inspector + Permission Audit Inspector] -> Conflict Resolution GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 conflict-resolution、idempotency、permission-auth、audit-log、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；协作编辑栈、版本模型、offline queue、permission model、audit、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque conflict resolution requiere evidencia por fases, no single-user save ni last-write-wins.",
            "task_scope": f"Alcance limitado a collaborative editing conflict resolution: {task}; sin editor rewrite, inventory/usage concurrency ni WebSocket polish.",
            "success_surface": "Éxito significa no silent overwrite, optimistic locking o safe merge/reject, offline replay idempotent, both sides preserved, permission negatives, audit y monitoring.",
            "fake_done_risks": "Bloquear single-user-save-only, last-write-wins, WebSocket-only, missing optimistic lock, offline replay, both-sides proof, permission negative, audit, monitoring o governance.",
            "evidence_preferences": "Preferir two-user fixtures, lost-update negatives, conflict UI/API response, safe merge/reject, offline replay idempotency, permission negatives, audit, monitoring y governance.",
            "execution_strategy": "Conflict Contract Inspector fija targets; Collaboration Builder implementa; Conflict Evidence y Permission Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de lost-update prevention, optimistic locking, offline replay, both-sides-preserved, permission negative, audit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Conflict correctness, replay idempotency, permissions, audit and monitoring beat fast two-user save.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Conflict Evidence refuta lost update/replay; Permission Audit verifica permissions/audit/monitoring.",
            "workflow_shape": "Conflict Contract Inspector -> Collaboration Builder -> [Conflict Evidence Inspector + Permission Audit Inspector] -> Conflict Resolution GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; stack, version model, offline queue, permissions, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because collaborative editing conflict resolution cannot be judged from one Agent pass, single-user save, a happy-path WebSocket update, or final review. "
            "Later rounds must produce staged evidence for two-user concurrency, optimistic locking, safe merge/reject, offline replay idempotency, permission negatives, audit, monitoring, and governance."
        ),
        "task_scope": (
            f"Scope stays on collaborative editing conflict resolution: {task}. The Loop should not expand into a general editor rewrite, inventory/usage concurrency, WebSocket polish, or a single-user save flow."
        ),
        "success_surface": (
            "Success means two users editing the same paragraph do not silently overwrite each other; version conflict / optimistic locking produces a conflict prompt or safe merge/reject; offline edits replay idempotently after reconnect; both sides of a conflict are preserved; lower-permission or revoked users cannot overwrite someone else; audit logs record base_version, resolved_by, merge outcome, retry/replay, and permission denials."
        ),
        "fake_done_risks": (
            "Block single-user-save-only, last-write-wins, happy-path WebSocket-only, missing optimistic-lock proof, missing offline replay idempotency, missing both-sides-preserved proof, missing permission negative, missing audit, missing monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer two-user same-paragraph fixtures, lost-update negatives, version conflict UI/API response, optimistic-lock checks, safe merge/reject artifacts, both-sides-preserved evidence, offline replay idempotency, retry/replay proof, permission matrix negatives, audit refs, monitoring alerts, and local-governance evidence. "
            "Classify each conflict claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Conflict Contract Inspector first freezes proof targets; Collaboration Builder implements from that handoff; Conflict Evidence Inspector and Permission Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor editor UI polish, extra conflict fixture coverage, or non-critical collaboration presence may remain only with owner/follow-up; missing lost-update prevention, optimistic locking, offline replay, both-sides-preserved, permission negative, audit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": "Conflict correctness, replay idempotency, permission negatives, audit, and monitoring beat quickly seeing two users save.",
        "local_governance": (
            "If project-local governance markers are present, Conflict Contract Inspector and Collaboration Builder read applicable rules, both parallel Inspectors verify related design/test/access/audit/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Conflict Contract Inspector freezes concurrency, versioning, merge/reject, offline replay, permission, audit, and monitoring targets; Collaboration Builder implements only from that handoff; Conflict Evidence Inspector refutes lost update, last-write-wins, offline replay, and both-sides-preserved gaps; Permission Audit Inspector verifies permission negatives, audit, monitoring, and governance; GateKeeper fails closed on shallow collaboration proof."
        ),
        "workflow_shape": (
            "Use Conflict Contract Inspector -> Collaboration Builder -> [Conflict Evidence Inspector + Permission Audit Inspector] -> Conflict Resolution GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries conflict-resolution, idempotency, permission-auth, audit-log, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Collaboration stack, version model, offline queue, permission model, audit, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _inventory_reservation_consistency_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 checkout inventory reservation 的真实完成要通过 same-SKU 并发、oversell negatives、hold TTL/expiry release、payment webhook replay/order、取消/退款/失败支付释放、幂等重试、ledger/order/provider 对账、售罄/低库存状态、audit 和 monitoring 证据分阶段证明；"
                "one-user checkout、UI stock decrement 或 DB decrement only 太晚发现超卖、hold 泄漏、重复扣减、释放失败、对账缺口或不可审计 retry。"
            ),
            "task_scope": f"范围固定为 checkout inventory reservation / oversell prevention / payment-ledger reconciliation：{task}。不扩展成完整库存平台、通用支付重写或无关报表。",
            "success_surface": (
                "成功意味着 same-SKU concurrent checkout 不会 oversell，hold TTL 到期释放，支付成功确认并扣减库存，取消/退款/失败支付释放 hold，webhook/retry 幂等，inventory ledger / order / payment provider 可对账，低库存/售罄状态一致，audit 和 monitoring 可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 one-user checkout、UI stock decrement、DB decrement only、happy-path-only payment、TTL expiry 缺失、release proof 缺失、webhook replay/order 缺失、ledger reconciliation 缺失、sold-out consistency 缺失、audit/monitoring 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 same-SKU concurrent checkout race tests、oversell negative proof、hold TTL expiry release proof、payment webhook replay/order fixtures、cancellation/refund/failed-payment release proof、idempotency retry proof、ledger/order/provider reconciliation artifacts、sold-out/low-stock checks、audit log proof、monitoring alerts 和 local-governance evidence。"
                "每条库存预留 claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Inventory Contract Inspector 先固定库存/预留 proof targets；Inventory Reservation Builder 读取 contract handoff 后实现；"
                "Reservation Race Inspector 与 Payment Ledger Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微额外并发 fixture coverage、非关键库存 UI polish 或超出本轮的压力样本可作为 Residual risk 留下并指定 owner/follow-up；缺少防超卖、TTL 释放、失败/退款释放、webhook 幂等、ledger 对账、售罄状态、audit/monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "库存正确性、防超卖、释放闭环、幂等与对账证据优先于快速上线 checkout；速度不能覆盖竞态、hold 泄漏、重复 webhook、静默释放失败、售罄状态漂移或不可审计库存变化。",
            "local_governance": (
                "若存在项目本地治理入口，Inventory Contract Inspector 与 Inventory Reservation Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/payment/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Inventory Contract Inspector 固定 SKU invariants、reservation state machine、TTL/release/idempotency/reconciliation/audit proof targets；Inventory Reservation Builder 只基于 handoff 实现；"
                "Reservation Race Inspector 反证 concurrent checkout、oversell、TTL expiry 和售罄状态；Payment Ledger Inspector 验证 webhook replay/order、release reasons、idempotency、ledger/order/provider reconciliation、audit 和 governance；GateKeeper 对浅层库存证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Inventory Contract Inspector -> Inventory Reservation Builder -> [Reservation Race Inspector + Payment Ledger Inspector] -> Inventory Reservation GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 inventory-reservation、conflict-resolution、webhook-ordering、idempotency、ledger-reconciliation、payment-refund-billing、audit-log、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；库存源、checkout/payment flow、webhook handler、ledger/order model、audit/logging、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque inventory reservation se prueba por checkout concurrente same-SKU, oversell negatives, TTL expiry release, webhook replay/order, release por cancel/refund/payment failure, idempotency, reconciliation, sold-out/low-stock, audit y monitoring.",
            "task_scope": f"Alcance limitado a checkout inventory reservation / oversell prevention / payment-ledger reconciliation: {task}; sin plataforma de inventario amplia.",
            "success_surface": "Éxito significa no oversell bajo concurrent checkout, TTL expiry release, payment confirm/decrement, release por cancel/refund/failed payment, webhook/retry idempotente, reconciliation ledger/order/provider, estados sold-out/low-stock consistentes, audit y monitoring probados.",
            "fake_done_risks": "Bloquear one-user checkout, UI stock decrement, DB decrement only, happy payment only, missing TTL, release, webhook replay/order, reconciliation, sold-out consistency, audit/monitoring o governance.",
            "evidence_preferences": "Preferir concurrency race tests, oversell negatives, TTL release, webhook replay/order fixtures, release proof, retry/idempotency, reconciliation artifacts, sold-out/low-stock checks, audit, monitoring y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Inventory Contract Inspector fija targets; Inventory Reservation Builder implementa desde handoff; Reservation Race y Payment Ledger inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de oversell prevention, TTL release, release por failed/refund, webhook idempotency, reconciliation, sold-out state, audit/monitoring o governance fail closed.",
            "judgment_tradeoffs": "Inventory correctness, oversell prevention, release closure, idempotency and reconciliation proof beats fast checkout shipping.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Reservation Race refuta concurrency/oversell/TTL/sold-out; Payment Ledger verifica webhook, release, idempotency, reconciliation, audit y governance; GateKeeper falla cerrado.",
            "workflow_shape": "Inventory Contract Inspector -> Inventory Reservation Builder -> [Reservation Race Inspector + Payment Ledger Inspector] -> Inventory Reservation GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; inventory source, checkout/payment, webhooks, ledger/order, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because checkout inventory reservation completion is proven through same-SKU concurrency, oversell negatives, hold TTL/expiry release, payment webhook replay/order, cancellation/refund/failed-payment release, idempotent retry, ledger/order/provider reconciliation, sold-out/low-stock state consistency, audit, and monitoring evidence over staged handoffs. "
            "One-user checkout, UI stock decrement, or DB decrement only arrives too late to catch oversell races, leaked holds, duplicate decrements, release failures, reconciliation gaps, or unauditable retries."
        ),
        "task_scope": (
            f"Scope stays on checkout inventory reservation / oversell prevention / payment-ledger reconciliation: {task}. The Loop should not expand into a full inventory platform, generic payment rewrite, or unrelated stock reporting export."
        ),
        "success_surface": (
            "Success means same-SKU concurrent checkout cannot oversell, hold TTL expires and releases, payment success confirms and decrements inventory, cancellation/refund/failed payment releases holds, webhook/retry handling is idempotent, inventory ledger/order/payment-provider reconciliation passes, low-stock and sold-out states are consistent, and audit plus monitoring are reviewable."
        ),
        "fake_done_risks": (
            "Block one-user checkout, UI stock decrement, DB decrement only, happy-path-only payment, missing TTL expiry, missing release proof, missing webhook replay/order, missing ledger reconciliation, missing sold-out consistency, missing audit/monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer same-SKU concurrent checkout race tests, oversell negative proof, hold TTL expiry release proof, payment webhook replay/order fixtures, cancellation/refund/failed-payment release proof, idempotency retry proof, ledger/order/provider reconciliation artifacts, sold-out/low-stock checks, audit log proof, monitoring alerts, and local-governance evidence. "
            "Classify each inventory reservation claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Inventory Contract Inspector first freezes inventory/reservation proof targets; Inventory Reservation Builder implements from that handoff; Reservation Race Inspector and Payment Ledger Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor extra concurrency fixture coverage, non-critical inventory UI polish, or out-of-scope load samples may remain only with owner/follow-up; missing oversell prevention, TTL release, failed/refund release, webhook idempotency, ledger reconciliation, sold-out state, audit/monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Inventory correctness, oversell prevention, release closure, idempotency, and reconciliation proof beats quickly shipping checkout; speed cannot hide race conditions, leaked holds, duplicate webhooks, silent release failure, sold-out drift, or unauditable stock changes."
        ),
        "local_governance": (
            "If project-local governance markers are present, Inventory Contract Inspector and Inventory Reservation Builder read applicable rules, both parallel Inspectors verify related design/test/payment/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Inventory Contract Inspector freezes SKU invariants, reservation state machine, TTL/release/idempotency/reconciliation/audit proof targets; Inventory Reservation Builder implements only from that handoff; Reservation Race Inspector refutes concurrent checkout, oversell, TTL expiry, and sold-out-state claims; Payment Ledger Inspector verifies webhook replay/order, release reasons, idempotency, ledger/order/provider reconciliation, audit, and governance; GateKeeper fails closed on shallow inventory proof."
        ),
        "workflow_shape": (
            "Use Inventory Contract Inspector -> Inventory Reservation Builder -> [Reservation Race Inspector + Payment Ledger Inspector] -> Inventory Reservation GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries inventory-reservation, conflict-resolution, webhook-ordering, idempotency, ledger-reconciliation, payment-refund-billing, audit-log, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Inventory source, checkout/payment flow, webhook handler, ledger/order model, audit/logging, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _file_upload_storage_safety_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 user file upload / object storage safety 的真实完成要通过 MIME/content sniffing、size limits、malware scan、quarantine-before-serving、private object ACL、signed URL permission/expiry、tenant isolation、failed/orphan cleanup、audit 和 monitoring 证据分阶段证明；"
                "returned URL、one happy PDF、browser content-type 或 public bucket 太晚发现恶意文件可访问、跨租户读取、URL 过期/权限缺口、孤儿对象或不可审计扫描失败。"
            ),
            "task_scope": f"范围固定为 user file upload / object storage safety：{task}。不扩展成完整 DAM、通用对象存储平台或无关 CSV import。",
            "success_surface": (
                "成功意味着 MIME/content-type sniffing、extension/content mismatch、size limits、virus/malware scan、quarantine before serving、private bucket/object ACL、signed URL auth/expiry、tenant object isolation、failed/orphan cleanup、audit fields 和 monitoring alerts 都可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 returned-URL-only、one happy PDF、browser-content-type-only、public bucket、scan-as-follow-up、quarantine 缺失、tenant negatives 缺失、cleanup 缺失、audit/monitoring 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 MIME spoofing、oversize rejection、malware fixture quarantine、quarantine-before-serving proof、private ACL proof、signed URL auth/expiry negatives、cross-tenant object access negatives、failed/orphan cleanup proof、audit actor/object/hash/verdict/reason fields、scan failure alerts 和 local-governance evidence。"
                "每条上传存储 claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Upload Storage Contract Inspector 先固定上传/存储 proof targets；File Upload Builder 读取 contract handoff 后实现；"
                "Storage Access Inspector 与 Malware Cleanup Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微额外文件类型 fixture、非关键上传 UI polish 或超出本轮的性能样本可作为 Residual risk 留下并指定 owner/follow-up；缺少 MIME/size、malware quarantine、signed URL auth/expiry、tenant negatives、cleanup、audit/monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "存储访问安全、恶意文件隔离、清理闭环、租户隔离和审计证据优先于快速返回上传 URL；速度不能覆盖 public bucket、scan follow-up、跨租户读取、孤儿对象、URL 权限漂移或不可审计扫描失败。",
            "local_governance": (
                "若存在项目本地治理入口，Upload Storage Contract Inspector 与 File Upload Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/security/storage/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Upload Storage Contract Inspector 固定 MIME/size/malware/quarantine/ACL/signed URL/tenant/cleanup/audit proof targets；File Upload Builder 只基于 handoff 实现；"
                "Storage Access Inspector 反证 private ACL、signed URL auth/expiry、tenant negative access、object-key isolation 和 public exposure；Malware Cleanup Inspector 验证 MIME spoofing、oversize、malware quarantine、cleanup、audit verdict fields、scan failure alerts 和 governance；GateKeeper 对浅层上传证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Upload Storage Contract Inspector -> File Upload Builder -> [Storage Access Inspector + Malware Cleanup Inspector] -> Upload Storage GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 file-upload-safety、tenant-isolation、permission-auth、privacy-redaction、audit-log、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；上传 handler、object storage/bucket policy、signed URL issuer、scanner/quarantine path、tenant model、audit/logging、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque upload storage safety se prueba por MIME sniffing, size limits, malware scan, quarantine, private ACL, signed URL auth/expiry, tenant isolation, cleanup, audit y monitoring.",
            "task_scope": f"Alcance limitado a user file upload / object storage safety: {task}; sin DAM amplio ni CSV import.",
            "success_surface": "Éxito significa MIME/content sniffing, size limits, malware scan, quarantine before serving, private ACL, signed URL auth/expiry, tenant isolation, cleanup, audit y monitoring probados.",
            "fake_done_risks": "Bloquear returned-URL-only, happy PDF only, browser-content-type-only, public bucket, scan follow-up, missing quarantine, tenant negatives, cleanup, audit/monitoring o governance.",
            "evidence_preferences": "Preferir MIME spoofing, oversize rejection, malware quarantine, private ACL, signed URL negatives, tenant negatives, cleanup, audit verdict fields, scan alerts y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Upload Storage Contract Inspector fija targets; File Upload Builder implementa desde handoff; Storage Access y Malware Cleanup inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de MIME/size, quarantine, signed URL auth/expiry, tenant negatives, cleanup, audit/monitoring o governance fail closed.",
            "judgment_tradeoffs": "Storage access safety, malware quarantine, cleanup, tenant isolation and audit proof beats fast URL return.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Storage Access refuta ACL/signed URL/tenant/public exposure; Malware Cleanup verifica MIME/malware/quarantine/cleanup/audit/alerts; GateKeeper falla cerrado.",
            "workflow_shape": "Upload Storage Contract Inspector -> File Upload Builder -> [Storage Access Inspector + Malware Cleanup Inspector] -> Upload Storage GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; upload handler, bucket policy, signed URL issuer, scanner, tenant model, audit, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because user file upload / object storage safety is proven through MIME/content sniffing, size limits, malware scan, quarantine-before-serving, private object ACL, signed URL permission/expiry, tenant isolation, failed/orphan cleanup, audit, and monitoring evidence over staged handoffs. "
            "Returned URL, one happy PDF, browser content-type, or public bucket proof arrives too late to catch accessible malware, cross-tenant reads, signed URL permission drift, orphan objects, or unauditable scan failures."
        ),
        "task_scope": (
            f"Scope stays on user file upload / object storage safety: {task}. The Loop should not expand into a full DAM, generic object-storage platform, or unrelated CSV import."
        ),
        "success_surface": (
            "Success means MIME/content-type sniffing, extension/content mismatch cases, size limits, virus/malware scan, quarantine before serving, private bucket/object ACL, signed URL auth/expiry, tenant object isolation, failed/orphan cleanup, audit fields, and monitoring alerts are reviewable."
        ),
        "fake_done_risks": (
            "Block returned-URL-only, one happy PDF, browser-content-type-only, public bucket, scan-as-follow-up, missing quarantine, missing tenant negatives, missing cleanup, missing audit/monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer MIME spoofing, oversize rejection, malware fixture quarantine, quarantine-before-serving proof, private ACL proof, signed URL auth/expiry negatives, cross-tenant object access negatives, failed/orphan cleanup proof, audit actor/object/hash/verdict/reason fields, scan failure alerts, and local-governance evidence. "
            "Classify each file upload storage claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Upload Storage Contract Inspector first freezes upload/storage proof targets; File Upload Builder implements from that handoff; Storage Access Inspector and Malware Cleanup Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor extra file-type fixtures, non-critical upload UI polish, or out-of-scope performance samples may remain only with owner/follow-up; missing MIME/size, malware quarantine, signed URL auth/expiry, tenant negatives, cleanup, audit/monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Storage access safety, malware quarantine, cleanup closure, tenant isolation, and audit proof beats quickly returning upload URLs; speed cannot hide public buckets, scan follow-up, cross-tenant reads, orphan objects, signed URL drift, or unauditable scan failures."
        ),
        "local_governance": (
            "If project-local governance markers are present, Upload Storage Contract Inspector and File Upload Builder read applicable rules, both parallel Inspectors verify related design/test/security/storage/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Upload Storage Contract Inspector freezes MIME/size/malware/quarantine/ACL/signed URL/tenant/cleanup/audit proof targets; File Upload Builder implements only from that handoff; Storage Access Inspector refutes private ACL, signed URL auth/expiry, tenant negative access, object-key isolation, and public exposure claims; Malware Cleanup Inspector verifies MIME spoofing, oversize rejection, malware quarantine, cleanup, audit verdict fields, scan failure alerts, and governance; GateKeeper fails closed on shallow upload proof."
        ),
        "workflow_shape": (
            "Use Upload Storage Contract Inspector -> File Upload Builder -> [Storage Access Inspector + Malware Cleanup Inspector] -> Upload Storage GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries file-upload-safety, tenant-isolation, permission-auth, privacy-redaction, audit-log, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Upload handler, object storage/bucket policy, signed URL issuer, scanner/quarantine path, tenant model, audit/logging, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _dsar_data_export_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 DSAR / subject access data export 的真实完成要通过身份与权限、导出范围、串用户/串租户负例、"
                "PII/secret redaction、legal hold / retention exceptions、异步任务生命周期、加密短期交付、下载审计、通知去重、限流、监控和本地治理证据分阶段证明；"
                "一个 CSV、下载按钮或 export ready 看板太晚发现越权、漏导、过导、泄露、保留例外误处理或不可审计下载。"
            ),
            "task_scope": f"范围固定为 GDPR/CCPA DSAR data export：{task}。不扩展成 data deletion、通用 notification deliverability、data residency 或 BI reporting。",
            "success_surface": (
                "成功意味着用户、管理员或 API 发起 subject access request 后，身份验证和权限正确；profile、billing、orders、messages、attachments 和 audit-visible metadata 覆盖完整；"
                "其他用户和其他 tenant 被排除；PII/secret redaction 与 legal hold / retention exceptions 正确；async export job 可重试、取消、超时和幂等；导出文件加密、签名 URL 短期有效并会过期清理；下载审计、通知去重、rate limit、monitoring 和 local governance 都有证据。"
            ),
            "fake_done_risks": (
                "必须阻断 CSV-only、download-button-only、dashboard-ready-only、request/auth proof 缺失、scope coverage 缺失、tenant/user negatives 缺失、redaction 缺失、legal-hold exception 缺失、async lifecycle 缺失、encrypted expiring file proof 缺失、download audit 缺失、duplicate notifications、rate limit 缺失、monitoring 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 DSAR request fixtures、user/admin/API permission negatives、scope inventory matrix、profile/billing/orders/messages/attachments/audit metadata parity、cross-user/cross-tenant negatives、redaction samples、legal hold/retention exception fixtures、async job retry/cancel/timeout/idempotency proof、encrypted file and signed URL expiry checks、expiry cleanup proof、download audit rows、notification send/suppress logs、rate-limit negatives、monitoring alerts 和 local-governance evidence。"
                "每条 DSAR export claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "DSAR Export Contract Inspector 先固定 privacy export proof targets；Privacy Export Builder 读取 contract handoff 后实现；"
                "Export Scope Inspector 与 Access Retention Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 export 格式 polish 或非关键 provider sample 可作为 Residual risk 留下并指定 owner/follow-up；缺少身份/权限、导出范围、租户/用户负例、redaction、retention/legal hold、async lifecycle、加密过期交付、下载审计、通知去重、rate limit、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "隐私边界、scope coverage、负向越权证据、retention 例外、加密过期交付和审计证据优先于快速给出 CSV；速度不能覆盖漏导、过导、泄露、不可撤销链接、重复通知或不可审计下载。",
            "local_governance": (
                "若存在项目本地治理入口，DSAR Export Contract Inspector 与 Privacy Export Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/privacy/access/retention/operations 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "DSAR Export Contract Inspector 固定 request/auth/scope/redaction/retention/async/delivery/audit proof targets；Privacy Export Builder 只基于 handoff 实现；"
                "Export Scope Inspector 反证 coverage、format parity、partial failure、cross-user/cross-tenant claims；Access Retention Audit Inspector 验证 auth/permission negatives、redaction、legal hold/retention exceptions、async retry/cancel/timeout、encryption/signed URL expiry、cleanup、download audit、notification dedupe、rate limit、monitoring 和 governance；GateKeeper 对浅层导出证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 DSAR Export Contract Inspector -> Privacy Export Builder -> [Export Scope Inspector + Access Retention Audit Inspector] -> DSAR Export GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 data-export、privacy-redaction、permission-auth、tenant-isolation、deletion-retention、async-job-lifecycle、idempotency、audit-log、message-delivery、rate-limit、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；privacy request model、auth/permission model、data sources、export job runner、storage/signed URL layer、audit writer、notification path、rate limiter、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque DSAR data export se prueba con auth, scope coverage, tenant/user negatives, redaction, retention exceptions, async jobs, encrypted expiry delivery, audit, notifications, rate limits, monitoring y governance.",
            "task_scope": f"Alcance limitado a GDPR/CCPA DSAR data export: {task}; no data deletion, notification deliverability, data residency ni BI reporting genéricos.",
            "success_surface": "Éxito significa request user/admin/API con identidad y permisos, scope profile/billing/orders/messages/attachments/audit metadata, tenant/user negatives, redaction, legal hold/retention, async retry/cancel/timeout, encrypted signed URL expiry, cleanup, download audit, notification dedupe, rate limits, monitoring y governance.",
            "fake_done_risks": "Bloquear CSV-only, download-button-only, dashboard-ready-only, missing auth, scope, tenant/user negatives, redaction, legal hold, async lifecycle, encrypted expiry file, download audit, duplicate notifications, rate limits, monitoring o governance.",
            "evidence_preferences": "Preferir fixtures DSAR, permission negatives, scope matrix, data-source parity, tenant/user negatives, redaction samples, retention exceptions, async job proof, encryption/signed URL expiry, cleanup, download audit, notification logs, rate-limit negatives, monitoring y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "DSAR Export Contract Inspector fija targets; Privacy Export Builder implementa desde handoff; Export Scope y Access Retention Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de auth, scope, tenant/user negatives, redaction, retention, async lifecycle, encrypted delivery, audit, notifications, rate limit, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Privacy boundaries, scope coverage, negative evidence, retention exceptions, encrypted expiry delivery y audit proof vencen un CSV rápido.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Scope Inspector refuta coverage/tenant/user/format; Access Retention Audit verifica auth, redaction, retention, async, delivery, audit, notifications, rate limits, monitoring y governance; GateKeeper falla cerrado.",
            "workflow_shape": "DSAR Export Contract Inspector -> Privacy Export Builder -> [Export Scope Inspector + Access Retention Audit Inspector] -> DSAR Export GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; request model, auth, data sources, export runner, storage, audit, notification, rate limiter, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because DSAR / subject access data export readiness is proven through identity and permission checks, export scope, cross-user/cross-tenant negatives, PII/secret redaction, legal hold / retention exceptions, async job lifecycle, encrypted short-lived delivery, download audit, notification dedupe, rate limits, monitoring, and governance across staged handoffs. "
            "A CSV, download button, or export-ready dashboard arrives too late to catch unauthorized export, missing sources, over-export, privacy leaks, retention-exception errors, non-expiring links, or unaudited downloads."
        ),
        "task_scope": f"Scope stays on GDPR/CCPA DSAR data export: {task}. The Loop should not become data deletion, generic notification deliverability, data residency, or BI reporting.",
        "success_surface": (
            "Success means user, admin, or API subject access requests authenticate and authorize correctly; profile, billing, orders, messages, attachments, and audit-visible metadata are covered; other users and tenants are excluded; PII/secrets are redacted; legal hold and retention exceptions behave correctly; async export jobs can retry, cancel, timeout, and remain idempotent; files are encrypted, signed URLs expire, expired files are cleaned up, downloads are audited, notifications dedupe, rate limits work, and monitoring plus local governance are evidenced."
        ),
        "fake_done_risks": (
            "Block CSV-only, download-button-only, dashboard-ready-only, missing request/auth proof, missing scope coverage, missing tenant/user negatives, missing redaction, missing legal-hold exception, missing async lifecycle, missing encrypted expiring file proof, missing download audit, duplicate notifications, missing rate limits, missing monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer DSAR request fixtures, user/admin/API permission negatives, scope inventory matrices, profile/billing/orders/messages/attachments/audit metadata parity, cross-user/cross-tenant negatives, redaction samples, legal hold/retention exception fixtures, async job retry/cancel/timeout/idempotency proof, encrypted file and signed URL expiry checks, expiry cleanup proof, download audit rows, notification send/suppress logs, rate-limit negatives, monitoring alerts, and local-governance evidence. "
            "Classify each DSAR export claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "DSAR Export Contract Inspector first freezes privacy export proof targets; Privacy Export Builder implements from that handoff; Export Scope Inspector and Access Retention Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor export format polish or non-critical provider samples may remain only with owner/follow-up; missing identity/permission, scope, tenant/user negatives, redaction, retention/legal hold, async lifecycle, encrypted expiring delivery, download audit, notification dedupe, rate-limit, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Privacy boundaries, scope coverage, negative authorization evidence, retention exceptions, encrypted expiring delivery, and audit proof beat quickly producing a CSV; speed cannot hide missing sources, over-export, leaks, non-expiring links, duplicate notifications, or unaudited downloads."
        ),
        "local_governance": (
            "If project-local governance markers are present, DSAR Export Contract Inspector and Privacy Export Builder read applicable rules, both parallel Inspectors verify related design/test/privacy/access/retention/operations obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "DSAR Export Contract Inspector freezes request/auth/scope/redaction/retention/async/delivery/audit proof targets; Privacy Export Builder implements only from that handoff; Export Scope Inspector refutes coverage, format parity, partial failure, cross-user, and cross-tenant claims; Access Retention Audit Inspector verifies auth/permission negatives, redaction, legal hold/retention exceptions, async retry/cancel/timeout, encryption/signed URL expiry, cleanup, download audit, notification dedupe, rate limits, monitoring, and governance; GateKeeper fails closed on shallow export proof."
        ),
        "workflow_shape": (
            "Use DSAR Export Contract Inspector -> Privacy Export Builder -> [Export Scope Inspector + Access Retention Audit Inspector] -> DSAR Export GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries data-export, privacy-redaction, permission-auth, tenant-isolation, deletion-retention, async-job-lifecycle, idempotency, audit-log, message-delivery, rate-limit, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Privacy request model, auth/permission model, data sources, export job runner, storage/signed URL layer, audit writer, notification path, rate limiter, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _support_ticket_sla_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 support ticket triage / SLA escalation 的真实完成要通过 email/API import、dedupe/merge、queue lifecycle、claim/assign/priority/status permissions、SLA clock boundary、breach escalation、manager queue health、notification dedupe/suppression、audit notes、tenant isolation、PII redaction、monitoring 和 local governance 证据分阶段证明；"
                "Kanban 页面、manager dashboard、queued/open 状态或一次通知太晚发现重复工单、错误领取/分配、SLA 计时漂移、升级漏发、通知重复、跨租户泄露、PII 未脱敏或审计不可追踪。"
            ),
            "task_scope": f"范围固定为 support ticket triage / SLA escalation dashboard：{task}。不扩展成完整客服平台、通用通知系统或 broad BI reporting。",
            "success_surface": (
                "成功意味着 ticket 从 email/API 导入后能 dedupe/merge 并入队，agent 按权限领取、分配、改 priority/status，SLA clock、暂停/恢复、breach escalation 正确，manager queue health 可对账，客户与负责人通知不会重复，audit notes 可追踪，tenant isolation 和 PII redaction 有负向证据。"
            ),
            "fake_done_risks": (
                "必须阻断 Kanban-only、manager-dashboard-only、queued/open status-only、missing email/API dedupe、missing lifecycle transitions、missing SLA boundary/breach escalation、missing permission negatives、missing tenant isolation、missing notification suppression、missing audit notes、missing PII redaction、missing monitoring 或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 email/API import fixtures、dedupe/idempotency proof、state-machine transition tests、claim/assign/priority/status permission negatives、tenant isolation negatives、SLA clock boundary and breach escalation tests、queue health reconciliation、notification send/suppress logs、audit notes、PII redaction negatives、monitoring alerts 和 local-governance evidence。"
                "每条 support ticket claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Support Ticket Contract Inspector 先固定 lifecycle/SLA proof targets；Ticket SLA Builder 读取 contract handoff 后实现；"
                "Ticket Lifecycle Inspector 与 Access Notification Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 dashboard polish、额外队列表格字段或非关键报表维度可作为 Residual risk 留下并指定 owner/follow-up；缺少导入去重、状态机、权限/租户负例、SLA breach escalation、通知去重、audit/PII、monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "ticket lifecycle、SLA escalation、权限/租户边界、通知去重和审计/隐私证据优先于快速做一个 Kanban 或 manager dashboard；速度不能覆盖状态机薄弱、SLA 漂移、重复通知、串租户、PII 泄露或不可审计处理。",
            "local_governance": (
                "若存在项目本地治理入口，Support Ticket Contract Inspector 与 Ticket SLA Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/access/privacy/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Support Ticket Contract Inspector 固定 import/dedupe/lifecycle/permission/SLA/escalation/notification/audit/privacy proof targets；Ticket SLA Builder 只基于 handoff 实现；"
                "Ticket Lifecycle Inspector 反证 import dedupe、state transitions、queue health、SLA clock、breach escalation 和 status-only claims；Access Notification Audit Inspector 验证 permissions、tenant negatives、notification dedupe/suppression、audit notes、PII redaction、monitoring 和 governance；GateKeeper 对浅层 dashboard 证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Support Ticket Contract Inspector -> Ticket SLA Builder -> [Ticket Lifecycle Inspector + Access Notification Audit Inspector] -> Support Ticket GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 support-ticket-lifecycle、sla-escalation、idempotency、queue-recovery、permission-auth、tenant-isolation、message-delivery、audit-log、privacy-redaction、monitoring、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；ticket import source、queue/store、permission model、SLA scheduler/clock、notification provider/logs、audit/logging、PII redaction、monitoring 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque support ticket SLA se prueba con import email/API, dedupe, lifecycle, permissions, SLA clock, breach escalation, queue health, notification dedupe, audit, tenant isolation, PII redaction, monitoring y governance.",
            "task_scope": f"Alcance limitado a support ticket triage / SLA escalation dashboard: {task}; sin plataforma completa de soporte ni sistema genérico de notificaciones.",
            "success_surface": "Éxito significa import email/API con dedupe/merge, queue lifecycle, claim/assign/priority/status permissions, SLA clock and breach escalation, queue health reconciliation, notification suppression, audit notes, tenant isolation y PII redaction probados.",
            "fake_done_risks": "Bloquear Kanban-only, manager-dashboard-only, status-only, missing dedupe, lifecycle, SLA breach escalation, permission/tenant negatives, notification suppression, audit/PII, monitoring o governance.",
            "evidence_preferences": "Preferir import fixtures, dedupe/idempotency, state-machine tests, permission and tenant negatives, SLA boundary and escalation tests, queue health reconciliation, notification send/suppress logs, audit notes, PII negatives, monitoring y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Support Ticket Contract Inspector fija targets; Ticket SLA Builder implementa desde handoff; Ticket Lifecycle y Access Notification Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de import dedupe, lifecycle, permissions/tenant negatives, SLA escalation, notification dedupe, audit/PII, monitoring o governance fail closed.",
            "judgment_tradeoffs": "Lifecycle, SLA escalation, access boundaries, notification dedupe, audit/privacy proof beats a fast Kanban or dashboard.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Lifecycle refuta import/state/SLA/queue claims; Access Notification Audit verifica permissions, tenant negatives, notification dedupe, audit, PII, monitoring y governance; GateKeeper falla cerrado.",
            "workflow_shape": "Support Ticket Contract Inspector -> Ticket SLA Builder -> [Ticket Lifecycle Inspector + Access Notification Audit Inspector] -> Support Ticket GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; ticket import, queue/store, permission model, SLA scheduler, notification provider/logs, audit, PII redaction, monitoring y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because support ticket triage / SLA escalation is proven through email/API import, dedupe/merge, queue lifecycle, claim/assign/priority/status permissions, SLA clock boundaries, breach escalation, manager queue health, notification dedupe/suppression, audit notes, tenant isolation, PII redaction, monitoring, and local-governance evidence over staged handoffs. "
            "A Kanban page, manager dashboard, queued/open status, or one notification arrives too late to catch duplicate tickets, bad assignment, SLA drift, missed escalation, duplicate notifications, cross-tenant leakage, unredacted PII, or unauditable handling."
        ),
        "task_scope": (
            f"Scope stays on support ticket triage / SLA escalation dashboard: {task}. The Loop should not expand into a full support platform, generic notification system, or broad BI reporting."
        ),
        "success_surface": (
            "Success means tickets imported from email/API dedupe/merge and enqueue correctly; agents can claim, assign, and change priority/status only through permissions; SLA clock pause/resume, breach escalation, and queue health reconciliation are correct; customer and owner notifications are not duplicated; audit notes are traceable; tenant isolation and PII redaction have negative evidence."
        ),
        "fake_done_risks": (
            "Block Kanban-only, manager-dashboard-only, queued/open status-only, missing email/API dedupe, missing lifecycle transitions, missing SLA boundary or breach escalation proof, missing permission negatives, missing tenant isolation, missing notification suppression, missing audit notes, missing PII redaction, missing monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer email/API import fixtures, dedupe/idempotency proof, state-machine transition tests, claim/assign/priority/status permission negatives, tenant isolation negatives, SLA clock boundary and breach escalation tests, queue health reconciliation, notification send/suppress logs, audit notes, PII redaction negatives, monitoring alerts, and local-governance evidence. "
            "Classify each support ticket claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Support Ticket Contract Inspector first freezes lifecycle/SLA proof targets; Ticket SLA Builder implements from that handoff; Ticket Lifecycle Inspector and Access Notification Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard polish, extra queue table fields, or non-critical reporting dimensions may remain only with owner/follow-up; missing import dedupe, lifecycle, permission/tenant negatives, SLA breach escalation, notification dedupe, audit/PII, monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Ticket lifecycle, SLA escalation, permission and tenant boundaries, notification dedupe, and audit/privacy proof beats quickly shipping a Kanban or manager dashboard; speed cannot hide weak state machines, SLA drift, duplicate notifications, tenant leaks, PII exposure, or unauditable handling."
        ),
        "local_governance": (
            "If project-local governance markers are present, Support Ticket Contract Inspector and Ticket SLA Builder read applicable rules, both parallel Inspectors verify related design/test/access/privacy/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Support Ticket Contract Inspector freezes import/dedupe/lifecycle/permission/SLA/escalation/notification/audit/privacy proof targets; Ticket SLA Builder implements only from that handoff; Ticket Lifecycle Inspector refutes import dedupe, state transitions, queue health, SLA clock, breach escalation, and status-only claims; Access Notification Audit Inspector verifies permissions, tenant negatives, notification dedupe/suppression, audit notes, PII redaction, monitoring, and governance; GateKeeper fails closed on shallow dashboard proof."
        ),
        "workflow_shape": (
            "Use Support Ticket Contract Inspector -> Ticket SLA Builder -> [Ticket Lifecycle Inspector + Access Notification Audit Inspector] -> Support Ticket GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries support-ticket-lifecycle, sla-escalation, idempotency, queue-recovery, permission-auth, tenant-isolation, message-delivery, audit-log, privacy-redaction, monitoring, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Ticket import source, queue/store, permission model, SLA scheduler/clock, notification provider/logs, audit/logging, PII redaction, monitoring, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _usage_quota_metering_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 SaaS API usage metering / plan quota enforcement 的真实完成要通过 concurrent API calls、duplicate usage events、retry/idempotency、plan upgrade/downgrade、billing reset timezone、grace/hard limits、permission-safe over-limit errors、ledger/invoice/provider reconciliation、audit、monitoring 和 migration 证据分阶段证明；"
                "dashboard、single 429、cron reset 或 provider total 太晚发现少计/多计、重复扣量、窗口时区漂移、套餐变更错误、权限绕过或不可对账。"
            ),
            "task_scope": f"范围固定为 SaaS API usage metering / plan quota enforcement：{task}。不扩展成通用 billing platform、payment webhook ingestion 或 unrelated analytics dashboard。",
            "success_surface": (
                "成功意味着同一 org 在 concurrent API calls、duplicate usage events、retry、plan upgrade/downgrade、billing period reset、grace/hard limits 下不会超用或少计，quota window/reset timezone 正确，usage ledger/invoice/subscription provider 可对账，over-limit error 权限安全，低余量/超限告警和 audit fields 可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 dashboard-only usage、single 429、cron reset only、provider total only、duplicate-event proof 缺失、concurrency proof 缺失、plan-change proof 缺失、reset timezone proof 缺失、reconciliation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 concurrent API usage tests、duplicate usage event idempotency fixtures、retry proof、plan upgrade/downgrade samples、billing reset timezone proof、grace/hard limit negatives、permission-safe over-limit errors、ledger/invoice/provider reconciliation artifacts、low/exhausted alerts、audit metering refs、migration compatibility 和 local-governance evidence。"
                "每条 usage/quota claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Quota Contract Inspector 先固定 usage/quota proof targets；Usage Metering Builder 读取 contract handoff 后实现；"
                "Quota Race Inspector 与 Billing Reconciliation Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 dashboard copy、额外 usage dimensions 或超出本轮的 legacy billing polish 可作为 Residual risk 留下并指定 owner/follow-up；缺少并发计量、duplicate idempotency、plan-change、reset timezone、限额、对账、audit/monitoring、migration 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "计量正确性、幂等、窗口、限额、权限安全错误和对账证据优先于快速展示用量或返回一次 429；速度不能覆盖重复事件、时区漂移、套餐变更、provider total-only 或不可审计 usage event。",
            "local_governance": (
                "若存在项目本地治理入口，Quota Contract Inspector 与 Usage Metering Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/billing/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Quota Contract Inspector 固定 schema/idempotency/org-plan-window/concurrency/reset/limit/reconciliation/audit proof targets；Usage Metering Builder 只基于 handoff 实现；"
                "Quota Race Inspector 反证 concurrent calls、duplicate events、retry、limits、reset timezone 和 permission-safe errors；Billing Reconciliation Inspector 验证 plan changes、ledger/invoice/provider reconciliation、alerts、audit、migration 和 governance；GateKeeper 对浅层 usage 证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Quota Contract Inspector -> Usage Metering Builder -> [Quota Race Inspector + Billing Reconciliation Inspector] -> Usage Quota GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 quota-metering、idempotency、conflict-resolution、permission-auth、ledger-reconciliation、payment-refund-billing、audit-log、monitoring、backward-compatibility、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；usage event source、quota store、billing provider integration、invoice/ledger model、audit/logging、monitoring、migration path 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque usage quota se prueba por concurrency, duplicates, retry/idempotency, plan changes, reset timezone, limits, permission-safe errors, reconciliation, audit, monitoring y migration.",
            "task_scope": f"Alcance limitado a SaaS API usage metering / plan quota enforcement: {task}; sin billing platform amplio ni payment webhook ingestion.",
            "success_surface": "Éxito significa no overuse/undercount bajo concurrency, duplicates, retries, plan changes, reset windows, limits; reconciliation ledger/invoice/provider, permission-safe errors, alerts y audit probados.",
            "fake_done_risks": "Bloquear dashboard-only, single 429, cron reset, provider total only, missing duplicates, concurrency, plan-change, reset timezone, reconciliation, audit/monitoring, migration o governance.",
            "evidence_preferences": "Preferir concurrency tests, duplicate idempotency, retry proof, plan changes, reset timezone, limits negatives, permission-safe errors, reconciliation artifacts, alerts, audit refs, migration y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Quota Contract Inspector fija targets; Usage Metering Builder implementa desde handoff; Quota Race y Billing Reconciliation inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de concurrency, duplicate idempotency, plan-change, reset timezone, limits, reconciliation, audit/monitoring, migration o governance fail closed.",
            "judgment_tradeoffs": "Metering correctness, idempotency, windows, limits, permission-safe errors and reconciliation proof beats dashboard or single 429 progress.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Quota Race refuta concurrency/duplicates/retries/limits/windows; Billing Reconciliation verifica plan changes/reconciliation/alerts/audit/migration; GateKeeper falla cerrado.",
            "workflow_shape": "Quota Contract Inspector -> Usage Metering Builder -> [Quota Race Inspector + Billing Reconciliation Inspector] -> Usage Quota GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; usage source, quota store, billing provider, invoice/ledger, audit, monitoring, migration y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because SaaS API usage metering / plan quota enforcement is proven through concurrent API calls, duplicate usage events, retry/idempotency, plan upgrade/downgrade, billing reset timezone, grace/hard limits, permission-safe over-limit errors, ledger/invoice/provider reconciliation, audit, monitoring, and migration evidence over staged handoffs. "
            "A dashboard, single 429, cron reset, or provider total arrives too late to catch overuse, undercounting, duplicate decrement, reset-window drift, plan-change errors, permission bypass, or unreconciled usage events."
        ),
        "task_scope": (
            f"Scope stays on SaaS API usage metering / plan quota enforcement: {task}. The Loop should not expand into a broad billing platform, payment webhook ingestion task, or unrelated analytics dashboard."
        ),
        "success_surface": (
            "Success means the same org cannot overuse or be undercounted under concurrent API calls, duplicate usage events, retries, plan upgrade/downgrade, billing period reset, grace and hard limits; quota window/reset timezone is correct; usage ledger/invoice/subscription provider reconcile; over-limit errors are permission-safe; low/exhausted alerts and audit fields are reviewable."
        ),
        "fake_done_risks": (
            "Block dashboard-only usage, single 429, cron reset only, provider total only, missing duplicate-event proof, missing concurrency proof, missing plan-change proof, missing reset timezone proof, missing reconciliation, missing audit/monitoring, missing migration, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer concurrent API usage tests, duplicate usage event idempotency fixtures, retry proof, plan upgrade/downgrade samples, billing reset timezone proof, grace/hard limit negatives, permission-safe over-limit errors, ledger/invoice/provider reconciliation artifacts, low/exhausted alerts, audit metering refs, migration compatibility, and local-governance evidence. "
            "Classify each usage/quota claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Quota Contract Inspector first freezes usage/quota proof targets; Usage Metering Builder implements from that handoff; Quota Race Inspector and Billing Reconciliation Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor dashboard copy, extra usage dimensions, or out-of-scope legacy billing polish may remain only with owner/follow-up; missing concurrency metering, duplicate idempotency, plan-change, reset timezone, limit, reconciliation, audit/monitoring, migration, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Metering correctness, idempotency, reset windows, quota limits, permission-safe errors, and reconciliation proof beats quickly showing usage or returning one 429; speed cannot hide duplicate events, timezone drift, plan changes, provider-total-only accounting, or unauditable usage events."
        ),
        "local_governance": (
            "If project-local governance markers are present, Quota Contract Inspector and Usage Metering Builder read applicable rules, both parallel Inspectors verify related design/test/billing/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Quota Contract Inspector freezes schema/idempotency/org-plan-window/concurrency/reset/limit/reconciliation/audit proof targets; Usage Metering Builder implements only from that handoff; Quota Race Inspector refutes concurrent calls, duplicate events, retry, limits, reset timezone, and permission-safe errors; Billing Reconciliation Inspector verifies plan changes, ledger/invoice/provider reconciliation, alerts, audit, migration, and governance; GateKeeper fails closed on shallow usage proof."
        ),
        "workflow_shape": (
            "Use Quota Contract Inspector -> Usage Metering Builder -> [Quota Race Inspector + Billing Reconciliation Inspector] -> Usage Quota GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries quota-metering, idempotency, conflict-resolution, permission-auth, ledger-reconciliation, payment-refund-billing, audit-log, monitoring, backward-compatibility, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Usage event source, quota store, billing provider integration, invoice/ledger model, audit/logging, monitoring, migration path, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _subscription_entitlement_billing_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 B2B SaaS 订阅升级/降级和权益生效的真实完成要通过 plan-change lifecycle、proration/credit memo、invoice/ledger/provider reconciliation、team entitlement propagation、quota/history preservation、权限/tenant 负向、provider webhook replay、幂等、audit、rollback、monitoring 和 governance 证据分阶段证明；"
                "按钮能点、checkout success、provider total 或 happy path 太晚发现账单金额错、权益不同步、降级提前/延迟错误、重复请求、provider replay 或不可对账。"
            ),
            "task_scope": f"范围固定为 B2B SaaS subscription upgrade/downgrade entitlement and proration：{task}。不扩展成普通 notification deliverability、usage quota metering、tax calculation、payment webhook ingestion 或 refund repair。",
            "success_surface": (
                "成功意味着升级立即正确生效，降级按下个计费周期或 period end 生效；proration、credit memo、invoice totals、ledger entries 和 provider 状态可对账；试用期、宽限期、billing period boundary 正确；重复点击和 webhook 延迟/重复/乱序保持幂等；团队成员权益、功能权限、历史用量和 quota 不丢；权限与 tenant 负向、audit fields、rollback/migration、monitoring 和 local governance 都可复验。"
            ),
            "fake_done_risks": (
                "必须阻断 button-only、checkout-success-only、provider-total-only、happy-path plan change、降级延迟生效证明缺失、proration/credit memo 缺失、invoice/ledger/provider 对账缺失、权益传播缺失、quota/history proof 缺失、权限或 tenant 负向缺失、webhook replay/idempotency 缺失、rollback/monitoring 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 plan-change state machine fixtures、upgrade immediate / downgrade next-cycle cases、proration and credit memo calculation artifacts、invoice/ledger/provider reconciliation、trial/grace/billing-period boundary samples、duplicate-click and webhook replay/out-of-order idempotency fixtures、team-member entitlement propagation checks、quota/history preservation proof、permission/tenant negative cases、audit samples、rollback/migration proof、monitoring alerts 和 local-governance evidence。"
                "每条 subscription entitlement claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Subscription Contract Inspector 先固定订阅/权益/账单 proof targets；Entitlement Billing Builder 读取 contract handoff 后实现；"
                "Entitlement State Inspector 与 Billing Proration Reconciliation Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 UI polish、额外 provider locale sample 或非关键 copy 可作为 Residual risk 留下并指定 owner/follow-up；缺少账单金额、权益状态、降级时机、provider replay、权限负向、对账、rollback/monitoring 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "账单金额、权益状态、降级时机、幂等、provider replay、权限负向、对账和审计监控证据优先于快速做出按钮或 checkout success；速度不能覆盖 provider-only 或 happy-path-only 证明。",
            "local_governance": (
                "若存在项目本地治理入口，Subscription Contract Inspector 与 Entitlement Billing Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/billing/permission/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Subscription Contract Inspector 固定 plan-change、proration、invoice/ledger/provider、trial/grace、webhook/idempotency、entitlement、quota/history、permission、audit、rollback 和 monitoring targets；Entitlement Billing Builder 只基于 handoff 实现；"
                "Entitlement State Inspector 反证权益时机、团队传播、quota/history 和权限/tenant；Billing Proration Reconciliation Inspector 验证 proration、credit memo、invoice/ledger/provider、webhook replay、rollback 和 monitoring；GateKeeper 对浅层 subscription 证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Subscription Contract Inspector -> Entitlement Billing Builder -> [Entitlement State Inspector + Billing Proration Reconciliation Inspector] -> Subscription Entitlement GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 subscription-entitlement、payment-refund-billing、ledger-reconciliation、provider-contract、idempotency、retry-timeout、permission-auth、tenant-isolation、quota-metering、audit-log、monitoring、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；subscription store、billing provider、invoice/ledger model、entitlement gates、quota/history store、permissions、audit/logging、monitoring、migration path 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque subscription entitlement/proration se prueba por lifecycle, proration/credit memo, reconciliation, entitlements, quota/history, permission negatives, webhook replay, idempotency, audit, rollback, monitoring y governance.",
            "task_scope": f"Alcance limitado a B2B SaaS subscription upgrade/downgrade entitlement and proration: {task}; sin notification, quota metering, tax, webhook ingestion ni refund repair como tarea principal.",
            "success_surface": "Éxito significa upgrade inmediato, downgrade next-cycle/period-end, proration, credit memo, invoice/ledger/provider reconciliation, trial/grace boundaries, duplicate-click/webhook replay idempotency, team entitlements, quota/history, permission/tenant negatives, audit, rollback, monitoring y governance probados.",
            "fake_done_risks": "Bloquear button-only, checkout-success-only, provider-total-only, happy path, missing downgrade delay, proration/credit memo, reconciliation, entitlements, quota/history, permission/tenant negatives, webhook replay, rollback/monitoring o governance.",
            "evidence_preferences": "Preferir fixtures de state machine, upgrade/downgrade timing, proration/credit memo artifacts, reconciliation, billing boundaries, webhook replay/idempotency, entitlement checks, quota/history, permission negatives, audit, rollback, monitoring y governance.",
            "execution_strategy": "Subscription Contract Inspector fija targets; Entitlement Billing Builder implementa; Entitlement State y Billing Proration Reconciliation inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de billing amount, entitlement state, downgrade timing, provider replay, permissions, reconciliation, rollback/monitoring o governance fail closed.",
            "judgment_tradeoffs": "Billing amount, entitlement state, timing, idempotency, provider replay, permissions, reconciliation, audit and monitoring proof beat button or checkout success progress.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Entitlement State refuta entitlement timing/quota/permissions; Billing Reconciliation verifica proration/provider/replay/rollback; GateKeeper falla cerrado.",
            "workflow_shape": "Subscription Contract Inspector -> Entitlement Billing Builder -> [Entitlement State Inspector + Billing Proration Reconciliation Inspector] -> Subscription Entitlement GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; subscription store, billing provider, invoice/ledger, entitlements, quota/history, permissions, audit, monitoring, migration y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because B2B SaaS subscription upgrade/downgrade and entitlement activation is proven through plan-change lifecycle, proration/credit memo, invoice/ledger/provider reconciliation, team entitlement propagation, quota/history preservation, permission and tenant negatives, provider webhook replay, idempotency, audit, rollback, monitoring, and governance evidence over staged handoffs. "
            "A clickable button, checkout success, provider total, or happy path arrives too late to catch wrong billing amounts, stale entitlements, downgrade timing errors, duplicate requests, provider replay gaps, or unreconciled state."
        ),
        "task_scope": (
            f"Scope stays on B2B SaaS subscription upgrade/downgrade entitlement and proration: {task}. The Loop should not route the main task to notification deliverability, usage quota metering, tax calculation, payment webhook ingestion, or refund repair."
        ),
        "success_surface": (
            "Success means upgrades take effect immediately, downgrades take effect at the next cycle or period end, proration, credit memo, invoice totals, ledger entries, and provider state reconcile, trial/grace/billing-period boundaries behave correctly, duplicate clicks and delayed/duplicate/out-of-order webhooks stay idempotent, team-member entitlements, feature access, historical usage, and quota are preserved, permission and tenant negatives block unsafe changes, and audit, rollback/migration, monitoring, and local governance are reviewable."
        ),
        "fake_done_risks": (
            "Block button-only, checkout-success-only, provider-total-only, happy-path plan change, missing downgrade-delayed proof, missing proration/credit memo, missing invoice/ledger/provider reconciliation, missing entitlement propagation, missing quota/history proof, missing permission or tenant negatives, missing webhook replay/idempotency, missing rollback/monitoring, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer plan-change state machine fixtures, upgrade immediate / downgrade next-cycle cases, proration and credit memo calculation artifacts, invoice/ledger/provider reconciliation, trial/grace/billing-period boundary samples, duplicate-click and webhook replay/out-of-order idempotency fixtures, team-member entitlement propagation checks, quota/history preservation proof, permission/tenant negative cases, audit samples, rollback/migration proof, monitoring alerts, and local-governance evidence. "
            "Classify each subscription entitlement claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Subscription Contract Inspector first freezes subscription/entitlement/billing proof targets; Entitlement Billing Builder implements from that handoff; Entitlement State Inspector and Billing Proration Reconciliation Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor UI polish, extra provider locale samples, or non-critical copy may remain only with owner/follow-up; missing billing amount, entitlement state, downgrade timing, provider replay, permission negatives, reconciliation, rollback/monitoring, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Billing amount, entitlement state, downgrade timing, idempotency, provider replay, permission negatives, reconciliation, audit, and monitoring proof beats quickly producing a button or checkout success; speed cannot hide provider-only or happy-path-only proof."
        ),
        "local_governance": (
            "If project-local governance markers are present, Subscription Contract Inspector and Entitlement Billing Builder read applicable rules, both parallel Inspectors verify related design/test/billing/permission/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Subscription Contract Inspector freezes plan-change, proration, invoice/ledger/provider, trial/grace, webhook/idempotency, entitlement, quota/history, permission, audit, rollback, and monitoring targets; Entitlement Billing Builder implements only from that handoff; Entitlement State Inspector refutes entitlement timing, team propagation, quota/history, and permission/tenant gaps; Billing Proration Reconciliation Inspector verifies proration, credit memo, invoice/ledger/provider, webhook replay, rollback, and monitoring; GateKeeper fails closed on shallow subscription proof."
        ),
        "workflow_shape": (
            "Use Subscription Contract Inspector -> Entitlement Billing Builder -> [Entitlement State Inspector + Billing Proration Reconciliation Inspector] -> Subscription Entitlement GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries subscription-entitlement, payment-refund-billing, ledger-reconciliation, provider-contract, idempotency, retry-timeout, permission-auth, tenant-isolation, quota-metering, audit-log, monitoring, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Subscription store, billing provider, invoice/ledger model, entitlement gates, quota/history store, permissions, audit/logging, monitoring, migration path, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _tax_calculation_compliance_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 checkout tax calculation compliance 的真实完成要通过 nexus、US sales tax、EU VAT、GST、jurisdiction/address matrix、taxability、exemption/reverse-charge、inclusive/exclusive display、rounding、invoice/refund reversal、provider fallback/idempotency、effective-date/timezone、audit、reconciliation、monitoring 和 migration 证据分阶段证明；"
                "one tax number、hardcoded rate、provider quote only 或 UI total only 太晚发现错误辖区、免税/反向征收遗漏、舍入漂移、退款冲销错误、provider fallback 不可审计或税务账本不可对账。"
            ),
            "task_scope": f"范围固定为 checkout tax calculation compliance：{task}。不扩展成通用 billing platform、payment webhook ingestion、tax report/export 或 compliance filing。",
            "success_surface": (
                "成功意味着 taxable nexus、US state sales tax、EU VAT/GST、shipping/billing address jurisdiction、digital/physical goods taxability、exemption certificate、B2B reverse charge、inclusive/exclusive display、discount/coupon/shipping/refund rounding、invoice/receipt totals、refund/credit memo reversal、provider fallback/retry/idempotency、rate effective date/timezone、provider-report reconciliation、audit fields、monitoring 和 migration 都可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 one checkout tax number、hardcoded rate、provider quote only、UI total only、jurisdiction matrix 缺失、taxability 缺失、exemption/reverse-charge 缺失、refund/reversal 缺失、rounding proof 缺失、provider fallback/idempotency 缺失、reconciliation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 jurisdiction/address matrix cases、taxability fixtures、exemption/reverse-charge samples、inclusive/exclusive display checks、discount/coupon/shipping/refund rounding negatives、invoice/receipt totals、refund/credit memo reversal proof、provider sandbox fallback/retry/idempotency evidence、effective-date/timezone proof、provider-report reconciliation artifacts、audit refs、monitoring alerts、migration compatibility 和 local-governance evidence。"
                "每条 tax calculation claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Tax Contract Inspector 先固定 tax calculation proof targets；Tax Calculation Builder 读取 contract handoff 后实现；"
                "Jurisdiction Rate Inspector 与 Invoice Reversal Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微 display copy、额外 tax category 或超出本轮的 filing/report polish 可作为 Residual risk 留下并指定 owner/follow-up；缺少 jurisdiction、taxability、exemption、rounding、refund/reversal、provider fallback/idempotency、reconciliation、audit/monitoring、migration 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "税务正确性、辖区矩阵、免税/反向征收、舍入/退款、provider resilience、对账和审计证据优先于快速显示税额；速度不能覆盖硬编码税率、provider quote-only、UI total-only 或不可复验 tax ledger。",
            "local_governance": (
                "若存在项目本地治理入口，Tax Contract Inspector 与 Tax Calculation Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/billing/tax/audit/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Tax Contract Inspector 固定 nexus/jurisdiction/taxability/exemption/display/rounding/invoice/refund/provider/audit/reconciliation proof targets；Tax Calculation Builder 只基于 handoff 实现；"
                "Jurisdiction Rate Inspector 反证 jurisdiction/address matrix、taxability、exemption/reverse-charge、provider fallback/idempotency 和 effective-date/timezone；Invoice Reversal Inspector 验证 display totals、rounding、invoice/receipt totals、refund/credit reversal、reconciliation、audit、monitoring、migration 和 governance；GateKeeper 对浅层 tax 证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Tax Contract Inspector -> Tax Calculation Builder -> [Jurisdiction Rate Inspector + Invoice Reversal Inspector] -> Tax Compliance GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 tax-compliance、provider-contract、idempotency、retry-timeout、ledger-reconciliation、payment-refund-billing、audit-log、monitoring、backward-compatibility、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；tax engine、provider integration、invoice/ledger model、refund/credit memo path、audit/logging、monitoring、migration path 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque tax calculation compliance se prueba por nexus, jurisdiction matrix, taxability, exemptions, display, rounding, refund reversal, provider fallback/idempotency, effective dates, audit, reconciliation, monitoring y migration.",
            "task_scope": f"Alcance limitado a checkout tax calculation compliance: {task}; sin billing platform amplio, payment webhook ingestion, tax report/export ni filing.",
            "success_surface": "Éxito significa nexus, sales tax/VAT/GST, address jurisdiction, taxability, exemptions, reverse charge, display, rounding, invoice/receipt totals, refund/credit reversal, provider fallback, effective-date/timezone, reconciliation, audit, monitoring y migration probados.",
            "fake_done_risks": "Bloquear one tax number, hardcoded rate, provider quote only, UI total only, missing jurisdiction, taxability, exemption, refund/reversal, rounding, provider fallback, reconciliation, audit/monitoring, migration o governance.",
            "evidence_preferences": "Preferir jurisdiction matrix, taxability fixtures, exemption/reverse-charge, display checks, rounding negatives, invoice totals, refund reversal, provider sandbox fallback/idempotency, effective-date proof, reconciliation artifacts, audit refs, monitoring, migration y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Tax Contract Inspector fija targets; Tax Calculation Builder implementa desde handoff; Jurisdiction Rate e Invoice Reversal inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de jurisdiction, taxability, exemption, rounding, refund/reversal, provider fallback, reconciliation, audit/monitoring, migration o governance fail closed.",
            "judgment_tradeoffs": "Tax correctness, jurisdiction matrix, exemption, rounding/refund, provider resilience, reconciliation and audit proof beats quickly showing one tax amount.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Jurisdiction Rate refuta matrix/taxability/exemption/provider/effective-date; Invoice Reversal verifica totals/rounding/refund/reconciliation/audit/migration; GateKeeper falla cerrado.",
            "workflow_shape": "Tax Contract Inspector -> Tax Calculation Builder -> [Jurisdiction Rate Inspector + Invoice Reversal Inspector] -> Tax Compliance GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; tax engine, provider, invoice/ledger, refund path, audit, monitoring, migration y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because checkout tax calculation compliance is proven through taxable nexus, US sales tax, EU VAT, GST, jurisdiction/address matrix, product taxability, exemptions, reverse charge, inclusive/exclusive display, rounding, invoice/refund reversal, provider fallback/idempotency, effective-date/timezone, audit, reconciliation, monitoring, and migration evidence over staged handoffs. "
            "One tax number, a hardcoded rate, provider quote only, or a UI total arrives too late to catch wrong jurisdiction, missing exemptions, rounding drift, refund reversal errors, provider fallback gaps, or unreconciled tax ledgers."
        ),
        "task_scope": (
            f"Scope stays on checkout tax calculation compliance: {task}. The Loop should not expand into a broad billing platform, payment webhook ingestion task, tax report/export, or compliance filing."
        ),
        "success_surface": (
            "Success means taxable nexus, US state sales tax, EU VAT/GST, shipping/billing address jurisdiction, digital/physical goods taxability, exemption certificates, B2B reverse charge, inclusive/exclusive display, discount/coupon/shipping/refund rounding, invoice/receipt totals, refund/credit memo reversal, provider fallback/retry/idempotency, rate effective-date/timezone, provider-report reconciliation, audit fields, monitoring, and migration are reviewable."
        ),
        "fake_done_risks": (
            "Block one checkout tax number, hardcoded rate, provider quote only, UI total only, missing jurisdiction matrix, missing taxability, missing exemption/reverse-charge, missing refund/reversal, missing rounding proof, missing provider fallback/idempotency, missing reconciliation, missing audit/monitoring, missing migration, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer jurisdiction/address matrix cases, taxability fixtures, exemption/reverse-charge samples, inclusive/exclusive display checks, discount/coupon/shipping/refund rounding negatives, invoice/receipt totals, refund/credit memo reversal proof, provider sandbox fallback/retry/idempotency evidence, effective-date/timezone proof, provider-report reconciliation artifacts, audit refs, monitoring alerts, migration compatibility, and local-governance evidence. "
            "Classify each tax calculation claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Tax Contract Inspector first freezes tax calculation proof targets; Tax Calculation Builder implements from that handoff; Jurisdiction Rate Inspector and Invoice Reversal Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor display copy, extra tax categories, or out-of-scope filing/report polish may remain only with owner/follow-up; missing jurisdiction, taxability, exemption, rounding, refund/reversal, provider fallback/idempotency, reconciliation, audit/monitoring, migration, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Tax correctness, jurisdiction matrix, exemption/reverse-charge, rounding/refund behavior, provider resilience, reconciliation, and audit proof beats quickly showing a tax amount; speed cannot hide hardcoded rates, provider-quote-only accounting, UI-total-only proof, or unauditable tax ledgers."
        ),
        "local_governance": (
            "If project-local governance markers are present, Tax Contract Inspector and Tax Calculation Builder read applicable rules, both parallel Inspectors verify related design/test/billing/tax/audit/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Tax Contract Inspector freezes nexus/jurisdiction/taxability/exemption/display/rounding/invoice/refund/provider/audit/reconciliation proof targets; Tax Calculation Builder implements only from that handoff; Jurisdiction Rate Inspector refutes jurisdiction/address matrix, taxability, exemption/reverse-charge, provider fallback/idempotency, and effective-date/timezone; Invoice Reversal Inspector verifies display totals, rounding, invoice/receipt totals, refund/credit reversal, reconciliation, audit, monitoring, migration, and governance; GateKeeper fails closed on shallow tax proof."
        ),
        "workflow_shape": (
            "Use Tax Contract Inspector -> Tax Calculation Builder -> [Jurisdiction Rate Inspector + Invoice Reversal Inspector] -> Tax Compliance GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries tax-compliance, provider-contract, idempotency, retry-timeout, ledger-reconciliation, payment-refund-billing, audit-log, monitoring, backward-compatibility, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Tax engine, provider integration, invoice/ledger model, refund/credit memo path, audit/logging, monitoring, migration path, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _auth_session_token_lifecycle_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": (
                f"任务锚点（{task}）适合 Loopora，因为 auth session/token lifecycle 的真实完成要通过 access/refresh expiry、refresh rotation/reuse detection、logout/all-device revocation、password reset/MFA invalidation、revoked/stolen/expired token negatives、cookie/CSRF/API boundaries、audit、monitoring 和 migration 证据分阶段证明；"
                "login/logout happy path、frontend-only clear、framework defaults 或 short-expiry-only 太晚发现 refresh reuse、旧 session 仍可用、撤销不生效、CSRF/API 边界漂移或不可审计 replay。"
            ),
            "task_scope": f"范围固定为 auth session/token lifecycle hardening：{task}。不扩展成完整身份平台、企业 SSO、API key rotation 或 support impersonation。",
            "success_surface": (
                "成功意味着 access token expiry、refresh token rotation/reuse detection、logout current/all-device revocation、password reset 和 MFA step-up session invalidation、expired/revoked/stolen token negatives、secure/httpOnly/SameSite cookies、CSRF/API token boundaries、tenant/device/session audit、replay/reuse alerts、backward-compatible migration 都可审计。"
            ),
            "fake_done_risks": (
                "必须阻断 login/logout happy path、frontend-only session clear、framework defaults、short-expiry-only、revoked/stolen/expired token negatives 缺失、refresh reuse proof 缺失、session invalidation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过。"
            ),
            "evidence_preferences": (
                "优先 expired/revoked/stolen token negative calls、refresh rotation/reuse fixtures、logout current/all-device revocation checks、password reset/MFA invalidation proof、cookie flag inspection、CSRF/API boundary tests、tenant/device/session audit refs、replay/reuse alerts、migration compatibility proof 和 local-governance evidence。"
                "每条 session/token claim 必须进入 Proven、Weak、Unproven、Blocking 或 Residual risk。"
            ),
            "execution_strategy": (
                "Session Token Contract Inspector 先固定 session/token proof targets；Session Token Builder 读取 contract handoff 后实现；"
                "Token Misuse Inspector 与 Session Revocation Audit Inspector 并行读取 contract 与 builder handoff；GateKeeper 汇总裁决。"
            ),
            "residual_risk_policy": (
                "轻微非关键 copy、额外设备矩阵或超出本轮的 legacy client polish 可作为 Residual risk 留下并指定 owner/follow-up；缺少 token negatives、refresh reuse detection、revocation/invalidation、cookie/CSRF/API boundary、audit/monitoring、migration 或本地治理证据必须 fail closed。"
            ),
            "judgment_tradeoffs": "session/token 安全、负向滥用证据、撤销失效闭环、审计和监控优先于快速接通登录；速度不能覆盖旧 token 仍可用、refresh reuse、frontend-only clear、框架默认或不可审计 replay。",
            "local_governance": (
                "若存在项目本地治理入口，Session Token Contract Inspector 与 Session Token Builder 必须读取适用规则，两个并行 Inspector 验证相关 design/test/security/session/monitoring 义务，"
                "GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
            ),
            "role_posture": (
                "Session Token Contract Inspector 固定 expiry、rotation/reuse、revocation/invalidation、cookie/CSRF/API、audit/monitoring/migration proof targets；Session Token Builder 只基于 handoff 实现；"
                "Token Misuse Inspector 反证 expired/revoked/stolen/replayed/reused token、refresh reuse、cookie/CSRF/API boundary 和 tenant negatives；Session Revocation Audit Inspector 验证 logout/all-device、password reset/MFA invalidation、audit、monitoring、migration 和 governance；GateKeeper 对浅层 auth 证明 fail closed。"
            ),
            "workflow_shape": (
                "采用 Session Token Contract Inspector -> Session Token Builder -> [Token Misuse Inspector + Session Revocation Audit Inspector] -> Auth Session GateKeeper。"
                "两个 Inspector 使用同一个 parallel_group、读取 contract 与 builder handoff；GateKeeper 查询 session-lifecycle、permission-auth、privacy-redaction、tenant-isolation、audit-log、monitoring、backward-compatibility、migration-rollback、negative_evidence 和 local-governance。"
            ),
            "workdir_facts": "已观察事实只限目标路径和 Workdir Snapshot；auth middleware、token store、session store、cookie/CSRF config、audit/logging、monitoring、migration path 和 test runner 必须在运行中验证后才能声称。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La ancla ({task}) encaja con Loopora porque auth session/token lifecycle se prueba por expiry, refresh rotation/reuse, revocation, invalidation, token negatives, cookie/CSRF/API boundaries, audit, monitoring y migration.",
            "task_scope": f"Alcance limitado a auth session/token lifecycle hardening: {task}; sin identity platform amplio, enterprise SSO, API key rotation ni support impersonation.",
            "success_surface": "Éxito significa access expiry, refresh rotation/reuse detection, logout revocation, password reset/MFA invalidation, token negatives, cookie flags, CSRF/API boundaries, audit, alerts y migration probados.",
            "fake_done_risks": "Bloquear login/logout happy path, frontend-only clear, framework defaults, short-expiry-only, missing token negatives, refresh reuse proof, invalidation, audit/monitoring, migration o governance.",
            "evidence_preferences": "Preferir token negative calls, refresh reuse fixtures, logout revocation, password reset/MFA invalidation, cookie inspection, CSRF/API tests, audit refs, alerts, migration proof y governance; clasificar cada claim como Proven, Weak, Unproven, Blocking o Residual risk.",
            "execution_strategy": "Session Token Contract Inspector fija targets; Session Token Builder implementa desde handoff; Token Misuse y Session Revocation Audit inspeccionan en paralelo; GateKeeper decide.",
            "residual_risk_policy": "Faltas de token negatives, refresh reuse, revocation/invalidation, cookie/CSRF/API boundary, audit/monitoring, migration o governance fail closed.",
            "judgment_tradeoffs": "Session/token security, misuse negatives, revocation closure, audit and monitoring proof beats fast login progress.",
            "local_governance": "Contract Inspector y Builder leen reglas locales; ambos Inspectors verifican obligaciones; GateKeeper bloquea governance omitida.",
            "role_posture": "Contract Inspector congela targets; Builder implementa; Token Misuse refuta token misuse/boundaries; Revocation Audit verifica logout/invalidation/audit/migration; GateKeeper falla cerrado.",
            "workflow_shape": "Session Token Contract Inspector -> Session Token Builder -> [Token Misuse Inspector + Session Revocation Audit Inspector] -> Auth Session GateKeeper con parallel_group explícito.",
            "workdir_facts": "Hechos observados limitados al path y snapshot; auth middleware, token/session store, cookie/CSRF config, audit, monitoring, migration y runner deben verificarse durante ejecución.",
            "open_questions": "Esperando confirmación explícita del acuerdo.",
        }
    return {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because auth session/token lifecycle completion is proven through access/refresh expiry, refresh rotation and reuse detection, logout/all-device revocation, password reset/MFA invalidation, revoked/stolen/expired token negatives, cookie/CSRF/API boundaries, audit, monitoring, and migration evidence over staged handoffs. "
            "Login/logout happy path, frontend-only clear, framework defaults, or short-expiry-only changes arrive too late to catch refresh reuse, old sessions that still work, failed revocation, CSRF/API boundary drift, or unauditable replay."
        ),
        "task_scope": (
            f"Scope stays on auth session/token lifecycle hardening: {task}. The Loop should not expand into a full identity platform, enterprise SSO, API key rotation, or support impersonation."
        ),
        "success_surface": (
            "Success means access token expiry, refresh token rotation/reuse detection, logout current/all-device revocation, password reset and MFA step-up session invalidation, expired/revoked/stolen token negatives, secure/httpOnly/SameSite cookies, CSRF/API token boundaries, tenant/device/session audit, replay/reuse alerts, and backward-compatible migration are reviewable."
        ),
        "fake_done_risks": (
            "Block login/logout happy path, frontend-only session clear, framework defaults, short-expiry-only, missing revoked/stolen/expired token negatives, missing refresh reuse proof, missing session invalidation, missing audit/monitoring, missing migration, or skipped local governance."
        ),
        "evidence_preferences": (
            "Prefer expired/revoked/stolen token negative calls, refresh rotation/reuse fixtures, logout current/all-device revocation checks, password reset/MFA invalidation proof, cookie flag inspection, CSRF/API boundary tests, tenant/device/session audit refs, replay/reuse alerts, migration compatibility proof, and local-governance evidence. "
            "Classify each session/token claim as Proven, Weak, Unproven, Blocking, or Residual risk."
        ),
        "execution_strategy": (
            "Session Token Contract Inspector first freezes session/token proof targets; Session Token Builder implements from that handoff; Token Misuse Inspector and Session Revocation Audit Inspector inspect in parallel; GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Minor non-critical copy, extra device-matrix coverage, or out-of-scope legacy client polish may remain only with owner/follow-up; missing token negatives, refresh reuse detection, revocation/invalidation, cookie/CSRF/API boundary, audit/monitoring, migration, or local-governance evidence must fail closed."
        ),
        "judgment_tradeoffs": (
            "Session/token security, negative misuse proof, revocation/invalidation closure, audit, and monitoring beats quickly connecting login; speed cannot hide old tokens that still work, refresh reuse, frontend-only clearing, framework defaults, or unauditable replay."
        ),
        "local_governance": (
            "If project-local governance markers are present, Session Token Contract Inspector and Session Token Builder read applicable rules, both parallel Inspectors verify related design/test/security/session/monitoring obligations, and GateKeeper treats skipped governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Session Token Contract Inspector freezes expiry, rotation/reuse, revocation/invalidation, cookie/CSRF/API, audit/monitoring/migration proof targets; Session Token Builder implements only from that handoff; Token Misuse Inspector refutes expired/revoked/stolen/replayed/reused tokens, refresh reuse, cookie/CSRF/API boundaries, and tenant negatives; Session Revocation Audit Inspector verifies logout/all-device, password reset/MFA invalidation, audit, monitoring, migration, and governance; GateKeeper fails closed on shallow auth proof."
        ),
        "workflow_shape": (
            "Use Session Token Contract Inspector -> Session Token Builder -> [Token Misuse Inspector + Session Revocation Audit Inspector] -> Auth Session GateKeeper. Both Inspectors share one parallel_group and read contract plus builder handoffs; GateKeeper queries session-lifecycle, permission-auth, privacy-redaction, tenant-isolation, audit-log, monitoring, backward-compatibility, migration-rollback, negative_evidence, and local-governance."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Auth middleware, token store, session store, cookie/CSRF config, audit/logging, monitoring, migration path, and test runner must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def _agreement_is_search_index_consistency_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\bRAG\b|检索增强", text, re.IGNORECASE):
        return False
    if not re.search(
        r"search\s+index|full[- ]?text\s+search|全文搜索|搜索索引|索引重建|reindex|indexing|indexer|索引",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"\beval(?:uation)?\b|eval\s*set|benchmark|top[- ]?5|human\s+review|manual\s+review|relevance|groundedness|hallucination|评测|评估集|基准|人工评审|相关性|幻觉",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"create|update|delete|deleted[- ]?document|incremental|document\s+event|新建|更新|删除|已删除|增量|文档事件",
        r"ACL|permission|revocation|unauthorized|tenant|cross[- ]?tenant|权限|撤销|无权限|租户|跨租户",
        r"reindex|backfill|idempot(?:ent|ency)|rerun|重建|回填|幂等|重跑",
        r"watermark|cursor|checkpoint|recovery|retry|DLQ|failure|水位|游标|检查点|恢复|重试|死信|失败",
        r"lag|stale\s+index|SLO|alert|monitoring|延迟|陈旧索引|告警|监控",
        r"pagination|sort|ordering|分页|排序",
        r"audit|审计",
        r"local[- ]?search[- ]?only|green[- ]?index[- ]?job|row[- ]?count\s+sample|dashboard\s+latest|本地搜索|绿色|抽样|看板",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _agreement_is_search_quality_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\bRAG\b|检索增强", text, re.IGNORECASE):
        return False
    if not re.search(r"semantic\s+search|search|retrieval|ranking|top[- ]?5|搜索|检索|排序|相关性", text, re.IGNORECASE):
        return False
    markers = (
        r"\beval(?:uation)?\b|eval\s*set|benchmark|评测|评估集|评测集|基准",
        r"human\s+review|manual\s+review|人工评审|人工审核",
        r"relevance|groundedness|hallucination|quality|相关性|幻觉|质量",
        r"negative\s+quer|negative\s+example|regression\s+sample|负例|负向|回归样本",
        r"demo\s+query|single\s+score|单点|单个\s*demo|单个\s*benchmark",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_rag_long_chain_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(r"\bRAG\b|retrieval|知识库|检索增强", text, re.IGNORECASE):
        return False
    phase_markers = (
        r"\bingestion\b|文档\s*ingestion|语料|corpus",
        r"retrieval\s*ACL|permission-filtered\s+retrieval|tenant\s+filtering|检索权限|租户过滤",
        r"answer/tool|tool\s+gating|tool\s+allowlist|答案.*工具|工具.*白名单",
        r"\beval(?:uation)?\b|eval\s*set|human\s+review|评估|评测集|人工评审",
        r"monitoring|regression\s+monitoring|监控|告警",
        r"evidence\s+hardening|hardening|证据.*修复|补证据",
    )
    matched = sum(1 for pattern in phase_markers if re.search(pattern, text, re.IGNORECASE))
    if matched >= 4 and re.search(r"独立阶段|阶段|long[- ]?chain|长链|phase", text, re.IGNORECASE):
        return True
    success_markers = (
        r"grounded|source\s+chunks?|source\s+span|citation|document\s+version|答案.*来源|文档版本|引用",
        r"retrieval\s*ACL|tenant\s+filtering|permission-filtered|检索权限|租户过滤|权限过滤",
        r"prompt[- ]?injection|system\s+prompt|系统提示词|提示词注入",
        r"tool\s+allowlist|unauthorized\s+tool|tool[- ]?call|工具.*白名单|未授权\s*tool",
        r"PII|secrets?|redaction|脱敏|敏感|隐私",
        r"hallucination|fallback|handoff|no[- ]?answer|幻觉|兜底|转人工|无法回答",
        r"eval\s*set|golden\s+Q&A|faithfulness|citation\s+precision|top[- ]?k|human\s+review|评测集|人工评审",
        r"demo\s+question|plausible|embedding\s+search|UI\s+citations?|单个\s*demo|看起来合理|UI.*citation",
    )
    return sum(1 for pattern in success_markers if re.search(pattern, text, re.IGNORECASE)) >= 6


def _agreement_is_prompt_asset_ownership_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"system[-_ ]?prompts?|developer[-_ ]?prompts?|fixed\s+prompts?|prompt\s+assets?|system_prompt_assets|system_prompts|系统提示词|提示词资产|固定提示词",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"hardcod|inline|literal|asset(?:ize|s|ed)?|decoupl|migrat|ownership|locale|language[- ]?specific|branch|\\.zh|\\.en|硬编码|内联|解耦|迁移|资产|归属|语言分支|多语言",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"system[-_ ]?prompts?|developer[-_ ]?prompts?|fixed\s+prompts?|系统提示词|固定提示词",
        r"Agent\s+Native|managed\s+entries?|role[- ]?agent|Claude\s+session|runtime\s+(?:role\s+)?prefix|output\s+contracts?|alignment\s+compiler|role\s+metadata|托管入口|角色",
        r"system_prompt_assets|system_prompts|prompt\s+assets?|asset\s+refs?|load(?:ed|ing)?|render(?:ed|ing)?|提示词资产|资产引用",
        r"hardcod|inline|literal|Python|code|硬编码|内联|代码",
        r"locale|language[- ]?specific|\\.zh|\\.en|named\s+user\s+language|语言|多语言|中文|英文",
        r"test|AST|long[- ]?instruction|static\s+asset\s+refs?|unresolved\s+placeholders?|placeholder|测试|占位符",
        r"Strategy\s+Source|user[- ]?editable\s+presets?|preset\s+boundary|策略源|预设",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _agreement_is_backup_restore_recovery_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"restore|recover|disaster[- ]?recovery|PITR|point[- ]?in[- ]?time|RPO|RTO|恢复|灾备|灾难恢复|时间点恢复",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"backup|restore|disaster[- ]?recovery|PITR|point[- ]?in[- ]?time|RPO|RTO|备份|恢复|灾备|灾难恢复|时间点恢复",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"restore[- ]?drill|cross[- ]?region|snapshot|retention|legal[- ]?hold|checksum|row[- ]?count|smoke|encryption[- ]?key|audit|monitoring|备份任务|快照|恢复演练|保留|法务保留|校验和|行数|冒烟|密钥|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"backup|restore|disaster[- ]?recovery|PITR|point[- ]?in[- ]?time|RPO|RTO|备份|恢复|灾备|灾难恢复|时间点恢复",
        r"nightly|snapshot|cross[- ]?region|replication\s+lag|复制延迟|快照|跨区",
        r"restore[- ]?drill|isolated|tenant\s+restore|full\s+database|schema\s+migration|恢复演练|隔离|租户恢复|全量库|schema\s*migration",
        r"checksum|row[- ]?count|application\s+smoke|integrity|校验和|行数|冒烟|完整性",
        r"retention|legal[- ]?hold|expired\s+backup|过期|保留|法务保留",
        r"encryption[- ]?key|key\s+access|permission|operator|restore\s+permission|KMS|密钥|权限|操作员",
        r"audit|backup\s+id|snapshot\s+id|restore\s+run|failure\s+reason|monitoring|alert|审计|监控|告警|失败原因",
        r"backup[- ]?job[- ]?green|snapshot\s+file|dashboard\s+green|备份任务成功|备份作业成功|快照文件|看板绿色",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _agreement_is_audit_log_integrity_retention_task(task: str) -> bool:
    text = str(task or "")
    if (
        _agreement_is_support_impersonation_task(text)
        or _agreement_is_kyc_aml_screening_task(text)
        or _agreement_is_authorization_policy_task(text)
    ):
        return False
    if re.search(
        r"GDPR|account\s+deletion|delete|deletion|erase|erasure|right[- ]?to[- ]?be[- ]?forgotten|search[- ]?index\s+purge|cache\s+purge|analytics\s+anonymization|export\s+suppression|数据删除|删除|擦除|遗忘权|搜索.*清理|缓存.*清理|匿名化|导出.*抑制",
        text,
        re.IGNORECASE,
    ) and not re.search(
        r"audit[- ]?log\s+integrity|audit\s+trail\s+integrity|append[- ]?only|tamper|hash[- ]?chain|WORM|immutable|sequence\s+gap|logging\s+failure|stale\s+exporter|不可篡改|防篡改|哈希链|序列缺口|日志失败|导出滞后",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"audit[- ]?log\s+integrity|audit\s+trail\s+integrity|compliance\s+audit|审计日志.*完整性|合规审计",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"contract[- ]?first|parallel|retention\s+direction|Audit\s+Contract\s+Inspector|Audit\s+Trail\s+Builder|Audit\s+Integrity\s+Inspector|Retention\s+Export\s+Inspector|合约优先|并行|留存",
        text,
        re.IGNORECASE,
    ):
        return True
    if not re.search(
        r"audit\s+(?:trail|log)|compliance\s+audit|audit[- ]?log\s+integrity|审计日志|审计链路|合规审计",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"append[- ]?only|tamper|hash[- ]?chain|WORM|immutable|retention|legal[- ]?hold|SIEM|export|sequence\s+gap|logging\s+failure|stale\s+exporter|追加|不可篡改|防篡改|哈希链|保留|法务保留|导出|序列|漏记|告警",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"audit\s+(?:trail|log)|compliance\s+audit|审计日志|审计链路|合规审计",
        r"create/update/delete|permission\s+change|failed\s+attempt|敏感操作|权限变更|失败尝试|增删改",
        r"actor|subject|tenant|request\s+id|IP|user\s+agent|before/after|reason\s+code|timestamp|sequence|租户|请求|原因码|时间戳|序列",
        r"PII|token|redact|redaction|脱敏|敏感",
        r"append[- ]?only|immutable|tamper|hash[- ]?chain|WORM|不可变|不可篡改|防篡改|哈希链|追加",
        r"clock\s+skew|monotonic|单调|时钟偏移",
        r"retention|legal[- ]?hold|保留|法务保留",
        r"SIEM|export|reconciliation|导出|对账",
        r"access\s+control|tenant\s+isolation|cross[- ]?tenant|访问控制|租户隔离|跨租户",
        r"retry|duplicate|no[- ]?miss|no[- ]?duplicate|idempot|重试|重复|漏记|幂等",
        r"logging\s+failure|stale\s+exporter|sequence\s+gap|monitoring|alert|日志失败|导出滞后|序列缺口|监控|告警",
        r"database\s+row|console\s+log|UI\s+history|reviewability|follow[- ]?up|数据库表|控制台|历史|可审计|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_schedule_phase_task(task: str) -> bool:
    text = str(task or "")
    if re.search(
        r"usage\s+meter(?:ing|ed)?|usage\s+event|quota\s+(?:enforcement|limit|window)|plan\s+(?:quota|limit)|api\s+usage|usage\s+ledger|额度|配额|限额",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"concurrent|duplicate|idempot|plan\s+upgrade|plan\s+downgrade|billing\s+period|grace\s+limit|hard\s+limit|over[- ]?limit|invoice|subscription\s+provider|并发|重复|幂等|套餐|计费周期|宽限|硬限制|超限|发票|订阅",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(r"weekly\s+digest|digest|schedule|scheduler|cron|timezone|DST|定时|周一|夏令时", text, re.IGNORECASE):
        return False
    phase_markers = (
        r"timezone|时区",
        r"\bDST\b|daylight|夏令时",
        r"missed[- ]?run|catch[- ]?up|错过执行|补偿|补一次",
        r"retry|provider\s+replay|duplicate|idempotenc|重试|重复|幂等",
        r"subscription|unsubscribe|disabled|tenant|locale|退订|禁用|租户",
        r"audit|scheduled_at|due_at|sent_at|skipped_reason|job_run_id|审计",
        r"monitoring|alert|drift|backlog|provider\s+failure|监控|告警|漂移|积压",
        r"cron[- ]?only|local[- ]?trigger|UTC[- ]?only|single[- ]?timezone|本地触发|只测|一个时区",
    )
    return sum(1 for pattern in phase_markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _agreement_is_dsar_data_export_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_data_residency_task(text) or _agreement_is_support_impersonation_task(text):
        return False
    explicit_export = re.search(
        r"\b(?:DSAR|subject\s+access\s+request|data\s+subject\s+access|privacy\s+export|data\s+export|export\s+request)\b|"
        r"个人信息导出|隐私导出|数据主体访问|数据访问请求",
        text,
        re.IGNORECASE,
    )
    subject_access_export = re.search(
        r"\b(?:DSAR|subject\s+access\s+request|data\s+subject\s+access|privacy\s+export|export\s+request)\b|"
        r"个人信息导出|隐私导出|数据主体访问|数据访问请求",
        text,
        re.IGNORECASE,
    )
    compliance_export = re.search(r"\b(?:GDPR|CCPA|GDPR\s*/?\s*CCPA)\b", text, re.IGNORECASE) and re.search(
        r"export|download|subject\s+access|access\s+request|导出|下载|访问请求",
        text,
        re.IGNORECASE,
    )
    if not explicit_export and not compliance_export:
        return False
    if not subject_access_export and re.search(
        r"erase|erasure|delete|deletion|right[- ]?to[- ]?be[- ]?forgotten|account\s+deletion|数据删除|删除|擦除|遗忘权",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"export|download|request|identity|verification|permission|admin|API|scope|profile|billing|orders?|messages?|attachments?|metadata|tenant|redact|PII|secret|legal[- ]?hold|retention|async|job|signed\s+URL|expiry|cleanup|download\s+audit|notification|rate\s+limit|导出|下载|请求|身份|权限|范围|资料|账单|订单|消息|附件|元数据|租户|脱敏|法务保留|保留|异步|签名|过期|清理|审计|通知|限流",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:DSAR|subject\s+access\s+request|data\s+subject\s+access|GDPR\s*/?\s*CCPA|GDPR|CCPA|privacy\s+export|data\s+export|export\s+request)\b|个人信息导出|隐私导出|数据主体访问|数据访问请求",
        r"identity\s+verification|requester|admin|API|permission|authorization|身份|请求者|管理员|权限|授权",
        r"profile|billing|orders?|messages?|attachments?|audit[- ]?visible\s+metadata|metadata|资料|账单|订单|消息|附件|元数据",
        r"tenant|cross[- ]?tenant|other\s+users?|user\s+exclusion|租户|跨租户|其他用户|用户排除",
        r"PII|secret|redact|redaction|privacy|脱敏|隐私|敏感",
        r"legal[- ]?hold|retention\s+exceptions?|retention|法务保留|保留例外|保留",
        r"async|export\s+job|retry|cancel|timeout|idempot|异步|导出任务|重试|取消|超时|幂等",
        r"encrypt|signed\s+URL|presigned|expiry|expires?|cleanup|delete\s+expired|加密|签名|过期|清理",
        r"download\s+audit|audit|notification|dedupe|rate\s+limit|monitoring|下载审计|审计|通知|去重|限流|监控",
        r"CSV[- ]?only|download[- ]?button[- ]?only|dashboard[- ]?ready|export\s+ready|只有.*CSV|下载按钮|看板",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_support_ticket_sla_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_support_impersonation_task(text):
        return False
    if not re.search(
        r"support\s+ticket|ticket\s+triage|ticket\s+queue|ticket\s+lifecycle|SLA\s+escalation|"
        r"客服工单|工单|客服.*SLA|SLA.*升级|工单.*升级|客服.*队列",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"SLA|escalat(?:e|ion)?|breach|queue|triage|dedupe|deduplicat|merge|email|API|claim|assign|priority|status|agent|manager|tenant|PII|redact|audit|notification|"
        r"升级|违约|队列|分诊|去重|合并|邮件|领取|分配|优先级|状态|坐席|经理|租户|脱敏|审计|通知",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"support\s+ticket|ticket\s+triage|ticket\s+queue|ticket\s+lifecycle|客服工单|工单|客服",
        r"email|API|import|ingest|dedupe|deduplicat|merge|邮件|导入|接入|去重|合并",
        r"queue|enqueue|dequeue|claim|assign|priority|status|state\s+machine|lifecycle|队列|入队|领取|分配|优先级|状态|状态机|生命周期",
        r"SLA|breach|escalat(?:e|ion)?|clock|timer|pause|resume|SLO|违约|升级|计时|暂停|恢复",
        r"agent|manager|queue\s+health|backlog|ownership|owner|负责人|坐席|经理|队列健康|积压",
        r"permission|authorization|RBAC|ACL|role|unauthorized|权限|授权|角色|无权限",
        r"tenant|cross[- ]?tenant|租户|跨租户",
        r"notification|notify|email|message|duplicate\s+notification|suppress|通知|消息|重复通知|抑制",
        r"audit|notes?|audit\s+note|trace|审计|备注|追踪",
        r"PII|redact|redaction|privacy|mask|脱敏|隐私|掩码",
        r"Kanban|dashboard[- ]?only|manager\s+dashboard|queued/open|status[- ]?only|看板|状态",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_analytics_experiment_instrumentation_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"analytics|telemetry|instrumentation|tracking|analytics\s+events?|funnel|clickstream|Segment|埋点|漏斗",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"\bA/B\b|\bab[- ]?test\b|\bsplit[- ]?test\b|\bexperiment(?:s)?\b|\bassignment(?:s)?\b|\bexposure(?:s)?\b|\bvariant(?:s)?\b|\bholdout(?:s)?\b|\breassignment\b|实验|分流|曝光|变体|对照组|重分配",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"event[- ]?schema|event\s+payload|versioned|schema\s+version|app_open|signup|onboarding|paywall|事件.*schema|版本",
        r"anonymous|logged[- ]?in|identity\s+merge|double\s+count|user\s+id|匿名|登录|身份.*合并|重复计数",
        r"consent|PII|privacy|redact|tracking\s+denial|同意|隐私|脱敏|拒绝.*跟踪",
        r"duplicate|dedupe|retry|refresh|offline\s+replay|SDK\s+callback|idempot|重复|去重|重试|离线|回放|幂等",
        r"\bexperiment(?:s)?\b|\bassignment(?:s)?\b|\bexposure(?:s)?\b|\bvariant(?:s)?\b|\bholdout(?:s)?\b|\breassignment\b|restart|device|实验|分流|曝光|变体|对照|重分配|重启|设备",
        r"warehouse|dashboard|raw[- ]?event|assignment\s+log|reconciliation|Segment|provider\s+accepted|数仓|仪表盘|原始事件|对账|供应商",
        r"monitoring|drift|missing\s+exposure|duplicate\s+spike|schema\s+mismatch|alert|监控|漂移|缺失曝光|峰值|不匹配|告警",
        r"button|click|console\.?log|mock\s+analytics|mock\s+call|follow[- ]?up|按钮|控制台|模拟|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_database_schema_migration_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"database|schema\s+migration|DB\s+migration|data\s+model|table|normalized|migration/backfill|数据库|数据表|表结构|数据模型|迁移|回填",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"backfill|dual[- ]?write|old/new\s+reader|reader\s+compat|rollback\s+to\s+old|mixed\s+migrated|schema\s+semantics|normalized\s+tables?|回填|双写|旧读|新读|读兼容|回滚|混合迁移",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"old/new\s+schema|schema\s+semantics|normalized|plan_entitlements|table\s+changes?|表结构|新旧.*schema|规范化",
        r"dual[- ]?write|read[- ]?after[- ]?write|old/new\s+reader|reader\s+compat|compatibility\s+adapter|双写|读后写|旧读|新读|兼容",
        r"backfill|cursor|idempotenc|retry|failed\s+batch|partial\s+failure|pause/resume|resume|回填|游标|幂等|重试|失败批次|暂停|恢复",
        r"tenant\s+isolation|mixed\s+migrated|unmigrated|cross[- ]?tenant|租户隔离|混合迁移|未迁移|跨租户",
        r"invoice|billing|reconciliation|no[- ]?drift|ledger|发票|账单|对账|漂移",
        r"rollback|old\s+readers?|cleanup|migration\s+rollback|回滚|旧读|清理",
        r"monitoring|progress|lag|alert|监控|进度|滞后|告警",
        r"table[- ]?only|one[- ]?time\s+backfill|happy[- ]?path|docs[- ]?only|schema[- ]?only|只建表|单次回填|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_cdc_replication_consistency_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_analytics_experiment_instrumentation_task(text):
        return False
    if not re.search(
        r"\b(?:CDC|change[- ]?data[- ]?capture|logical[- ]?replication|streaming[- ]?replication|"
        r"replication|replica|replicate|read[- ]?model|warehouse|sync[- ]?connector|Debezium)\b|"
        r"变更数据捕获|逻辑复制|流式复制|复制|同步|数仓|读模型",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"ordering|out[- ]?of[- ]?order|replay|checkpoint|lag|schema\s+evolution|schema[- ]?version|"
        r"snapshot|backfill|tombstone|delete|tenant\s+(?:filter|isolation)|reconciliation|"
        r"row\s+count|checksum|event\s+count|target\s+drift|connector\s+failure|"
        r"顺序|乱序|回放|检查点|延迟|schema\s*演进|快照|回填|墓碑|删除|租户|对账|漂移|恢复",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"source\s+event\s+schema|event\s+schema|source\s+table|源事件|事件\s*schema|源表",
        r"ordering|out[- ]?of[- ]?order|deterministic\s+order|顺序|乱序",
        r"replay|checkpoint|watermark|LSN|idempot(?:ent|ency)|duplicate|回放|检查点|水位|幂等|重复",
        r"lag|SLO|alert|stale\s+checkpoint|monitoring|延迟|告警|监控|滞后",
        r"schema\s+evolution|schema[- ]?version|column\s+rename|additive\s+column|schema\s*演进|版本|列重命名",
        r"snapshot|backfill|concurrent\s+writes?|快照|回填|并发写",
        r"delete|tombstone|墓碑|删除",
        r"tenant\s+(?:filter|isolation)|cross[- ]?tenant|tenant\s+negative|租户|跨租户",
        r"warehouse|read[- ]?model|reconciliation|row\s+count|checksum|event\s+count|aggregate|target\s+drift|数仓|读模型|对账|漂移",
        r"connector\s+failure|DLQ|poison\s+event|sync\s+failure|restart|recovery|连接器|死信|毒丸|失败|恢复",
        r"green\s+sync\s+job|sync\s+job\s+green|row[- ]?count\s+sample|dashboard\s+(?:latest|shows)|dashboard.*latest|绿色|抽样|看板|latest",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_metric_reporting_reconciliation_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_analytics_experiment_instrumentation_task(text) or _agreement_is_cdc_replication_consistency_task(text):
        return False
    if not re.search(
        r"\b(?:MRR|ARR|NRR|net\s+revenue\s+retention|revenue\s+report(?:ing)?|revenue\s+dashboard|"
        r"MRR\s+dashboard|metric\s+(?:definition|contract|reconciliation|reporting)|metrics?\s+dashboard|"
        r"reporting\s+dashboard|churn|expansion|contraction)\b|收入报表|收入看板|指标口径|指标对账|指标报表|月经常性收入",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"metric\s+definition|trial|coupon|discount|refund|proration|downgrade|upgrade|paused\s+subscription|"
        r"currency|FX|cutoff|timezone|ledger|invoice|provider\s+reconciliation|locked[- ]?month|backfill|"
        r"permission|segment|export|audit|chart[- ]?only|CSV[- ]?only|口径|试用|优惠券|折扣|退款|按比例|降级|升级|暂停|"
        r"币种|汇率|截断|时区|账本|发票|对账|锁账|回填|权限|分段|导出|审计|图表",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:MRR|ARR|NRR|net\s+revenue\s+retention|churn|expansion|contraction)\b|月经常性收入|收入留存|流失|扩张|收缩",
        r"metric\s+definition|metric\s+version|definition\s+version|指标口径|指标版本|口径版本",
        r"trial|coupon|discount|refund|proration|downgrade|upgrade|paused\s+subscription|试用|优惠券|折扣|退款|按比例|降级|升级|暂停",
        r"currency|FX|foreign\s+exchange|exchange\s+rate|币种|汇率|外汇",
        r"month\s+cutoff|cutoff|timezone|月.*截断|时区",
        r"billing\s+ledger|ledger|invoice|subscription\s+provider|provider\s+reconciliation|账本|发票|订阅供应商|对账",
        r"historical\s+backfill|backfill|locked[- ]?month|locked\s+months?|锁账|历史回填|回填",
        r"permission|revenue\s+segment|segment\s+permission|tenant|权限|收入分段|分段|租户",
        r"export|CSV|dashboard/export|导出|CSV",
        r"audit|backfill\s+run|metric\s+definition\s+version|审计|回填运行",
        r"chart[- ]?only|charts?\s+showing|CSV[- ]?only|provider[- ]?total[- ]?only|dashboard\s+matches|图表|只.*CSV|只.*provider|看板.*总数",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_dispute_chargeback_lifecycle_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_metric_reporting_reconciliation_task(text) or _agreement_is_inventory_reservation_consistency_task(text):
        return False
    if re.search(
        r"\b(?:KYC|KYB|AML)\b|sanctions?|PEP|watchlist|identity\s+verification|business\s+registry|"
        r"beneficial\s+owner|document\s+OCR|liveness|risk\s+score|manual\s+review|periodic\s+rescreen|"
        r"provider\s+sandbox\s+approved|身份核验|反洗钱|制裁筛查|受益所有人",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"dispute(?:\.created|\.updated|\.closed)?|chargeback|representment|retrieval\s+request|"
        r"issuer|acquirer|reason\s+code|win/loss|won/lost|partial\s+dispute|duplicate\s+dispute|"
        r"争议|拒付|调单|申诉举证|原因码",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"seller\s+balance\s+ledger|seller[- ]?payout|marketplace[- ]?payout|payout[- ]?settlement|"
        r"double[- ]?payout|provider\s+transfer|bank\s+statement|卖家余额|重复打款",
        text,
        re.IGNORECASE,
    ) and not re.search(
        r"representment|retrieval\s+request|reason\s+code|win/loss|won/lost|partial\s+dispute|duplicate\s+dispute|"
        r"evidence\s+(?:package|submission)|调单|申诉举证|原因码",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"dispute(?:\.created|\.updated|\.closed)?|chargeback|争议|拒付",
        r"retrieval\s+request|representment|evidence\s+(?:package|submission)|deadline|调单|申诉举证|截止",
        r"issuer|acquirer|reason\s+code|win/loss|won/lost|partial\s+dispute|duplicate\s+dispute|原因码|部分争议|重复争议",
        r"refund\s+overlap|chargeback\s+overlap|order\s+fulfillment|退款.*重叠|履约",
        r"provider\s+dispute|webhook|signature|replay|out[- ]?of[- ]?order|供应商|重放|乱序",
        r"ledger|invoice|balance\s+adjustment|provisional\s+credit|provisional\s+debit|fee|账本|发票|余额调整|临时贷记|临时借记|费用",
        r"payout\s+hold|payout\s+release|hold/release|打款冻结|打款释放",
        r"customer\s+notification|merchant\s+response|SLA|notification\s+delivery|客户通知|商户响应",
        r"audit|monitoring|failed\s+dispute|stale\s+dispute|审计|监控|过期争议",
        r"dashboard\s+(?:won|lost)|provider\s+dispute\s+id|happy[- ]?path\s+close|UI\s+status|看.*won/lost|只保存",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_payout_settlement_reconciliation_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_metric_reporting_reconciliation_task(text) or _agreement_is_dispute_chargeback_lifecycle_task(text):
        return False
    if re.search(
        r"\b(?:KYB|AML)\b|sanctions?|PEP|watchlist|identity\s+verification|business\s+registry|"
        r"beneficial\s+owner|document\s+OCR|manual\s+review|rescreening|身份核验|反洗钱|制裁筛查|受益所有人",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"Webhook\s+Contract\s+Inspector|payment\s+provider\s+webhook|webhook\s+ingestion|provider\s+event\s+schemas?|"
        r"signature\s+verification|timestamp\s+tolerance|replay\s+protection|dead[- ]?letter|DLQ|manual\s+replay|"
        r"checkout\.session|支付.*webhook|供应商事件",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"\b(?:marketplace[- ]?payout|seller[- ]?payout|merchant[- ]?payout|payout[- ]?settlement|"
        r"payout[- ]?batch|seller\s+balance|merchant\s+balance|provider\s+transfer|failed\s+payout|"
        r"double[- ]?payout|stuck\s+payout)\b|"
        r"打款|结算|卖家余额|商户余额|付款批次",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"seller\s+balance\s+ledger|ledger|captured|refunded|chargeback|platform\s+fee|tax|adjustment|"
        r"hold|reserve|negative\s+balance|batch\s+cutoff|timezone|currency|FX|provider\s+transfer|bank\s+account|"
        r"KYC\s+hold|failed\s+payout|retry|reversal|double[- ]?payout|payout\s+report|bank\s+statement|tenant|audit|monitoring|"
        r"账本|捕获|退款|拒付|费用|税|调整|冻结|准备金|负余额|批次|截断|时区|币种|转账|银行|失败|重试|冲销|重复打款|对账|租户|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"marketplace[- ]?payout|seller[- ]?payout|merchant[- ]?payout|payout[- ]?settlement|payout[- ]?batch|seller\s+balance|打款|结算|卖家余额",
        r"seller\s+balance\s+ledger|ledger|captured|refunded|chargeback|账本|捕获|退款|拒付",
        r"platform\s+fee|tax|adjustment|hold|reserve|negative\s+balance|费用|税|调整|冻结|准备金|负余额",
        r"batch\s+cutoff|timezone|currency|FX|rounding|批次|截断|时区|币种|舍入",
        r"provider\s+transfer|bank\s+account|payout\s+report|bank\s+statement|Stripe|Adyen|转账|银行|报告|对账单",
        r"KYC\s+hold|failed\s+payout|retry|reversal|idempot(?:ent|ency)|double[- ]?payout|失败|重试|冲销|幂等|重复打款",
        r"reconciliation|local\s+ledger|invoice|bank\s+statement|provider[- ]?bank|对账|本地账本|发票|银行",
        r"tenant|seller\s+access|cross[- ]?tenant|permission|租户|权限|跨租户",
        r"audit|payout\s+batch\s+id|ledger\s+entry\s+id|provider\s+transfer\s+id|failure\s+reason|审计|失败原因",
        r"monitoring|stuck\s+payout|failed\s+transfer|mismatch|alert|监控|告警|卡住|失败转账|不一致",
        r"dashboard\s+paid|test\s+payout|UI\s+balance|dashboard.*paid|一笔|余额减少",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_notification_subscription_deliverability_task(task: str) -> bool:
    text = str(task or "")
    if (
        _agreement_is_schedule_phase_task(text)
        or _agreement_is_analytics_experiment_instrumentation_task(text)
        or _agreement_is_dispute_chargeback_lifecycle_task(text)
        or _agreement_is_support_ticket_sla_task(text)
        or _agreement_is_dsar_data_export_task(text)
        or _agreement_is_subscription_entitlement_billing_task(text)
    ):
        return False
    if re.search(
        r"notification\s+subscription[- ]?deliverability|subscription[- ]?deliverability|notification\s+deliverability",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"contract[- ]?first|parallel|evidence\s+direction|Notification\s+Contract\s+Inspector|Deliverability\s+Evidence\s+Inspector|Template\s+Privacy\s+Inspector|合约优先|并行",
        text,
        re.IGNORECASE,
    ):
        return True
    if not re.search(
        r"notification|email|campaign|lifecycle\s+campaign|deliverability|subscription\s+preferences?|preference\s+center|unsubscribe|suppression\s+list|bounce|complaint|通知|邮件|退订|订阅|偏好|投递",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"subscribed|eligible|unsubscribe|preference|suppression|bounce|complaint|dropped|disabled\s+user|locale|template|PII|token|provider|webhook|delivered|delivery\s+audit|duplicate|retry|DLQ|manual\s+replay|monitoring|订阅|退订|偏好|抑制|退信|投诉|模板|脱敏|投递|重复|重试|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"notification|email|campaign|lifecycle\s+campaign|message|通知|邮件|消息",
        r"subscription|subscribed|eligible|preference\s+center|preference|unsubscribe|订阅|偏好|退订",
        r"suppression\s+list|suppression|bounce|complaint|dropped|drop|抑制|退信|投诉|丢弃",
        r"provider|accepted|delivered|delivery\s+event|webhook|replay|signature|供应商|已接收|已投递|投递事件|重放|签名",
        r"duplicate|idempot(?:ent|ency)|retry|backoff|rate\s+limit|DLQ|dead[- ]?letter|manual\s+replay|重复|幂等|重试|速率|死信|手动重放",
        r"locale|i18n|template|variable|English|Chinese|fallback|中文|英文|模板|变量|回退",
        r"PII|token|redact|redaction|privacy|leak|脱敏|隐私|泄露",
        r"disabled\s+user|tenant|cross[- ]?tenant|禁用用户|租户|跨租户",
        r"audit|reason\s+code|reconciliation|monitoring|alert|审计|原因码|对账|监控|告警",
        r"one\s+test\s+email|test\s+email|provider\s+accepted|UI\s+toggle|happy[- ]?path|docs[- ]?only|follow[- ]?up|测试邮件|只.*provider|UI|文档|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_data_lifecycle_deletion_retention_task(task: str) -> bool:
    text = str(task or "")
    if (
        _agreement_is_data_residency_task(text)
        or _agreement_is_audit_log_integrity_retention_task(text)
        or _agreement_is_dsar_data_export_task(text)
    ):
        return False
    if not re.search(
        r"delete|deletion|erase|erasure|right[- ]?to[- ]?be[- ]?forgotten|GDPR|tombstone|legal[- ]?hold|backup\s+expiry|search[- ]?index\s+purge|cache\s+purge|analytics\s+anonymization|export\s+suppression|数据删除|删除|擦除|遗忘权|法务保留|备份过期|搜索.*清理|缓存.*清理|匿名化|导出.*抑制",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"account\s+deletion|delete|deletion|erase|erasure|tombstone|soft[- ]?delete|数据删除|删除|擦除|墓碑|软删除",
        r"retention|retention\s+exception|billing[- ]?record|legal[- ]?hold|backup\s+expiry|expired\s+backup|保留|例外|账单记录|法务保留|备份过期",
        r"search[- ]?index\s+purge|cache\s+purge|purge|analytics\s+anonymization|anonymi[sz]ation|export\s+suppression|搜索.*清理|缓存.*清理|匿名化|导出.*抑制",
        r"tenant\s+isolation|cross[- ]?tenant|permission|audit\s+trail|audit[- ]?log|monitoring|alert|租户隔离|跨租户|权限|审计|监控|告警",
        r"UI\s+delete|delete\s+button|happy[- ]?path|soft[- ]?delete|docs[- ]?only|UI.*删除|按钮|单一正向|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_feature_flag_rollout_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"feature[- ]?flag|release[- ]?flag|rollout|canary|灰度|功能开关|特性开关|发布开关",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"default[- ]?off|cohort|targeting|percentage|percent[- ]?rollout|sticky[- ]?assignment|exposure|kill[- ]?switch|rollback|roll\s+back|canary|默认关闭|分群|百分比|稳定分配|曝光|熔断|回滚|灰度",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"feature[- ]?flag|release[- ]?flag|rollout|canary|功能开关|特性开关|发布开关|灰度",
        r"default[- ]?off|cohort|targeting|percentage|percent[- ]?rollout|默认关闭|分群|百分比",
        r"sticky[- ]?assignment|exposure|session\s+consistency|session|稳定分配|曝光|会话一致",
        r"kill[- ]?switch|rollback|roll\s+back|cleanup|dirty\s+state|熔断|回滚|脏状态",
        r"monitoring|alerts?|error[- ]?rate|conversion|payment\s+conversion|监控|告警|错误率|转化率",
        r"audit|flag\s+change|who\s+changed|local[- ]?only|local\s+flag|UI\s+toggle|docs[- ]?only|审计|本地|按钮|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _agreement_is_cache_invalidation_consistency_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_data_lifecycle_deletion_retention_task(text) or _agreement_is_data_residency_task(text):
        return False
    if not re.search(r"cache|CDN|Redis|read[- ]?model|TTL|缓存|回源|失效", text, re.IGNORECASE):
        return False
    if not re.search(r"price|pricing|old\s+price|商品|价格|旧价", text, re.IGNORECASE):
        return False
    if not re.search(
        r"invalidation|invalidate|purge|refresh|refetch|TTL|stale|cache[- ]?key|缓存失效|刷新|回源|旧价",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"price|pricing|PDP|cart|checkout|API|商品|价格|购物车|下单|旧价",
        r"cache|CDN|Redis|read[- ]?model|cache[- ]?key|缓存|缓存\s*key",
        r"invalidation|invalidate|purge|refresh|refetch|TTL|stale|回源|失效|刷新",
        r"old\s+price|checkout|payment|cannot\s+checkout|旧价|下单|支付",
        r"region|currency|locale|key\s+isolation|地区|区域|货币|币种|串",
        r"rollback|roll\s+back|cleanup|恢复旧价|回滚|清理",
        r"audit|invalidation\s+event|actor|monitoring|alert|审计|监控|告警",
        r"database[- ]?update|manual\s+refresh|single[- ]?cache[- ]?layer|docs[- ]?only|数据库|手动刷新|单层|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_data_import_validation_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_authorization_policy_task(text) or _agreement_is_payment_webhook_ledger_task(text):
        return False
    if re.search(r"\bexport\b|download|report(?:ing)?|BI\s+report|导出|下载|报表", text, re.IGNORECASE) and not re.search(
        r"\bimport\b|upload|导入|上传",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"\b(?:import|bulk[- ]?import|data[- ]?import|customer[- ]?import|row[- ]?import|import[- ]?job|import[- ]?pipeline|CSV\s+(?:bulk\s+)?import|import\s+CSV|CSV\s+upload|upload(?:ed|ing)?\s+CSV)\b|批量导入|数据导入|客户导入|导入任务|导入流程|上传\s*CSV",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"mapping|schema|required|type\s+validation|row[- ]?level|partial[- ]?failure|bad[- ]?rows?|dry[- ]?run|preview|idempot(?:ent|ency)|dedupe|duplicate|external[-_ ]?id|PII|redact|audit|permission|字段映射|必填|类型|坏行|错误报告|部分失败|预览|幂等|去重|审计|权限|隐私",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:import|bulk[- ]?import|data[- ]?import|customer[- ]?import|row[- ]?import|import[- ]?job|import[- ]?pipeline|CSV\s+(?:bulk\s+)?import|import\s+CSV|CSV\s+upload|upload(?:ed|ing)?\s+CSV)\b|批量导入|数据导入|客户导入|导入任务|导入流程|上传\s*CSV",
        r"field[- ]?mapping|mapping|column\s+mapping|字段映射|列映射",
        r"schema|required|type\s+validation|validation|必填|类型|校验|验证",
        r"dry[- ]?run|preview|import[- ]?preview|预览|试运行",
        r"mixed\s+good/bad|bad[- ]?rows?|invalid\s+rows?|row[- ]?level|error\s+report|坏行|错误行|行级|错误报告",
        r"partial[- ]?failure|isolation|all[- ]?or[- ]?nothing|部分失败|隔离|全有全无",
        r"idempot(?:ent|ency)|retry|idempotency\s+key|幂等|重试",
        r"dedupe|duplicate|external[-_ ]?id|reconciliation|去重|重复|外部\s*id|对账",
        r"PII|privacy|redact|permission|auth|tenant|隐私|脱敏|权限|授权|租户",
        r"audit|batch\s+(?:id|fields?|actor|source|counts?|reason|status)|monitoring|cleanup|审计|批次|监控|清理",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_concurrency_conflict_resolution_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_inventory_reservation_consistency_task(text) or _agreement_is_usage_quota_metering_task(text):
        return False
    if not re.search(
        r"collaborative\s+(?:document|editing|editor)|collab(?:oration)?\s+(?:document|editing)|document\s+editing|same[- ]paragraph|协作文档|协同编辑|协作编辑|同一段|文档编辑",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"conflict|concurrent|optimistic\s+lock|version|lost[- ]update|silent\s+overwrite|last[- ]write[- ]wins|offline\s+replay|冲突|并发|乐观锁|版本|覆盖|离线|重放",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"two\s+users?|same[- ]paragraph|concurrent\s+edit|双用户|两个用户|同一段|并发编辑",
        r"silent\s+overwrite|lost[- ]update|last[- ]write[- ]wins|静默覆盖|覆盖|最后写入",
        r"version\s+conflict|optimistic\s+lock|base_version|版本冲突|乐观锁|版本",
        r"safe\s+merge|merge\s+outcome|reject|both\s+sides|保留两边|安全\s*merge|合并|拒绝",
        r"offline\s+(?:edit|queue|replay)|reconnect|idempot(?:ent|ency)|retry|离线|重连|幂等|重试",
        r"permission|unauthorized|lower[- ]permission|revocation|权限|无权限|低权限|撤销",
        r"audit|resolved_by|base_version|merge\s+outcome|审计",
        r"single[- ]user[- ]save|WebSocket[- ]only|happy[- ]path|单人保存|单用户|happy path",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _agreement_is_usage_quota_metering_task(task: str) -> bool:
    text = str(task or "")
    if (
        _agreement_is_inventory_reservation_consistency_task(text)
        or _agreement_is_notification_subscription_deliverability_task(text)
        or _agreement_is_subscription_entitlement_billing_task(text)
    ):
        return False
    if not re.search(
        r"usage\s+meter(?:ing|ed)?|usage\s+event|metered\s+usage|quota\s+(?:enforcement|limit|window)|plan\s+(?:quota|limit)|rate[- ]?limit|api\s+usage|usage\s+ledger|usage\s+limit|计量|用量|额度|配额|限额",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"concurrent|duplicate|retry|idempot|plan\s+upgrade|plan\s+downgrade|billing\s+period|reset\s+timezone|grace\s+limit|hard\s+limit|over[- ]?limit|invoice|subscription\s+provider|audit|monitoring|并发|重复|重试|幂等|套餐|计费周期|重置|宽限|硬限制|超限|发票|订阅|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"usage\s+meter(?:ing|ed)?|usage\s+event|metered\s+usage|api\s+usage|usage\s+ledger|计量|用量",
        r"quota\s+(?:enforcement|limit|window)|plan\s+(?:quota|limit)|usage\s+limit|rate[- ]?limit|quota|额度|配额|限额",
        r"concurrent|same\s+org|race|parallel\s+calls|并发|同一\s*org|同一组织",
        r"duplicate\s+usage\s+events?|idempot(?:ent|ency)|retry|幂等|重复|重试",
        r"plan\s+upgrade|plan\s+downgrade|plan\s+change|套餐|升降级|变更",
        r"billing\s+period|reset\s+timezone|quota\s+window|reset\s+run|计费周期|重置|窗口|时区",
        r"grace\s+limit|hard\s+limit|over[- ]?limit|429|permission[- ]?safe|宽限|硬限制|超限|权限",
        r"ledger|invoice|subscription\s+provider|reconciliation|对账|账本|发票|订阅",
        r"low[- ]?quota|exhaust(?:ed|ion)?|alert|monitoring|低余量|用尽|告警|监控",
        r"audit|usage\s+event\s+id|metering\s+version|actor|org|plan|审计|版本",
        r"dashboard|single\s+429|cron\s+reset|provider\s+total|follow[- ]?up|看板|单次|定时|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_subscription_entitlement_billing_task(task: str) -> bool:
    text = str(task or "")
    has_entitlement_anchor = bool(
        re.search(
            r"entitlement(?:s)?|entitlement[- ]?(?:sync|state|propagation)|feature[- ]?access|"
            r"seat[- ]?access|team[- ]?member|权益|权益生效|权益同步|功能权限|团队成员",
            text,
            re.IGNORECASE,
        )
    )
    has_plan_change_execution_anchor = bool(
        re.search(
            r"proration|prorated|credit[- ]?memo|按比例|贷项|credit\s*memo",
            text,
            re.IGNORECASE,
        )
        and re.search(
            r"provider[- ]?checkout|checkout|webhook|duplicate[- ]?click|"
            r"upgrade[- ]?immediate|downgrade[- ]?(?:next[- ]?cycle|delayed|at[- ]?period[- ]?end)|"
            r"effective[- ]?(?:now|next[- ]?cycle)|重复点击|立即生效|下个周期生效|降级延迟|周期结束生效",
            text,
            re.IGNORECASE,
        )
    )
    if not (has_entitlement_anchor or has_plan_change_execution_anchor):
        return False
    if not re.search(
        r"subscription[- ]?(?:plan|billing|change|upgrade|downgrade)|plan[- ]?(?:upgrade|downgrade|change)|"
        r"entitlement(?:s)?|proration|prorated|credit[- ]?memo|trial|grace[- ]?period|"
        r"订阅套餐|套餐升级|套餐降级|套餐变更|订阅升级|订阅降级|权益|权益生效|proration|按比例|credit\s*memo|试用期|宽限期",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"invoice|ledger|provider|checkout|webhook|idempot|duplicate|billing[- ]?period|quota|permission|tenant|audit|rollback|monitoring|"
        r"发票|账本|供应商|provider|checkout|webhook|幂等|重复|计费周期|配额|权限|租户|审计|回滚|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"subscription[- ]?(?:plan|billing|change|upgrade|downgrade)|plan[- ]?(?:upgrade|downgrade|change)|订阅套餐|套餐升级|套餐降级|套餐变更|订阅升级|订阅降级",
        r"entitlement(?:s)?|feature[- ]?access|seat[- ]?access|team[- ]?member|权益|功能权限|团队成员",
        r"proration|prorated|credit[- ]?memo|invoice|ledger|按比例|credit\s*memo|贷项|发票|账本",
        r"trial|grace[- ]?period|billing[- ]?period|试用期|宽限期|计费周期",
        r"provider|checkout|webhook|replay|out[- ]?of[- ]?order|供应商|provider|checkout|webhook|重放|乱序",
        r"duplicate[- ]?click|idempot|concurrent|重复点击|幂等|并发",
        r"quota|historical[- ]?usage|usage\s+history|历史用量|配额",
        r"permission|tenant|cross[- ]?tenant|权限|租户|跨租户",
        r"audit|rollback|monitoring|审计|回滚|监控",
        r"button[- ]?only|checkout[- ]?success|provider[- ]?total|happy[- ]?path|只做按钮|按钮能点|只信\s*provider|只信\s*checkout",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_tax_calculation_compliance_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_subscription_entitlement_billing_task(text):
        return False
    if re.search(r"tax\s+report|tax\s+export|monthly\s+tax\s+totals|CSV|报税报表|税务报表|税务导出", text, re.IGNORECASE) and not re.search(
        r"checkout|calculation|calculate|VAT|GST|sales\s+tax|taxability|exemption|rounding|refund|invoice|结账|计算|免税|舍入|退款|发票",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"tax\s+calculation|sales\s+tax|\bVAT\b|\bGST\b|taxability|taxable\s+nexus|checkout\s+tax|tax\s+provider|税务计算|税率|增值税|消费税|销售税|免税",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"jurisdiction|nexus|shipping\s+address|billing\s+address|digital\s+goods|physical\s+goods|exemption|reverse\s+charge|inclusive|exclusive|rounding|refund|credit\s+memo|invoice|receipt|provider|effective\s+date|timezone|audit|reconciliation|辖区|地址|免税|反向征收|含税|不含税|舍入|退款|贷项|发票|供应商|生效|时区|审计|对账",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"tax\s+calculation|checkout\s+tax|sales\s+tax|\bVAT\b|\bGST\b|税务计算|税率|增值税|消费税|销售税",
        r"taxable\s+nexus|nexus|US\s+state|EU\s+VAT|jurisdiction|辖区|州|欧盟",
        r"shipping\s+address|billing\s+address|address\s+jurisdiction|收货地址|账单地址|地址",
        r"digital\s+goods|physical\s+goods|product\s+tax(?:ability|able)|taxability|数字商品|实物商品|商品税",
        r"exemption|certificate|B2B\s+reverse\s+charge|reverse\s+charge|免税|证书|反向征收",
        r"inclusive|exclusive|display|含税|不含税|展示",
        r"discount|coupon|shipping\s+fee|rounding|currency|折扣|优惠券|运费|舍入|币种",
        r"refund|credit\s+memo|reversal|退款|贷项|冲销|反转",
        r"invoice|receipt|line\s+item|ledger|reconciliation|provider\s+report|发票|收据|账本|对账|供应商报告",
        r"provider|sandbox|fallback|retry|idempot(?:ent|ency)|request\s+id|供应商|沙箱|降级|重试|幂等|请求",
        r"rate\s+(?:change|effective|version|source)|effective\s+date|timezone|rate\s+version|生效|时区|版本|来源",
        r"audit|jurisdiction|rate\s+source|exemption\s+id|provider\s+request\s+id|monitoring|审计|监控",
        r"one\s+(?:checkout\s+)?tax\s+number|hardcoded\s+rate|provider\s+quote\s+only|UI\s+total|follow[- ]?up|一个.*税|硬编码|只.*provider|只.*UI|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_inventory_reservation_consistency_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\b(?:stock|inventory|SKU)\s+report\b|库存报表|库存报告", text, re.IGNORECASE) and not re.search(
        r"reservation|reserve|oversell|checkout|hold|预留|超卖|下单",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"inventory\s+reservation|reservation\s+hold|stock\s+reservation|oversell|over[- ]?sell|same[- ]?SKU|SKU|checkout\s+inventory|库存预留|库存|预留|超卖|售罄|低库存",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"checkout|payment\s+webhook|payment|refund|cancellation|failed\s+payment|TTL|expiry|release|ledger|reconciliation|concurrent|race|idempot|retry|sold[- ]?out|low[- ]?stock|audit|monitoring|下单|支付|退款|取消|失败支付|到期|释放|账本|对账|并发|竞态|幂等|重试|售罄|低库存|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"inventory\s+reservation|reservation\s+hold|stock\s+reservation|SKU|checkout\s+inventory|库存预留|库存|预留",
        r"oversell|over[- ]?sell|same[- ]?SKU|cannot\s+oversell|防超卖|超卖",
        r"concurrent|race\s+condition|lock|conflict|same[- ]?SKU\s+checkout|并发|竞态|冲突|锁",
        r"TTL|expiry|expires?|hold\s+expiry|release|释放|到期|过期",
        r"payment\s+webhook|webhook|payment\s+success|confirm|decrement|支付|扣减|确认",
        r"cancellation|cancel|refund|failed\s+payment|release\s+reason|取消|退款|失败支付|释放原因",
        r"idempot(?:ent|ency)|retry|duplicate\s+webhook|replay|幂等|重试|重复|重放",
        r"ledger|reconciliation|reconcile|order\s+rows?|provider|账本|对账|订单|供应商",
        r"sold[- ]?out|low[- ]?stock|user\s+state|售罄|低库存|用户状态",
        r"audit|reservation\s+id|hold\s+expiry|monitoring|alert|审计|预留\s*id|监控|告警",
        r"happy[- ]?path|UI\s+stock|DB\s+decrement|database\s+decrement|follow[- ]?up|单个用户|界面|数据库|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_file_upload_storage_safety_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_data_import_validation_task(text) or re.search(
        r"\bCSV\b|spreadsheet|row[- ]?level|field[- ]?mapping|external[-_ ]?id|批量导入|数据导入|字段映射",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"file\s+upload|upload(?:ed|ing)?\s+(?:file|PDF|image|object)|object\s+storage|stored\s+object|S3|bucket|signed\s+URL|presigned|文件上传|对象存储|上传文件|存储对象|签名\s*URL",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"MIME|content[- ]?type|sniff|size\s+limit|virus|malware|scan|quarantine|signed\s+URL|presigned|private\s+(?:bucket|object)|ACL|tenant|cleanup|orphan|audit|monitoring|MIME|内容类型|嗅探|大小限制|病毒|恶意|扫描|隔离|签名|私有|租户|清理|孤儿|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"file\s+upload|upload(?:ed|ing)?\s+(?:file|PDF|image|object)|object\s+storage|stored\s+object|S3|bucket|文件上传|对象存储|上传文件|存储对象",
        r"MIME|content[- ]?type|sniff|extension|spoof|内容类型|嗅探|扩展名|伪造",
        r"size\s+limit|oversize|large\s+file|大小限制|超大|大文件",
        r"virus|malware|scan|scanner|恶意|病毒|扫描",
        r"quarantine|before\s+serv(?:e|ing)|隔离|访问前|提供前",
        r"signed\s+URL|presigned|URL\s+permission|expiry|expires?|签名\s*URL|过期|权限",
        r"private\s+(?:bucket|object)|object\s+ACL|bucket\s+ACL|public\s+bucket|public[- ]?object|ACL|私有|公开桶|公开对象",
        r"tenant|cross[- ]?tenant|object[- ]?key|key\s+isolation|租户|跨租户|对象\s*key|隔离",
        r"failed\s+upload|cleanup|orphan|失败上传|清理|孤儿",
        r"audit|actor|object\s+id|content\s+hash|scan\s+verdict|reason|monitoring|alert|审计|哈希|扫描结果|原因|监控|告警",
        r"returned\s+URL|happy[- ]?path|browser\s+content[- ]?type|scan\s+follow[- ]?up|返回\s*URL|浏览器|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_auth_session_token_lifecycle_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_identity_sso_task(text) or _agreement_is_key_rotation_task(text) or _agreement_is_support_impersonation_task(text):
        return False
    if re.search(r"API\s+token\s+usage\s+analytics|token\s+volume|usage\s+trends|用量分析|使用趋势", text, re.IGNORECASE):
        return False
    if not re.search(
        r"auth\s+session|session\s+token|token\s+lifecycle|access\s+token|refresh\s+token|password\s+reset|reset\s+token|logout|all[- ]?devices?|MFA\s+step[- ]?up|session\s+revocation|session\s+invalidation|认证会话|会话|访问\s*token|刷新\s*token|密码重置|重置\s*token|登出|退出登录|多设备|撤销|失效",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"expir(?:y|e|ed|ation)|rotat(?:e|ion)|reuse|replay|revok(?:e|ed|ing|ation)?|stolen|secure|httpOnly|SameSite|cookie|CSRF|audit|monitoring|migration|过期|轮换|重用|复用|重放|撤销|失效|被盗|安全|审计|监控|迁移",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"auth\s+session|session\s+token|token\s+lifecycle|认证会话|会话|token\s*生命周期",
        r"access\s+token|refresh\s+token|访问\s*token|刷新\s*token",
        r"refresh\s+rotation|reuse\s+detection|refresh\s+reuse|rotation|reuse|轮换|重用|复用",
        r"logout|all[- ]?devices?|session\s+revocation|revok(?:e|ed|ing|ation)?|登出|退出登录|全设备|撤销",
        r"password\s+reset|reset\s+token|old\s+session|密码重置|重置\s*token|旧\s*session|旧会话",
        r"MFA\s+step[- ]?up|step[- ]?up|multi[- ]?factor|二次验证|多因素|提升验证",
        r"expired|expiry|expiration|stolen|replay|revoked|negative|过期|被盗|重放|负向",
        r"secure|httpOnly|SameSite|cookie|CSRF|API\s+token\s+boundary|安全|边界",
        r"tenant|device|session\s+audit|audit\s+trail|audit[- ]?log|monitoring|alert|租户|设备|审计|监控|告警",
        r"backward[- ]?compat|migration|rollback|兼容|迁移|回滚",
        r"login/logout\s+happy|frontend[- ]?only|framework\s+defaults?|short[- ]?expiry[- ]?only|follow[- ]?up|前端|默认|短过期|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def _agreement_is_authorization_policy_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\bRAG\b|retrieval|retrieval\s*ACL|grounded|citation|source\s+span|知识库|检索增强", text, re.IGNORECASE):
        return False
    if not re.search(r"authorization|policy\s+decision|RBAC|ABAC|权限|授权|访问策略|权限策略", text, re.IGNORECASE):
        return False
    markers = (
        r"authorization|policy\s+decision|permission\s+matrix|RBAC|ABAC|权限|授权|权限矩阵|访问策略|权限策略",
        r"API|UI|background\s+jobs?|CSV|exports?|reports?|audit|cache|endpoint|后台任务|导出|报表|审计|缓存",
        r"tenant|cross[- ]?tenant|field[- ]?level|role\s+hierarchy|owner|admin|viewer|租户|字段级|角色",
        r"SCIM|SSO|group\s+mapping|temporary\s+access|version\s+rollout|backward\s+compat|临时权限|版本|兼容",
        r"hidden\s+buttons?|middleware|happy[- ]?path|negative\s+authorization|stale\s+cache|revocation|隐藏按钮|负向授权|撤销",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_data_residency_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"data[- ]?residen|regional[- ]?isolation|region[- ]?isolation|tenant[- ]?residency|wrong[- ]?region|数据驻留|区域隔离|租户驻留|错区",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"data[- ]?residen|regional[- ]?isolation|tenant[- ]?residency|wrong[- ]?region|region[- ]?routing|residency[- ]?policy|数据驻留|区域隔离|租户驻留|错区|区域路由",
        r"primary[- ]?(?:db|database)|object[- ]?storage|search[- ]?index|cache|queue|backup|logs?|analytics|DB|数据库|对象存储|搜索索引|缓存|队列|备份|日志|分析",
        r"processor|subprocessor|DPA|allowlist|third[- ]?party|处理方|子处理方",
        r"key[- ]?region|encryption|failover|migration|backfill|密钥|故障转移|迁移|回填",
        r"support/admin|support[- ]?access|admin[- ]?access|data[- ]?export|audit|observability|trace|egress|客服|管理员|导出|审计|观测|出站",
        r"UI\s+showing\s+region|env\s+var|tenant\s+table\s+region|one\s+routed\s+request|docs[- ]?only\s+DPA|region=EU|字段|配置",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_support_impersonation_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_data_residency_task(text):
        return False
    if not re.search(r"support\s+impersonation|impersonat|break[- ]?glass|login[- ]as|代理登录|破窗|代入|模拟登录", text, re.IGNORECASE):
        return False
    markers = (
        r"support\s+impersonation|impersonat|break[- ]?glass|login[- ]as|代理登录|破窗|代入|模拟登录",
        r"approved\s+ticket|customer\s+consent|reason\s+code|supervisor\s+approval|审批|同意|原因码|主管",
        r"actor|acting_as|on_behalf_of|attribution|session|MFA|step[- ]?up|归因|会话|限时",
        r"PII|privacy|tenant|audit|tamper|revoke|expiry|export|monitoring|隐私|租户|审计|撤销|过期|导出|监控",
        r"shared\s+admin\s+token|shared[- ]?token|banner|feature\s+flag|no[- ]?ticket|after[- ]?hours|共享.*token|横幅",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_kyc_aml_screening_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_payout_settlement_reconciliation_task(text):
        return False
    if not re.search(
        r"\bKYC\b|\bKYB\b|\bAML\b|sanctions?|PEP|watchlist|身份核验|反洗钱|制裁筛查|受益所有人",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\bKYC\b|\bKYB\b|\bAML\b|sanctions?|PEP|watchlist|adverse\s+media|身份核验|反洗钱|制裁",
        r"identity|business\s+registry|beneficial\s+owner|document|OCR|liveness|address|身份|企业|受益所有人|证件|活体",
        r"manual\s+review|appeal|resubmission|risk\s+score|periodic\s+rescreen|人工审核|申诉|复筛|风险评分",
        r"provider|webhook|signature|replay|out[- ]?of[- ]?order|idempot|供应商|重放|乱序|幂等",
        r"payout|ledger|hold|release|retention|audit\s+reason|privacy|monitoring|打款|账本|冻结|释放|保留|审计|隐私|监控",
        r"sandbox\s+approved|UI\s+verified|provider\s+status|happy[- ]?path|沙箱|已验证",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_identity_sso_task(task: str) -> bool:
    text = str(task or "")
    if _agreement_is_authorization_policy_task(text):
        return False
    if not re.search(
        r"\b(?:SAML|OIDC|OpenID[- ]?Connect|SSO|IdP|identity[- ]?provider)\b|单点登录|身份提供商|身份断言",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:SAML|OIDC|OpenID[- ]?Connect|SSO|IdP|identity[- ]?provider|metadata|assertion|issuer|audience)\b|单点登录|身份提供商|身份断言|断言|发行方|受众",
        r"signature|signed|forged|replay|expired|expiry|session|logout|签名|伪造|重放|过期|会话|登出",
        r"tenant|domain\s+binding|cross[- ]?tenant|company\s+[AB]|租户|域名绑定|跨租户",
        r"SCIM|JIT|provision|deprovision|role\s+mapping|group\s+mapping|owner|admin|member|开通|停用|角色映射|组映射",
        r"password[- ]?login|backward\s+compat|migration|audit|monitoring|alert|密码登录|兼容|迁移|审计|监控|告警",
        r"Okta|library|UI\s+enabled|admin[- ]?only|happy[- ]?path|测试用户|已启用|只.*admin",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_key_rotation_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"\b(?:api[- ]?key|access[- ]?key|service[- ]?account[- ]?secret|client[- ]?secret|credential|kms[- ]?key)\b|API\s*key|访问密钥|服务账号密钥|客户端密钥|KMS\s*密钥",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"key[- ]?rotation|secret[- ]?rotation|rotat(?:e|ed|ion)|overlap[- ]?window|zero[- ]?downtime|compromised[- ]?key|revok|hash|kms[- ]?encrypt|last[- ]?used|stale[- ]?key|密钥轮换|密钥旋转|轮换|重叠窗口|无中断|撤销|吊销|哈希|KMS\s*加密|最后使用|陈旧密钥",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:api[- ]?key|access[- ]?key|service[- ]?account[- ]?secret|client[- ]?secret|credential|kms[- ]?key)\b|API\s*key|访问密钥|服务账号密钥|客户端密钥|KMS\s*密钥",
        r"key[- ]?rotation|secret[- ]?rotation|rotat(?:e|ed|ion)|overlap[- ]?window|zero[- ]?downtime|轮换|重叠窗口|无中断",
        r"compromised[- ]?key|revok(?:e|ed|ing|ation)?|revoked[- ]?key|rollback|stale[- ]?key|被盗密钥|泄露密钥|撤销|吊销|失效|回滚|陈旧密钥",
        r"scope|tenant[- ]?binding|permission|auth|租户绑定|权限范围|密钥范围",
        r"hash(?:ed)?|kms[- ]?encrypt(?:ed|ion)|encrypted[- ]?storage|plaintext|secret\s+storage|哈希|哈希存储|KMS\s*加密|加密存储|明文",
        r"expiry|expires?|expiration|last[- ]?used|telemetry|rotation[- ]?schedule|key[- ]?id|过期|有效期|最后使用|使用遥测|轮换计划|密钥\s*id",
        r"audit|monitoring|alert|rotation[- ]?failure|stale[- ]?key|审计|监控|告警|轮换失败|陈旧密钥",
        r"new[- ]?key|env\s+var|happy[- ]?path|docs[- ]?only|UI|新\s*key|环境变量|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _agreement_is_payment_webhook_ledger_task(task: str) -> bool:
    text = str(task or "")
    if (
        _agreement_is_cdc_replication_consistency_task(text)
        or _agreement_is_dispute_chargeback_lifecycle_task(text)
        or _agreement_is_identity_sso_task(text)
        or _agreement_is_usage_quota_metering_task(text)
        or _agreement_is_tax_calculation_compliance_task(text)
        or _agreement_is_inventory_reservation_consistency_task(text)
        or _agreement_is_subscription_entitlement_billing_task(text)
    ):
        return False
    if not re.search(
        r"webhook|provider\s+event|event\s+(?:schema|id)|signed\s+fixture|checkout\.session|支付.*事件|付款.*事件|供应商事件",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"payment\s+provider|checkout|refund|dispute|chargeback|payout|settlement|payment|invoice|balance|ledger|reconciliation|stripe|adyen|支付|结账|退款|争议|拒付|打款|结算|发票|余额|账本|对账",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"webhook|provider\s+event|event\s+schema|signature|timestamp|replay|out[- ]?of[- ]?order|idempot|duplicate|webhook|签名|时间戳|重放|乱序|幂等|重复",
        r"checkout|refund|dispute|chargeback|payout|settlement|payment|invoice|balance|支付|结账|退款|争议|拒付|打款|结算|发票|余额",
        r"ledger|reconciliation|reconcile|accounting|settlement\s+report|bank\s+statement|账本|对账|会计|结算报告|银行流水",
        r"retry|backoff|dead[- ]?letter|DLQ|queue|manual\s+replay|provider\s+failure|重试|退避|死信|队列|手动重放|供应商失败",
        r"audit|privacy|redaction|monitoring|alert|审计|隐私|脱敏|监控|告警",
        r"happy[- ]?path|unsigned|dev\s+mode|provider[- ]?status|database\s+unique|unique\s+constraint|docs[- ]?only|无签名|开发模式|状态|唯一约束|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_is_incident_root_cause_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(r"incident|outage|production\s+bug|duplicate\s+charge|root[- ]?cause|RCA|事故|故障|重复扣款|根因", text, re.IGNORECASE):
        return False
    markers = (
        r"incident|outage|production\s+bug|事故|故障|duplicate\s+charge|重复扣款",
        r"root[- ]?cause|RCA|根因",
        r"repro|reproduce|trigger\s+condition|failure\s+mode|复现|触发条件",
        r"regression|monitoring|alert|recurrence|rollback|release|回归|监控|告警|复发|回滚|发布",
        r"patch|repair|fix|修复|补丁",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _agreement_task_clause(task_text: str) -> str:
    return str(task_text or "").strip().rstrip("。.!?？")


def _task_anchor_terms_text(task_text: str) -> str:
    terms = agent_candidate_traceability_terms(task_text)
    if terms:
        return ", ".join(terms[:8])
    return "the confirmed task scope"


def _task_success_surface_evidence(
    task_text: str,
    *,
    anchors: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    explicit = _task_sentence_matching(
        task_text,
        (
            r"\b(?:success|done|complete|completion|must prove|must show|prove|verified|audit(?:able)?)\b",
            r"完成时|成功|完成标准|必须证明|需要证明|证明|可审计|可追踪|用户能|用户可以",
        ),
        reject_patterns=(
            r"\b(?:fake[- ]?done|not enough|not complete|doesn't count|happy[- ]?path|screenshot|mock[- ]?only)\b",
            r"不算完成|假完成|截图|只有|只靠|happy path|mock-only",
        ),
    )
    if explicit:
        if str(display_language or "").strip().lower() == "es":
            return (
                f"La superficie de éxito sigue el juicio de cierre del usuario: {explicit}. GateKeeper también necesita comportamiento ejecutable, "
                "artefactos duraderos, handoffs y buckets de evidencia que prueben ese juicio."
            )
        return (
            f"成功面采用用户给出的完成判断：{explicit}。GateKeeper 还要看到可运行行为、持久 artifact、handoff 和证据桶能证明这条判断。"
            if prefers_chinese
            else f"Success surface follows the user's completion judgment: {explicit}. GateKeeper also needs runnable behavior, durable artifacts, handoffs, and evidence buckets that prove this judgment."
        )
    if str(display_language or "").strip().lower() == "es":
        return (
            "El éxito significa que el usuario puede auditar cómo se satisface la ancla de tarea con comportamiento ejecutable, "
            f"artefactos duraderos, handoffs y buckets de evidencia ligados a estas anclas: {anchors}."
        )
    if prefers_chinese:
        return f"成功意味着用户能从可运行行为、持久 artifact、handoff 和证据桶里审计任务锚点如何成立；需要保留这些锚点：{anchors}。"
    return (
        "Success means the user can inspect how the task anchor is satisfied through runnable behavior, "
        f"durable artifacts, handoffs, and evidence buckets tied to these anchors: {anchors}."
    )


def _task_fake_done_risk_evidence(
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    explicit = _task_sentence_matching(
        task_text,
        (
            r"\b(?:fake[- ]?done|not enough|not complete|doesn't count|happy[- ]?path|screenshot|mock[- ]?only|block)\b",
            r"不算完成|假完成|截图|只有|只靠|happy path|mock-only|必须阻断|要阻断",
        ),
    )
    if str(display_language or "").strip().lower() == "es":
        base = (
            "Rechazar evidencia solo happy path, solo mock, capturas o cambios de estado sin casos negativos, "
            "handoffs genéricos, falta de timeout/retry/fallback cuando importa el fallo de provider, y cualquier bundle que pierda el ancla de tarea."
        )
        return f"Riesgo de falso terminado nombrado por el usuario: {explicit}. {base}" if explicit else base
    if prefers_chinese:
        base = (
            "拒绝只有 happy path、mock-only、没有负向样本的截图或状态变化、泛泛 handoff；"
            "涉及 provider failure 时缺少 timeout、retry/backoff 或 fallback 证据也必须阻断；不得把任务锚点降级成泛化首版框架。"
        )
    else:
        base = (
            "Reject happy-path-only proof, mock-only proof, screenshots or status changes without negative cases, "
            "generic handoffs, missing timeout / retry / fallback proof when provider failure matters, "
            "and any bundle that drops the task anchor into starter-experience framing."
        )
    if not explicit:
        return base
    return f"用户点名的假完成风险：{explicit}。{base}" if prefers_chinese else f"User-named fake-done risk: {explicit}. {base}"


def _task_sentence_matching(
    task_text: str,
    patterns: tuple[str, ...],
    *,
    reject_patterns: tuple[str, ...] = (),
) -> str:
    for sentence in _task_sentences(task_text):
        if reject_patterns and any(re.search(pattern, sentence, re.IGNORECASE) for pattern in reject_patterns):
            continue
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in patterns):
            return sentence
    return ""


def _task_sentences(task_text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(task_text or "")).strip()
    if not normalized:
        return []
    sentences = [item.strip(" \t\r\n,，.。;；:：") for item in re.split(r"[。.!?！？；;]\s*", normalized)]
    return [sentence for sentence in sentences if sentence]


def alignment_refund_agreement_response() -> dict:
    payload = alignment_agreement_response()
    payload["assistant_message"] = (
        "Please confirm this refund working agreement; I will compile authorization, eligibility, "
        "audit, provider failure, and support handoff judgment into the Loop."
    )
    payload["agreement_summary"] = (
        "Govern the refund self-service flow around authorization, eligibility, audit trail, provider failure, "
        "double-refund blocking, and support handoff evidence."
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            "The refund task fits Loopora because final production and finance feedback arrives too late; later rounds "
            "must produce intermediate authorization, eligibility, provider failure, audit trail, and support handoff "
            "evidence that can trigger repair or blocking before GateKeeper can close."
        ),
        "task_scope": (
            "Scope is a refund self-service flow for customer admins: authorized admins request eligible refunds, "
            "while disputed, closed-accounting, partial-refund, and double-refund cases are controlled."
        ),
        "success_surface": (
            "Success means an eligible refund can be requested by an authorized admin, recorded with an audit trail, "
            "and traced by support or finance from durable evidence."
        ),
        "fake_done_risks": (
            "Reject pages, buttons, mocked eligibility, or happy-path-only tests that do not prove refund authorization, "
            "auditability, provider failure handling, and double-refund prevention."
        ),
        "evidence_preferences": (
            "Trusted proof is permission checks, eligibility cases, payment-provider failure behavior, audit records, "
            "support handoff artifacts, and final Proven / Weak / Unproven / Blocking / Residual risk buckets."
        ),
        "execution_strategy": (
            "First prove authorization, eligibility, audit, provider failure, and support handoff on a narrow refund path; "
            "defer UI polish or broader billing expansion until those risks have direct evidence."
        ),
        "residual_risk_policy": (
            "Rare provider edge cases may remain only when visible and assigned; unauthorized refunds, missing audit trails, "
            "silent provider failure, and double refunds must block closure."
        ),
        "judgment_tradeoffs": (
            "Prefer a rough but proven refund path over a polished billing screen; reject speed or UI completeness "
            "when it hides authorization, audit, provider, or support risk."
        ),
        "local_governance": (
            "If project-local governance markers are present, Builder reads the applicable rules before editing, "
            "Inspector verifies the related design or test obligations, and GateKeeper treats skipped local governance "
            "as Weak, Unproven, or Blocking without inventing marker contents."
        ),
        "role_posture": (
            "Builder implements refund safety, Inspector tries to disprove authorization and audit claims, "
            "Guide narrows repair if evidence is weak, and GateKeeper blocks unauthorized or double-refund risk."
        ),
        "workflow_shape": (
            "Builder -> Inspector -> Guide repair -> Builder -> GateKeeper fits because refund drift must surface "
            "through evidence before the final GateKeeper verdict, and weak proof must redirect the next pass toward "
            "evidence-first repair rather than broader implementation."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path; billing, payment, and audit code locations must be verified during the run."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }
    return payload


def alignment_chinese_refund_agreement_response() -> dict:
    payload = alignment_chinese_agreement_response()
    payload["assistant_message"] = "请确认退款自助流程工作协议；确认后我会编译授权、资格、审计和支付失败证据。"
    payload["agreement_summary"] = "围绕退款自助流程治理授权、退款资格、审计记录、支付失败、重复退款阻断和客服交接证据。"
    payload["readiness_evidence"] = {
        "loop_fit": "退款任务适合 Loopora，因为真正的生产、财务或合规反馈来得太晚；后续轮次必须产生授权、退款资格、审计记录、支付失败和客服交接等中间证据，用来提前触发修复或阻断，而不是等一次最终反馈。",
        "task_scope": "范围是客户管理员的退款自助流程：授权管理员申请符合资格的退款，并控制争议订单、已关账发票、部分退款和重复退款。",
        "success_surface": "成功意味着授权管理员能申请符合资格的退款，系统记录审计轨迹，客服或财务能追踪退款决定。",
        "fake_done_risks": "拒绝只有页面、按钮、模拟资格或 happy path 测试，却没有证明退款授权、审计、支付失败处理和重复退款防护的结果。",
        "evidence_preferences": "可信证据包括授权检查、退款资格用例、支付服务失败行为、审计记录、客服交接产物，以及最终已证明、弱证据、未证明、阻断和残余风险证据桶。",
        "execution_strategy": "先证明授权、退款资格、支付失败、审计和客服交接，再考虑扩展界面体验；证据薄弱时先收窄到可证明路径。",
        "residual_risk_policy": "少见支付服务边缘情况只有在可见并分配后才可接受；未授权退款、缺失审计、静默支付失败和重复退款必须阻断。",
        "judgment_tradeoffs": "优先选择粗糙但已证明的退款路径，而不是漂亮但未证明授权、审计、支付或客服风险的账单界面。",
        "local_governance": "若存在项目本地治理入口，Builder 先读取适用规则，Inspector 验证相关 design 或 test 义务，GateKeeper 将跳过本地治理视为弱证据、未证明或阻断，且不编造 marker 内容。",
        "role_posture": "Builder 实现退款安全，Inspector 反证授权和审计声明，Guide 在证据薄弱时收窄修复，GateKeeper 阻断未授权或重复退款风险。",
        "workflow_shape": "Builder -> Inspector -> Guide 修复 -> Builder -> GateKeeper 适合退款任务，因为退款偏差必须在最终裁决前通过证据暴露，且弱证据要把下一轮转向补证据，而不是继续铺开实现。",
        "workdir_facts": "已观察到的工作区事实只限目标路径；退款、支付、审计代码位置必须在运行中验证。",
        "open_questions": "等待用户明确确认这份工作协议。",
    }
    return payload
