from __future__ import annotations

from loopora.executor_alignment_bundle_task_visible_scaffold_assets import apply_task_visible_scaffold_template_from_asset
from loopora.executor_alignment_task_projection import AlignmentTaskDomainProjection


def _replace_metric_reporting_reconciliation_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    projection: AlignmentTaskDomainProjection,
) -> None:
    apply_task_visible_scaffold_template_from_asset(
        bundle,
        scaffold_key="metric_reporting_reconciliation",
        prefers_chinese=prefers_chinese,
        task=task,
        projection=projection,
    )


def _replace_dispute_chargeback_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    projection: AlignmentTaskDomainProjection,
) -> None:
    apply_task_visible_scaffold_template_from_asset(
        bundle,
        scaffold_key="dispute_chargeback_lifecycle",
        prefers_chinese=prefers_chinese,
        task=task,
        projection=projection,
    )


def _replace_payout_settlement_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    projection: AlignmentTaskDomainProjection,
) -> None:
    apply_task_visible_scaffold_template_from_asset(
        bundle,
        scaffold_key="payout_settlement_reconciliation",
        prefers_chinese=prefers_chinese,
        task=task,
        projection=projection,
    )
