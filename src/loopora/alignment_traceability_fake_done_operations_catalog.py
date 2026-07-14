from __future__ import annotations

"""Fake-done catalog entries for operational, commerce, identity, and notification proof gaps."""

from loopora.alignment_traceability_domain_patterns import (
    ANALYTICS_EVENT_INTEGRITY_PATTERN,
    ASYNC_JOB_LIFECYCLE_PATTERN,
    AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
    BILLING_LEDGER_RECONCILIATION_PATTERN,
    DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
    EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
    IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
    IDENTITY_SSO_ASSERTION_PATTERN,
    KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
    METRIC_REPORTING_RECONCILIATION_PATTERN,
    NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
    PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
    QUEUE_FAILURE_RECOVERY_PATTERN,
    SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
    WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
)

from loopora.alignment_traceability_risk_markers import (
    FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
    FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
    FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN,
    risk_marker_near_domain_pattern,
)

FAKE_DONE_OPERATIONS_CATEGORY_PATTERNS = (
    (
        "analytics/event-integrity",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            ANALYTICS_EVENT_INTEGRITY_PATTERN,
            window=160,
            extra_marker_pattern=r"console\.log",
        ),
        ANALYTICS_EVENT_INTEGRITY_PATTERN,
    ),
    (
        "experiment/assignment-consistency",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
            window=160,
        ),
        EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
    ),
    (
        "async/job-lifecycle",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            ASYNC_JOB_LIFECYCLE_PATTERN,
            window=160,
        ),
        ASYNC_JOB_LIFECYCLE_PATTERN,
    ),
    (
        "queue/failure-recovery",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            QUEUE_FAILURE_RECOVERY_PATTERN,
            window=160,
        ),
        QUEUE_FAILURE_RECOVERY_PATTERN,
    ),
    (
        "schedule/timezone-recurrence",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
            window=180,
            extra_marker_pattern=r"cron|local[- ]?only|本地触发一次",
        ),
        SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
    ),
    (
        "webhook/signature-replay-ordering",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
            window=180,
        ),
        WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
    ),
    (
        "billing/ledger-reconciliation",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            BILLING_LEDGER_RECONCILIATION_PATTERN,
            window=180,
        ),
        BILLING_LEDGER_RECONCILIATION_PATTERN,
    ),
    (
        "payment/dispute-chargeback-lifecycle",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
            window=220,
            extra_marker_pattern=(
                r"stripe[- ]?dashboard|provider[- ]?dispute[- ]?id|ui[- ]?status|happy[- ]?path[- ]?close|"
                r"只存.*争议|只保存.*争议|只改.*状态|dashboard|看.*won|看.*lost"
            ),
        ),
        DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
    ),
    (
        "payout/settlement-reconciliation",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
            window=420,
            extra_marker_pattern=(
                r"stripe[- ]?dashboard[- ]?(?:paid|shows?)|provider[- ]?dashboard[- ]?(?:paid|shows?)|"
                r"test[- ]?payout|single[- ]?payout|ui[- ]?(?:balance|shows?|decreas(?:e|ed))|"
                r"balance[- ]?decreas(?:e|ed)|Stripe\\s*dashboard|供应商看板|一笔测试打款|"
                r"单笔打款|测试打款|UI\\s*显示余额|余额减少"
            ),
        ),
        PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
    ),
    (
        "reporting/metric-reconciliation",
        risk_marker_near_domain_pattern(
            FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN,
            METRIC_REPORTING_RECONCILIATION_PATTERN,
            window=420,
            extra_marker_pattern=(
                r"chart[- ]?only|chart[- ]?render(?:s|ed)?|csv|export|dashboard[- ]?only|"
                r"number(?:s)?[- ]?display|图表|数字|能导出|导出"
            ),
        ),
        METRIC_REPORTING_RECONCILIATION_PATTERN,
    ),
    (
        "identity/sso-assertion",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            IDENTITY_SSO_ASSERTION_PATTERN,
            window=180,
        ),
        IDENTITY_SSO_ASSERTION_PATTERN,
    ),
    (
        "identity/provisioning-role-mapping",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN,
            IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
            window=180,
        ),
        IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
    ),
    (
        "auth/session-token-lifecycle",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
            window=220,
            extra_marker_pattern=r"email[- ]?sent|link[- ]?sent|reset[- ]?email|邮件发出|重置邮件|链接发出",
        ),
        AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
    ),
    (
        "security/key-rotation-lifecycle",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
            window=220,
            extra_marker_pattern=r"ui|env(?:ironment)?[- ]?var(?:iable)?|new[- ]?key|新密钥|环境变量|页面显示",
        ),
        KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
    ),
    (
        "notification/subscription-deliverability",
        NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
        NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
    ),
)

__all__ = ("FAKE_DONE_OPERATIONS_CATEGORY_PATTERNS",)
