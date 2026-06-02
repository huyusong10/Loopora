from __future__ import annotations

from loopora.service_alignment_execution import (
    AlignmentExecutionState,
    alignment_bundle_candidate_outcome,
    alignment_bundle_executor_settings_issues,
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
