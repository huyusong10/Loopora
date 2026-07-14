from __future__ import annotations

"""Agent-candidate success-surface operational and commerce categories."""

from loopora.alignment_traceability_domain_patterns import (
    ANALYTICS_EVENT_INTEGRITY_PATTERN,
    ASYNC_JOB_LIFECYCLE_PATTERN,
    BILLING_LEDGER_RECONCILIATION_PATTERN,
    DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
    EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
    METRIC_REPORTING_RECONCILIATION_PATTERN,
    PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
    QUEUE_FAILURE_RECOVERY_PATTERN,
    SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
    WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
)

SUCCESS_SURFACE_OPERATIONS_CATEGORY_PATTERNS = (
    (
        "analytics/event-integrity",
        ANALYTICS_EVENT_INTEGRITY_PATTERN,
    ),
    (
        "experiment/assignment-consistency",
        EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
    ),
    (
        "async/job-lifecycle",
        ASYNC_JOB_LIFECYCLE_PATTERN,
    ),
    (
        "queue/failure-recovery",
        QUEUE_FAILURE_RECOVERY_PATTERN,
    ),
    (
        "schedule/timezone-recurrence",
        SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
    ),
    (
        "webhook/signature-replay-ordering",
        WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
    ),
    (
        "billing/ledger-reconciliation",
        BILLING_LEDGER_RECONCILIATION_PATTERN,
    ),
    (
        "payment/dispute-chargeback-lifecycle",
        DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
    ),
    (
        "payout/settlement-reconciliation",
        PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
    ),
    (
        "reporting/metric-reconciliation",
        METRIC_REPORTING_RECONCILIATION_PATTERN,
    ),
)

__all__ = ("SUCCESS_SURFACE_OPERATIONS_CATEGORY_PATTERNS",)
