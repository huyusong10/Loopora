from __future__ import annotations

import hashlib
from pathlib import Path

from loopora.service_alignment_artifacts import (
    alignment_bundle_content_fingerprint,
    alignment_invocation_dir,
    alignment_latest_invocation_dir,
    alignment_next_invocation_dir,
    alignment_output_debug_payload,
    finalize_alignment_invocation_files,
    write_alignment_invocation_input_files,
    write_alignment_validation_log,
)


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
    assert (root / "artifacts" / "validation.json").read_text(encoding="utf-8") == (
        latest_invocation / "validation.json"
    ).read_text(encoding="utf-8")


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
