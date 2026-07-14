from __future__ import annotations

from loopora import executor_alignment_agreement_task_responses_commercial as commercial_task_responses
from loopora.executor_alignment_agreement_predicates import (
    _agreement_is_dispute_chargeback_lifecycle_task,
    _agreement_is_metric_reporting_reconciliation_task,
    _agreement_is_payment_webhook_ledger_task,
    _agreement_is_payout_settlement_reconciliation_task,
    _agreement_is_subscription_entitlement_billing_task,
    _agreement_is_tax_calculation_compliance_task,
    _agreement_is_usage_quota_metering_task,
)
from loopora.executor_alignment_agreement_task_dispatch_types import AgreementTaskFactoryRoute

COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES: dict[str, AgreementTaskFactoryRoute] = {
    "metric_reporting_reconciliation": (
        _agreement_is_metric_reporting_reconciliation_task,
        (
            commercial_task_responses.alignment_chinese_metric_reporting_reconciliation_agreement_response,
            commercial_task_responses.alignment_spanish_metric_reporting_reconciliation_agreement_response,
            commercial_task_responses.alignment_english_metric_reporting_reconciliation_agreement_response,
        ),
    ),
    "dispute_chargeback_lifecycle": (
        _agreement_is_dispute_chargeback_lifecycle_task,
        (
            commercial_task_responses.alignment_chinese_dispute_chargeback_lifecycle_agreement_response,
            commercial_task_responses.alignment_spanish_dispute_chargeback_lifecycle_agreement_response,
            commercial_task_responses.alignment_english_dispute_chargeback_lifecycle_agreement_response,
        ),
    ),
    "payout_settlement_reconciliation": (
        _agreement_is_payout_settlement_reconciliation_task,
        (
            commercial_task_responses.alignment_chinese_payout_settlement_reconciliation_agreement_response,
            commercial_task_responses.alignment_spanish_payout_settlement_reconciliation_agreement_response,
            commercial_task_responses.alignment_english_payout_settlement_reconciliation_agreement_response,
        ),
    ),
    "subscription_entitlement_billing": (
        _agreement_is_subscription_entitlement_billing_task,
        (
            commercial_task_responses.alignment_chinese_subscription_entitlement_billing_agreement_response,
            commercial_task_responses.alignment_spanish_subscription_entitlement_billing_agreement_response,
            commercial_task_responses.alignment_english_subscription_entitlement_billing_agreement_response,
        ),
    ),
    "usage_quota_metering": (
        _agreement_is_usage_quota_metering_task,
        (
            commercial_task_responses.alignment_chinese_usage_quota_metering_agreement_response,
            commercial_task_responses.alignment_spanish_usage_quota_metering_agreement_response,
            commercial_task_responses.alignment_english_usage_quota_metering_agreement_response,
        ),
    ),
    "tax_calculation_compliance": (
        _agreement_is_tax_calculation_compliance_task,
        (
            commercial_task_responses.alignment_chinese_tax_calculation_compliance_agreement_response,
            commercial_task_responses.alignment_spanish_tax_calculation_compliance_agreement_response,
            commercial_task_responses.alignment_english_tax_calculation_compliance_agreement_response,
        ),
    ),
    "payment_webhook_ledger": (
        _agreement_is_payment_webhook_ledger_task,
        (
            commercial_task_responses.alignment_chinese_payment_webhook_ledger_agreement_response,
            commercial_task_responses.alignment_spanish_payment_webhook_ledger_agreement_response,
            commercial_task_responses.alignment_english_payment_webhook_ledger_agreement_response,
        ),
    ),
}
