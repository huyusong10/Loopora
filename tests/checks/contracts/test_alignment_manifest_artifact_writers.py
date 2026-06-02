from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_artifacts import (
    alignment_artifact_paths,
    alignment_manifest_payload,
    write_alignment_manifest,
    write_alignment_transcript_log,
    write_alignment_validation_artifacts,
)


MANIFEST_MESSAGE_COUNT = 3
MANIFEST_REPAIR_ATTEMPT_COUNT = 2


def test_alignment_manifest_payload_redacts_preview_fields_without_embedding_private_logs(tmp_path: Path) -> None:
    root = tmp_path / "align_1"
    manifest = alignment_manifest_payload(
        {
            "id": "align_1",
            "status": "failed",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "workdir": str(tmp_path),
            "bundle_path": str(root / "artifacts" / "bundle.yml"),
            "alignment_stage": "ready_review",
            "repair_attempts": MANIFEST_REPAIR_ATTEMPT_COUNT,
            "error_message": "provider failed with Authorization: Bearer MANIFEST_TOKEN_SECRET",
            "transcript": [
                {"role": "assistant", "content": "Ignore"},
                {"role": "user", "content": "Use Cookie: sid=MANIFEST_COOKIE_SECRET"},
                {"role": "assistant", "content": "Final Authorization: Bearer MANIFEST_LAST_SECRET"},
            ],
        }
    )
    rendered = str(manifest)

    assert "MANIFEST_TOKEN_SECRET" not in rendered
    assert "MANIFEST_COOKIE_SECRET" not in rendered
    assert "MANIFEST_LAST_SECRET" not in rendered
    assert "<secret omitted>" in rendered
    assert manifest["artifact_dir"] == str(root)
    assert manifest["repair_attempts"] == MANIFEST_REPAIR_ATTEMPT_COUNT
    assert manifest["message_count"] == MANIFEST_MESSAGE_COUNT
    assert manifest["paths"] == {
        "transcript": "conversation/transcript.jsonl",
        "working_agreement": "agreement/current.json",
        "bundle": "artifacts/bundle.yml",
        "validation": "artifacts/validation.json",
        "events": "events/events.jsonl",
        "invocations": "invocations",
    }
    assert "transcript" not in manifest
    assert "working_agreement" not in manifest
    assert "validation" not in manifest


def test_alignment_artifact_writers_emit_manifest_transcript_and_agreement(tmp_path: Path) -> None:
    root = tmp_path / "align_1"
    session = {
        "id": "align_1",
        "status": "idle",
        "bundle_path": str(root / "artifacts" / "bundle.yml"),
        "transcript": [{"role": "user", "content": "Hello"}],
        "working_agreement": {"summary": "Agreement"},
    }

    write_alignment_transcript_log(session)

    paths = alignment_artifact_paths(session)
    assert paths["manifest"].exists()
    assert paths["transcript"].read_text(encoding="utf-8").strip().endswith('"content": "Hello"}')
    assert '"summary": "Agreement"' in paths["agreement"].read_text(encoding="utf-8")

    updated = {**session, "status": "failed", "error_message": "Authorization: Bearer WRITE_MANIFEST_TOKEN_SECRET"}
    write_alignment_manifest(updated)
    manifest_text = paths["manifest"].read_text(encoding="utf-8")

    assert "WRITE_MANIFEST_TOKEN_SECRET" not in manifest_text
    assert "<secret omitted>" in manifest_text


def test_alignment_validation_writer_updates_session_and_invocation_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "align_1"
    invocation_dir = root / "invocations" / "0001"
    session = {
        "id": "align_1",
        "status": "idle",
        "bundle_path": str(root / "artifacts" / "bundle.yml"),
        "transcript": [],
    }
    validation = {"ok": False, "error": "needs repair"}

    write_alignment_validation_artifacts(session, validation, invocation_dir=invocation_dir)

    paths = alignment_artifact_paths(session)
    assert paths["validation"].read_text(encoding="utf-8") == invocation_dir.joinpath("validation.json").read_text(
        encoding="utf-8"
    )
    assert '"ok": false' in paths["validation"].read_text(encoding="utf-8")
    assert paths["manifest"].exists()
