from pathlib import Path

from alignment_orchestration_test_support import AlignmentOrchestrationHarness, execute_alignment_orchestration
from loopora.executor import ExecutionStopped
from loopora.service_alignment_orchestration import ALIGNMENT_LOCAL_RUNTIME_ERROR


def test_alignment_orchestration_records_cancelled_execution_as_cancelled_failure() -> None:
    harness = AlignmentOrchestrationHarness([{"raise": ExecutionStopped("stop requested")}])

    execute_alignment_orchestration(harness)

    assert harness.failures == [
        {"session_id": "align_1", "error": "Cancelled by user.", "event_type": "alignment_cancelled"}
    ]
    assert harness.repository.updates[-1] == {"session_id": "align_1", "fields": {"clear_active_child_pid": True}}


def test_alignment_orchestration_redacts_local_runtime_os_errors_from_session_failure(tmp_path: Path) -> None:
    private_path = tmp_path / "private" / "prompt.md"
    harness = AlignmentOrchestrationHarness([{"raise": OSError(f"permission denied: {private_path}")}])

    execute_alignment_orchestration(harness)

    assert harness.failures == [
        {"session_id": "align_1", "error": ALIGNMENT_LOCAL_RUNTIME_ERROR, "event_type": "alignment_failed"}
    ]
    assert "permission denied" not in harness.failures[0]["error"]
    assert str(private_path) not in harness.failures[0]["error"]
