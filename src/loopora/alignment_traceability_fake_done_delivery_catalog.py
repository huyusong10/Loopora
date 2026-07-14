from __future__ import annotations

"""Fake-done catalog entries for delivery, quality, release, and provider proof gaps."""

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

from loopora.alignment_traceability_risk_markers import (
    FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
    FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
    FAKE_DONE_PROOF_GAP_MARKER_PATTERN,
    FAKE_DONE_PROOF_GAP_OR_MISSING_MARKER_PATTERN,
    FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN,
    risk_marker_near_domain_pattern,
)

FAKE_DONE_DELIVERY_CATEGORY_PATTERNS = (
    (
        "migration/rollback-integrity",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_MARKER_PATTERN,
            MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
            window=120,
        ),
        MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
    ),
    (
        "compatibility/backward-compat",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_MARKER_PATTERN,
            BACKWARD_COMPATIBILITY_PATTERN,
            window=120,
        ),
        BACKWARD_COMPATIBILITY_PATTERN,
    ),
    (
        "evaluation/eval-set",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN,
            EVALUATION_SET_PATTERN,
            window=120,
        ),
        EVALUATION_SET_PATTERN,
    ),
    (
        "quality/human-review",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN,
            HUMAN_REVIEW_QUALITY_PATTERN,
            window=120,
        ),
        HUMAN_REVIEW_QUALITY_PATTERN,
    ),
    (
        "ai/rag-grounding-tool-safety",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN,
            RAG_GROUNDING_TOOL_SAFETY_PATTERN,
            window=220,
            extra_marker_pattern=(
                r"demo[- ]?question|plausible[- ]?answer|embedding[- ]?search|ui[- ]?citation(?:s)?|"
                r"只让|看起来合理|界面引用|向量搜索|嵌入搜索"
            ),
        ),
        RAG_GROUNDING_TOOL_SAFETY_PATTERN,
    ),
    (
        "incident/root-cause-repro",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_OR_MISSING_MARKER_PATTERN,
            INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
            window=120,
        ),
        INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
    ),
    (
        "regression/monitoring-guard",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_OR_MISSING_MARKER_PATTERN,
            REGRESSION_MONITORING_GUARD_PATTERN,
            window=120,
        ),
        REGRESSION_MONITORING_GUARD_PATTERN,
    ),
    (
        "release/feature-flag-rollout",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
            window=220,
            extra_marker_pattern=r"local[- ]?flag|toggle|flag[- ]?toggle|本地开关|开关能打开",
        ),
        FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
    ),
    (
        "external/provider-contract",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            EXTERNAL_PROVIDER_CONTRACT_PATTERN,
            window=140,
        ),
        EXTERNAL_PROVIDER_CONTRACT_PATTERN,
    ),
    (
        "compliance/kyc-aml-sanctions-screening",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN,
            KYC_AML_SANCTIONS_SCREENING_PATTERN,
            window=220,
            extra_marker_pattern=(
                r"sandbox[- ]?approved|provider[- ]?status|ui[- ]?verified|happy[- ]?path[- ]?webhook|"
                r"沙箱通过|供应商状态|界面显示已认证|只跑.*webhook"
            ),
        ),
        KYC_AML_SANCTIONS_SCREENING_PATTERN,
    ),
    (
        "resilience/retry-timeout",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            RESILIENCE_RETRY_TIMEOUT_PATTERN,
            window=140,
        ),
        RESILIENCE_RETRY_TIMEOUT_PATTERN,
    ),
)

__all__ = ("FAKE_DONE_DELIVERY_CATEGORY_PATTERNS",)
