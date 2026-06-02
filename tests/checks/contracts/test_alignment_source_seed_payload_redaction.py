from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_source_seed import alignment_source_seed_payload, alignment_spec_file_source_seed


def test_alignment_source_seed_payload_redacts_source_and_emits_identity_event() -> None:
    payload = alignment_source_seed_payload(
        {
            "mode": "improvement",
            "source_type": "run",
            "source_bundle_id": "bundle_1",
            "source_loop_id": "loop_1",
            "source_run_id": "run_1",
            "reason": "improve_from_run",
            "auth_token": "SOURCE_SEED_TOKEN_SECRET",
            "nested": {"cookie": "sid=SOURCE_SEED_COOKIE_SECRET"},
        },
        seed_bundle={"metadata": {"name": "Seed", "api_key": "SOURCE_SEED_API_SECRET"}},
        linked_bundle_id="bundle_1",
        linked_loop_id="loop_1",
        linked_run_id="run_1",
    )
    rendered = str(payload["working_agreement"])

    assert "SOURCE_SEED_TOKEN_SECRET" not in rendered
    assert "SOURCE_SEED_COOKIE_SECRET" not in rendered
    assert "SOURCE_SEED_API_SECRET" not in rendered
    assert payload["linked_bundle_id"] == "bundle_1"
    assert payload["linked_loop_id"] == "loop_1"
    assert payload["linked_run_id"] == "run_1"
    assert payload["event"] == {
        "source_type": "run",
        "source_bundle_id": "bundle_1",
        "source_loop_id": "loop_1",
        "source_run_id": "run_1",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_run",
    }
    assert "<secret omitted>" in rendered


def test_alignment_spec_file_source_seed_reads_redacted_spec_and_emits_identity_event(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("Task uses Authorization: Bearer SPEC_SOURCE_TOKEN_SECRET.\n", encoding="utf-8")

    payload = alignment_spec_file_source_seed({"spec_path": str(spec_path)})
    rendered_source = str(payload["working_agreement"]["source"])

    assert "SPEC_SOURCE_TOKEN_SECRET" not in rendered_source
    assert "<secret omitted>" in rendered_source
    assert payload["seed_bundle"] == {}
    assert payload["linked_bundle_id"] == ""
    assert payload["event"] == {
        "source_type": "spec_file",
        "source_bundle_id": "",
        "source_loop_id": "",
        "source_run_id": "",
        "source_alignment_session_id": "",
        "spec_path": str(spec_path),
        "reason": "start_from_workdir_spec",
    }
    assert payload["working_agreement"]["source"]["artifact_paths"] == {"spec": str(spec_path)}
