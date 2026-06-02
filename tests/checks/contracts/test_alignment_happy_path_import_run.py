from __future__ import annotations

import json
from pathlib import Path

from alignment_test_support import (
    _assert_alignment_preview_control_summary,
    _assert_run_succeeds_and_joins,
    _bundle_invocation_dir,
    _confirm_alignment_agreement,
)


def test_alignment_service_writes_validates_previews_imports_and_runs(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    bundle_path = Path(session["bundle_path"])
    artifact_root = sample_workdir / ".loopora" / "alignment_sessions" / session["id"]
    assert bundle_path == artifact_root / "artifacts" / "bundle.yml"
    assert bundle_path.exists()
    assert session["validation"]["ok"] is True
    assert (artifact_root / "manifest.json").exists()
    assert (artifact_root / "conversation" / "transcript.jsonl").exists()
    assert (artifact_root / "agreement" / "current.json").exists()
    assert (artifact_root / "artifacts" / "validation.json").exists()
    assert (artifact_root / "events" / "events.jsonl").exists()
    invocation_dir = artifact_root / "invocations" / "0001"
    assert (invocation_dir / "prompt.md").exists()
    assert (invocation_dir / "schema.json").exists()
    assert (invocation_dir / "output.json").exists()
    assert (invocation_dir / "stdout.log").exists()
    assert (invocation_dir / "stderr.log").exists()
    bundle_invocation_dir = _bundle_invocation_dir(artifact_root)
    assert bundle_invocation_dir != invocation_dir
    invocation_output = json.loads((invocation_dir / "output.json").read_text(encoding="utf-8"))
    assert "bundle_yaml" not in invocation_output
    assert invocation_output["bundle_written"] is False
    invocation_output = json.loads((bundle_invocation_dir / "output.json").read_text(encoding="utf-8"))
    assert "bundle_yaml" not in invocation_output
    assert invocation_output["bundle_written"] is True
    assert invocation_output["bundle_path"] == str(bundle_path)
    manifest = json.loads((artifact_root / "manifest.json").read_text(encoding="utf-8"))
    assert "transcript" not in manifest
    assert "validation" not in manifest
    assert "working_agreement" not in manifest
    assert "Build a focused starter experience." in (artifact_root / "conversation" / "transcript.jsonl").read_text(
        encoding="utf-8"
    )
    assert session["alignment_stage"] == "ready"

    preview = service.get_alignment_bundle(session["id"])
    assert preview["ok"] is True
    assert preview["bundle"]["loop"]["workdir"] == str(sample_workdir.resolve())
    assert preview["workflow_preview"]["roles"][0]["name"] == "Focused Builder"
    _assert_alignment_preview_control_summary(preview)
    assert "Ship the focused starter experience" in preview["spec_rendered_html"]

    imported = service.import_alignment_bundle(session["id"], start_immediately=True)
    assert imported["bundle"]["loop_id"]
    assert imported["run"]["id"]
    final_session = service.get_alignment_session(session["id"])
    assert final_session["status"] == "running_loop"
    assert final_session["linked_bundle_id"] == imported["bundle"]["id"]
    assert final_session["linked_loop_id"] == imported["bundle"]["loop_id"]
    assert final_session["linked_run_id"] == imported["run"]["id"]
    _assert_run_succeeds_and_joins(service, imported["run"]["id"])


def test_alignment_import_string_false_does_not_start_run(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    imported = service.import_alignment_bundle(session["id"], start_immediately="false")

    assert imported["run"] is None
    assert imported["session"]["status"] == "imported"
    assert imported["session"]["linked_run_id"] == ""
    events = service.list_alignment_events(session["id"])
    assert any(event["event_type"] == "alignment_imported" for event in events)
    assert not any(event["event_type"] == "alignment_run_started" for event in events)
