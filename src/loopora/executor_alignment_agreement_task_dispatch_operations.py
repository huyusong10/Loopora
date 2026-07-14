from __future__ import annotations

from loopora import executor_alignment_agreement_task_responses_operations as operations_task_responses
from loopora.executor_alignment_agreement_predicates import (
    _agreement_is_cache_invalidation_consistency_task,
    _agreement_is_concurrency_conflict_resolution_task,
    _agreement_is_feature_flag_rollout_task,
    _agreement_is_incident_root_cause_task,
)
from loopora.executor_alignment_agreement_task_dispatch_types import AgreementTaskFactoryRoute

OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES: dict[str, AgreementTaskFactoryRoute] = {
    "feature_flag_rollout": (
        _agreement_is_feature_flag_rollout_task,
        (
            operations_task_responses.alignment_chinese_feature_flag_rollout_agreement_response,
            operations_task_responses.alignment_spanish_feature_flag_rollout_agreement_response,
            operations_task_responses.alignment_english_feature_flag_rollout_agreement_response,
        ),
    ),
    "cache_invalidation_consistency": (
        _agreement_is_cache_invalidation_consistency_task,
        (
            operations_task_responses.alignment_chinese_cache_invalidation_consistency_agreement_response,
            operations_task_responses.alignment_spanish_cache_invalidation_consistency_agreement_response,
            operations_task_responses.alignment_english_cache_invalidation_consistency_agreement_response,
        ),
    ),
    "concurrency_conflict_resolution": (
        _agreement_is_concurrency_conflict_resolution_task,
        (
            operations_task_responses.alignment_chinese_concurrency_conflict_resolution_agreement_response,
            operations_task_responses.alignment_spanish_concurrency_conflict_resolution_agreement_response,
            operations_task_responses.alignment_english_concurrency_conflict_resolution_agreement_response,
        ),
    ),
    "incident_root_cause": (
        _agreement_is_incident_root_cause_task,
        (
            operations_task_responses.alignment_chinese_incident_root_cause_agreement_response,
            operations_task_responses.alignment_spanish_incident_root_cause_agreement_response,
            operations_task_responses.alignment_english_incident_root_cause_agreement_response,
        ),
    ),
}
