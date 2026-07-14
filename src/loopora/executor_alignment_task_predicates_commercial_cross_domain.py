from __future__ import annotations


def is_analytics_experiment_instrumentation_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_product import is_analytics_experiment_instrumentation_task as predicate

    return predicate(task)


def is_cdc_replication_consistency_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_data import is_cdc_replication_consistency_task as predicate

    return predicate(task)


def is_identity_sso_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_trust import is_identity_sso_task as predicate

    return predicate(task)


def is_inventory_reservation_consistency_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_product import is_inventory_reservation_consistency_task as predicate

    return predicate(task)


def is_kyc_aml_screening_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_trust import is_kyc_aml_screening_task as predicate

    return predicate(task)


def is_notification_subscription_deliverability_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_product import is_notification_subscription_deliverability_task as predicate

    return predicate(task)
