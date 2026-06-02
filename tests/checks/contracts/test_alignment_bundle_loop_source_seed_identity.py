from __future__ import annotations

from loopora.service_alignment_source_seed import (
    alignment_bundle_revision_source_context,
    alignment_bundle_source_seed,
    alignment_loop_source_seed,
)


def test_alignment_bundle_source_seed_preserves_identity_and_seed_metadata() -> None:
    payload = alignment_bundle_source_seed(
        {"source_bundle_id": "bundle_1", "source_loop_id": "loop_from_option"},
        {
            "loop_id": "loop_from_bundle",
            "loop": {"completion_mode": "all_checks_pass"},
        },
        seed_bundle={
            "metadata": {
                "name": "Bundle seed",
                "auth_token": "BUNDLE_SOURCE_SEED_TOKEN_SECRET",
            }
        },
    )
    rendered_agreement = str(payload["working_agreement"])

    assert "BUNDLE_SOURCE_SEED_TOKEN_SECRET" not in rendered_agreement
    assert "<secret omitted>" in rendered_agreement
    assert payload["linked_bundle_id"] == "bundle_1"
    assert payload["linked_loop_id"] == ""
    assert payload["working_agreement"]["source"]["source_loop_id"] == "loop_from_option"
    assert payload["working_agreement"]["source"]["source_completion_mode"] == "all_checks_pass"
    assert payload["event"] == {
        "source_type": "bundle",
        "source_bundle_id": "bundle_1",
        "source_loop_id": "loop_from_option",
        "source_run_id": "",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_workdir_context",
    }


def test_alignment_bundle_revision_source_context_preserves_revision_reason() -> None:
    source = alignment_bundle_revision_source_context(
        "bundle_1",
        {"loop": {"completion_mode": "all_checks_pass"}},
    )

    assert source == {
        "mode": "improvement",
        "source_type": "bundle",
        "source_bundle_id": "bundle_1",
        "source_run_id": "",
        "source_completion_mode": "all_checks_pass",
        "reason": "improve_imported_bundle",
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }


def test_alignment_loop_source_seed_preserves_loop_identity_and_seed_metadata() -> None:
    payload = alignment_loop_source_seed(
        {"source_loop_id": "loop_1"},
        {"id": "loop_1", "name": "Improve --token LOOP_NAME_TOKEN_SECRET"},
        {"loop": {"completion_mode": "manual_review"}},
        seed_bundle={"metadata": {"name": "Loop seed"}},
    )
    rendered_agreement = str(payload["working_agreement"])

    assert "LOOP_NAME_TOKEN_SECRET" not in rendered_agreement
    assert "<secret omitted>" in rendered_agreement
    assert payload["linked_bundle_id"] == ""
    assert payload["linked_loop_id"] == "loop_1"
    assert payload["working_agreement"]["source"]["source_completion_mode"] == "manual_review"
    assert payload["event"] == {
        "source_type": "loop",
        "source_bundle_id": "",
        "source_loop_id": "loop_1",
        "source_run_id": "",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_workdir_loop",
    }
