from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_execution import alignment_executor_role_request


ALIGNMENT_ROLE_IDLE_TIMEOUT_SECONDS = 12.5


def test_alignment_executor_role_request_projects_session_runtime_boundary(tmp_path: Path) -> None:
    workdir = tmp_path / "target"
    invocation_dir = tmp_path / "alignment_sessions" / "s1" / "invocations" / "0007"
    schema = {"type": "object"}
    session = {
        "workdir": str(workdir),
        "model": "gpt-5",
        "reasoning_effort": "medium",
        "executor_kind": "claude",
        "executor_mode": "custom",
        "command_cli": "claude",
        "command_args_text": "--resume {resume_session_id}",
        "alignment_stage": "confirmed",
        "working_agreement": {"summary": "Confirmed agreement."},
        "executor_session_ref": {"session_id": "native-123", "provider": "claude"},
    }

    request = alignment_executor_role_request(
        "s1",
        session,
        mode="repair",
        prompt="Repair the bundle.",
        invocation_dir=invocation_dir,
        output_schema=schema,
        idle_timeout_seconds=12.5,
        validation_error="bundle was incomplete",
        prefers_chinese=True,
    )

    assert request.run_id == "alignment:s1"
    assert request.role == "alignment"
    assert request.role_archetype == "alignment"
    assert request.role_name == "Bundle Alignment"
    assert request.prompt == "Repair the bundle."
    assert request.workdir == workdir
    assert request.output_schema is schema
    assert request.output_path == invocation_dir / "output.json"
    assert request.run_dir == invocation_dir
    assert request.executor_kind == "claude"
    assert request.executor_mode == "custom"
    assert request.command_cli == "claude"
    assert request.command_args_text == "--resume {resume_session_id}"
    assert request.inherit_session is True
    assert request.resume_session_id == "native-123"
    assert request.sandbox == "read-only"
    assert request.idle_timeout_seconds == ALIGNMENT_ROLE_IDLE_TIMEOUT_SECONDS
    assert request.extra_context == {
        "target_workdir": str(workdir),
        "alignment_session_id": "s1",
        "alignment_mode": "repair",
        "alignment_stage": "confirmed",
        "working_agreement": {"summary": "Confirmed agreement."},
        "validation_error": "bundle was incomplete",
        "session_ref": {"session_id": "native-123", "provider": "claude"},
        "invocation_id": "0007",
        "prefers_chinese": True,
        "display_language": "",
    }
