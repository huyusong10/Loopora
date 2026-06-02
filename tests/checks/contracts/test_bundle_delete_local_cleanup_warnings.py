from __future__ import annotations

import logging
from pathlib import Path

from bundle_lifecycle_test_support import _bundle_yaml, _has_cleanup_record
from loopora.settings import configure_logging
import loopora.service_cleanup_diagnostics as cleanup_diagnostics


def test_bundle_delete_logs_noncritical_managed_dir_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_rmtree = cleanup_diagnostics.shutil.rmtree

    def fail_bundle_dir_rmtree(path: Path) -> None:
        if Path(path).name == imported["id"]:
            raise OSError("forced managed dir cleanup failure")
        original_rmtree(path)

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_bundle_dir_rmtree)
    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"):
        deleted = service.delete_bundle(imported["id"])

    assert deleted["id"] == imported["id"]
    assert deleted["deleted"] is True
    assert deleted["local_cleanup"] == "partial_failed"
    assert deleted["cleanup_warnings"][0]["operation"] == "bundle_managed_dir_delete"
    assert "forced managed dir cleanup failure" in deleted["cleanup_warnings"][0]["error"]
    assert _has_cleanup_record(
        caplog,
        operation="bundle_managed_dir_delete",
        resource_type="path",
        owner_id=imported["id"],
    )


def test_bundle_delete_reports_linked_artifact_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    artifact_dir = tmp_path / "artifact-copy"
    artifact_dir.mkdir()
    original_rmtree = cleanup_diagnostics.shutil.rmtree

    def fake_preflight(bundle: dict, *, links) -> list[Path]:
        assert bundle["id"] == imported["id"]
        assert links is not None
        return [artifact_dir]

    def fail_artifact_rmtree(path: Path) -> None:
        if Path(path) == artifact_dir:
            raise OSError("forced linked artifact cleanup failure")
        original_rmtree(path)

    monkeypatch.setattr(service, "_preflight_bundle_graph_delete", fake_preflight)
    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_artifact_rmtree)
    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"):
        deleted = service.delete_bundle(imported["id"])

    assert deleted["id"] == imported["id"]
    assert deleted["deleted"] is True
    assert deleted["local_cleanup"] == "partial_failed"
    assert deleted["cleanup_warnings"][0]["operation"] == "bundle_link_artifact_delete"
    assert deleted["cleanup_warnings"][0]["resource_id"] == str(artifact_dir)
    assert "forced linked artifact cleanup failure" in deleted["cleanup_warnings"][0]["error"]
    assert _has_cleanup_record(
        caplog,
        operation="bundle_link_artifact_delete",
        resource_type="path",
        owner_id=imported["id"],
    )
