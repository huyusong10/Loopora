from __future__ import annotations

import json
import logging
from pathlib import Path

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.settings import app_home, configure_logging
import loopora.service_cleanup_diagnostics as cleanup_diagnostics


def test_bundle_replace_updates_plan_without_advancing_revision(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))

    revised = service.import_bundle_text(
        _bundle_yaml(
            sample_workdir,
            collaboration_summary="Prefer maintainability over shallow pass signals.",
        ),
        replace_bundle_id=imported["id"],
    )

    assert revised["id"] == imported["id"]
    assert revised["revision"] == imported["revision"]
    assert revised["source_bundle_id"] == ""
    exported = service.export_bundle(revised["id"])
    assert exported["collaboration_summary"].startswith("Prefer maintainability")


def test_bundle_replace_logs_backup_cleanup_runtime_failure_without_failing(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_rmtree = cleanup_diagnostics.shutil.rmtree

    def fail_backup_rmtree(path: Path) -> None:
        target = Path(path)
        if target.name.startswith(f"{imported['id']}.backup_"):
            raise RuntimeError("backup cleanup crashed")
        original_rmtree(path)

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_backup_rmtree)

    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"):
        revised = service.import_bundle_text(
            _bundle_yaml(
                sample_workdir,
                collaboration_summary="Prefer resilient replacement cleanup diagnostics.",
            ),
            replace_bundle_id=imported["id"],
        )

    assert revised["id"] == imported["id"]
    records = [
        {
            "event": getattr(record, "event", ""),
            "context": getattr(record, "context", {}) or {},
        }
        for record in caplog.records
    ]
    log_path = app_home() / "logs" / "service.log"
    if log_path.exists():
        records.extend(json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip())
    assert any(
        record.get("event") == "service.cleanup.failed"
        and (record.get("context") or {}).get("operation") == "bundle_backup_cleanup"
        and (record.get("context") or {}).get("resource_type") == "path"
        and (record.get("context") or {}).get("owner_id") == imported["id"]
        and (record.get("context") or {}).get("error_type") == "RuntimeError"
        for record in records
    )
