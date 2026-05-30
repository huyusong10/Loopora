from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_execution import (
    AlignmentExecutionState,
    AlignmentSessionTransitionPlan,
    alignment_bundle_candidate_outcome,
    alignment_bundle_executor_settings_issues,
    alignment_bundle_ready_transition_plan,
    alignment_bundle_repair_transition_plan,
    alignment_executor_output_action,
    alignment_executor_output_failure_message,
    alignment_executor_output_waits_for_user,
    alignment_executor_role_request,
    alignment_executor_session_ref_event_payload,
    alignment_executor_session_ref_from_output,
    alignment_native_resume_fallback_event_payload,
    alignment_request_can_native_resume_fallback,
    alignment_waiting_user_transition_plan,
    apply_alignment_native_resume_fallback,
)


def test_alignment_execution_state_defaults_to_normal_generation() -> None:
    assert AlignmentExecutionState() == AlignmentExecutionState(mode="normal", validation_error="", invalid_yaml="")
    assert AlignmentExecutionState(mode="repair", validation_error="bad bundle", invalid_yaml="version: 1\n").mode == "repair"


def test_alignment_bundle_candidate_outcome_classifies_ready_repair_and_failed() -> None:
    assert alignment_bundle_candidate_outcome(ok=True, error="", repair_attempts=0, bundle_yaml="").action == "ready"

    repair = alignment_bundle_candidate_outcome(
        ok=False,
        error="bundle is invalid",
        repair_attempts=0,
        bundle_yaml="version: 1\n",
    )
    assert repair.action == "repair"
    assert repair.error == "bundle is invalid"
    assert repair.next_repair_attempts == 1
    assert repair.next_state == AlignmentExecutionState(
        mode="repair",
        validation_error="bundle is invalid",
        invalid_yaml="version: 1\n",
    )

    failed = alignment_bundle_candidate_outcome(
        ok=False,
        error="still invalid",
        repair_attempts=1,
        bundle_yaml="version: 1\n",
    )
    assert failed.action == "failed"
    assert failed.error == "still invalid"
    assert failed.next_state is None


def test_alignment_bundle_executor_settings_issues_ignore_default_preset_sessions() -> None:
    session = {"executor_kind": "codex", "executor_mode": "preset"}
    bundle = {"loop": {"executor_kind": "custom"}, "role_definitions": [{"key": "builder", "executor_mode": "command"}]}

    assert alignment_bundle_executor_settings_issues(session, bundle) == []


def test_alignment_bundle_executor_settings_issues_report_runtime_surface_mismatches() -> None:
    session = {
        "executor_kind": "custom",
        "executor_mode": "command",
        "command_cli": "uv",
        "command_args_text": "run loopora",
        "model": "gpt-5",
        "reasoning_effort": "medium",
    }
    bundle = {
        "loop": {
            "executor_kind": "custom",
            "executor_mode": "preset",
            "command_cli": "uv",
            "command_args_text": "run loopora",
            "model": " gpt-5 ",
            "reasoning_effort": "low",
        },
        "role_definitions": [
            {
                "key": "builder",
                "executor_kind": "codex",
                "executor_mode": "command",
                "command_cli": "uv",
                "command_args_text": "run loopora",
                "model": "gpt-5",
                "reasoning_effort": "medium",
            }
        ],
    }

    assert alignment_bundle_executor_settings_issues(session, bundle) == [
        "alignment bundle must preserve selected Web executor settings for command/custom sessions: "
        "loop.executor_mode, loop.reasoning_effort, role_definition builder.executor_kind"
    ]


def test_alignment_waiting_user_transition_plan_projects_terminal_dialogue_state() -> None:
    assert alignment_waiting_user_transition_plan() == AlignmentSessionTransitionPlan(
        action="waiting_user",
        update_fields={"status": "waiting_user", "error_message": ""},
        event_type="alignment_waiting_user",
        event_payload={"status": "waiting_user"},
        finish_session=True,
        clear_active_child_pid=True,
    )


def test_alignment_bundle_transition_plans_project_ready_and_repair_state() -> None:
    ready = alignment_bundle_ready_transition_plan(bundle_path="/tmp/alignment/bundle.yaml")

    assert ready == AlignmentSessionTransitionPlan(
        action="ready",
        update_fields={"status": "ready", "alignment_stage": "ready", "error_message": ""},
        event_type="alignment_ready",
        event_payload={"status": "ready", "bundle_path": "/tmp/alignment/bundle.yaml"},
        finish_session=True,
        clear_active_child_pid=True,
    )

    repair = alignment_bundle_candidate_outcome(
        ok=False,
        error="bundle is invalid",
        repair_attempts=0,
        bundle_yaml="version: 1\n",
    )

    assert alignment_bundle_repair_transition_plan(repair) == AlignmentSessionTransitionPlan(
        action="repair",
        update_fields={"status": "repairing", "repair_attempts": 1, "error_message": "bundle is invalid"},
        event_type="alignment_repair_started",
        event_payload={"status": "repairing", "error": "bundle is invalid"},
    )


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
    assert request.idle_timeout_seconds == 12.5
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
    }


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
    assert alignment_executor_session_ref_event_payload(request, {"session_id": "new-session", "provider": "opencode"}) == {
        "executor_kind": "opencode",
        "session_ref": {"session_id": "new-session", "provider": "opencode"},
        "native_resume_available": True,
    }


def test_alignment_executor_output_action_prioritizes_bundle_before_waiting_user() -> None:
    assert (
        alignment_executor_output_action(
            {"needs_user_input": True, "alignment_phase": "blocked"},
            assistant_message="I still have a question.",
            bundle_yaml="version: 1\n",
        )
        == "bundle"
    )


def test_alignment_executor_output_action_waits_for_user_on_explicit_need_or_blocked_message() -> None:
    assert alignment_executor_output_action({"needs_user_input": True}, assistant_message="", bundle_yaml="") == "waiting_user"
    assert (
        alignment_executor_output_action(
            {"status": "blocked"},
            assistant_message="This task does not fit a Loop.",
            bundle_yaml="",
        )
        == "waiting_user"
    )
    assert alignment_executor_output_waits_for_user({"alignment_phase": "blocked"}, assistant_message="Need a decision.") is True
    assert alignment_executor_output_waits_for_user({"alignment_phase": "blocked"}, assistant_message="") is False


def test_alignment_executor_output_action_fails_without_bundle_or_user_wait() -> None:
    assert alignment_executor_output_action({}, assistant_message="", bundle_yaml="") == "failed"
    assert alignment_executor_output_failure_message("") == "Agent finished without a bundle or a clarifying question."
    assert alignment_executor_output_failure_message("Done without bundle.") == "Done without bundle."
