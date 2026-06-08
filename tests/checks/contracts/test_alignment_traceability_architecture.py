from __future__ import annotations

from pathlib import Path

from loopora.alignment_traceability_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.alignment_traceability_rules import alignment_agent_candidate_tradeoff_issues
from loopora.alignment_traceability_terms import agent_candidate_task_anchor_terms, agent_candidate_traceability_terms


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_traceability_risk_categories_have_dedicated_boundary() -> None:
    categories_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_categories.py").read_text(
        encoding="utf-8"
    )
    risk_categories_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_risk_categories.py"
    ).read_text(encoding="utf-8")
    domain_patterns_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert agent_candidate_fake_done_categories.__module__ == "loopora.alignment_traceability_risk_categories"
    assert agent_candidate_evidence_preference_categories.__module__ == "loopora.alignment_traceability_risk_categories"
    assert "from loopora.alignment_traceability_risk_categories import" in categories_source
    assert "from loopora.alignment_traceability_domain_patterns import" in categories_source
    assert "from loopora.alignment_traceability_domain_patterns import" in risk_categories_source
    for marker in (
        "ACCESSIBILITY_A11Y_PATTERN",
        "ANALYTICS_EVENT_INTEGRITY_PATTERN",
        "AUDIT_LOG_INTEGRITY_RETENTION_PATTERN",
        "ASYNC_JOB_LIFECYCLE_PATTERN",
        "AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN",
        "AUTHORIZATION_POLICY_CONSISTENCY_PATTERN",
        "BACKUP_RESTORE_RECOVERY_PATTERN",
        "BILLING_LEDGER_RECONCILIATION_PATTERN",
        "CACHE_INVALIDATION_CONSISTENCY_PATTERN",
        "CDC_REPLICATION_CONSISTENCY_PATTERN",
        "CONSENT_PREFERENCE_GOVERNANCE_PATTERN",
        "CONCURRENCY_CONFLICT_RESOLUTION_PATTERN",
        "DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN",
        "DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN",
        "DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN",
        "MIGRATION_ROLLBACK_INTEGRITY_PATTERN",
        "BACKWARD_COMPATIBILITY_PATTERN",
        "EVALUATION_SET_PATTERN",
        "EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN",
        "FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN",
        "HUMAN_REVIEW_QUALITY_PATTERN",
        "FILE_UPLOAD_STORAGE_SAFETY_PATTERN",
        "INCIDENT_ROOT_CAUSE_REPRO_PATTERN",
        "INVENTORY_RESERVATION_CONSISTENCY_PATTERN",
        "KYC_AML_SANCTIONS_SCREENING_PATTERN",
        "REGRESSION_MONITORING_GUARD_PATTERN",
        "EXTERNAL_PROVIDER_CONTRACT_PATTERN",
        "IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN",
        "IDENTITY_SSO_ASSERTION_PATTERN",
        "KEY_ROTATION_SECRET_LIFECYCLE_PATTERN",
        "LOCALE_I18N_PATTERN",
        "METRIC_REPORTING_RECONCILIATION_PATTERN",
        "RESILIENCE_RETRY_TIMEOUT_PATTERN",
        "SCHEDULE_TIMEZONE_RECURRENCE_PATTERN",
        "SEARCH_INDEX_CONSISTENCY_PATTERN",
        "SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN",
        "TAX_CALCULATION_COMPLIANCE_PATTERN",
        "USAGE_QUOTA_METERING_PATTERN",
        "NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN",
        "PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN",
        "TENANT_ISOLATION_PATTERN",
        "DATA_LIFECYCLE_DELETION_RETENTION_PATTERN",
        "QUEUE_FAILURE_RECOVERY_PATTERN",
        "RAG_GROUNDING_TOOL_SAFETY_PATTERN",
        "WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN",
    ):
        assert marker in domain_patterns_source
        assert marker in categories_source
        assert marker in risk_categories_source
    for marker in ("def agent_candidate_fake_done_categories", "def agent_candidate_evidence_preference_categories"):
        assert marker in risk_categories_source
        assert marker not in categories_source
    assert "alignment_traceability_risk_categories.py" in design_source
    assert "alignment_traceability_domain_patterns.py" in design_source


def test_alignment_traceability_terms_use_dedicated_catalog_boundary() -> None:
    terms_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_terms.py").read_text(encoding="utf-8")
    catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_term_catalog.py").read_text(
        encoding="utf-8"
    )
    generic_catalog_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_generic_term_catalog.py"
    ).read_text(encoding="utf-8")
    cjk_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_cjk_term_catalog.py").read_text(
        encoding="utf-8"
    )
    agent_catalog_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_agent_term_catalog.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.alignment_traceability_term_catalog import" in terms_source
    assert "from loopora.alignment_traceability_generic_term_catalog import" in catalog_source
    assert "from loopora.alignment_traceability_cjk_term_catalog import" in catalog_source
    assert "from loopora.alignment_traceability_agent_term_catalog import" in catalog_source
    for marker, source in (
        ("ALIGNMENT_TRACEABILITY_GENERIC_TERMS", generic_catalog_source),
        ("ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS", generic_catalog_source),
        ("ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS", cjk_catalog_source),
        ("ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS", cjk_catalog_source),
        ("ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS", cjk_catalog_source),
        ("ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS", agent_catalog_source),
    ):
        assert marker in source
        assert marker in catalog_source
        assert f"{marker} =" not in terms_source
    for marker in (
        "def agent_candidate_traceability_terms",
        "def agreement_cjk_traceability_terms",
        "def agreement_repeated_cjk_traceability_terms",
        "def agreement_traceability_terms",
    ):
        assert marker in terms_source
        assert marker not in catalog_source
    assert "alignment_traceability_term_catalog.py" in design_source
    assert "alignment_traceability_generic_term_catalog.py" in design_source
    assert "alignment_traceability_cjk_term_catalog.py" in design_source
    assert "alignment_traceability_agent_term_catalog.py" in design_source


def test_alignment_agent_candidate_terms_keep_billing_ledger_anchors_without_generic_action_words() -> None:
    terms = agent_candidate_traceability_terms(
        "Prepare a Stripe webhook implementation for ledger reconciliation with replay and signature proof."
    )

    assert "prepare" not in terms
    assert "implementation" not in terms
    assert "stripe" in terms
    assert "webhook" in terms
    assert "ledger" in terms


def test_alignment_agent_candidate_terms_ignore_loopora_internal_evidence_ledger() -> None:
    terms = agent_candidate_traceability_terms(
        "Reject invented evidence refs before non-GateKeeper output enters the ledger."
    )

    assert "ledger" not in terms


def test_alignment_agent_candidate_task_anchor_terms_require_business_domain_anchor() -> None:
    assert agent_candidate_task_anchor_terms("请帮我生成一个中文任务的循环方案。") == []
    assert agent_candidate_task_anchor_terms("Build a starter experience with weak execution_strategy evidence.") == []

    stripe_terms = agent_candidate_task_anchor_terms(
        "Build Stripe webhook ledger reconciliation with replay and signature proof."
    )
    rag_terms = agent_candidate_task_anchor_terms(
        "Prepare a RAG support chatbot that proves retrieval ACL, citation grounding, and fallback behavior."
    )

    assert {"stripe", "webhook", "ledger"}.issubset(stripe_terms)
    assert {"retrieval", "citation", "grounding"}.issubset(rag_terms)


def test_alignment_agent_candidate_traceability_category_rules_have_dedicated_boundary() -> None:
    rules_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_rules.py").read_text(encoding="utf-8")
    agent_candidate_rules_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_agent_candidate_rules.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert alignment_agent_candidate_tradeoff_issues.__module__ == (
        "loopora.alignment_traceability_agent_candidate_rules"
    )
    assert "from loopora.alignment_traceability_agent_candidate_rules import" in rules_source
    for marker in (
        "def alignment_agent_candidate_tradeoff_issues",
        "def alignment_agent_candidate_execution_strategy_issues",
        "def alignment_agent_candidate_residual_risk_policy_issues",
    ):
        assert marker in agent_candidate_rules_source
        assert marker not in rules_source
    assert "alignment_traceability_agent_candidate_rules.py" in design_source
