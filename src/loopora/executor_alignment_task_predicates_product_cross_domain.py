from __future__ import annotations


def is_dispute_chargeback_lifecycle_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_commercial import is_dispute_chargeback_lifecycle_task as predicate

    return predicate(task)


def is_dsar_data_export_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_data import is_dsar_data_export_task as predicate

    return predicate(task)


def is_subscription_entitlement_billing_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_commercial import is_subscription_entitlement_billing_task as predicate

    return predicate(task)


def is_support_impersonation_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_trust import is_support_impersonation_task as predicate

    return predicate(task)


def is_usage_quota_metering_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_commercial import is_usage_quota_metering_task as predicate

    return predicate(task)
