from __future__ import annotations

"""Agent-candidate success-surface delivery and release-quality categories."""

from loopora.alignment_traceability_domain_patterns import (
    BACKWARD_COMPATIBILITY_PATTERN,
    EVALUATION_SET_PATTERN,
    EXTERNAL_PROVIDER_CONTRACT_PATTERN,
    FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
    HUMAN_REVIEW_QUALITY_PATTERN,
    INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
    KYC_AML_SANCTIONS_SCREENING_PATTERN,
    MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
    RAG_GROUNDING_TOOL_SAFETY_PATTERN,
    REGRESSION_MONITORING_GUARD_PATTERN,
    RESILIENCE_RETRY_TIMEOUT_PATTERN,
)

SUCCESS_SURFACE_DELIVERY_CATEGORY_PATTERNS = (
    (
        "migration/rollback-integrity",
        MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
    ),
    (
        "compatibility/backward-compat",
        BACKWARD_COMPATIBILITY_PATTERN,
    ),
    (
        "evaluation/eval-set",
        EVALUATION_SET_PATTERN,
    ),
    (
        "quality/human-review",
        HUMAN_REVIEW_QUALITY_PATTERN,
    ),
    (
        "ai/rag-grounding-tool-safety",
        RAG_GROUNDING_TOOL_SAFETY_PATTERN,
    ),
    (
        "incident/root-cause-repro",
        INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
    ),
    (
        "regression/monitoring-guard",
        REGRESSION_MONITORING_GUARD_PATTERN,
    ),
    (
        "release/feature-flag-rollout",
        FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
    ),
    (
        "external/provider-contract",
        EXTERNAL_PROVIDER_CONTRACT_PATTERN,
    ),
    (
        "compliance/kyc-aml-sanctions-screening",
        KYC_AML_SANCTIONS_SCREENING_PATTERN,
    ),
    (
        "resilience/retry-timeout",
        RESILIENCE_RETRY_TIMEOUT_PATTERN,
    ),
)

__all__ = ("SUCCESS_SURFACE_DELIVERY_CATEGORY_PATTERNS",)
