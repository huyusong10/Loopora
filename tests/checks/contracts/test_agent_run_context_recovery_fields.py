from __future__ import annotations

from loopora.service_alignment_run_context_recovery_fields import (
    agent_exact_binding_recovery_action,
    agent_failed_preview_choice_repair_fields,
    agent_redacted_context_binding,
)


def test_agent_exact_binding_recovery_action_maps_choice_state() -> None:
    assert agent_exact_binding_recovery_action({"linked_run_id": "run_1", "alignment_status": "ready"}) == "resume_run"
    assert agent_exact_binding_recovery_action({"linked_run_id": "", "alignment_status": "ready"}) == "start_ready_preview"
    assert agent_exact_binding_recovery_action({"linked_run_id": "", "alignment_status": "imported"}) == "start_ready_preview"
    assert agent_exact_binding_recovery_action({"linked_run_id": "", "alignment_status": "failed"}) == "blocked"


def test_agent_failed_preview_repair_fields_prioritize_user_source_and_validation_error() -> None:
    fields = agent_failed_preview_choice_repair_fields(
        {
            "id": "align_failed",
            "status": "failed",
            "error_message": "session error",
            "validation": {
                "error": "validation error",
                "bundle_path": "/tmp/validation-preview.yaml",
            },
        },
        payload={"source_path": "/workspace/loopora-plan.yaml"},
        failed_payload={
            "error": "event error",
            "bundle_path": "/tmp/event-preview.yaml",
        },
    )

    assert fields["validation_error"] == "validation error"
    assert fields["plan_file_to_repair"] == "/workspace/loopora-plan.yaml"
    assert fields["preview_plan_copy"] == "/tmp/validation-preview.yaml"
    assert fields["next_repair_step"].startswith("repair the candidate plan file")


def test_agent_failed_preview_repair_fields_fall_back_to_event_payload_and_omit_empty_fields() -> None:
    event_fields = agent_failed_preview_choice_repair_fields(
        {"id": "align_failed", "status": "failed"},
        failed_payload={
            "error": "event error",
            "bundle_path": "/tmp/event-preview.yaml",
        },
    )
    empty_fields = agent_failed_preview_choice_repair_fields({"id": "align_failed", "status": "failed"})

    assert event_fields["validation_error"] == "event error"
    assert event_fields["plan_file_to_repair"] == "/tmp/event-preview.yaml"
    assert event_fields["preview_plan_copy"] == "/tmp/event-preview.yaml"
    assert "validation_error" not in empty_fields
    assert "plan_file_to_repair" not in empty_fields
    assert "preview_plan_copy" not in empty_fields
    assert empty_fields == {
        "next_repair_step": "repair the candidate plan file, rerun /loopora-plan, then use /loopora-run only after the preview is ready"
    }


def test_agent_redacted_context_binding_keeps_recovery_fields_and_omits_non_contract_data() -> None:
    redacted = agent_redacted_context_binding(
        {
            "path": "/workspace/.loopora/agent-binding.json",
            "alignment_session_id": "align_1",
            "alignment_status": "ready",
            "linked_run_id": "run_1",
            "linked_loop_id": "loop_1",
            "linked_bundle_id": "bundle_1",
            "workdir": "/workspace/project",
            "host_context_id": "thread_1",
            "context_source": "codex_project_skill",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "requires_web_alignment": False,
            "requires_candidate_repair": True,
            "loopora_fit_contradiction": "needs better evidence",
            "preview_path": "/loops/new/bundle?alignment_session_id=align_1",
            "run_path": "/runs/run_1",
            "raw_transcript": "private implementation detail",
            "random_field": "not a recovery contract",
        }
    )

    assert redacted == {
        "path": "/workspace/.loopora/agent-binding.json",
        "alignment_session_id": "align_1",
        "alignment_status": "ready",
        "linked_run_id": "run_1",
        "linked_loop_id": "loop_1",
        "linked_bundle_id": "bundle_1",
        "workdir": "/workspace/project",
        "host_context_id": "thread_1",
        "context_source": "codex_project_skill",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "requires_web_alignment": False,
        "requires_candidate_repair": True,
        "loopora_fit_contradiction": "needs better evidence",
        "preview_path": "/loops/new/bundle?alignment_session_id=align_1",
        "run_path": "/runs/run_1",
    }


def test_agent_redacted_context_binding_redacts_sensitive_allowed_values() -> None:
    redacted = agent_redacted_context_binding(
        {
            "path": "/workspace/.loopora/agent-binding.json?token=PATH_TOKEN_SECRET",
            "workdir": "Cookie: sid=WORKDIR_COOKIE_SECRET",
            "preview_path": "/preview?x-loopora-token=PREVIEW_TOKEN_SECRET",
        }
    )

    assert "PATH_TOKEN_SECRET" not in str(redacted)
    assert "WORKDIR_COOKIE_SECRET" not in str(redacted)
    assert "PREVIEW_TOKEN_SECRET" not in str(redacted)
    assert "<secret omitted>" in str(redacted)
