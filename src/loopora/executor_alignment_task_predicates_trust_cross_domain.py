from __future__ import annotations


def is_payout_settlement_reconciliation_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_commercial import is_payout_settlement_reconciliation_task as predicate

    return predicate(task)
