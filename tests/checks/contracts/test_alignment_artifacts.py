from __future__ import annotations

import hashlib
from pathlib import Path

from loopora.service_alignment_artifacts import (
    alignment_assistant_message_record,
    alignment_artifact_paths,
    alignment_artifact_paths_from_root,
    alignment_artifact_root_from_bundle_path,
    alignment_bundle_content_fingerprint,
    alignment_invocation_dir,
    alignment_latest_invocation_dir,
    alignment_next_invocation_dir,
    alignment_output_debug_payload,
    alignment_manifest_payload,
    alignment_repair_attempts,
    alignment_session_root,
    alignment_user_message_record,
    ensure_alignment_artifact_dirs,
    finalize_alignment_invocation_files,
    write_alignment_invocation_input_files,
    write_alignment_manifest,
    write_alignment_transcript_log,
    write_alignment_validation_artifacts,
    write_alignment_validation_log,
)


def test_alignment_session_root_supports_modern_and_legacy_bundle_paths(tmp_path: Path) -> None:
    root = tmp_path / "align_1"

    assert alignment_artifact_root_from_bundle_path(root / "artifacts" / "bundle.yml") == root
    assert alignment_artifact_root_from_bundle_path(root / "bundle.yml") == root
    assert alignment_session_root({"bundle_path": str(root / "artifacts" / "bundle.yml")}) == root


def test_alignment_artifact_paths_and_directories_are_stable(tmp_path: Path) -> None:
    root = tmp_path / "align_1"
    paths = alignment_artifact_paths_from_root(root)

    assert paths["manifest"] == root / "manifest.json"
    assert paths["transcript"] == root / "conversation" / "transcript.jsonl"
    assert paths["agreement"] == root / "agreement" / "current.json"
    assert paths["bundle"] == root / "artifacts" / "bundle.yml"
    assert paths["validation"] == root / "artifacts" / "validation.json"
    assert paths["events"] == root / "events" / "events.jsonl"
    assert paths["legacy_dir"] == root / "legacy"
    assert alignment_artifact_paths({"bundle_path": str(root / "artifacts" / "bundle.yml")}) == paths

    ensure_alignment_artifact_dirs(root)

    assert paths["conversation_dir"].is_dir()
    assert paths["agreement_dir"].is_dir()
    assert paths["artifacts_dir"].is_dir()
    assert paths["events_dir"].is_dir()
    assert paths["invocations_dir"].is_dir()
    assert not paths["legacy_dir"].exists()


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
            "repair_attempts": 2,
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
    assert manifest["repair_attempts"] == 2
    assert manifest["message_count"] == 3
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
    assert paths["validation"].read_text(encoding="utf-8") == invocation_dir.joinpath("validation.json").read_text(encoding="utf-8")
    assert '"ok": false' in paths["validation"].read_text(encoding="utf-8")
    assert paths["manifest"].exists()


def test_alignment_invocation_dir_helpers_choose_stable_and_next_paths(tmp_path: Path) -> None:
    root = tmp_path / "align_1"
    first = alignment_invocation_dir(root, "bad", repair=False)
    first.mkdir(parents=True)
    second = alignment_next_invocation_dir(root, "bad", repair=False)
    repair = alignment_invocation_dir(root, 1, repair=True)

    assert first == root / "invocations" / "0001"
    assert second == root / "invocations" / "0002"
    assert repair == root / "invocations" / "0002-repair"
    assert alignment_latest_invocation_dir(root) == first
    assert alignment_latest_invocation_dir(tmp_path / "missing") is None


def test_alignment_validation_log_uses_latest_invocation_or_repair_attempt_default(tmp_path: Path) -> None:
    root = tmp_path / "align_1"
    session = {
        "id": "align_1",
        "status": "idle",
        "bundle_path": str(root / "artifacts" / "bundle.yml"),
        "repair_attempts": 2,
        "transcript": [],
    }

    write_alignment_validation_log(session, {"ok": False, "error": "first"})

    default_invocation = root / "invocations" / "0003-repair"
    assert (default_invocation / "validation.json").exists()

    latest_invocation = root / "invocations" / "9999"
    latest_invocation.mkdir(parents=True)
    write_alignment_validation_log(session, {"ok": True})

    assert '"ok": true' in (latest_invocation / "validation.json").read_text(encoding="utf-8")
    assert (root / "artifacts" / "validation.json").read_text(encoding="utf-8") == (latest_invocation / "validation.json").read_text(encoding="utf-8")


def test_alignment_assistant_message_record_projects_transcript_entry_and_event_payload() -> None:
    record = alignment_assistant_message_record(
        "Need one more decision.",
        created_at="2026-05-29T00:00:00Z",
        decision_options=[
            {
                "id": "go",
                "label": "Continue",
                "description": "Proceed with the recommended direction.",
                "recommended": True,
                "user_reply": "Continue with the recommended direction.",
            },
            {
                "id": "adjust",
                "label": "Adjust",
                "description": "Revise one of the judgments before continuing.",
                "recommended": False,
                "user_reply": "I want to adjust one judgment.",
            },
            {"id": "bad", "label": "Missing fields"},
        ],
        missing_items=["task_scope"],
    )

    assert record.entry == {
        "role": "assistant",
        "content": "Need one more decision.",
        "created_at": "2026-05-29T00:00:00Z",
        "decision_options": [
            {
                "id": "go",
                "label": "Continue",
                "description": "Proceed with the recommended direction.",
                "recommended": True,
                "user_reply": "Continue with the recommended direction.",
            },
            {
                "id": "adjust",
                "label": "Adjust",
                "description": "Revise one of the judgments before continuing.",
                "recommended": False,
                "user_reply": "I want to adjust one judgment.",
            },
        ],
        "missing_items": ["task_scope"],
    }
    assert record.event_payload == {
        "role": "assistant",
        "content": "Need one more decision.",
        "decision_options": record.entry["decision_options"],
        "missing_items": ["task_scope"],
    }


def test_alignment_assistant_message_record_omits_empty_optional_fields() -> None:
    record = alignment_assistant_message_record("Done.", created_at="now", decision_options=[], missing_items=[])

    assert record.entry == {"role": "assistant", "content": "Done.", "created_at": "now"}
    assert record.event_payload == {"role": "assistant", "content": "Done."}


def test_alignment_user_message_record_projects_transcript_entry_and_event_payload() -> None:
    record = alignment_user_message_record("Please continue.", created_at="2026-05-29T00:01:00Z")

    assert record.entry == {
        "role": "user",
        "content": "Please continue.",
        "created_at": "2026-05-29T00:01:00Z",
    }
    assert record.event_payload == {"role": "user", "content": "Please continue."}


def test_alignment_invocation_input_writer_emits_prompt_schema_and_logs(tmp_path: Path) -> None:
    invocation_dir = tmp_path / "invocations" / "0001"

    write_alignment_invocation_input_files(
        invocation_dir,
        prompt="Prompt text\n\n",
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )

    assert (invocation_dir / "prompt.md").read_text(encoding="utf-8") == "Prompt text\n"
    assert '"type": "object"' in (invocation_dir / "schema.json").read_text(encoding="utf-8")
    assert (invocation_dir / "stdout.log").read_text(encoding="utf-8") == ""
    assert (invocation_dir / "stderr.log").read_text(encoding="utf-8") == ""


def test_alignment_bundle_content_fingerprint_uses_utf8_bytes() -> None:
    bundle_yaml = "version: 1\nmetadata:\n  name: 中文\n"
    data = bundle_yaml.encode("utf-8")

    assert alignment_bundle_content_fingerprint(bundle_yaml) == {
        "bundle_sha256": hashlib.sha256(data).hexdigest(),
        "bundle_bytes": len(data),
    }


def test_alignment_invocation_output_helpers_redact_and_finalize_debug_payload(tmp_path: Path) -> None:
    invocation_dir = tmp_path / "invocations" / "0001"
    invocation_dir.mkdir(parents=True)
    (invocation_dir / "alignment_schema.json").write_text("{}\n", encoding="utf-8")
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    output = {
        "assistant_message": "Use Authorization: Bearer OUTPUT_AUTH_SECRET",
        "bundle_yaml": "version: 1\nmetadata:\n  name: Output\n",
        "nested": {"Cookie": "sid=OUTPUT_COOKIE_SECRET"},
    }

    payload = alignment_output_debug_payload(output, bundle_path)
    finalize_alignment_invocation_files(invocation_dir, output, bundle_path)
    finalized = (invocation_dir / "output.json").read_text(encoding="utf-8")

    assert payload["bundle_written"] is True
    assert payload["bundle_path"] == str(bundle_path)
    assert payload["bundle_sha256"]
    assert "bundle_yaml" not in payload
    assert "OUTPUT_AUTH_SECRET" not in finalized
    assert "OUTPUT_COOKIE_SECRET" not in finalized
    assert "<secret omitted>" in finalized
    assert (invocation_dir / "schema.json").exists()
    assert not (invocation_dir / "alignment_schema.json").exists()


def test_alignment_repair_attempts_normalizes_invalid_values() -> None:
    assert alignment_repair_attempts({"repair_attempts": 3}) == 3
    assert alignment_repair_attempts({"repair_attempts": -1}) == 0
    assert alignment_repair_attempts({"repair_attempts": "bad"}, invalid_default=7) == 7
    assert alignment_repair_attempts({}) == 0
