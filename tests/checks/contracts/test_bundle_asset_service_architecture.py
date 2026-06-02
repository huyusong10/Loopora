from __future__ import annotations

from bundle_service_architecture_test_support import design_contracts_source, loopora_source


def test_bundle_asset_snapshot_sync_has_dedicated_boundary() -> None:
    service_bundle_assets_source = loopora_source("service_bundle_assets.py")
    snapshot_source = loopora_source("service_bundle_loop_snapshot.py")
    projection_source = loopora_source("service_bundle_projection.py")
    contracts_source = design_contracts_source()

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
    for marker in ("def _bundle_preview_payload", "def _bundle_governance_summary", "def _bundle_revision_summary"):
        assert marker in projection_source
        assert marker not in service_bundle_assets_source
    assert "with_coverage_targets" in snapshot_source
    assert "with_coverage_targets" not in service_bundle_assets_source
    assert "STRATEGY_ROLE_EXECUTION_FIELDS" in snapshot_source
    assert "STRATEGY_ROLE_EXECUTION_FIELDS" not in service_bundle_assets_source
    assert "service_bundle_loop_snapshot.py" in contracts_source
    assert "service_bundle_projection.py" in contracts_source


def test_bundle_asset_export_has_dedicated_boundary() -> None:
    service_bundle_assets_source = loopora_source("service_bundle_assets.py")
    export_source = loopora_source("service_bundle_export.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_bundle_export import BundleDeriveRequest, ServiceBundleExportMixin" in service_bundle_assets_source
    for marker in ("class BundleDeriveRequest", "def export_bundle", "def derive_bundle_from_loop", "def _sync_bundle_yaml"):
        assert marker in export_source
        assert marker not in service_bundle_assets_source
    assert "LoopfileExportProjectionInput" in export_source
    assert "LoopfileExportProjectionInput" not in service_bundle_assets_source
    assert "service_bundle_export.py" in contracts_source


def test_bundle_asset_import_lifecycle_has_dedicated_boundary() -> None:
    service_bundle_assets_source = loopora_source("service_bundle_assets.py")
    import_source = loopora_source("service_bundle_import.py")
    import_cleanup_source = loopora_source("service_bundle_import_cleanup.py")
    delete_source = loopora_source("service_bundle_delete.py")
    links_source = loopora_source("service_bundle_links.py")
    contracts_source = design_contracts_source()

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
    for marker in ("def delete_bundle", "def _delete_bundle_links", "def _record_bundle_cleanup_failure"):
        assert marker in delete_source
        assert marker not in service_bundle_assets_source
    for marker in ("def _hydrate_bundle_links", "def _bundle_record_for_loop_id", "def _touch_bundle_for_orchestration"):
        assert marker in links_source
        assert marker not in service_bundle_assets_source
    assert "BundleImportTarget" in service_bundle_assets_source
    assert '"BundleImportTarget"' in service_bundle_assets_source
    for marker in (
        "service_bundle_import.py",
        "service_bundle_import_cleanup.py",
        "service_bundle_delete.py",
        "service_bundle_links.py",
    ):
        assert marker in contracts_source
