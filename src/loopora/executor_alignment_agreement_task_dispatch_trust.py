from __future__ import annotations

from loopora import executor_alignment_agreement_task_responses_trust as trust_task_responses
from loopora.executor_alignment_agreement_predicates import (
    _agreement_is_auth_session_token_lifecycle_task,
    _agreement_is_authorization_policy_task,
    _agreement_is_data_residency_task,
    _agreement_is_identity_sso_task,
    _agreement_is_key_rotation_task,
    _agreement_is_kyc_aml_screening_task,
    _agreement_is_prompt_asset_ownership_task,
    _agreement_is_support_impersonation_task,
)
from loopora.executor_alignment_agreement_task_dispatch_types import AgreementTaskFactoryRoute

TRUST_TASK_AGREEMENT_FACTORY_ROUTES: dict[str, AgreementTaskFactoryRoute] = {
    "prompt_asset_ownership": (
        _agreement_is_prompt_asset_ownership_task,
        (
            trust_task_responses.alignment_chinese_prompt_asset_ownership_agreement_response,
            trust_task_responses.alignment_spanish_prompt_asset_ownership_agreement_response,
            trust_task_responses.alignment_english_prompt_asset_ownership_agreement_response,
        ),
    ),
    "auth_session_token_lifecycle": (
        _agreement_is_auth_session_token_lifecycle_task,
        (
            trust_task_responses.alignment_chinese_auth_session_token_lifecycle_agreement_response,
            trust_task_responses.alignment_spanish_auth_session_token_lifecycle_agreement_response,
            trust_task_responses.alignment_english_auth_session_token_lifecycle_agreement_response,
        ),
    ),
    "data_residency": (
        _agreement_is_data_residency_task,
        (
            trust_task_responses.alignment_chinese_data_residency_agreement_response,
            trust_task_responses.alignment_spanish_data_residency_agreement_response,
            trust_task_responses.alignment_english_data_residency_agreement_response,
        ),
    ),
    "support_impersonation": (
        _agreement_is_support_impersonation_task,
        (
            trust_task_responses.alignment_chinese_support_impersonation_agreement_response,
            trust_task_responses.alignment_spanish_support_impersonation_agreement_response,
            trust_task_responses.alignment_english_support_impersonation_agreement_response,
        ),
    ),
    "kyc_aml_screening": (
        _agreement_is_kyc_aml_screening_task,
        (
            trust_task_responses.alignment_chinese_kyc_aml_screening_agreement_response,
            trust_task_responses.alignment_spanish_kyc_aml_screening_agreement_response,
            trust_task_responses.alignment_english_kyc_aml_screening_agreement_response,
        ),
    ),
    "identity_sso": (
        _agreement_is_identity_sso_task,
        (
            trust_task_responses.alignment_chinese_identity_sso_agreement_response,
            trust_task_responses.alignment_spanish_identity_sso_agreement_response,
            trust_task_responses.alignment_english_identity_sso_agreement_response,
        ),
    ),
    "key_rotation": (
        _agreement_is_key_rotation_task,
        (
            trust_task_responses.alignment_chinese_key_rotation_agreement_response,
            trust_task_responses.alignment_spanish_key_rotation_agreement_response,
            trust_task_responses.alignment_english_key_rotation_agreement_response,
        ),
    ),
    "authorization_policy": (
        _agreement_is_authorization_policy_task,
        (
            trust_task_responses.alignment_chinese_authorization_policy_agreement_response,
            trust_task_responses.alignment_spanish_authorization_policy_agreement_response,
            trust_task_responses.alignment_english_authorization_policy_agreement_response,
        ),
    ),
}
