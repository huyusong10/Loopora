from alignment_orchestration_test_support import AlignmentOrchestrationHarness, execute_alignment_orchestration


def test_alignment_orchestration_waits_for_user_without_promoting_runtime_success_to_bundle() -> None:
    harness = AlignmentOrchestrationHarness(
        [{"needs_user_input": True, "assistant_message": "I need one decision before compiling."}]
    )

    execute_alignment_orchestration(harness)

    assert harness.transition_actions == ["waiting_user"]
    assert harness.bundle_candidates == []
    assert harness.failures == []
