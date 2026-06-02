from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_execution import (
    alignment_executor_role_request,
    alignment_executor_session_ref_event_payload,
    alignment_executor_session_ref_from_output,
    alignment_native_resume_fallback_event_payload,
    alignment_request_can_native_resume_fallback,
    apply_alignment_native_resume_fallback,
)


def test_alignment_native_resume_fallback_only_applies_to_supported_executor_requests(tmp_path: Path) -> None:
    session = {
        "workdir": str(tmp_path),
        "executor_kind": "codex",
        "executor_session_ref": {"session_id": "stale-native-session"},
    }
    request = alignment_executor_role_request(
        "s2",
        session,
        mode="normal",
        prompt="Continue alignment.",
        invocation_dir=tmp_path / "invocations" / "0001",
        output_schema={},
        idle_timeout_seconds=None,
    )

    assert alignment_request_can_native_resume_fallback(request) is True

    request.executor_kind = "custom"
    assert alignment_request_can_native_resume_fallback(request) is False

    request.executor_kind = "codex"
    request.resume_session_id = ""
    assert alignment_request_can_native_resume_fallback(request) is False

    request.resume_session_id = "stale-native-session"
    apply_alignment_native_resume_fallback(request)

    assert request.inherit_session is False
    assert request.resume_session_id == ""
    assert request.extra_context["session_ref"] == {}


def test_alignment_native_resume_fallback_event_payload_preserves_failed_resume_context(tmp_path: Path) -> None:
    request = alignment_executor_role_request(
        "s2b",
        {
            "workdir": str(tmp_path),
            "executor_kind": "claude",
            "executor_session_ref": {"session_id": "stale-native-session"},
        },
        mode="normal",
        prompt="Continue alignment.",
        invocation_dir=tmp_path / "invocations" / "0002",
        output_schema={},
        idle_timeout_seconds=None,
    )

    assert alignment_native_resume_fallback_event_payload(request) == {
        "executor_kind": "claude",
        "resume_session_id": "stale-native-session",
        "message": "Native CLI session resume failed; retrying with Loopora transcript context.",
    }


def test_alignment_executor_session_ref_merges_existing_request_ref_with_output_ref(tmp_path: Path) -> None:
    request = alignment_executor_role_request(
        "s3",
        {
            "workdir": str(tmp_path),
            "executor_session_ref": {"session_id": "existing-session", "provider": "codex"},
        },
        mode="normal",
        prompt="Continue alignment.",
        invocation_dir=tmp_path / "invocations" / "0001",
        output_schema={},
        idle_timeout_seconds=None,
    )

    session_ref = alignment_executor_session_ref_from_output(
        request,
        {"session_ref": {"session_id": "new-session", "provider": "codex", "empty": ""}},
    )

    assert session_ref == {"session_id": "new-session", "provider": "codex"}


def test_alignment_executor_session_ref_event_payload_reports_native_resume_availability(tmp_path: Path) -> None:
    request = alignment_executor_role_request(
        "s3b",
        {"workdir": str(tmp_path), "executor_kind": "opencode"},
        mode="normal",
        prompt="Continue alignment.",
        invocation_dir=tmp_path / "invocations" / "0003",
        output_schema={},
        idle_timeout_seconds=None,
    )

    assert alignment_executor_session_ref_event_payload(request, {"provider": "opencode"}) == {
        "executor_kind": "opencode",
        "session_ref": {"provider": "opencode"},
        "native_resume_available": False,
    }
    assert alignment_executor_session_ref_event_payload(
        request,
        {"session_id": "new-session", "provider": "opencode"},
    ) == {
        "executor_kind": "opencode",
        "session_ref": {"session_id": "new-session", "provider": "opencode"},
        "native_resume_available": True,
    }
