from __future__ import annotations

from loopora import executor_alignment_agreement_task_responses_product as product_task_responses
from loopora.executor_alignment_agreement_predicates import (
    _agreement_is_analytics_experiment_instrumentation_task,
    _agreement_is_inventory_reservation_consistency_task,
    _agreement_is_notification_subscription_deliverability_task,
    _agreement_is_rag_long_chain_task,
    _agreement_is_schedule_phase_task,
    _agreement_is_search_index_consistency_task,
    _agreement_is_search_quality_task,
    _agreement_is_support_ticket_sla_task,
)
from loopora.executor_alignment_agreement_task_dispatch_types import AgreementTaskFactoryRoute

PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES: dict[str, AgreementTaskFactoryRoute] = {
    "analytics_experiment_instrumentation": (
        _agreement_is_analytics_experiment_instrumentation_task,
        (
            product_task_responses.alignment_chinese_analytics_experiment_instrumentation_agreement_response,
            product_task_responses.alignment_spanish_analytics_experiment_instrumentation_agreement_response,
            product_task_responses.alignment_english_analytics_experiment_instrumentation_agreement_response,
        ),
    ),
    "schedule_timezone_recurrence": (
        _agreement_is_schedule_phase_task,
        (
            product_task_responses.alignment_chinese_schedule_timezone_recurrence_agreement_response,
            product_task_responses.alignment_spanish_schedule_timezone_recurrence_agreement_response,
            product_task_responses.alignment_english_schedule_timezone_recurrence_agreement_response,
        ),
    ),
    "support_ticket_sla": (
        _agreement_is_support_ticket_sla_task,
        (
            product_task_responses.alignment_chinese_support_ticket_sla_agreement_response,
            product_task_responses.alignment_spanish_support_ticket_sla_agreement_response,
            product_task_responses.alignment_english_support_ticket_sla_agreement_response,
        ),
    ),
    "notification_subscription_deliverability": (
        _agreement_is_notification_subscription_deliverability_task,
        (
            product_task_responses.alignment_chinese_notification_subscription_deliverability_agreement_response,
            product_task_responses.alignment_spanish_notification_subscription_deliverability_agreement_response,
            product_task_responses.alignment_english_notification_subscription_deliverability_agreement_response,
        ),
    ),
    "inventory_reservation_consistency": (
        _agreement_is_inventory_reservation_consistency_task,
        (
            product_task_responses.alignment_chinese_inventory_reservation_consistency_agreement_response,
            product_task_responses.alignment_spanish_inventory_reservation_consistency_agreement_response,
            product_task_responses.alignment_english_inventory_reservation_consistency_agreement_response,
        ),
    ),
    "rag_long_chain": (
        _agreement_is_rag_long_chain_task,
        (
            product_task_responses.alignment_chinese_rag_long_chain_agreement_response,
            product_task_responses.alignment_spanish_rag_long_chain_agreement_response,
            product_task_responses.alignment_english_rag_long_chain_agreement_response,
        ),
    ),
    "search_index_consistency": (
        _agreement_is_search_index_consistency_task,
        (
            product_task_responses.alignment_chinese_search_index_consistency_agreement_response,
            product_task_responses.alignment_spanish_search_index_consistency_agreement_response,
            product_task_responses.alignment_english_search_index_consistency_agreement_response,
        ),
    ),
    "search_quality": (
        _agreement_is_search_quality_task,
        (
            product_task_responses.alignment_chinese_search_quality_agreement_response,
            product_task_responses.alignment_spanish_search_quality_agreement_response,
            product_task_responses.alignment_english_search_quality_agreement_response,
        ),
    ),
}
