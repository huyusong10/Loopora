from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
import json

from loopora.alignment_guidance import alignment_guidance_dir
from loopora.executor_alignment_bundle_task_predicates import (
    _is_analytics_experiment_instrumentation_task,
    _is_audit_log_integrity_retention_task,
    _is_auth_session_token_lifecycle_task,
    _is_authorization_policy_task,
    _is_backup_restore_recovery_task,
    _is_cache_invalidation_consistency_task,
    _is_cdc_replication_consistency_task,
    _is_concurrency_conflict_resolution_task,
    _is_data_import_validation_task,
    _is_data_lifecycle_deletion_retention_task,
    _is_data_residency_task,
    _is_database_schema_migration_task,
    _is_dispute_chargeback_lifecycle_task,
    _is_dsar_data_export_task,
    _is_feature_flag_rollout_task,
    _is_file_upload_storage_safety_task,
    _is_identity_sso_task,
    _is_incident_root_cause_task,
    _is_inventory_reservation_consistency_task,
    _is_key_rotation_task,
    _is_kyc_aml_screening_task,
    _is_metric_reporting_reconciliation_task,
    _is_notification_subscription_deliverability_task,
    _is_payment_webhook_ledger_task,
    _is_payout_settlement_reconciliation_task,
    _is_prompt_asset_ownership_task,
    _is_rag_long_chain_task,
    _is_schedule_phase_task,
    _is_search_index_consistency_task,
    _is_search_quality_task,
    _is_subscription_entitlement_billing_task,
    _is_support_impersonation_task,
    _is_support_ticket_sla_task,
    _is_tax_calculation_compliance_task,
    _is_usage_quota_metering_task,
)
from loopora.service_types import LooporaError

TaskRolePredicate = Callable[[str], bool]


@dataclass(frozen=True)
class TaskRoleFixtureReplacement:
    predicate: TaskRolePredicate
    fixture_key: str


TASK_ROLE_FIXTURE_REPLACERS: tuple[TaskRoleFixtureReplacement, ...] = (
    TaskRoleFixtureReplacement(_is_prompt_asset_ownership_task, "prompt_asset_ownership"),
    TaskRoleFixtureReplacement(_is_backup_restore_recovery_task, "backup_restore_recovery"),
    TaskRoleFixtureReplacement(_is_audit_log_integrity_retention_task, "audit_log_integrity_retention"),
    TaskRoleFixtureReplacement(_is_database_schema_migration_task, "database_schema_migration"),
    TaskRoleFixtureReplacement(_is_cdc_replication_consistency_task, "cdc_replication_consistency"),
    TaskRoleFixtureReplacement(_is_metric_reporting_reconciliation_task, "metric_reporting_reconciliation"),
    TaskRoleFixtureReplacement(_is_dispute_chargeback_lifecycle_task, "dispute_chargeback_lifecycle"),
    TaskRoleFixtureReplacement(_is_payout_settlement_reconciliation_task, "payout_settlement_reconciliation"),
    TaskRoleFixtureReplacement(_is_analytics_experiment_instrumentation_task, "analytics_experiment_instrumentation"),
    TaskRoleFixtureReplacement(_is_dsar_data_export_task, "dsar_data_export"),
    TaskRoleFixtureReplacement(_is_support_ticket_sla_task, "support_ticket_sla"),
    TaskRoleFixtureReplacement(_is_subscription_entitlement_billing_task, "subscription_entitlement_billing"),
    TaskRoleFixtureReplacement(_is_notification_subscription_deliverability_task, "notification_subscription_deliverability"),
    TaskRoleFixtureReplacement(_is_data_lifecycle_deletion_retention_task, "data_lifecycle_deletion_retention"),
    TaskRoleFixtureReplacement(_is_feature_flag_rollout_task, "feature_flag_rollout"),
    TaskRoleFixtureReplacement(_is_cache_invalidation_consistency_task, "cache_invalidation_consistency"),
    TaskRoleFixtureReplacement(_is_data_import_validation_task, "data_import_validation"),
    TaskRoleFixtureReplacement(_is_concurrency_conflict_resolution_task, "concurrency_conflict_resolution"),
    TaskRoleFixtureReplacement(_is_usage_quota_metering_task, "usage_quota_metering"),
    TaskRoleFixtureReplacement(_is_tax_calculation_compliance_task, "tax_calculation_compliance"),
    TaskRoleFixtureReplacement(_is_inventory_reservation_consistency_task, "inventory_reservation_consistency"),
    TaskRoleFixtureReplacement(_is_file_upload_storage_safety_task, "file_upload_storage_safety"),
    TaskRoleFixtureReplacement(_is_auth_session_token_lifecycle_task, "auth_session_token_lifecycle"),
    TaskRoleFixtureReplacement(_is_rag_long_chain_task, "rag_long_chain"),
    TaskRoleFixtureReplacement(_is_schedule_phase_task, "schedule_phase"),
    TaskRoleFixtureReplacement(_is_data_residency_task, "data_residency"),
    TaskRoleFixtureReplacement(_is_support_impersonation_task, "support_impersonation"),
    TaskRoleFixtureReplacement(_is_kyc_aml_screening_task, "kyc_aml_screening"),
    TaskRoleFixtureReplacement(_is_identity_sso_task, "identity_sso"),
    TaskRoleFixtureReplacement(_is_key_rotation_task, "key_rotation"),
    TaskRoleFixtureReplacement(_is_payment_webhook_ledger_task, "payment_webhook_ledger"),
    TaskRoleFixtureReplacement(_is_authorization_policy_task, "authorization_policy"),
    TaskRoleFixtureReplacement(_is_incident_root_cause_task, "incident_root_cause"),
    TaskRoleFixtureReplacement(_is_search_index_consistency_task, "search_index_consistency"),
    TaskRoleFixtureReplacement(_is_search_quality_task, "search_quality"),
)


def _rag_long_chain_governance_prompt(archetype: str) -> str:
    prompts = _task_role_governance_prompts()
    return prompts.get(str(archetype or "").strip(), prompts["default"])


@lru_cache(maxsize=1)
def _task_role_governance_prompts() -> dict[str, str]:
    asset_path = alignment_guidance_dir() / "task-role-governance.json"
    try:
        payload = json.loads(asset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LooporaError(f"invalid task role governance prompt asset: {asset_path.name}") from exc
    if not isinstance(payload, dict):
        raise LooporaError("task role governance prompt asset must decode to an object")
    prompts = {str(key).strip(): str(value).strip() for key, value in payload.items() if str(key).strip()}
    required = {"builder", "inspector", "gatekeeper", "default"}
    missing = sorted(key for key in required if not prompts.get(key))
    if missing:
        raise LooporaError(f"task role governance prompt asset missing keys: {', '.join(missing)}")
    return prompts


def _replace_task_anchored_roles(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    for replacement in TASK_ROLE_FIXTURE_REPLACERS:
        if replacement.predicate(task):
            _replace_task_role_definitions_from_asset(
                bundle,
                fixture_key=replacement.fixture_key,
                prefers_chinese=prefers_chinese,
                task=task,
                display_language=display_language,
            )
            return
    _replace_task_role_definitions_from_asset(
        bundle,
        fixture_key="generic_task_anchor",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _apply_search_refactor_improvement_roles(bundle: dict) -> None:
    _replace_task_role_definitions_from_asset(
        bundle,
        fixture_key="search_refactor_improvement",
        prefers_chinese=True,
        task="Search refactor improvement from source Loop feedback.",
    )


def _apply_refund_repair_roles(bundle: dict, *, prefers_chinese: bool) -> None:
    task = (
        "受治理的退款自助路径，需证明授权、支付失败、审计、客服交接和重复退款防护"
        if prefers_chinese
        else "governed refund self-service path with authorization, provider failure, audit, support handoff, and double-refund proof"
    )
    _replace_task_role_definitions_from_asset(
        bundle,
        fixture_key="refund_repair",
        prefers_chinese=prefers_chinese,
        task=task,
    )


def _replace_task_role_definitions_from_asset(
    bundle: dict,
    *,
    fixture_key: str,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    locale = _task_role_fixture_locale(prefers_chinese=prefers_chinese, display_language=display_language)
    task_fixture = _task_role_fixtures_asset().get("tasks", {}).get(fixture_key)
    if not isinstance(task_fixture, dict):
        raise LooporaError(f"missing task role fixture: {fixture_key}")
    roles = task_fixture.get("roles")
    if not isinstance(roles, list) or not roles:
        raise LooporaError(f"task role fixture must define roles: {fixture_key}")
    bundle["role_definitions"] = [_task_role_definition_from_asset(role, locale=locale, task=task) for role in roles]


def _task_role_definition_from_asset(role: object, *, locale: str, task: str) -> dict:
    if not isinstance(role, dict):
        raise LooporaError("task role fixture role must be an object")
    key = _required_task_role_text(role, "key")
    archetype = _required_task_role_text(role, "archetype")
    prompt_body = _required_task_role_text(role, "prompt_body")
    return {
        "key": key,
        "name": _localized_task_role_text(role.get("name"), locale=locale),
        "description": _localized_task_role_text(role.get("description"), locale=locale),
        "archetype": archetype,
        "prompt_ref": f"{key}.md",
        "prompt_markdown": _task_role_prompt_markdown(archetype=archetype, prompt_body=prompt_body, task=task),
        "posture_notes": _localized_task_role_text(role.get("posture"), locale=locale),
        "executor_kind": "codex",
        "executor_mode": "preset",
        "command_cli": "codex",
        "command_args_text": "",
        "model": "",
        "reasoning_effort": "",
    }


def _task_role_prompt_markdown(*, archetype: str, prompt_body: str, task: str) -> str:
    return (
        f"---\nversion: 1\narchetype: {archetype}\n---\n\n{prompt_body}\n"
        f"{_rag_long_chain_governance_prompt(archetype)}\n"
        f"Task anchor: {task}\n"
        "Use Proven, Weak, Unproven, Blocking, and Residual risk buckets.\n"
    )


def _task_role_fixture_locale(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return "zh"
    if str(display_language or "").strip().lower() == "es":
        return "es"
    return "en"


def _localized_task_role_text(value: object, *, locale: str) -> str:
    if isinstance(value, dict):
        text = value.get(locale) or value.get("en")
        if isinstance(text, str) and text.strip():
            return text
    raise LooporaError(f"task role fixture text missing locale: {locale}")


def _required_task_role_text(role: dict, key: str) -> str:
    value = role.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LooporaError(f"task role fixture role missing {key}")
    return value


@lru_cache(maxsize=1)
def _task_role_fixtures_asset() -> dict:
    path = alignment_guidance_dir() / "task-role-fixtures.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LooporaError("invalid task role fixture asset") from exc
    if not isinstance(value, dict):
        raise LooporaError("task role fixture asset must decode to an object")
    if not isinstance(value.get("tasks"), dict):
        raise LooporaError("task role fixture asset must define tasks")
    return value
