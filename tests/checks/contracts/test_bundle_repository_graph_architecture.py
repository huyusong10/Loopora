from __future__ import annotations

from bundle_service_architecture_test_support import design_contracts_source, loopora_source


def test_repository_bundle_graph_records_have_dedicated_boundary() -> None:
    bundle_source = loopora_source("db_bundle_records.py")
    graph_source = loopora_source("db_bundle_graph_records.py")
    contracts_source = design_contracts_source()

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
