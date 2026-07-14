from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_metric_reporting_reconciliation_task,
    _is_payment_webhook_ledger_task,
    _is_subscription_entitlement_billing_task,
    _is_tax_calculation_compliance_task,
    _is_usage_quota_metering_task,
)
from loopora.executor_alignment_bundle_task_spec_notes import (
    append_task_spec_workflow_note_for_task as _append_note,
    task_spec_workflow_note_context as _note_context,
)
from loopora.executor_alignment_bundle_task_spec_scaffold_templates import apply_task_spec_scaffold_template_from_asset


def _append_payment_webhook_ledger_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_payment_webhook_ledger_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="payment_webhook_ledger",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_metric_reporting_reconciliation_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_metric_reporting_reconciliation_task,
        "metric_reporting_reconciliation",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_usage_quota_metering_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_usage_quota_metering_task,
        "usage_quota_metering",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_subscription_entitlement_billing_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_subscription_entitlement_billing_task,
        "subscription_entitlement_billing",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_tax_calculation_compliance_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_tax_calculation_compliance_task,
        "tax_calculation_compliance",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )
