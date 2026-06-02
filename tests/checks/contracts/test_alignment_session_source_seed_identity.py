from __future__ import annotations

from loopora.service_alignment_source_seed import alignment_session_source_seed


def test_alignment_session_source_seed_preserves_session_identity_and_redacts_transcript() -> None:
    payload = alignment_session_source_seed(
        {
            "source_type": "alignment_session_file",
            "source_alignment_session_id": "align_1",
            "bundle_path": "/tmp/session-bundle.yml",
            "status": "ready",
        },
        {
            "id": "align_1",
            "status": "imported",
            "transcript": [
                {"role": "user", "content": "Use Cookie: sid=SESSION_TRANSCRIPT_COOKIE_SECRET", "created_at": "1"},
            ],
        },
        {"loop": {"completion_mode": "manual_review"}},
        seed_bundle={"metadata": {"name": "Session seed"}},
    )
    rendered_agreement = str(payload["working_agreement"])

    assert "SESSION_TRANSCRIPT_COOKIE_SECRET" not in rendered_agreement
    assert "<secret omitted>" in rendered_agreement
    assert payload["linked_bundle_id"] == ""
    assert payload["linked_loop_id"] == ""
    assert payload["linked_run_id"] == ""
    assert payload["working_agreement"]["source"]["source_status"] == "imported"
    assert payload["working_agreement"]["source"]["source_completion_mode"] == "manual_review"
    assert payload["event"] == {
        "source_type": "alignment_session_file",
        "source_bundle_id": "",
        "source_loop_id": "",
        "source_run_id": "",
        "source_alignment_session_id": "align_1",
        "spec_path": "",
        "reason": "improve_from_workdir_alignment_session",
    }
