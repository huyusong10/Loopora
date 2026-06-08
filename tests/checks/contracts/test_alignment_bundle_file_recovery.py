from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.web import build_app

from alignment_test_support import (
    _bundle_invocation_dir,
    _confirm_alignment_agreement,
    _wait_for_status,
)


def test_alignment_bundle_source_file_rejects_invalid_utf8(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    preview_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    Path(preview_session["bundle_path"]).write_bytes(b"\xff")

    preview = service.get_alignment_bundle(preview_session["id"])
    assert preview["ok"] is False
    assert preview["yaml"] == ""
    assert "UTF-8 encoded YAML" in preview["validation"]["error"]

    sync_result = service.sync_alignment_bundle_from_file(preview_session["id"])
    assert sync_result["ok"] is False
    assert "UTF-8 encoded YAML" in sync_result["validation"]["error"]
    synced_session = service.get_alignment_session(preview_session["id"])
    assert synced_session["status"] == "failed"
    assert "UTF-8 encoded YAML" in synced_session["error_message"]
    assert any(
        event["event_type"] == "alignment_bundle_sync_failed"
        for event in service.list_alignment_events(preview_session["id"])
    )

    Path(preview_session["bundle_path"]).write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    recovered = service.sync_alignment_bundle_from_file(preview_session["id"])
    recovered_session = service.get_alignment_session(preview_session["id"])
    assert recovered["ok"] is True
    assert recovered_session["status"] == "ready"
    assert recovered_session["error_message"] == ""
    assert recovered_session["finished_at"] is None


def test_alignment_bundle_preview_revalidates_current_file_without_mutating_session(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    bundle_path = Path(session["bundle_path"])
    ready_bundle = load_bundle_text(bundle_path.read_text(encoding="utf-8"))
    ready_bundle["spec"]["markdown"] = ready_bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps or residual risks only when they are explicitly named, visible, tracked, and owned as a follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )
    bundle_path.write_text(bundle_to_yaml(ready_bundle), encoding="utf-8")

    preview = service.get_alignment_bundle(session["id"])

    assert preview["ok"] is False
    assert preview["validation"]["ok"] is False
    assert "Residual Risk guidance" in preview["validation"]["error"]
    assert service.get_alignment_session(session["id"])["status"] == "ready"


def test_alignment_bundle_source_file_recovers_after_invalid_utf8(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    preview_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    Path(preview_session["bundle_path"]).write_bytes(b"\xff")
    sync_result = service.sync_alignment_bundle_from_file(preview_session["id"])
    assert sync_result["ok"] is False

    import_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create an importable Loop.")["id"],
    )
    Path(import_session["bundle_path"]).write_bytes(b"\xff")
    client = TestClient(build_app(service=service))

    import_response = client.post(
        f"/api/alignments/sessions/{import_session['id']}/import",
        json={"start_immediately": False},
    )
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert "UTF-8 encoded YAML" in import_response.json()["error"]
    import_failed_session = service.get_alignment_session(import_session["id"])
    assert import_failed_session["status"] == "ready"
    assert "UTF-8 encoded YAML" in import_failed_session["error_message"]
    assert any(event["event_type"] == "alignment_import_failed" for event in service.list_alignment_events(import_session["id"]))


def test_alignment_message_after_corrupt_ready_bundle_keeps_session_usable(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a recoverable Loop.")["id"],
    )
    Path(session["bundle_path"]).write_bytes(b"\xff")

    service.append_alignment_message(session["id"], "请根据对话重新整理方案。")

    continued = _wait_for_status(service, session["id"], "ready")
    assert continued["error_message"] == ""
    assert continued["validation"]["ok"] is True
    assert continued["transcript"][-1]["role"] == "assistant"
    prompt_text = (_bundle_invocation_dir(Path(continued["artifact_dir"])) / "prompt.md").read_text(encoding="utf-8")
    assert "Current bundle file could not be read" in prompt_text
