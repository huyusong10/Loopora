from __future__ import annotations

from pathlib import Path

from executor_predicate_architecture_checks import (
    _assert_commercial_task_predicate_domain_boundaries,
    _assert_data_task_predicate_domain_boundaries,
    _assert_product_task_predicate_domain_boundaries,
    _assert_trust_task_predicate_domain_boundaries,
)
from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def loopora_source(filename: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")


def design_contracts_source() -> str:
    return design_boundary_source()


def _bundle_task_routing_boundary_sources() -> dict[str, str]:
    service_boundaries_path = REPO_ROOT / "design" / "service-boundaries.md"
    return {
        "variants": loopora_source("executor_alignment_bundle_fixtures.py"),
        "task_anchor": loopora_source("executor_alignment_bundle_task_anchor.py"),
        "routing": loopora_source("executor_alignment_bundle_task_routing.py"),
        "bundle_predicates": loopora_source("executor_alignment_bundle_task_predicates.py"),
        "task_predicates": loopora_source("executor_alignment_task_predicates.py"),
        "commercial_task_predicates": loopora_source("executor_alignment_task_predicates_commercial.py"),
        "commercial_billing_task_predicates": loopora_source("executor_alignment_task_predicates_commercial_billing.py"),
        "commercial_cross_domain_task_predicates": loopora_source("executor_alignment_task_predicates_commercial_cross_domain.py"),
        "commercial_metrics_task_predicates": loopora_source("executor_alignment_task_predicates_commercial_metrics.py"),
        "commercial_payments_task_predicates": loopora_source("executor_alignment_task_predicates_commercial_payments.py"),
        "data_task_predicates": loopora_source("executor_alignment_task_predicates_data.py"),
        "data_cross_domain_task_predicates": loopora_source("executor_alignment_task_predicates_data_cross_domain.py"),
        "data_ingest_task_predicates": loopora_source("executor_alignment_task_predicates_data_ingest.py"),
        "data_lifecycle_task_predicates": loopora_source("executor_alignment_task_predicates_data_lifecycle.py"),
        "data_migration_task_predicates": loopora_source("executor_alignment_task_predicates_data_migration.py"),
        "data_read_models_task_predicates": loopora_source("executor_alignment_task_predicates_data_read_models.py"),
        "data_resilience_task_predicates": loopora_source("executor_alignment_task_predicates_data_resilience.py"),
        "operations_task_predicates": loopora_source("executor_alignment_task_predicates_operations.py"),
        "product_task_predicates": loopora_source("executor_alignment_task_predicates_product.py"),
        "product_cross_domain_task_predicates": loopora_source("executor_alignment_task_predicates_product_cross_domain.py"),
        "product_engagement_task_predicates": loopora_source("executor_alignment_task_predicates_product_engagement.py"),
        "product_operations_task_predicates": loopora_source("executor_alignment_task_predicates_product_operations.py"),
        "product_search_ai_task_predicates": loopora_source("executor_alignment_task_predicates_product_search_ai.py"),
        "trust_task_predicates": loopora_source("executor_alignment_task_predicates_trust.py"),
        "trust_access_task_predicates": loopora_source("executor_alignment_task_predicates_trust_access.py"),
        "trust_cross_domain_task_predicates": loopora_source("executor_alignment_task_predicates_trust_cross_domain.py"),
        "trust_governance_task_predicates": loopora_source("executor_alignment_task_predicates_trust_governance.py"),
        "trust_secrets_task_predicates": loopora_source("executor_alignment_task_predicates_trust_secrets.py"),
        "spec_notes": loopora_source("executor_alignment_bundle_task_spec_notes.py"),
        "spec_notes_asset": (REPO_ROOT / "src" / "loopora" / "assets" / "alignment" / "task-spec-workflow-notes.json").read_text(encoding="utf-8"),
        "spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds.py"),
        "commercial_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_commercial.py"),
        "data_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_data.py"),
        "operations_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_operations.py"),
        "product_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_product.py"),
        "product_engagement_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_product_engagement.py"),
        "product_operations_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_product_operations.py"),
        "product_search_ai_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_product_search_ai.py"),
        "trust_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_trust.py"),
        "trust_access_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_trust_access.py"),
        "trust_governance_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_trust_governance.py"),
        "trust_secrets_spec_scaffolds": loopora_source("executor_alignment_bundle_task_spec_scaffolds_trust_secrets.py"),
        "contracts": design_contracts_source(),
        "service_boundaries": service_boundaries_path.read_text(encoding="utf-8"),
    }


def _assert_bundle_task_routing_dispatch_boundary(sources: dict[str, str]) -> None:
    assert "from loopora.executor_alignment_bundle_task_routing import" in sources["task_anchor"]
    assert "from loopora.executor_alignment_bundle_task_spec_scaffolds import" not in sources["routing"]
    assert "from loopora.executor_alignment_bundle_task_spec_scaffolds_commercial import" in sources["routing"]
    assert "from loopora.executor_alignment_bundle_task_spec_scaffolds_data import" in sources["routing"]
    assert "from loopora.executor_alignment_bundle_task_spec_scaffolds_operations import" in sources["routing"]
    assert "from loopora.executor_alignment_bundle_task_spec_scaffolds_product import" in sources["routing"]
    assert "from loopora.executor_alignment_bundle_task_spec_scaffolds_trust import" in sources["routing"]
    assert "from loopora.executor_alignment_bundle_task_predicates import" not in sources["routing"]
    assert "from loopora import executor_alignment_task_predicates as _task_predicates" in sources["bundle_predicates"]
    for domain_module in (
        "executor_alignment_task_predicates_commercial",
        "executor_alignment_task_predicates_data",
        "executor_alignment_task_predicates_operations",
        "executor_alignment_task_predicates_product",
        "executor_alignment_task_predicates_trust",
    ):
        assert f"from loopora.{domain_module} import" in sources["task_predicates"]
    for data_module in (
        "executor_alignment_task_predicates_data_cross_domain",
        "executor_alignment_task_predicates_data_ingest",
        "executor_alignment_task_predicates_data_lifecycle",
        "executor_alignment_task_predicates_data_migration",
        "executor_alignment_task_predicates_data_read_models",
        "executor_alignment_task_predicates_data_resilience",
    ):
        assert f"from loopora.{data_module} import" in sources["data_task_predicates"]
    for product_module in (
        "executor_alignment_task_predicates_product_cross_domain",
        "executor_alignment_task_predicates_product_engagement",
        "executor_alignment_task_predicates_product_operations",
        "executor_alignment_task_predicates_product_search_ai",
    ):
        assert f"from loopora.{product_module} import" in sources["product_task_predicates"]
    for commercial_module in (
        "executor_alignment_task_predicates_commercial_billing",
        "executor_alignment_task_predicates_commercial_metrics",
        "executor_alignment_task_predicates_commercial_payments",
    ):
        assert f"from loopora.{commercial_module} import" in sources["commercial_task_predicates"]
    for trust_module in (
        "executor_alignment_task_predicates_trust_access",
        "executor_alignment_task_predicates_trust_governance",
        "executor_alignment_task_predicates_trust_secrets",
    ):
        assert f"from loopora.{trust_module} import" in sources["trust_task_predicates"]
    _assert_commercial_task_predicate_domain_boundaries(sources)
    _assert_trust_task_predicate_domain_boundaries(sources)
    _assert_product_task_predicate_domain_boundaries(sources)
    _assert_data_task_predicate_domain_boundaries(sources)
    for predicate_marker in (
        "def is_feature_flag_rollout_task",
        "def is_incident_root_cause_task",
    ):
        assert predicate_marker in sources["operations_task_predicates"]
        assert predicate_marker not in sources["task_predicates"]
        assert predicate_marker not in sources["routing"]
        assert predicate_marker not in sources["variants"]
    for predicate_marker in (
        "_is_schedule_phase_task = _task_predicates.is_schedule_phase_task",
        "_is_search_index_consistency_task = _task_predicates.is_search_index_consistency_task",
        "_is_payment_webhook_ledger_task = _task_predicates.is_payment_webhook_ledger_task",
    ):
        assert predicate_marker in sources["bundle_predicates"]


def _assert_bundle_task_routing_appender_boundary(sources: dict[str, str]) -> None:
    for routing_marker in ("def _append_selected_workflow_spec_notes", "TASK_SPEC_NOTE_APPENDERS", "TaskSpecNoteAppenderRegistration"):
        assert routing_marker in sources["routing"]
    for appender_marker in (
        "def _append_rag_long_chain_spec_notes",
        "def _append_metric_reporting_reconciliation_spec_notes",
        "def _append_database_schema_migration_spec_notes",
        "def _append_incident_root_cause_spec_notes",
    ):
        for source_key in ("routing", "bundle_predicates", "spec_scaffolds", "variants"):
            assert appender_marker not in sources[source_key]
    for routing_non_contract in ("markdown.rstrip() + notes", "appenders = {"):
        assert routing_non_contract not in sources["routing"]
    for source_key in ("spec_scaffolds", *_SPEC_SCAFFOLD_SOURCE_KEYS):
        assert "def _append_selected_workflow_spec_notes" not in sources[source_key]
    body_source = "".join(sources[source_key] for source_key in _SPEC_SCAFFOLD_BODY_SOURCE_KEYS)
    assert "append_task_spec_workflow_note_for_task" in sources["spec_notes"]
    assert "append_task_spec_workflow_note_for_task" in body_source
    assert "append_task_spec_workflow_note_from_asset" not in body_source
    assert 'markdown.rstrip() + note["text"]' in sources["spec_notes"]
    assert "markdown.rstrip() + notes" not in body_source


_PRODUCT_SPEC_BODY_KEYS = ("product_engagement_spec_scaffolds", "product_operations_spec_scaffolds", "product_search_ai_spec_scaffolds")
_TRUST_SPEC_BODY_KEYS = ("trust_access_spec_scaffolds", "trust_governance_spec_scaffolds", "trust_secrets_spec_scaffolds")
_SPEC_SCAFFOLD_SOURCE_KEYS = (
    "commercial_spec_scaffolds",
    "data_spec_scaffolds",
    "operations_spec_scaffolds",
    "product_spec_scaffolds",
    *_PRODUCT_SPEC_BODY_KEYS,
    "trust_spec_scaffolds",
    *_TRUST_SPEC_BODY_KEYS,
)
_SPEC_SCAFFOLD_BODY_SOURCE_KEYS = (
    "commercial_spec_scaffolds",
    "data_spec_scaffolds",
    "operations_spec_scaffolds",
    *_PRODUCT_SPEC_BODY_KEYS,
    *_TRUST_SPEC_BODY_KEYS,
)


def _assert_scaffold_marker_owned_by_source(sources: dict[str, str], marker: str, *, owner_key: str) -> None:
    assert marker in sources[owner_key]
    for source_key in _SPEC_SCAFFOLD_SOURCE_KEYS:
        if source_key != owner_key:
            assert marker not in sources[source_key]
    assert marker not in sources["spec_scaffolds"]
    assert marker not in sources["routing"]
    assert marker not in sources["variants"]


def _assert_bundle_task_spec_scaffold_domain_boundaries(sources: dict[str, str]) -> None:
    _assert_scaffold_marker_owned_by_source(sources, "def _append_schedule_phase_spec_notes", owner_key="product_engagement_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_search_index_consistency_spec_notes", owner_key="product_search_ai_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_concurrency_conflict_resolution_spec_notes", owner_key="product_operations_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_payment_webhook_ledger_spec_notes", owner_key="commercial_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_metric_reporting_reconciliation_spec_notes", owner_key="commercial_spec_scaffolds")
    for scaffold_marker in (
        "def _append_backup_restore_recovery_spec_notes",
        "def _append_cdc_replication_consistency_spec_notes",
        "def _append_file_upload_storage_safety_spec_notes",
    ):
        _assert_scaffold_marker_owned_by_source(sources, scaffold_marker, owner_key="data_spec_scaffolds")
    for scaffold_marker in ("def _append_feature_flag_rollout_spec_notes", "def _append_incident_root_cause_spec_notes"):
        _assert_scaffold_marker_owned_by_source(sources, scaffold_marker, owner_key="operations_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_authorization_policy_spec_notes", owner_key="trust_access_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_data_residency_spec_notes", owner_key="trust_governance_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_prompt_asset_ownership_spec_notes", owner_key="trust_secrets_spec_scaffolds")
    _assert_scaffold_marker_owned_by_source(sources, "def _append_auth_session_token_lifecycle_spec_notes", owner_key="trust_access_spec_scaffolds")
    for facade_marker in (
        "_append_schedule_phase_spec_notes as _append_schedule_phase_spec_notes",
        "_append_payment_webhook_ledger_spec_notes as _append_payment_webhook_ledger_spec_notes",
        "_append_database_schema_migration_spec_notes as _append_database_schema_migration_spec_notes",
        "_append_incident_root_cause_spec_notes as _append_incident_root_cause_spec_notes",
        "_append_authorization_policy_spec_notes as _append_authorization_policy_spec_notes",
    ):
        assert facade_marker in sources["spec_scaffolds"]
    template_body_source = "".join(sources[source_key] for source_key in ("commercial_spec_scaffolds", *_PRODUCT_SPEC_BODY_KEYS, *_TRUST_SPEC_BODY_KEYS))
    assert "apply_task_spec_scaffold_template_from_asset" in template_body_source
    assert 'bundle["spec"]["markdown"] = f"""# Task' not in template_body_source
    assert 'bundle["spec"]["markdown"] = f"""# Task' not in sources["product_spec_scaffolds"]
    assert 'bundle["spec"]["markdown"] = f"""# Task' not in sources["trust_spec_scaffolds"]
    assert 'bundle["spec"]["markdown"] = f"""# Task' not in sources["spec_scaffolds"]
    assert 'bundle["spec"]["markdown"] = f"""# Task' not in sources["routing"]


def _task_workflow_boundary_sources() -> dict[str, str]:
    service_boundaries_path = Path(__file__).resolve().parents[3] / "design" / "service-boundaries.md"
    return {
        "variants": loopora_source("executor_alignment_bundle_fixtures.py"),
        "task_anchor": loopora_source("executor_alignment_bundle_task_anchor.py"),
        "dispatch": loopora_source("executor_alignment_bundle_task_workflow_dispatch.py"),
        "workflows": loopora_source("executor_alignment_bundle_task_workflows.py"),
        "commercial_workflows": loopora_source("executor_alignment_bundle_task_workflows_commercial.py"),
        "commercial_billing_workflows": loopora_source("executor_alignment_bundle_task_workflows_commercial_billing.py"),
        "commercial_billing_subscription_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_commercial_billing_subscription.py",
        ),
        "commercial_billing_tax_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_commercial_billing_tax.py",
        ),
        "commercial_billing_usage_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_commercial_billing_usage.py",
        ),
        "commercial_metrics_workflows": loopora_source("executor_alignment_bundle_task_workflows_commercial_metrics.py"),
        "commercial_payments_workflows": loopora_source("executor_alignment_bundle_task_workflows_commercial_payments.py"),
        "commercial_payments_dispute_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_commercial_payments_dispute.py",
        ),
        "commercial_payments_payout_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_commercial_payments_payout.py",
        ),
        "commercial_payments_webhook_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_commercial_payments_webhook.py",
        ),
        "data_workflows": loopora_source("executor_alignment_bundle_task_workflows_data.py"),
        "data_ingest_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_ingest.py"),
        "data_ingest_import_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_ingest_import.py"),
        "data_ingest_upload_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_ingest_upload.py"),
        "data_lifecycle_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_lifecycle.py"),
        "data_lifecycle_deletion_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_lifecycle_deletion.py"),
        "data_lifecycle_dsar_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_lifecycle_dsar.py"),
        "data_migration_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_migration.py"),
        "data_migration_cdc_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_migration_cdc.py"),
        "data_migration_schema_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_migration_schema.py"),
        "data_resilience_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_resilience.py"),
        "data_resilience_audit_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_resilience_audit.py"),
        "data_resilience_backup_workflows": loopora_source("executor_alignment_bundle_task_workflows_data_resilience_backup.py"),
        "operations_workflows": loopora_source("executor_alignment_bundle_task_workflows_operations.py"),
        "operations_collaboration_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_operations_collaboration.py",
        ),
        "operations_incident_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_operations_incident.py",
        ),
        "operations_release_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_operations_release.py",
        ),
        "operations_release_cache_workflows": loopora_source("executor_alignment_bundle_task_workflows_operations_release_cache.py"),
        "operations_release_flag_workflows": loopora_source("executor_alignment_bundle_task_workflows_operations_release_flag.py"),
        "product_workflows": loopora_source("executor_alignment_bundle_task_workflows_product.py"),
        "product_engagement_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_engagement.py"),
        "product_engagement_notification_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_engagement_notification.py"),
        "product_engagement_schedule_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_engagement_schedule.py"),
        "product_engagement_support_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_engagement_support.py"),
        "product_operations_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_operations.py"),
        "product_operations_analytics_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_operations_analytics.py"),
        "product_operations_inventory_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_operations_inventory.py"),
        "product_search_ai_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_search_ai.py"),
        "product_search_ai_index_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_search_ai_index.py"),
        "product_search_ai_quality_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_search_ai_quality.py"),
        "product_search_ai_rag_workflows": loopora_source("executor_alignment_bundle_task_workflows_product_search_ai_rag.py"),
        "trust_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust.py"),
        "trust_access_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_access.py"),
        "trust_access_authorization_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_trust_access_authorization.py",
        ),
        "trust_access_breakglass_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_trust_access_breakglass.py",
        ),
        "trust_access_identity_workflows": loopora_source(
            "executor_alignment_bundle_task_workflows_trust_access_identity.py",
        ),
        "trust_access_identity_session_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_access_identity_session.py"),
        "trust_access_identity_sso_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_access_identity_sso.py"),
        "trust_governance_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_governance.py"),
        "trust_governance_data_residency_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_governance_data_residency.py"),
        "trust_governance_kyc_aml_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_governance_kyc_aml.py"),
        "trust_secrets_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_secrets.py"),
        "trust_secrets_key_rotation_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_secrets_key_rotation.py"),
        "trust_secrets_prompt_asset_workflows": loopora_source("executor_alignment_bundle_task_workflows_trust_secrets_prompt_asset.py"),
        "workflow_helpers": loopora_source("executor_alignment_bundle_task_workflow_helpers.py"),
        "intents": loopora_source("executor_alignment_bundle_task_workflow_intents.py"),
        "visible": loopora_source("executor_alignment_bundle_task_visible_scaffolds.py"),
        "commercial_visible": loopora_source("executor_alignment_bundle_task_visible_scaffolds_commercial.py"),
        "product_visible": loopora_source("executor_alignment_bundle_task_visible_scaffolds_product.py"),
        "trust_visible": loopora_source("executor_alignment_bundle_task_visible_scaffolds_trust.py"),
        "contracts": design_contracts_source(),
        "service_boundaries": service_boundaries_path.read_text(encoding="utf-8"),
    }


def _assert_task_workflow_dispatch_boundary(sources: dict[str, str]) -> None:
    assert "from loopora.executor_alignment_bundle_task_workflow_dispatch import" in sources["task_anchor"]
    assert "from loopora.executor_alignment_bundle_task_predicates import" in sources["dispatch"]
    assert "from loopora.executor_alignment_bundle_task_routing import" not in sources["dispatch"]
    assert "from loopora.executor_alignment_bundle_task_workflows import" in sources["dispatch"]
    assert "from loopora.executor_alignment_bundle_task_workflows_commercial import" in sources["dispatch"]
    assert "from loopora.executor_alignment_bundle_task_workflows_data import" in sources["dispatch"]
    assert "from loopora.executor_alignment_bundle_task_workflows_product import" in sources["dispatch"]
    assert "from loopora.executor_alignment_bundle_task_workflows_trust import" in sources["dispatch"]
    for marker in (
        "def _replace_task_anchored_workflow",
        "TASK_WORKFLOW_REPLACERS",
        "TaskWorkflowReplacement",
        "_apply_task_workflow_replacement",
        "passes_task=False",
        "_is_schedule_phase_task",
        "_replace_schedule_phase_task_workflow",
        "_replace_generic_task_evidence_repair_workflow",
    ):
        assert marker in sources["dispatch"]
        assert marker not in sources["variants"]
    assert "lambda:" not in sources["dispatch"]


def _assert_marker_owned_by_source(
    sources: dict[str, str],
    marker: str,
    *,
    owner_key: str,
    other_keys: tuple[str, ...],
) -> None:
    assert marker in sources[owner_key]
    for source_key in other_keys:
        assert marker not in sources[source_key]
    assert marker not in sources["variants"]


def _assert_task_workflow_shape_boundaries(sources: dict[str, str]) -> None:
    helper_import = "from loopora.executor_alignment_bundle_task_workflow_helpers import"
    for source_key in _TASK_WORKFLOW_HELPER_SOURCE_KEYS:
        assert helper_import in sources[source_key]
    for source_key in _DOMAIN_FACADE_KEYS:
        assert helper_import not in sources[source_key]

    base_other_keys = tuple(source_key for source_key in _ALL_WORKFLOW_SHAPE_SOURCE_KEYS if source_key != "workflows")
    for marker in ("def _replace_generic_task_evidence_repair_workflow",):
        _assert_marker_owned_by_source(sources, marker, owner_key="workflows", other_keys=base_other_keys)

    _assert_data_task_workflow_shape_boundaries(sources)
    _assert_operations_task_workflow_shape_boundaries(sources)
    _assert_product_task_workflow_shape_boundaries(sources)
    _assert_commercial_task_workflow_shape_boundaries(sources)
    _assert_trust_task_workflow_shape_boundaries(sources)
    assert "def _dedupe_values" in sources["workflow_helpers"]
    for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
        assert "def _dedupe_values" not in sources[source_key]
    assert "def _dedupe_values" not in sources["variants"]


def _assert_partitioned_workflow_markers(
    sources: dict[str, str],
    *,
    facade_key: str,
    partition_keys: tuple[str, ...],
    marker_groups: dict[str, tuple[str, ...]],
    facade_exports: tuple[str, ...],
) -> None:
    for owner_key, markers in marker_groups.items():
        other_keys = tuple(source_key for source_key in partition_keys if source_key != owner_key)
        for marker in markers:
            _assert_marker_owned_by_source(sources, marker, owner_key=owner_key, other_keys=other_keys)
    for export_marker in facade_exports:
        assert export_marker in sources[facade_key]


def _assert_product_task_workflow_shape_boundaries(sources: dict[str, str]) -> None:
    _assert_partitioned_workflow_markers(
        sources,
        facade_key="product_workflows",
        partition_keys=_ALL_WORKFLOW_SHAPE_SOURCE_KEYS,
        marker_groups={
            "product_engagement_notification_workflows": ("def _replace_notification_subscription_deliverability_task_workflow",),
            "product_engagement_support_workflows": ("def _replace_support_ticket_sla_task_workflow",),
            "product_engagement_schedule_workflows": ("def _replace_schedule_phase_task_workflow",),
            "product_operations_analytics_workflows": ("def _replace_analytics_experiment_instrumentation_task_workflow",),
            "product_operations_inventory_workflows": ("def _replace_inventory_reservation_consistency_task_workflow",),
            "product_search_ai_index_workflows": ("def _replace_search_index_consistency_task_workflow",),
            "product_search_ai_quality_workflows": ("def _replace_search_quality_task_workflow",),
            "product_search_ai_rag_workflows": ("def _replace_rag_long_chain_task_workflow",),
        },
        facade_exports=(
            "_replace_notification_subscription_deliverability_task_workflow as _replace_notification_subscription_deliverability_task_workflow",
            "_replace_analytics_experiment_instrumentation_task_workflow as _replace_analytics_experiment_instrumentation_task_workflow",
            "_replace_search_index_consistency_task_workflow as _replace_search_index_consistency_task_workflow",
        ),
    )
    for export_marker in (
        "_replace_notification_subscription_deliverability_task_workflow as _replace_notification_subscription_deliverability_task_workflow",
        "_replace_support_ticket_sla_task_workflow as _replace_support_ticket_sla_task_workflow",
        "_replace_schedule_phase_task_workflow as _replace_schedule_phase_task_workflow",
    ):
        assert export_marker in sources["product_engagement_workflows"]
    for export_marker in (
        "_replace_analytics_experiment_instrumentation_task_workflow as _replace_analytics_experiment_instrumentation_task_workflow",
        "_replace_inventory_reservation_consistency_task_workflow as _replace_inventory_reservation_consistency_task_workflow",
    ):
        assert export_marker in sources["product_operations_workflows"]
    for export_marker in (
        "_replace_search_index_consistency_task_workflow as _replace_search_index_consistency_task_workflow",
        "_replace_search_quality_task_workflow as _replace_search_quality_task_workflow",
        "_replace_rag_long_chain_task_workflow as _replace_rag_long_chain_task_workflow",
    ):
        assert export_marker in sources["product_search_ai_workflows"]


def _assert_data_task_workflow_shape_boundaries(sources: dict[str, str]) -> None:
    _assert_partitioned_workflow_markers(
        sources,
        facade_key="data_workflows",
        partition_keys=_ALL_WORKFLOW_SHAPE_SOURCE_KEYS,
        marker_groups={
            "data_resilience_backup_workflows": ("def _replace_backup_restore_recovery_task_workflow",),
            "data_resilience_audit_workflows": ("def _replace_audit_log_integrity_retention_task_workflow",),
            "data_migration_schema_workflows": ("def _replace_database_schema_migration_task_workflow",),
            "data_migration_cdc_workflows": ("def _replace_cdc_replication_consistency_task_workflow",),
            "data_lifecycle_deletion_workflows": ("def _replace_data_lifecycle_deletion_retention_task_workflow",),
            "data_lifecycle_dsar_workflows": ("def _replace_dsar_data_export_task_workflow",),
            "data_ingest_import_workflows": ("def _replace_data_import_validation_task_workflow",),
            "data_ingest_upload_workflows": ("def _replace_file_upload_storage_safety_task_workflow",),
        },
        facade_exports=(
            "_replace_backup_restore_recovery_task_workflow as _replace_backup_restore_recovery_task_workflow",
            "_replace_database_schema_migration_task_workflow as _replace_database_schema_migration_task_workflow",
            "_replace_data_import_validation_task_workflow as _replace_data_import_validation_task_workflow",
        ),
    )
    for export_marker in (
        "_replace_data_lifecycle_deletion_retention_task_workflow as _replace_data_lifecycle_deletion_retention_task_workflow",
        "_replace_dsar_data_export_task_workflow as _replace_dsar_data_export_task_workflow",
    ):
        assert export_marker in sources["data_lifecycle_workflows"]
    for export_marker in (
        "_replace_data_import_validation_task_workflow as _replace_data_import_validation_task_workflow",
        "_replace_file_upload_storage_safety_task_workflow as _replace_file_upload_storage_safety_task_workflow",
    ):
        assert export_marker in sources["data_ingest_workflows"]
    for export_marker in (
        "_replace_database_schema_migration_task_workflow as _replace_database_schema_migration_task_workflow",
        "_replace_cdc_replication_consistency_task_workflow as _replace_cdc_replication_consistency_task_workflow",
    ):
        assert export_marker in sources["data_migration_workflows"]
    for export_marker in (
        "_replace_backup_restore_recovery_task_workflow as _replace_backup_restore_recovery_task_workflow",
        "_replace_audit_log_integrity_retention_task_workflow as _replace_audit_log_integrity_retention_task_workflow",
    ):
        assert export_marker in sources["data_resilience_workflows"]


def _assert_operations_task_workflow_shape_boundaries(sources: dict[str, str]) -> None:
    _assert_partitioned_workflow_markers(
        sources,
        facade_key="operations_workflows",
        partition_keys=_ALL_WORKFLOW_SHAPE_SOURCE_KEYS,
        marker_groups={
            "operations_release_flag_workflows": ("def _replace_feature_flag_rollout_task_workflow",),
            "operations_release_cache_workflows": ("def _replace_cache_invalidation_consistency_task_workflow",),
            "operations_collaboration_workflows": ("def _replace_concurrency_conflict_resolution_task_workflow",),
            "operations_incident_workflows": ("def _replace_incident_root_cause_task_workflow",),
        },
        facade_exports=(
            "_replace_feature_flag_rollout_task_workflow as _replace_feature_flag_rollout_task_workflow",
            "_replace_cache_invalidation_consistency_task_workflow as _replace_cache_invalidation_consistency_task_workflow",
            "_replace_concurrency_conflict_resolution_task_workflow as _replace_concurrency_conflict_resolution_task_workflow",
            "_replace_incident_root_cause_task_workflow as _replace_incident_root_cause_task_workflow",
        ),
    )
    for export_marker in (
        "_replace_feature_flag_rollout_task_workflow as _replace_feature_flag_rollout_task_workflow",
        "_replace_cache_invalidation_consistency_task_workflow as _replace_cache_invalidation_consistency_task_workflow",
    ):
        assert export_marker in sources["operations_release_workflows"]


def _assert_commercial_task_workflow_shape_boundaries(sources: dict[str, str]) -> None:
    _assert_partitioned_workflow_markers(
        sources,
        facade_key="commercial_workflows",
        partition_keys=_ALL_WORKFLOW_SHAPE_SOURCE_KEYS,
        marker_groups={
            "commercial_payments_webhook_workflows": ("def _replace_payment_webhook_ledger_task_workflow",),
            "commercial_payments_dispute_workflows": ("def _replace_dispute_chargeback_lifecycle_task_workflow",),
            "commercial_payments_payout_workflows": ("def _replace_payout_settlement_reconciliation_task_workflow",),
            "commercial_metrics_workflows": ("def _replace_metric_reporting_reconciliation_task_workflow",),
            "commercial_billing_subscription_workflows": ("def _replace_subscription_entitlement_billing_task_workflow",),
            "commercial_billing_usage_workflows": ("def _replace_usage_quota_metering_task_workflow",),
            "commercial_billing_tax_workflows": ("def _replace_tax_calculation_compliance_task_workflow",),
        },
        facade_exports=(
            "_replace_payment_webhook_ledger_task_workflow as _replace_payment_webhook_ledger_task_workflow",
            "_replace_metric_reporting_reconciliation_task_workflow as _replace_metric_reporting_reconciliation_task_workflow",
            "_replace_usage_quota_metering_task_workflow as _replace_usage_quota_metering_task_workflow",
        ),
    )
    for export_marker in (
        "_replace_payment_webhook_ledger_task_workflow as _replace_payment_webhook_ledger_task_workflow",
        "_replace_dispute_chargeback_lifecycle_task_workflow as _replace_dispute_chargeback_lifecycle_task_workflow",
        "_replace_payout_settlement_reconciliation_task_workflow as _replace_payout_settlement_reconciliation_task_workflow",
    ):
        assert export_marker in sources["commercial_payments_workflows"]
    for export_marker in (
        "_replace_subscription_entitlement_billing_task_workflow as _replace_subscription_entitlement_billing_task_workflow",
        "_replace_usage_quota_metering_task_workflow as _replace_usage_quota_metering_task_workflow",
        "_replace_tax_calculation_compliance_task_workflow as _replace_tax_calculation_compliance_task_workflow",
    ):
        assert export_marker in sources["commercial_billing_workflows"]


def _assert_trust_task_workflow_shape_boundaries(sources: dict[str, str]) -> None:
    _assert_partitioned_workflow_markers(
        sources,
        facade_key="trust_workflows",
        partition_keys=_ALL_WORKFLOW_SHAPE_SOURCE_KEYS,
        marker_groups={
            "trust_governance_data_residency_workflows": ("def _replace_data_residency_task_workflow",),
            "trust_governance_kyc_aml_workflows": ("def _replace_kyc_aml_screening_task_workflow",),
            "trust_access_breakglass_workflows": ("def _replace_support_impersonation_task_workflow",),
            "trust_access_identity_sso_workflows": ("def _replace_identity_sso_task_workflow",),
            "trust_access_identity_session_workflows": ("def _replace_auth_session_token_lifecycle_task_workflow",),
            "trust_access_authorization_workflows": ("def _replace_authorization_policy_task_workflow",),
            "trust_secrets_key_rotation_workflows": ("def _replace_key_rotation_task_workflow",),
            "trust_secrets_prompt_asset_workflows": ("def _replace_prompt_asset_ownership_task_workflow",),
        },
        facade_exports=(
            "_replace_data_residency_task_workflow as _replace_data_residency_task_workflow",
            "_replace_support_impersonation_task_workflow as _replace_support_impersonation_task_workflow",
            "_replace_key_rotation_task_workflow as _replace_key_rotation_task_workflow",
        ),
    )
    for export_marker in (
        "_replace_data_residency_task_workflow as _replace_data_residency_task_workflow",
        "_replace_kyc_aml_screening_task_workflow as _replace_kyc_aml_screening_task_workflow",
    ):
        assert export_marker in sources["trust_governance_workflows"]
    for export_marker in (
        "_replace_key_rotation_task_workflow as _replace_key_rotation_task_workflow",
        "_replace_prompt_asset_ownership_task_workflow as _replace_prompt_asset_ownership_task_workflow",
    ):
        assert export_marker in sources["trust_secrets_workflows"]
    for export_marker in (
        "_replace_authorization_policy_task_workflow as _replace_authorization_policy_task_workflow",
        "_replace_support_impersonation_task_workflow as _replace_support_impersonation_task_workflow",
        "_replace_auth_session_token_lifecycle_task_workflow as _replace_auth_session_token_lifecycle_task_workflow",
        "_replace_identity_sso_task_workflow as _replace_identity_sso_task_workflow",
    ):
        assert export_marker in sources["trust_access_workflows"]
    for export_marker in (
        "_replace_auth_session_token_lifecycle_task_workflow as _replace_auth_session_token_lifecycle_task_workflow",
        "_replace_identity_sso_task_workflow as _replace_identity_sso_task_workflow",
    ):
        assert export_marker in sources["trust_access_identity_workflows"]


_COMMERCIAL_BILLING_BODY_KEYS = ("commercial_billing_subscription_workflows", "commercial_billing_tax_workflows", "commercial_billing_usage_workflows")
_COMMERCIAL_PAYMENTS_BODY_KEYS = ("commercial_payments_dispute_workflows", "commercial_payments_payout_workflows", "commercial_payments_webhook_workflows")
_COMMERCIAL_BODY_KEYS = (*_COMMERCIAL_BILLING_BODY_KEYS, "commercial_metrics_workflows", *_COMMERCIAL_PAYMENTS_BODY_KEYS)
_DATA_INGEST_BODY_KEYS = ("data_ingest_import_workflows", "data_ingest_upload_workflows")
_DATA_LIFECYCLE_BODY_KEYS = ("data_lifecycle_deletion_workflows", "data_lifecycle_dsar_workflows")
_DATA_MIGRATION_BODY_KEYS = ("data_migration_cdc_workflows", "data_migration_schema_workflows")
_DATA_RESILIENCE_BODY_KEYS = ("data_resilience_audit_workflows", "data_resilience_backup_workflows")
_DATA_BODY_KEYS = (*_DATA_INGEST_BODY_KEYS, *_DATA_LIFECYCLE_BODY_KEYS, *_DATA_MIGRATION_BODY_KEYS, *_DATA_RESILIENCE_BODY_KEYS)
_OPERATIONS_RELEASE_BODY_KEYS = ("operations_release_cache_workflows", "operations_release_flag_workflows")
_OPERATIONS_BODY_KEYS = ("operations_collaboration_workflows", "operations_incident_workflows", *_OPERATIONS_RELEASE_BODY_KEYS)
_PRODUCT_ENGAGEMENT_BODY_KEYS = ("product_engagement_notification_workflows", "product_engagement_schedule_workflows", "product_engagement_support_workflows")
_PRODUCT_OPERATIONS_BODY_KEYS = ("product_operations_analytics_workflows", "product_operations_inventory_workflows")
_PRODUCT_SEARCH_AI_BODY_KEYS = ("product_search_ai_index_workflows", "product_search_ai_quality_workflows", "product_search_ai_rag_workflows")
_PRODUCT_BODY_KEYS = (*_PRODUCT_ENGAGEMENT_BODY_KEYS, *_PRODUCT_OPERATIONS_BODY_KEYS, *_PRODUCT_SEARCH_AI_BODY_KEYS)
_TRUST_ACCESS_IDENTITY_BODY_KEYS = ("trust_access_identity_session_workflows", "trust_access_identity_sso_workflows")
_TRUST_ACCESS_BODY_KEYS = ("trust_access_authorization_workflows", "trust_access_breakglass_workflows", *_TRUST_ACCESS_IDENTITY_BODY_KEYS)
_TRUST_GOVERNANCE_BODY_KEYS = ("trust_governance_data_residency_workflows", "trust_governance_kyc_aml_workflows")
_TRUST_SECRETS_BODY_KEYS = ("trust_secrets_key_rotation_workflows", "trust_secrets_prompt_asset_workflows")
_TRUST_BODY_KEYS = (*_TRUST_ACCESS_BODY_KEYS, *_TRUST_GOVERNANCE_BODY_KEYS, *_TRUST_SECRETS_BODY_KEYS)
# fmt: off
_DOMAIN_FACADE_KEYS = (
    "commercial_billing_workflows", "commercial_workflows", "commercial_payments_workflows",
    "data_workflows", "data_ingest_workflows", "data_lifecycle_workflows", "data_migration_workflows", "data_resilience_workflows",
    "operations_workflows", "operations_release_workflows", "product_engagement_workflows", "product_operations_workflows", "product_search_ai_workflows",
    "product_workflows", "trust_workflows", "trust_access_workflows", "trust_access_identity_workflows", "trust_governance_workflows", "trust_secrets_workflows",
)
# fmt: on
_DOMAIN_BODY_KEYS = (*_COMMERCIAL_BODY_KEYS, *_DATA_BODY_KEYS, *_OPERATIONS_BODY_KEYS, *_PRODUCT_BODY_KEYS, *_TRUST_BODY_KEYS)
_ALL_WORKFLOW_SHAPE_SOURCE_KEYS = ("workflows", *_DOMAIN_FACADE_KEYS, *_DOMAIN_BODY_KEYS)
_TASK_WORKFLOW_BODY_SOURCE_KEYS = ("workflows", *_DOMAIN_BODY_KEYS)
_TASK_WORKFLOW_HELPERLESS_BODY_KEYS = (
    "product_engagement_schedule_workflows",
    "product_search_ai_quality_workflows",
    "product_search_ai_rag_workflows",
)
_TASK_WORKFLOW_HELPER_SOURCE_KEYS = tuple(source_key for source_key in _TASK_WORKFLOW_BODY_SOURCE_KEYS if source_key not in _TASK_WORKFLOW_HELPERLESS_BODY_KEYS)
_TASK_WORKFLOW_SOURCE_KEYS = (*_DOMAIN_FACADE_KEYS, *_TASK_WORKFLOW_BODY_SOURCE_KEYS)


def _assert_task_workflow_prose_boundaries(sources: dict[str, str]) -> None:
    _assert_task_workflow_intent_imports(sources)
    _assert_task_workflow_visible_scaffold_imports(sources)
    _assert_task_workflow_visible_scaffold_exports(sources)
    _assert_task_workflow_visible_scaffold_body_boundaries(sources)
    _assert_task_workflow_intent_boundaries(sources)
    _assert_task_workflow_role_and_routing_boundaries(sources)


def _assert_task_workflow_intent_imports(sources: dict[str, str]) -> None:
    intent_import = "from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents"
    for source_key in _TASK_WORKFLOW_BODY_SOURCE_KEYS:
        assert intent_import in sources[source_key]
    for source_key in _DOMAIN_FACADE_KEYS:
        assert intent_import not in sources[source_key]


def _assert_task_workflow_visible_scaffold_imports(sources: dict[str, str]) -> None:
    shared_visible_import = "from loopora.executor_alignment_bundle_task_visible_scaffolds import"
    for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
        assert shared_visible_import not in sources[source_key]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import" in sources["commercial_payments_dispute_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import" in sources["commercial_payments_payout_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import" not in sources["commercial_payments_webhook_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import" not in sources["commercial_payments_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import" in sources["commercial_metrics_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import" not in sources["commercial_billing_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import" not in sources["commercial_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" in sources["product_engagement_schedule_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_engagement_notification_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_engagement_support_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_engagement_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_operations_analytics_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_operations_inventory_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_operations_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_search_ai_index_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_search_ai_quality_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_search_ai_rag_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_search_ai_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_product import" not in sources["product_workflows"]
    trust_visible_import = "from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import"
    for source_key in (
        "trust_access_breakglass_workflows",
        "trust_governance_data_residency_workflows",
        "trust_governance_kyc_aml_workflows",
        "trust_secrets_key_rotation_workflows",
    ):
        assert trust_visible_import in sources[source_key]
    for source_key in ("trust_access_authorization_workflows", "trust_access_identity_workflows", "trust_secrets_prompt_asset_workflows"):
        assert trust_visible_import not in sources[source_key]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import" not in sources["trust_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import" not in sources["trust_access_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import" not in sources["trust_governance_workflows"]
    assert "from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import" not in sources["trust_secrets_workflows"]


def _assert_task_workflow_visible_scaffold_exports(sources: dict[str, str]) -> None:
    for marker in (
        "_replace_metric_reporting_reconciliation_visible_scaffold as _replace_metric_reporting_reconciliation_visible_scaffold",
        "_replace_schedule_phase_visible_scaffold as _replace_schedule_phase_visible_scaffold",
        "_replace_data_residency_visible_scaffold as _replace_data_residency_visible_scaffold",
    ):
        assert marker in sources["visible"]


def _assert_task_workflow_visible_scaffold_body_boundaries(sources: dict[str, str]) -> None:
    for marker in (
        "def _replace_data_residency_visible_scaffold",
        "def _replace_support_impersonation_visible_scaffold",
        "def _replace_kyc_aml_screening_visible_scaffold",
        "def _replace_key_rotation_visible_scaffold",
    ):
        assert marker in sources["trust_visible"]
        assert marker not in sources["visible"]
        for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
            assert marker not in sources[source_key]
        assert marker not in sources["variants"]
    for marker in (
        "def _replace_metric_reporting_reconciliation_visible_scaffold",
        "def _replace_dispute_chargeback_visible_scaffold",
        "def _replace_payout_settlement_visible_scaffold",
    ):
        assert marker in sources["commercial_visible"]
        assert marker not in sources["visible"]
        for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
            assert marker not in sources[source_key]
        assert marker not in sources["variants"]
    assert "def _replace_schedule_phase_visible_scaffold" in sources["product_visible"]
    assert "def _replace_schedule_phase_visible_scaffold" not in sources["trust_visible"]
    assert "def _replace_schedule_phase_visible_scaffold" not in sources["commercial_visible"]
    for marker in ("def _replace_schedule_phase_visible_scaffold",):
        assert marker not in sources["visible"]
        for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
            assert marker not in sources[source_key]
        assert marker not in sources["variants"]
    for marker in (
        'bundle["metadata"]["name"]',
        'bundle["collaboration_summary"]',
        'bundle["spec"]["markdown"]',
    ):
        assert marker not in sources["visible"] + sources["commercial_visible"] + sources["product_visible"] + sources["trust_visible"]
        for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
            assert marker not in sources[source_key]
    assert "apply_task_visible_scaffold_template_from_asset" in sources["commercial_visible"]
    assert "apply_task_visible_scaffold_from_asset" in sources["product_visible"] + sources["trust_visible"]


def _assert_task_workflow_intent_boundaries(sources: dict[str, str]) -> None:
    for marker in (
        "TASK_WORKFLOW_INTENT_REPLACERS",
        '"_replace_generic_task_evidence_repair_workflow_intent"',
        '"_replace_payment_webhook_ledger_task_workflow_intent"',
        '"_replace_metric_reporting_reconciliation_task_workflow_intent"',
        '"_replace_dispute_chargeback_lifecycle_task_workflow_intent"',
        '"_replace_rag_long_chain_task_workflow_intent"',
        'workflow["collaboration_intent"]',
        "task-workflow-intents.json",
    ):
        assert marker in sources["intents"]
        for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
            assert marker not in sources[source_key]
        assert marker not in sources["variants"]


def _assert_task_workflow_role_and_routing_boundaries(sources: dict[str, str]) -> None:
    for source_key in _TASK_WORKFLOW_SOURCE_KEYS:
        assert "from loopora.executor_alignment_bundle_task_routing import" not in sources[source_key]
        assert "def _replace_task_role_definitions_from_asset" not in sources[source_key]


def _assert_task_workflow_design_inventory(sources: dict[str, str]) -> None:
    # fmt: off
    workflow_module_suffixes = (
        "commercial", "commercial_billing", "commercial_billing_subscription", "commercial_billing_tax", "commercial_billing_usage",
        "commercial_metrics", "commercial_payments", "commercial_payments_dispute", "commercial_payments_payout", "commercial_payments_webhook",
        "data", "data_ingest", "data_ingest_import", "data_ingest_upload", "data_lifecycle", "data_lifecycle_deletion", "data_lifecycle_dsar", "data_migration", "data_migration_cdc", "data_migration_schema",
        "data_resilience", "data_resilience_audit", "data_resilience_backup",
        "operations", "operations_collaboration", "operations_incident", "operations_release", "operations_release_cache", "operations_release_flag",
        "product", "product_engagement", "product_engagement_notification", "product_engagement_schedule", "product_engagement_support",
        "product_operations", "product_operations_analytics", "product_operations_inventory",
        "product_search_ai", "product_search_ai_index", "product_search_ai_quality", "product_search_ai_rag",
        "trust", "trust_access", "trust_access_authorization", "trust_access_breakglass", "trust_access_identity", "trust_access_identity_session", "trust_access_identity_sso",
        "trust_governance", "trust_governance_data_residency", "trust_governance_kyc_aml", "trust_secrets",
        "trust_secrets_key_rotation", "trust_secrets_prompt_asset",
    )
    # fmt: on
    for module_name in (
        "executor_alignment_bundle_task_workflow_dispatch.py",
        "executor_alignment_bundle_task_workflows.py",
        *(f"executor_alignment_bundle_task_workflows_{suffix}.py" for suffix in workflow_module_suffixes),
        "executor_alignment_bundle_task_workflow_helpers.py",
        "executor_alignment_bundle_task_workflow_intents.py",
        "task-workflow-intents.json",
        "executor_alignment_bundle_task_visible_scaffolds.py",
        "executor_alignment_bundle_task_visible_scaffolds_commercial.py",
        "executor_alignment_bundle_task_visible_scaffolds_product.py",
        "executor_alignment_bundle_task_visible_scaffolds_trust.py",
        "executor_alignment_bundle_task_visible_scaffold_assets.py",
        "task-visible-scaffolds.json",
    ):
        assert module_name in sources["contracts"]
        assert module_name in sources["service_boundaries"]
