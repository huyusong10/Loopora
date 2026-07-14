from __future__ import annotations


def is_analytics_experiment_instrumentation_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_product import is_analytics_experiment_instrumentation_task as predicate

    return predicate(task)


def is_authorization_policy_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_trust import is_authorization_policy_task as predicate

    return predicate(task)


def is_data_residency_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_trust import is_data_residency_task as predicate

    return predicate(task)


def is_kyc_aml_screening_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_trust import is_kyc_aml_screening_task as predicate

    return predicate(task)


def is_metric_reporting_reconciliation_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_commercial import is_metric_reporting_reconciliation_task as predicate

    return predicate(task)


def is_payment_webhook_ledger_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_commercial import is_payment_webhook_ledger_task as predicate

    return predicate(task)


def is_support_impersonation_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_trust import is_support_impersonation_task as predicate

    return predicate(task)
