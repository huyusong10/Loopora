from alignment_orchestration_test_support import AlignmentOrchestrationHarness, execute_alignment_orchestration


def test_alignment_orchestration_accepts_bundle_candidate_and_cleans_dead_worker_thread() -> None:
    harness = AlignmentOrchestrationHarness(
        [
            {
                "alignment_phase": "bundle",
                "assistant_message": "I prepared the Loop.",
                "bundle_yaml": "version: 1\n",
                "decision_options": [{"id": "import"}],
                "missing_items": ["runtime_contract"],
            }
        ]
    )

    execute_alignment_orchestration(harness)

    assert harness.run_requests == [
        {"session_id": "align_1", "mode": "normal", "validation_error": "", "invalid_yaml": ""}
    ]
    assert harness.recorded_messages[0]["message"] == "I prepared the Loop."
    assert harness.recorded_messages[0]["decision_options"] == [{"id": "import"}]
    assert harness.recorded_messages[0]["missing_items"] == ["runtime_contract"]
    assert harness.bundle_candidates == ["version: 1"]
    assert harness.failures == []
    assert harness.repository.updates[-1] == {"session_id": "align_1", "fields": {"clear_active_child_pid": True}}
    assert "alignment:align_1" not in harness.threads
