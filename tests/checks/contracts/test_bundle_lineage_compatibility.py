from __future__ import annotations

from pathlib import Path

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.bundles import bundle_to_yaml


def test_legacy_bundle_lineage_metadata_imports_but_new_exports_omit_lineage(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = service.import_bundle_text(_bundle_yaml(sample_workdir))
    legacy_yaml = (
        _bundle_yaml(
            sample_workdir,
            collaboration_summary="Prefer stronger evidence coverage before revising again.",
        )
        .replace(
            'metadata:\n  name: "Guided Inspect First"\n  description: "Bundle created from task-scoped alignment."',
            "metadata:\n"
            '  name: "Guided Inspect First Revision"\n'
            '  description: "Bundle revision with tighter evidence language."\n'
            f'  source_bundle_id: "{source["id"]}"\n'
            f"  revision: {source['revision'] + 1}",
        )
        .replace(
            "- The implementation stays maintainable for the next round.",
            "- The implementation stays maintainable for the next round.\n            - Evidence coverage is visible before another revision starts.",
        )
    )
    imported = service.import_bundle_text(legacy_yaml)
    exported_yaml = bundle_to_yaml(service.export_bundle(imported["id"]))
    summary = service.get_bundle_revision_summary(imported["id"])

    assert imported["source_bundle_id"] == ""
    assert imported["revision"] == 1
    assert "source_bundle_id" not in exported_yaml
    assert "revision:" not in exported_yaml
    assert summary["lineage_state"] == "not_tracked"
    assert summary["source_bundle_id"] == ""
    assert summary["can_compare"] is False
    assert summary["surface_deltas"] == []
