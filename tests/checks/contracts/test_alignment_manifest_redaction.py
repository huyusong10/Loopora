from __future__ import annotations

import json
from pathlib import Path

from loopora.service_alignment_artifacts import write_alignment_manifest


def test_alignment_manifest_and_session_summary_redact_transcript_preview_secrets(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Start from --token MANIFEST_TOKEN_SECRET_MARKER and Cookie: sid=MANIFEST_COOKIE_SECRET_MARKER.",
        start_immediately=False,
    )
    artifact_root = Path(session["artifact_dir"])
    manifest = json.loads((artifact_root / "manifest.json").read_text(encoding="utf-8"))
    listed = service.list_alignment_sessions()[0]
    transcript_text = (artifact_root / "conversation" / "transcript.jsonl").read_text(encoding="utf-8")

    for payload in (json.dumps(manifest, ensure_ascii=False), json.dumps(listed, ensure_ascii=False)):
        assert "MANIFEST_TOKEN_SECRET_MARKER" not in payload
        assert "MANIFEST_COOKIE_SECRET_MARKER" not in payload
        assert "<secret omitted>" in payload

    assert "MANIFEST_TOKEN_SECRET_MARKER" in transcript_text
    assert "MANIFEST_COOKIE_SECRET_MARKER" in transcript_text


def test_alignment_manifest_redacts_error_message_preview_secrets(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a Loop later.",
        start_immediately=False,
    )

    service.repository.update_alignment_session(
        session["id"],
        status="failed",
        error_message="provider failed with Authorization: Bearer MANIFEST_ERROR_SECRET_MARKER",
    )
    write_alignment_manifest(service.get_alignment_session(session["id"]))

    manifest = json.loads((Path(session["artifact_dir"]) / "manifest.json").read_text(encoding="utf-8"))
    assert "MANIFEST_ERROR_SECRET_MARKER" not in json.dumps(manifest, ensure_ascii=False)
    assert manifest["error_message"] == "provider failed with Authorization: <secret omitted>"
