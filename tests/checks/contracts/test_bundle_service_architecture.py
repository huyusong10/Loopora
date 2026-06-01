from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _loopora_source(*parts: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / Path(*parts)).read_text(encoding="utf-8")


def test_bundle_asset_snapshot_sync_has_dedicated_boundary() -> None:
    service_bundle_assets_source = _loopora_source("service_bundle_assets.py")
    snapshot_source = _loopora_source("service_bundle_loop_snapshot.py")
    projection_source = _loopora_source("service_bundle_projection.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_bundle_loop_snapshot import ServiceBundleLoopSnapshotMixin" in service_bundle_assets_source
    assert "from loopora.service_bundle_projection import ServiceBundleProjectionMixin" in service_bundle_assets_source
    for marker in (
        "def _sync_bundle_loop_snapshot",
        "def _build_bundle_loop_snapshot",
        "def _apply_bundle_loop_snapshot",
        "def _resolve_bundle_orchestration_for_snapshot",
        "def _persist_refreshed_bundle_orchestration",
        "def _refresh_bundle_role_snapshots",
    ):
        assert marker in snapshot_source
        assert marker not in service_bundle_assets_source
    assert all(marker in projection_source and marker not in service_bundle_assets_source for marker in ("def _bundle_preview_payload", "def _bundle_governance_summary", "def _bundle_revision_summary"))
    assert "with_coverage_targets" in snapshot_source and "with_coverage_targets" not in service_bundle_assets_source
    assert "STRATEGY_ROLE_EXECUTION_FIELDS" in snapshot_source and "STRATEGY_ROLE_EXECUTION_FIELDS" not in service_bundle_assets_source
    assert "service_bundle_loop_snapshot.py" in contracts_source and "service_bundle_projection.py" in contracts_source


def test_bundle_asset_export_has_dedicated_boundary() -> None:
    service_bundle_assets_source = _loopora_source("service_bundle_assets.py")
    export_source = _loopora_source("service_bundle_export.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_bundle_export import BundleDeriveRequest, ServiceBundleExportMixin" in service_bundle_assets_source
    assert all(marker in export_source and marker not in service_bundle_assets_source for marker in ("class BundleDeriveRequest", "def export_bundle", "def derive_bundle_from_loop", "def _sync_bundle_yaml"))
    assert "LoopfileExportProjectionInput" in export_source and "LoopfileExportProjectionInput" not in service_bundle_assets_source
    assert "service_bundle_export.py" in contracts_source


def test_bundle_asset_import_lifecycle_has_dedicated_boundary() -> None:
    service_bundle_assets_source = _loopora_source("service_bundle_assets.py")
    import_source = _loopora_source("service_bundle_import.py")
    import_cleanup_source = _loopora_source("service_bundle_import_cleanup.py")
    delete_source = _loopora_source("service_bundle_delete.py")
    links_source = _loopora_source("service_bundle_links.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_bundle_import import" in service_bundle_assets_source
    assert "from loopora.service_bundle_delete import ServiceBundleDeleteMixin" in service_bundle_assets_source
    assert "from loopora.service_bundle_links import ServiceBundleLinksMixin" in service_bundle_assets_source
    for marker in (
        "def _import_normalized_bundle",
        "def _prepare_bundle_import_target",
        "def _write_imported_bundle_spec",
        "def _create_imported_bundle_roles",
        "def _create_imported_bundle_loop",
    ):
        assert marker in import_source
        assert marker not in service_bundle_assets_source
    for marker in (
        "class BundleImportTarget",
        "class BundleImportRollbackState",
        "def _rollback_failed_bundle_import",
        "def _cleanup_created_bundle_assets",
        "def _restore_bundle_dir_after_failed_import",
    ):
        assert marker in import_cleanup_source
        assert marker not in service_bundle_assets_source
        assert marker not in import_source
    assert "ServiceBundleImportCleanupMixin" in import_source
    assert "bundle_replaced_artifact_delete" in import_cleanup_source
    assert "bundle_import_rollback" in import_cleanup_source
    assert all(marker in delete_source and marker not in service_bundle_assets_source for marker in ("def delete_bundle", "def _delete_bundle_links", "def _record_bundle_cleanup_failure"))
    assert all(marker in links_source and marker not in service_bundle_assets_source for marker in ("def _hydrate_bundle_links", "def _bundle_record_for_loop_id", "def _touch_bundle_for_orchestration"))
    assert "BundleImportTarget" in service_bundle_assets_source and '"BundleImportTarget"' in service_bundle_assets_source
    assert all(marker in contracts_source for marker in ("service_bundle_import.py", "service_bundle_import_cleanup.py", "service_bundle_delete.py", "service_bundle_links.py"))


def test_bundle_yaml_facade_keeps_normalization_boundaries_split() -> None:
    bundles_source = _loopora_source("bundles.py")
    contract_source = _loopora_source("bundle_contract.py")
    loop_source = _loopora_source("bundle_loop_settings.py")
    role_source = _loopora_source("bundle_role_definitions.py")
    workflow_source = _loopora_source("bundle_workflow_normalization.py")
    normalization_source = _loopora_source("bundle_normalization.py")
    io_source = _loopora_source("bundle_io.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.bundle_contract import" in bundles_source
    assert "from loopora.bundle_io import" in bundles_source
    assert "from loopora.bundle_normalization import normalize_bundle" in bundles_source
    assert "class BundleError" in contract_source and "class BundleError" not in bundles_source
    assert "def normalize_bundle_identifier" in contract_source and "def normalize_bundle_identifier" not in bundles_source
    assert "def _normalize_bundle_loop_execution" in loop_source and "def _normalize_bundle_loop_execution" not in bundles_source
    assert "def _normalize_bundle_role_definition" in role_source and "def _normalize_bundle_role_definition" not in bundles_source
    assert "def _normalize_bundle_workflow_step_payload" in workflow_source and "def _normalize_bundle_workflow_step_payload" not in bundles_source
    assert "def normalize_bundle" in normalization_source and "def normalize_bundle" not in bundles_source
    assert all(marker in io_source and marker not in bundles_source for marker in ("def read_bundle_file_text", "def load_bundle_text", "def bundle_to_yaml"))
    assert all(
        marker in contracts_source
        for marker in (
            "bundle_contract.py",
            "bundle_loop_settings.py",
            "bundle_role_definitions.py",
            "bundle_workflow_normalization.py",
            "bundle_normalization.py",
            "bundle_io.py",
        )
    )


def test_bundle_semantic_lint_has_dedicated_rule_boundaries() -> None:
    lint_source = _loopora_source("bundle_semantic_lint.py")
    bundle_source = _loopora_source("bundle_semantic_bundle.py")
    generation_source = _loopora_source("bundle_semantic_generation.py")
    spec_source = _loopora_source("bundle_semantic_spec.py")
    text_source = _loopora_source("bundle_semantic_text.py")
    role_source = _loopora_source("bundle_semantic_roles.py")
    workflow_source = _loopora_source("bundle_semantic_workflow.py")
    gatekeeper_source = _loopora_source("bundle_semantic_workflow_gatekeeper.py")
    workflow_memory_source = _loopora_source("bundle_semantic_workflow_memory.py")
    workflow_support_source = _loopora_source("bundle_semantic_workflow_support.py")
    bundles_source = _loopora_source("bundles.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "def lint_alignment_bundle_semantics" in lint_source
    assert "def lint_alignment_bundle_generation_text" in generation_source and "def lint_alignment_bundle_generation_text" not in lint_source
    assert "from loopora.bundle_semantic_generation import" in lint_source
    assert "from loopora.bundle_semantic_lint import" in bundles_source
    assert "from loopora.bundle_semantic_bundle import" in lint_source
    assert "from loopora.bundle_semantic_roles import" in lint_source
    assert "from loopora.bundle_semantic_spec import" in lint_source
    assert "from loopora.bundle_semantic_text import" not in lint_source
    assert "from loopora.bundle_semantic_text import" in bundle_source
    assert "from loopora.bundle_semantic_text import" in spec_source
    assert "from loopora.bundle_semantic_text import" in workflow_source
    assert "from loopora.bundle_semantic_workflow import" in lint_source
    assert "from loopora.bundle_semantic_workflow_gatekeeper import" in lint_source
    assert "from loopora.bundle_semantic_workflow_memory import" in lint_source
    assert "from loopora.bundle_semantic_workflow_support import" in lint_source
    assert all(marker in text_source and marker not in lint_source for marker in ("def _semantic_text_mentions_personality_memory_antipattern", "def _semantic_text_mentions_workflow_judgment_flow"))
    assert "def _lint_alignment_collaboration_summary" in bundle_source and "def _lint_alignment_collaboration_summary" not in lint_source
    assert "def _lint_alignment_spec_semantics" in spec_source and "def _lint_alignment_spec_semantics" not in lint_source
    assert "def _lint_alignment_parallel_review_inputs" in workflow_source and "def _lint_alignment_parallel_review_inputs" not in lint_source
    assert "def _lint_alignment_gatekeeper_semantics" in gatekeeper_source and "def _lint_alignment_gatekeeper_semantics" not in workflow_source
    assert "def _lint_alignment_role_semantics" in role_source and "def _lint_alignment_role_semantics" not in workflow_source
    assert "def _lint_alignment_iteration_memory_inputs" in workflow_memory_source and "def _lint_alignment_iteration_memory_inputs" not in workflow_source
    assert "def _review_steps_since_latest_builder" in workflow_support_source and "def _review_steps_since_latest_builder" not in workflow_source
    assert "bundle_semantic_*.py" in contracts_source


def test_bundle_control_local_governance_trace_has_dedicated_rule_boundary() -> None:
    trace_mining_source = _loopora_source("service_bundle_control_trace_mining.py")
    local_governance_source = _loopora_source("service_bundle_control_local_governance.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_bundle_control_local_governance import" in trace_mining_source
    assert "def select_local_governance_trace" in local_governance_source
    assert "def local_governance_trace_priority" in local_governance_source
    assert "LOCAL_GOVERNANCE_MARKER_PATTERN" in local_governance_source
    assert "_LOCAL_GOVERNANCE_MARKER_PATTERN" not in trace_mining_source
    assert "service_bundle_control_local_governance.py" in contracts_source


def test_bundle_control_diagnostics_have_split_input_boundary() -> None:
    diagnostics_source = _loopora_source("service_bundle_control_diagnostics.py")
    input_diagnostics_source = _loopora_source("service_bundle_control_input_diagnostics.py")
    input_state_source = _loopora_source("service_bundle_control_input_state.py")
    entries_source = _loopora_source("service_bundle_control_diagnostic_entries.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_bundle_control_input_diagnostics import append_strategy_input_diagnostics" in diagnostics_source
    assert "from loopora.service_bundle_control_diagnostic_entries import" in diagnostics_source
    assert "from loopora.service_bundle_control_diagnostic_entries import" in input_diagnostics_source
    assert "from loopora.service_bundle_control_input_state import" in input_diagnostics_source
    for marker in (
        "def append_strategy_input_diagnostics",
        "def _diagnose_gatekeeper_parallel_review_fan_in",
    ):
        assert marker in input_diagnostics_source
        assert marker not in diagnostics_source
    for marker in (
        "def initial_strategy_input_diagnostic_state",
        "def advance_strategy_diagnostic_state",
        "def input_missing_handoffs",
        "def input_queries_any_archetype",
    ):
        assert marker in input_state_source
        assert marker not in input_diagnostics_source
        assert marker not in diagnostics_source
    for marker in ("def build_bundle_control_diagnostics", "def _append_traceability_diagnostics"):
        assert marker in diagnostics_source
        assert marker not in input_diagnostics_source
    assert "def append_bundle_control_diagnostic" in entries_source
    assert "def _append_diagnostic" not in diagnostics_source
    assert "service_bundle_control_input_diagnostics.py" in contracts_source
    assert "service_bundle_control_input_state.py" in contracts_source
    assert "service_bundle_control_diagnostic_entries.py" in contracts_source


def test_bundle_control_trace_mining_has_split_input_and_pattern_boundaries() -> None:
    traces_source = _loopora_source("service_bundle_control_traces.py")
    trace_mining_source = _loopora_source("service_bundle_control_trace_mining.py")
    trace_projection_source = _loopora_source("service_bundle_control_trace_projection.py")
    trace_inputs_source = _loopora_source("service_bundle_control_trace_inputs.py")
    trace_patterns_source = _loopora_source("service_bundle_control_trace_patterns.py")
    trace_preview_source = _loopora_source("service_bundle_control_trace_preview.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_bundle_control_trace_inputs import" in trace_mining_source
    assert "from loopora.service_bundle_control_trace_patterns import" in trace_mining_source
    assert "from loopora.service_bundle_control_trace_preview import" in trace_mining_source
    assert "from loopora.service_bundle_control_trace_preview import" in traces_source
    assert "from loopora.service_bundle_control_trace_projection import" in traces_source
    for marker in ("class TraceTextSource", "def trace_text_candidates", "def strategy_source_payload"):
        assert marker in trace_inputs_source
        assert marker not in trace_mining_source
    for marker in ("TRADEOFF_PATTERNS = (", "EXECUTION_STRATEGY_PATTERNS = ("):
        assert marker in trace_patterns_source
        assert marker not in trace_mining_source
    for marker in ("def preview_list_items", "def build_role_posture_trace", "def role_posture_preview"):
        assert marker in trace_preview_source
        assert marker not in trace_mining_source
    for marker in ("def append_trace_item", "def coverage_trace", "def gatekeeper_trace", "def control_trace"):
        assert marker in trace_projection_source
        assert marker not in traces_source
    assert "def _judgment_tradeoff_trace" in trace_mining_source
    assert "def _judgment_tradeoff_trace" not in trace_inputs_source
    assert "service_bundle_control_trace_inputs.py" in contracts_source
    assert "service_bundle_control_trace_patterns.py" in contracts_source
    assert "service_bundle_control_trace_preview.py" in contracts_source
    assert "service_bundle_control_trace_projection.py" in contracts_source


def test_repository_bundle_graph_records_have_dedicated_boundary() -> None:
    bundle_source = _loopora_source("db_bundle_records.py")
    graph_source = _loopora_source("db_bundle_graph_records.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.db_bundle_graph_records import RepositoryBundleGraphRecordsMixin" in bundle_source
    assert "class RepositoryBundleRecordsMixin(RepositoryBundleGraphRecordsMixin)" in bundle_source
    for marker in (
        "def delete_bundle_graph",
        "def replace_bundle_graph",
        "def _delete_owned_asset_rows_for_connection",
    ):
        assert marker in graph_source
        assert marker not in bundle_source
    for marker in ("def create_bundle", "def update_bundle", "def list_bundles"):
        assert marker in bundle_source
        assert marker not in graph_source
    assert "db_bundle_graph_records.py" in contracts_source
