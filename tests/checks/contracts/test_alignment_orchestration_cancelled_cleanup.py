from alignment_orchestration_test_support import AlignmentOrchestrationHarness, execute_alignment_orchestration
from loopora.executor import ExecutionStopped


def test_alignment_orchestration_records_cancelled_execution_as_cancelled_failure() -> None:
    harness = AlignmentOrchestrationHarness([{"raise": ExecutionStopped("stop requested")}])

    execute_alignment_orchestration(harness)

    assert harness.failures == [
        {"session_id": "align_1", "error": "Cancelled by user.", "event_type": "alignment_cancelled"}
    ]
    assert harness.repository.updates[-1] == {"session_id": "align_1", "fields": {"clear_active_child_pid": True}}
