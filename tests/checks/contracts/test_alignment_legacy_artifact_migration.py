from __future__ import annotations

import json
import logging
from pathlib import Path

import loopora.service_alignment_legacy as alignment_legacy_module


def test_alignment_service_lazily_migrates_legacy_flat_artifacts(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    session_id = "align_legacy"
    legacy_root = sample_workdir / ".loopora" / "alignment_sessions" / session_id
    legacy_root.mkdir(parents=True)
    legacy_bundle = legacy_root / "bundle.yml"
    legacy_bundle.write_text("version: 1\nmetadata:\n  name: Legacy\n  revision: 1\n", encoding="utf-8")
    (legacy_root / "transcript.jsonl").write_text(
        json.dumps({"role": "user", "content": "Legacy prompt"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (legacy_root / "working_agreement.json").write_text('{"summary":"Legacy agreement"}\n', encoding="utf-8")
    (legacy_root / "validation.json").write_text('{"ok":true}\n', encoding="utf-8")
    (legacy_root / "alignment_prompt_0.md").write_text("legacy prompt\n", encoding="utf-8")
    (legacy_root / "alignment_schema.json").write_text("{}\n", encoding="utf-8")
    (legacy_root / "alignment_output_0.json").write_text(
        json.dumps({"assistant_message": "done", "bundle_yaml": "raw yaml"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (legacy_root / "alignment_output_1.json").write_bytes(b"\xff")
    service.repository.create_alignment_session(
        {
            "id": session_id,
            "status": "ready",
            "workdir": str(sample_workdir),
            "bundle_path": str(legacy_bundle),
            "transcript": [{"role": "user", "content": "Legacy prompt", "created_at": "now"}],
            "validation": {"ok": True},
            "alignment_stage": "ready",
            "working_agreement": {"summary": "Legacy agreement"},
            "executor_session_ref": {},
        }
    )

    migrated = service.get_alignment_session(session_id)
    root = Path(migrated["artifact_dir"])

    assert Path(migrated["bundle_path"]) == root / "artifacts" / "bundle.yml"
    assert (root / "artifacts" / "bundle.yml").exists()
    assert (root / "conversation" / "transcript.jsonl").exists()
    assert (root / "agreement" / "current.json").exists()
    assert (root / "artifacts" / "validation.json").exists()
    output = json.loads((root / "invocations" / "0001" / "output.json").read_text(encoding="utf-8"))
    assert "bundle_yaml" not in output
    assert output["bundle_sha256"]
    assert (root / "invocations" / "0002" / "output.json").read_bytes() == b"\xff"
    assert (root / "legacy" / "bundle.yml").exists()


def test_alignment_legacy_migration_failure_writes_structured_diagnostics(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session_id = "align_legacy_diag"
    legacy_root = sample_workdir / ".loopora" / "alignment_sessions" / session_id
    legacy_root.mkdir(parents=True)
    legacy_bundle = legacy_root / "bundle.yml"
    legacy_bundle.write_text("version: 1\nmetadata:\n  name: Legacy\n  revision: 1\n", encoding="utf-8")
    stale_file = legacy_root / "stale.tmp"
    stale_file.write_text("left behind\n", encoding="utf-8")
    service.repository.create_alignment_session(
        {
            "id": session_id,
            "status": "ready",
            "workdir": str(sample_workdir),
            "bundle_path": str(legacy_bundle),
            "transcript": [],
            "validation": {"ok": True},
            "alignment_stage": "ready",
            "working_agreement": {},
            "executor_session_ref": {},
        }
    )
    original_move = alignment_legacy_module.shutil.move

    def fail_stale_move(source: str, target: str):
        if Path(source).name == "stale.tmp":
            raise OSError("locked legacy file")
        return original_move(source, target)

    monkeypatch.setattr(alignment_legacy_module.shutil, "move", fail_stale_move)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        migrated = service.get_alignment_session(session_id)

    assert Path(migrated["bundle_path"]).name == "bundle.yml"
    diagnostic_event = next(
        event
        for event in service.list_alignment_events(session_id)
        if event["event_type"] == "alignment_legacy_artifact_migration_failed"
    )
    assert diagnostic_event["payload"]["operation"] == "alignment_legacy_artifact_migration"
    assert diagnostic_event["payload"]["resource_type"] == "path"
    assert diagnostic_event["payload"]["resource_id"].endswith("stale.tmp")
    assert diagnostic_event["payload"]["owner_id"] == session_id
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_legacy_artifact_migration"
        for record in caplog.records
    )
