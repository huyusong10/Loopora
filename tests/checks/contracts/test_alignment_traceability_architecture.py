from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source

from loopora import alignment_traceability_candidate_execution_catalog as candidate_execution_catalog
from loopora import alignment_traceability_candidate_residual_risk_catalog as candidate_residual_risk_catalog
from loopora import alignment_traceability_candidate_success_surface_catalog as candidate_success_surface_catalog
from loopora import alignment_traceability_candidate_success_surface_core_catalog as candidate_success_surface_core_catalog
from loopora import alignment_traceability_candidate_success_surface_data_access_catalog as candidate_success_surface_data_access_catalog
from loopora import alignment_traceability_candidate_success_surface_delivery_catalog as candidate_success_surface_delivery_catalog
from loopora import alignment_traceability_candidate_success_surface_operations_catalog as candidate_success_surface_operations_catalog
from loopora import alignment_traceability_candidate_success_surface_trust_locale_catalog as candidate_success_surface_trust_locale_catalog
from loopora import alignment_traceability_candidate_tradeoff_catalog as candidate_tradeoff_catalog
from loopora import alignment_traceability_domain_patterns_data as domain_patterns_data
from loopora import alignment_traceability_domain_patterns_data_commerce as domain_patterns_data_commerce
from loopora import alignment_traceability_domain_patterns_data_ingest as domain_patterns_data_ingest
from loopora import alignment_traceability_domain_patterns_data_lifecycle as domain_patterns_data_lifecycle
from loopora import alignment_traceability_domain_patterns_data_read_models as domain_patterns_data_read_models
from loopora import alignment_traceability_domain_patterns_data_resilience as domain_patterns_data_resilience
from loopora import alignment_traceability_domain_patterns_trust as domain_patterns_trust
from loopora import alignment_traceability_domain_patterns_trust_access as domain_patterns_trust_access
from loopora import alignment_traceability_domain_patterns_trust_compliance as domain_patterns_trust_compliance
from loopora import alignment_traceability_domain_patterns_trust_identity as domain_patterns_trust_identity
from loopora import alignment_traceability_domain_patterns_trust_inclusion as domain_patterns_trust_inclusion
from loopora.alignment_traceability_candidate_catalog import (
    EXECUTION_STRATEGY_CATEGORY_PATTERNS,
    EXECUTION_STRATEGY_MARKER_PATTERNS,
    NO_ACCEPTED_RESIDUAL_RISK_BUNDLE_PATTERN,
    NO_ACCEPTED_RESIDUAL_RISK_TASK_PATTERN,
    RESIDUAL_RISK_BASE_CATEGORY,
    RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS,
    RESIDUAL_RISK_POLICY_MARKER_PATTERNS,
    SUCCESS_SURFACE_BASE_CATEGORY,
    SUCCESS_SURFACE_CATEGORY_PATTERNS,
    SUCCESS_SURFACE_MARKER_PATTERNS,
    TRADEOFF_CATEGORY_PATTERNS,
    TRADEOFF_MARKER_PATTERNS,
)
from loopora.alignment_traceability_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.alignment_traceability_cjk_domain_terms import ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS
from loopora.alignment_traceability_cjk_domain_terms_commerce import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_COMMERCE_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_core_trust import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_CORE_TRUST_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_data_platform import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_DATA_PLATFORM_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_governance import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_GOVERNANCE_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_operations import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_OPERATIONS_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_workflow import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_WORKFLOW_TERMS,
)
from loopora.alignment_traceability_evidence_catalog import EVIDENCE_PREFERENCE_CATEGORY_PATTERNS
from loopora.alignment_traceability_fake_done_catalog import FAKE_DONE_CATEGORY_PATTERNS
from loopora.alignment_traceability_fake_done_core_catalog import FAKE_DONE_CORE_CATEGORY_PATTERNS
from loopora.alignment_traceability_fake_done_data_access_catalog import FAKE_DONE_DATA_ACCESS_CATEGORY_PATTERNS
from loopora.alignment_traceability_fake_done_delivery_catalog import FAKE_DONE_DELIVERY_CATEGORY_PATTERNS
from loopora.alignment_traceability_fake_done_operations_catalog import FAKE_DONE_OPERATIONS_CATEGORY_PATTERNS
from loopora.alignment_traceability_fake_done_surface_catalog import FAKE_DONE_SURFACE_CATEGORY_PATTERNS
from loopora.alignment_traceability_risk_markers import (
    EXPLICIT_EVIDENCE_MARKER_PATTERNS,
    EXPLICIT_FAKE_DONE_MARKER_PATTERNS,
)
from loopora.alignment_traceability_rules import alignment_agent_candidate_tradeoff_issues
from loopora.alignment_traceability_terms import agent_candidate_task_anchor_terms, agent_candidate_traceability_terms


REPO_ROOT = Path(__file__).resolve().parents[3]


DOMAIN_PATTERN_MARKERS = (
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
)

DATA_DOMAIN_PATTERN_FAMILY_CATALOGS = (
    (
        "alignment_traceability_domain_patterns_data_ingest.py",
        "FILE_UPLOAD_STORAGE_SAFETY_PATTERN",
        "DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN",
    ),
    (
        "alignment_traceability_domain_patterns_data_commerce.py",
        "INVENTORY_RESERVATION_CONSISTENCY_PATTERN",
        "TAX_CALCULATION_COMPLIANCE_PATTERN",
    ),
    (
        "alignment_traceability_domain_patterns_data_resilience.py",
        "BACKUP_RESTORE_RECOVERY_PATTERN",
        "AUDIT_LOG_INTEGRITY_RETENTION_PATTERN",
    ),
    (
        "alignment_traceability_domain_patterns_data_read_models.py",
        "CACHE_INVALIDATION_CONSISTENCY_PATTERN",
        "SEARCH_INDEX_CONSISTENCY_PATTERN",
    ),
    (
        "alignment_traceability_domain_patterns_data_lifecycle.py",
        "DATA_LIFECYCLE_DELETION_RETENTION_PATTERN",
        "CONSENT_PREFERENCE_GOVERNANCE_PATTERN",
    ),
)

TRUST_DOMAIN_PATTERN_FAMILY_CATALOGS = (
    (
        "alignment_traceability_domain_patterns_trust_compliance.py",
        "KYC_AML_SANCTIONS_SCREENING_PATTERN",
        "KYC_AML_SANCTIONS_SCREENING_PATTERN",
    ),
    (
        "alignment_traceability_domain_patterns_trust_access.py",
        "TENANT_ISOLATION_PATTERN",
        "SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN",
    ),
    (
        "alignment_traceability_domain_patterns_trust_identity.py",
        "IDENTITY_SSO_ASSERTION_PATTERN",
        "KEY_ROTATION_SECRET_LIFECYCLE_PATTERN",
    ),
    (
        "alignment_traceability_domain_patterns_trust_inclusion.py",
        "ACCESSIBILITY_A11Y_PATTERN",
        "LOCALE_I18N_PATTERN",
    ),
)

CJK_DOMAIN_FAMILY_CATALOGS = (
    (
        "alignment_traceability_cjk_domain_terms_core_trust.py",
        "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_CORE_TRUST_TERMS",
        "审批",
    ),
    (
        "alignment_traceability_cjk_domain_terms_commerce.py",
        "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_COMMERCE_TERMS",
        "支付",
    ),
    (
        "alignment_traceability_cjk_domain_terms_data_platform.py",
        "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_DATA_PLATFORM_TERMS",
        "备份",
    ),
    (
        "alignment_traceability_cjk_domain_terms_workflow.py",
        "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_WORKFLOW_TERMS",
        "协作文档",
    ),
    (
        "alignment_traceability_cjk_domain_terms_governance.py",
        "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_GOVERNANCE_TERMS",
        "实验",
    ),
    (
        "alignment_traceability_cjk_domain_terms_operations.py",
        "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_OPERATIONS_TERMS",
        "自助",
    ),
)

CANDIDATE_FAMILY_CATALOGS = (
    (
        "alignment_traceability_candidate_tradeoff_catalog.py",
        "TRADEOFF_MARKER_PATTERNS",
        "proof/evidence",
    ),
    (
        "alignment_traceability_candidate_execution_catalog.py",
        "EXECUTION_STRATEGY_MARKER_PATTERNS",
        "repair/root-cause",
    ),
    (
        "alignment_traceability_candidate_residual_risk_catalog.py",
        "RESIDUAL_RISK_POLICY_MARKER_PATTERNS",
        "owner/follow-up",
    ),
    (
        "alignment_traceability_candidate_success_surface_catalog.py",
        "SUCCESS_SURFACE_MARKER_PATTERNS",
        "SUCCESS_SURFACE_CATEGORY_PATTERNS",
    ),
)

SUCCESS_SURFACE_FAMILY_CATALOGS = (
    (
        "alignment_traceability_candidate_success_surface_core_catalog.py",
        "SUCCESS_SURFACE_CORE_CATEGORY_PATTERNS",
        "actor/user-facing-outcome",
    ),
    (
        "alignment_traceability_candidate_success_surface_delivery_catalog.py",
        "SUCCESS_SURFACE_DELIVERY_CATEGORY_PATTERNS",
        "migration/rollback-integrity",
    ),
    (
        "alignment_traceability_candidate_success_surface_data_access_catalog.py",
        "SUCCESS_SURFACE_DATA_ACCESS_CATEGORY_PATTERNS",
        "access/tenant-isolation",
    ),
    (
        "alignment_traceability_candidate_success_surface_operations_catalog.py",
        "SUCCESS_SURFACE_OPERATIONS_CATEGORY_PATTERNS",
        "analytics/event-integrity",
    ),
    (
        "alignment_traceability_candidate_success_surface_trust_locale_catalog.py",
        "SUCCESS_SURFACE_TRUST_LOCALE_CATEGORY_PATTERNS",
        "identity/sso-assertion",
    ),
)

FAKE_DONE_FAMILY_CATALOGS = (
    (
        "alignment_traceability_fake_done_core_catalog.py",
        "FAKE_DONE_CORE_CATEGORY_PATTERNS",
        "permission/audit",
    ),
    (
        "alignment_traceability_fake_done_delivery_catalog.py",
        "FAKE_DONE_DELIVERY_CATEGORY_PATTERNS",
        "migration/rollback-integrity",
    ),
    (
        "alignment_traceability_fake_done_data_access_catalog.py",
        "FAKE_DONE_DATA_ACCESS_CATEGORY_PATTERNS",
        "access/tenant-isolation",
    ),
    (
        "alignment_traceability_fake_done_operations_catalog.py",
        "FAKE_DONE_OPERATIONS_CATEGORY_PATTERNS",
        "analytics/event-integrity",
    ),
    (
        "alignment_traceability_fake_done_surface_catalog.py",
        "FAKE_DONE_SURFACE_CATEGORY_PATTERNS",
        "visual/polish/screenshot-only",
    ),
)


def test_alignment_traceability_risk_categories_have_dedicated_boundary() -> None:
    categories_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_categories.py").read_text(encoding="utf-8")
    candidate_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_candidate_catalog.py").read_text(encoding="utf-8")
    candidate_family_source = "\n".join(
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _constant_name, _sample_label in (*CANDIDATE_FAMILY_CATALOGS, *SUCCESS_SURFACE_FAMILY_CATALOGS)
    )
    risk_categories_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_risk_categories.py").read_text(encoding="utf-8")
    evidence_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_evidence_catalog.py").read_text(encoding="utf-8")
    fake_done_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_fake_done_catalog.py").read_text(encoding="utf-8")
    fake_done_family_source = "\n".join(
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8") for filename, _constant_name, _sample_label in FAKE_DONE_FAMILY_CATALOGS
    )
    risk_markers_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_risk_markers.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert agent_candidate_fake_done_categories.__module__ == "loopora.alignment_traceability_risk_categories"
    assert agent_candidate_evidence_preference_categories.__module__ == "loopora.alignment_traceability_risk_categories"
    assert "from loopora.alignment_traceability_risk_categories import" in categories_source
    assert "from loopora.alignment_traceability_candidate_catalog import" in categories_source
    assert "from loopora.alignment_traceability_domain_patterns import" not in categories_source
    assert "from loopora.alignment_traceability_domain_patterns import" not in candidate_catalog_source
    assert "from loopora.alignment_traceability_domain_patterns import" in candidate_family_source
    assert "from loopora.alignment_traceability_evidence_catalog import" in risk_categories_source
    assert "from loopora.alignment_traceability_fake_done_catalog import" in risk_categories_source
    assert "from loopora.alignment_traceability_domain_patterns import" not in risk_categories_source
    assert "from loopora.alignment_traceability_domain_patterns import" in evidence_catalog_source
    assert "from loopora.alignment_traceability_domain_patterns import" not in fake_done_catalog_source
    assert "from loopora.alignment_traceability_domain_patterns import" in fake_done_family_source
    assert FAKE_DONE_CATEGORY_PATTERNS
    assert "FAKE_DONE_CATEGORY_PATTERNS" in fake_done_catalog_source
    fake_done_function_source = risk_categories_source.split("def agent_candidate_fake_done_categories", 1)[1].split(
        "def agent_candidate_evidence_preference_categories",
        1,
    )[0]
    assert "category_patterns = (" not in fake_done_function_source
    assert EVIDENCE_PREFERENCE_CATEGORY_PATTERNS
    assert "EVIDENCE_PREFERENCE_CATEGORY_PATTERNS" in evidence_catalog_source
    assert "category_patterns = (" not in risk_categories_source.split("def agent_candidate_evidence_preference_categories", 1)[1]
    assert "from loopora.alignment_traceability_risk_markers import" in risk_categories_source
    assert EXPLICIT_FAKE_DONE_MARKER_PATTERNS
    assert EXPLICIT_EVIDENCE_MARKER_PATTERNS
    for marker in (
        "EXPLICIT_FAKE_DONE_MARKER_PATTERNS",
        "EXPLICIT_EVIDENCE_MARKER_PATTERNS",
        "FAKE_DONE_BLOCKING_PATTERN",
        "FAKE_DONE_HAPPY_PATH_MARKER_PATTERN",
        "FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN",
        "FAKE_DONE_PROOF_GAP_MARKER_PATTERN",
        "FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN",
        "EVIDENCE_PROOF_PATTERN",
        "def marker_matches_any",
        "def risk_marker_near_domain_pattern",
        "extra_marker_pattern",
    ):
        assert marker in risk_markers_source
        assert marker in risk_categories_source or marker in fake_done_family_source or marker.startswith("def ")
    assert "extra_marker_pattern=" not in fake_done_catalog_source
    assert "extra_marker_pattern=" in fake_done_family_source
    for marker in ("explicit_fake_done_markers = (", "explicit_evidence_markers = ("):
        assert marker not in risk_categories_source
    for marker in ("def agent_candidate_fake_done_categories", "def agent_candidate_evidence_preference_categories"):
        assert marker in risk_categories_source
        assert marker not in categories_source
    for marker in (
        "TRADEOFF_MARKER_PATTERNS",
        "TRADEOFF_CATEGORY_PATTERNS",
        "EXECUTION_STRATEGY_MARKER_PATTERNS",
        "EXECUTION_STRATEGY_CATEGORY_PATTERNS",
        "RESIDUAL_RISK_POLICY_MARKER_PATTERNS",
        "RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS",
        "SUCCESS_SURFACE_MARKER_PATTERNS",
        "SUCCESS_SURFACE_CATEGORY_PATTERNS",
    ):
        assert marker in candidate_catalog_source
        assert marker in candidate_family_source
        assert marker in categories_source
    for catalog in (
        TRADEOFF_MARKER_PATTERNS,
        TRADEOFF_CATEGORY_PATTERNS,
        EXECUTION_STRATEGY_MARKER_PATTERNS,
        EXECUTION_STRATEGY_CATEGORY_PATTERNS,
        RESIDUAL_RISK_POLICY_MARKER_PATTERNS,
        RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS,
        SUCCESS_SURFACE_MARKER_PATTERNS,
        SUCCESS_SURFACE_CATEGORY_PATTERNS,
    ):
        assert catalog
    for marker in (
        "explicit_tradeoff_markers = (",
        "explicit_strategy_markers = (",
        "explicit_policy_markers = (",
        "explicit_success_markers = (",
        "category_patterns = (",
    ):
        assert marker not in categories_source
    assert "alignment_traceability_risk_categories.py" in design_source
    assert "alignment_traceability_candidate_catalog.py" in design_source
    assert "alignment_traceability_evidence_catalog.py" in design_source
    assert "alignment_traceability_fake_done_catalog.py" in design_source
    assert "alignment_traceability_risk_markers.py" in design_source


def test_alignment_traceability_domain_patterns_use_family_catalogs() -> None:
    candidate_family_source = "\n".join(
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _constant_name, _sample_label in (*CANDIDATE_FAMILY_CATALOGS, *SUCCESS_SURFACE_FAMILY_CATALOGS)
    )
    evidence_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_evidence_catalog.py").read_text(encoding="utf-8")
    fake_done_family_source = "\n".join(
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8") for filename, _constant_name, _sample_label in FAKE_DONE_FAMILY_CATALOGS
    )
    domain_patterns_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns.py").read_text(encoding="utf-8")
    data_family_source = "\n".join(
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _first_constant_name, _last_constant_name in DATA_DOMAIN_PATTERN_FAMILY_CATALOGS
    )
    trust_family_source = "\n".join(
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _first_constant_name, _last_constant_name in TRUST_DOMAIN_PATTERN_FAMILY_CATALOGS
    )
    domain_family_sources = (
        (REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns_delivery.py").read_text(encoding="utf-8"),
        (REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns_trust.py").read_text(encoding="utf-8"),
        trust_family_source,
        (REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns_data.py").read_text(encoding="utf-8"),
        data_family_source,
        (REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns_operations.py").read_text(encoding="utf-8"),
    )
    design_source = design_boundary_source()

    for marker in (
        "from loopora.alignment_traceability_domain_patterns_delivery import",
        "from loopora.alignment_traceability_domain_patterns_trust import",
        "from loopora.alignment_traceability_domain_patterns_data import",
        "from loopora.alignment_traceability_domain_patterns_operations import",
    ):
        assert marker in domain_patterns_source
    assert "_PATTERN = (" not in domain_patterns_source
    for marker in DOMAIN_PATTERN_MARKERS:
        assert marker in domain_patterns_source
        assert any(marker in source for source in domain_family_sources)
        assert marker in candidate_family_source
        assert marker in evidence_catalog_source or marker in fake_done_family_source or marker in candidate_family_source
    assert "alignment_traceability_domain_patterns.py" in design_source
    assert "alignment_traceability_domain_patterns_delivery.py" in design_source
    assert "alignment_traceability_domain_patterns_trust.py" in design_source
    assert "alignment_traceability_domain_patterns_data.py" in design_source
    assert "alignment_traceability_domain_patterns_operations.py" in design_source


def test_alignment_traceability_trust_domain_patterns_use_family_catalogs() -> None:
    trust_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns_trust.py").read_text(encoding="utf-8")
    family_sources = {
        filename: (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _first_constant_name, _last_constant_name in TRUST_DOMAIN_PATTERN_FAMILY_CATALOGS
    }
    design_source = design_boundary_source()

    for filename, first_constant_name, last_constant_name in TRUST_DOMAIN_PATTERN_FAMILY_CATALOGS:
        module_name = filename.removesuffix(".py")
        assert f"from loopora.{module_name} import" in trust_source
        assert first_constant_name in trust_source
        assert last_constant_name in trust_source
        assert first_constant_name in family_sources[filename]
        assert last_constant_name in family_sources[filename]
        assert filename in design_source
    assert 'r"(?:' not in trust_source
    assert "实名认证" not in trust_source
    assert domain_patterns_trust.KYC_AML_SANCTIONS_SCREENING_PATTERN is domain_patterns_trust_compliance.KYC_AML_SANCTIONS_SCREENING_PATTERN
    for pattern_name in (
        "TENANT_ISOLATION_PATTERN",
        "AUTHORIZATION_POLICY_CONSISTENCY_PATTERN",
        "DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN",
        "SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN",
    ):
        assert getattr(domain_patterns_trust, pattern_name) is getattr(domain_patterns_trust_access, pattern_name)
    for pattern_name in (
        "IDENTITY_SSO_ASSERTION_PATTERN",
        "IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN",
        "AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN",
        "KEY_ROTATION_SECRET_LIFECYCLE_PATTERN",
    ):
        assert getattr(domain_patterns_trust, pattern_name) is getattr(domain_patterns_trust_identity, pattern_name)
    for pattern_name in ("ACCESSIBILITY_A11Y_PATTERN", "LOCALE_I18N_PATTERN"):
        assert getattr(domain_patterns_trust, pattern_name) is getattr(domain_patterns_trust_inclusion, pattern_name)
    assert "alignment_traceability_domain_patterns_trust.py" in design_source


def test_alignment_traceability_data_domain_patterns_use_family_catalogs() -> None:
    data_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_domain_patterns_data.py").read_text(encoding="utf-8")
    family_sources = {
        filename: (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _first_constant_name, _last_constant_name in DATA_DOMAIN_PATTERN_FAMILY_CATALOGS
    }
    design_source = design_boundary_source()

    for filename, first_constant_name, last_constant_name in DATA_DOMAIN_PATTERN_FAMILY_CATALOGS:
        module_name = filename.removesuffix(".py")
        assert f"from loopora.{module_name} import" in data_source
        assert first_constant_name in data_source
        assert last_constant_name in data_source
        assert first_constant_name in family_sources[filename]
        assert last_constant_name in family_sources[filename]
        assert filename in design_source
    assert 'r"(?:' not in data_source
    assert domain_patterns_data.FILE_UPLOAD_STORAGE_SAFETY_PATTERN is domain_patterns_data_ingest.FILE_UPLOAD_STORAGE_SAFETY_PATTERN
    assert domain_patterns_data.DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN is domain_patterns_data_ingest.DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN
    assert domain_patterns_data.CONCURRENCY_CONFLICT_RESOLUTION_PATTERN is domain_patterns_data_ingest.CONCURRENCY_CONFLICT_RESOLUTION_PATTERN
    assert domain_patterns_data.INVENTORY_RESERVATION_CONSISTENCY_PATTERN is domain_patterns_data_commerce.INVENTORY_RESERVATION_CONSISTENCY_PATTERN
    assert domain_patterns_data.USAGE_QUOTA_METERING_PATTERN is domain_patterns_data_commerce.USAGE_QUOTA_METERING_PATTERN
    assert domain_patterns_data.SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN is domain_patterns_data_commerce.SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN
    assert domain_patterns_data.TAX_CALCULATION_COMPLIANCE_PATTERN is domain_patterns_data_commerce.TAX_CALCULATION_COMPLIANCE_PATTERN
    assert domain_patterns_data.BACKUP_RESTORE_RECOVERY_PATTERN is domain_patterns_data_resilience.BACKUP_RESTORE_RECOVERY_PATTERN
    assert domain_patterns_data.CDC_REPLICATION_CONSISTENCY_PATTERN is domain_patterns_data_resilience.CDC_REPLICATION_CONSISTENCY_PATTERN
    assert domain_patterns_data.AUDIT_LOG_INTEGRITY_RETENTION_PATTERN is domain_patterns_data_resilience.AUDIT_LOG_INTEGRITY_RETENTION_PATTERN
    assert domain_patterns_data.CACHE_INVALIDATION_CONSISTENCY_PATTERN is domain_patterns_data_read_models.CACHE_INVALIDATION_CONSISTENCY_PATTERN
    assert domain_patterns_data.SEARCH_INDEX_CONSISTENCY_PATTERN is domain_patterns_data_read_models.SEARCH_INDEX_CONSISTENCY_PATTERN
    assert domain_patterns_data.DATA_LIFECYCLE_DELETION_RETENTION_PATTERN is domain_patterns_data_lifecycle.DATA_LIFECYCLE_DELETION_RETENTION_PATTERN
    assert domain_patterns_data.CONSENT_PREFERENCE_GOVERNANCE_PATTERN is domain_patterns_data_lifecycle.CONSENT_PREFERENCE_GOVERNANCE_PATTERN
    assert "alignment_traceability_domain_patterns_data.py" in design_source


def test_alignment_traceability_candidate_catalog_uses_family_catalogs() -> None:
    candidate_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_candidate_catalog.py").read_text(encoding="utf-8")
    family_sources = {
        filename: (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _constant_name, _sample_label in CANDIDATE_FAMILY_CATALOGS
    }
    design_source = design_boundary_source()

    for filename, constant_name, sample_label in CANDIDATE_FAMILY_CATALOGS:
        module_name = filename.removesuffix(".py")
        assert f"from loopora.{module_name} import" in candidate_catalog_source
        assert constant_name in candidate_catalog_source
        assert constant_name in family_sources[filename]
        assert sample_label in family_sources[filename]
        assert filename in design_source
    assert '"proof/evidence",' not in candidate_catalog_source
    assert "AUTHORIZATION_POLICY_CONSISTENCY_PATTERN" not in candidate_catalog_source
    assert "alignment_traceability_candidate_catalog.py" in design_source
    assert TRADEOFF_MARKER_PATTERNS is candidate_tradeoff_catalog.TRADEOFF_MARKER_PATTERNS
    assert TRADEOFF_CATEGORY_PATTERNS is candidate_tradeoff_catalog.TRADEOFF_CATEGORY_PATTERNS
    assert EXECUTION_STRATEGY_MARKER_PATTERNS is candidate_execution_catalog.EXECUTION_STRATEGY_MARKER_PATTERNS
    assert EXECUTION_STRATEGY_CATEGORY_PATTERNS is candidate_execution_catalog.EXECUTION_STRATEGY_CATEGORY_PATTERNS
    assert RESIDUAL_RISK_POLICY_MARKER_PATTERNS is candidate_residual_risk_catalog.RESIDUAL_RISK_POLICY_MARKER_PATTERNS
    assert RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS is candidate_residual_risk_catalog.RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS
    assert RESIDUAL_RISK_BASE_CATEGORY is candidate_residual_risk_catalog.RESIDUAL_RISK_BASE_CATEGORY
    assert NO_ACCEPTED_RESIDUAL_RISK_TASK_PATTERN is candidate_residual_risk_catalog.NO_ACCEPTED_RESIDUAL_RISK_TASK_PATTERN
    assert NO_ACCEPTED_RESIDUAL_RISK_BUNDLE_PATTERN is candidate_residual_risk_catalog.NO_ACCEPTED_RESIDUAL_RISK_BUNDLE_PATTERN
    assert SUCCESS_SURFACE_MARKER_PATTERNS is candidate_success_surface_catalog.SUCCESS_SURFACE_MARKER_PATTERNS
    assert SUCCESS_SURFACE_CATEGORY_PATTERNS is candidate_success_surface_catalog.SUCCESS_SURFACE_CATEGORY_PATTERNS
    assert SUCCESS_SURFACE_BASE_CATEGORY is candidate_success_surface_catalog.SUCCESS_SURFACE_BASE_CATEGORY


def test_alignment_traceability_success_surface_catalog_uses_family_catalogs() -> None:
    success_surface_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_candidate_success_surface_catalog.py").read_text(encoding="utf-8")
    family_sources = {
        filename: (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _constant_name, _sample_label in SUCCESS_SURFACE_FAMILY_CATALOGS
    }
    design_source = design_boundary_source()

    for filename, constant_name, sample_label in SUCCESS_SURFACE_FAMILY_CATALOGS:
        module_name = filename.removesuffix(".py")
        assert f"from loopora.{module_name} import" in success_surface_source
        assert constant_name in success_surface_source
        assert constant_name in family_sources[filename]
        assert sample_label in family_sources[filename]
        assert filename in design_source
    assert '"actor/user-facing-outcome",' not in success_surface_source
    assert "AUTHORIZATION_POLICY_CONSISTENCY_PATTERN" not in success_surface_source
    expected_patterns = (
        *candidate_success_surface_core_catalog.SUCCESS_SURFACE_CORE_CATEGORY_PATTERNS,
        *candidate_success_surface_delivery_catalog.SUCCESS_SURFACE_DELIVERY_CATEGORY_PATTERNS,
        *candidate_success_surface_data_access_catalog.SUCCESS_SURFACE_DATA_ACCESS_CATEGORY_PATTERNS,
        *candidate_success_surface_operations_catalog.SUCCESS_SURFACE_OPERATIONS_CATEGORY_PATTERNS,
        *candidate_success_surface_trust_locale_catalog.SUCCESS_SURFACE_TRUST_LOCALE_CATEGORY_PATTERNS,
    )
    assert expected_patterns == SUCCESS_SURFACE_CATEGORY_PATTERNS
    assert len(SUCCESS_SURFACE_CATEGORY_PATTERNS) == 54
    assert SUCCESS_SURFACE_MARKER_PATTERNS is candidate_success_surface_core_catalog.SUCCESS_SURFACE_MARKER_PATTERNS
    assert SUCCESS_SURFACE_BASE_CATEGORY is candidate_success_surface_core_catalog.SUCCESS_SURFACE_BASE_CATEGORY
    assert "alignment_traceability_candidate_success_surface_catalog.py" in design_source


def test_alignment_traceability_fake_done_catalog_uses_family_catalogs() -> None:
    fake_done_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_fake_done_catalog.py").read_text(encoding="utf-8")
    family_sources = {
        filename: (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _constant_name, _sample_label in FAKE_DONE_FAMILY_CATALOGS
    }
    design_source = design_boundary_source()

    for filename, constant_name, sample_label in FAKE_DONE_FAMILY_CATALOGS:
        module_name = filename.removesuffix(".py")
        assert f"from loopora.{module_name} import" in fake_done_catalog_source
        assert constant_name in fake_done_catalog_source
        assert constant_name in family_sources[filename]
        assert sample_label in family_sources[filename]
        assert filename in design_source
    assert '"permission/audit",' not in fake_done_catalog_source
    assert "risk_marker_near_domain_pattern(" not in fake_done_catalog_source
    assert "FAKE_DONE_CATEGORY_PATTERNS = (" in fake_done_catalog_source
    expected_patterns = (
        *FAKE_DONE_CORE_CATEGORY_PATTERNS,
        *FAKE_DONE_DELIVERY_CATEGORY_PATTERNS,
        *FAKE_DONE_DATA_ACCESS_CATEGORY_PATTERNS,
        *FAKE_DONE_OPERATIONS_CATEGORY_PATTERNS,
        *FAKE_DONE_SURFACE_CATEGORY_PATTERNS,
    )
    assert expected_patterns == FAKE_DONE_CATEGORY_PATTERNS
    assert len(FAKE_DONE_CATEGORY_PATTERNS) == 56
    assert "alignment_traceability_fake_done_catalog.py" in design_source


def test_alignment_traceability_cjk_domain_terms_use_family_catalogs() -> None:
    cjk_domain_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_cjk_domain_terms.py").read_text(encoding="utf-8")
    family_sources = {
        filename: (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _constant_name, _sample_term in CJK_DOMAIN_FAMILY_CATALOGS
    }
    design_source = design_boundary_source()

    for filename, constant_name, sample_term in CJK_DOMAIN_FAMILY_CATALOGS:
        module_name = filename.removesuffix(".py")
        assert f"from loopora.{module_name} import" in cjk_domain_source
        assert constant_name in cjk_domain_source
        assert constant_name in family_sources[filename]
        assert sample_term in family_sources[filename]
        assert filename in design_source
    assert '"审批",' not in cjk_domain_source
    assert '"支付",' not in cjk_domain_source
    assert "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS = (" in cjk_domain_source
    expected_terms = (
        *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_CORE_TRUST_TERMS,
        *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_COMMERCE_TERMS,
        *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_DATA_PLATFORM_TERMS,
        *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_WORKFLOW_TERMS,
        *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_GOVERNANCE_TERMS,
        *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_OPERATIONS_TERMS,
    )
    assert expected_terms == ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS
    assert len(ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS) == 880
    assert "alignment_traceability_cjk_domain_terms.py" in design_source


def test_alignment_traceability_terms_use_dedicated_catalog_boundary() -> None:
    terms_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_terms.py").read_text(encoding="utf-8")
    catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_term_catalog.py").read_text(encoding="utf-8")
    generic_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_generic_term_catalog.py").read_text(encoding="utf-8")
    cjk_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_cjk_term_catalog.py").read_text(encoding="utf-8")
    cjk_domain_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_cjk_domain_terms.py").read_text(encoding="utf-8")
    cjk_generic_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_cjk_generic_terms.py").read_text(encoding="utf-8")
    cjk_stop_chars_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_cjk_stop_chars.py").read_text(encoding="utf-8")
    agent_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_agent_term_catalog.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.alignment_traceability_term_catalog import" in terms_source
    assert "from loopora.alignment_traceability_generic_term_catalog import" in catalog_source
    assert "from loopora.alignment_traceability_cjk_term_catalog import" in catalog_source
    assert "from loopora.alignment_traceability_agent_term_catalog import" in catalog_source
    assert "from loopora.alignment_traceability_cjk_domain_terms import" in cjk_catalog_source
    assert "from loopora.alignment_traceability_cjk_generic_terms import" in cjk_catalog_source
    assert "from loopora.alignment_traceability_cjk_stop_chars import" in cjk_catalog_source
    for marker, source in (
        ("ALIGNMENT_TRACEABILITY_GENERIC_TERMS", generic_catalog_source),
        ("ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS", generic_catalog_source),
        ("ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS", cjk_domain_source),
        ("ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS", cjk_stop_chars_source),
        ("ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS", cjk_generic_source),
        ("ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS", agent_catalog_source),
    ):
        assert marker in source
        assert marker in catalog_source
        assert f"{marker} =" not in terms_source
    for marker in (
        "ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS",
        "ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS",
        "ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS",
    ):
        assert marker in cjk_catalog_source
        assert f"{marker} =" not in cjk_catalog_source
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
    assert "alignment_traceability_cjk_domain_terms.py" in design_source
    assert "alignment_traceability_cjk_generic_terms.py" in design_source
    assert "alignment_traceability_cjk_stop_chars.py" in design_source
    assert "alignment_traceability_agent_term_catalog.py" in design_source


def test_alignment_agent_candidate_terms_keep_billing_ledger_anchors_without_generic_action_words() -> None:
    terms = agent_candidate_traceability_terms("Prepare a Stripe webhook implementation for ledger reconciliation with replay and signature proof.")

    assert "prepare" not in terms
    assert "implementation" not in terms
    assert "stripe" in terms
    assert "webhook" in terms
    assert "ledger" in terms


def test_alignment_agent_candidate_terms_ignore_loopora_internal_evidence_ledger() -> None:
    terms = agent_candidate_traceability_terms("Reject invented evidence refs before non-GateKeeper output enters the ledger.")

    assert "ledger" not in terms


def test_alignment_agent_candidate_task_anchor_terms_require_business_domain_anchor() -> None:
    assert agent_candidate_task_anchor_terms("请帮我生成一个中文任务的循环方案。") == []
    assert agent_candidate_task_anchor_terms("Build a starter experience with weak execution_strategy evidence.") == []

    stripe_terms = agent_candidate_task_anchor_terms("Build Stripe webhook ledger reconciliation with replay and signature proof.")
    rag_terms = agent_candidate_task_anchor_terms("Prepare a RAG support chatbot that proves retrieval ACL, citation grounding, and fallback behavior.")

    assert {"stripe", "webhook", "ledger"}.issubset(stripe_terms)
    assert {"retrieval", "citation", "grounding"}.issubset(rag_terms)


def test_alignment_agent_candidate_traceability_category_rules_have_dedicated_boundary() -> None:
    rules_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_rules.py").read_text(encoding="utf-8")
    agent_candidate_rules_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_agent_candidate_rules.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert alignment_agent_candidate_tradeoff_issues.__module__ == ("loopora.alignment_traceability_agent_candidate_rules")
    assert "from loopora.alignment_traceability_agent_candidate_rules import" in rules_source
    for marker in (
        "def alignment_agent_candidate_tradeoff_issues",
        "def alignment_agent_candidate_execution_strategy_issues",
        "def alignment_agent_candidate_residual_risk_policy_issues",
    ):
        assert marker in agent_candidate_rules_source
        assert marker not in rules_source
    assert "alignment_traceability_agent_candidate_rules.py" in design_source
