from alignment_orchestration_test_support import AlignmentOrchestrationHarness, execute_alignment_orchestration
from loopora.service_alignment_execution import AlignmentExecutionState


def test_alignment_orchestration_reenters_executor_with_repair_state_before_ready() -> None:
    harness = AlignmentOrchestrationHarness(
        [
            {"alignment_phase": "bundle", "assistant_message": "First draft.", "bundle_yaml": "bad: yaml"},
            {"alignment_phase": "bundle", "assistant_message": "Repaired draft.", "bundle_yaml": "version: 1\n"},
        ]
    )
    harness.bundle_candidate_states = [
        AlignmentExecutionState(mode="repair", validation_error="missing evidence flow", invalid_yaml="bad: yaml"),
        None,
    ]

    execute_alignment_orchestration(harness)

    assert harness.run_requests == [
        {"session_id": "align_1", "mode": "normal", "validation_error": "", "invalid_yaml": ""},
        {
            "session_id": "align_1",
            "mode": "repair",
            "validation_error": "missing evidence flow",
            "invalid_yaml": "bad: yaml",
        },
    ]
    assert harness.bundle_candidates == ["bad: yaml", "version: 1"]
    assert [item["message"] for item in harness.recorded_messages] == ["First draft.", "Repaired draft."]
