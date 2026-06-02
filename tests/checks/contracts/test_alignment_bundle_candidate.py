from pathlib import Path

from compacted_contract_support import (
    FakeAlignmentBundleCandidateRepository,
    bundle_candidate_context,
    candidate_session,
)
from loopora.service_alignment_bundle_candidate import handle_alignment_bundle_candidate
from loopora.service_alignment_execution import AlignmentExecutionState
from loopora.service_types import LooporaError


def test_alignment_bundle_candidate_writes_validated_bundle_and_marks_ready(tmp_path: Path) -> None:
    repo = FakeAlignmentBundleCandidateRepository(candidate_session(tmp_path))
    context, validation_logs, transition_plans, failures = bundle_candidate_context(repo)

    next_state = handle_alignment_bundle_candidate(context, "align_candidate", "version: 1\n")

    bundle_path = Path(repo.session["bundle_path"])
    assert next_state is None
    assert bundle_path.read_text(encoding="utf-8") == "version: 1\n# normalized\n"
    assert repo.session["status"] == "ready"
    assert repo.session["alignment_stage"] == "ready"
    assert repo.session["clear_active_child_pid"] is True
    assert repo.events[0]["event_type"] == "alignment_bundle_written"
    assert repo.events[1]["event_type"] == "alignment_validation_passed"
    assert repo.events[2] == {
        "event_type": "alignment_ready",
        "payload": {"status": "ready", "bundle_path": str(bundle_path)},
    }
    assert validation_logs[0]["validation"]["ok"] is True
    assert validation_logs[0]["validation"]["checked_at"] == "2026-05-30T00:00:00Z"
    assert transition_plans[0]["action"] == "ready"
    assert failures == []


def test_alignment_bundle_candidate_repair_transition_preserves_invalid_yaml_and_semantic_issue(tmp_path: Path) -> None:
    repo = FakeAlignmentBundleCandidateRepository(candidate_session(tmp_path, repair_attempts=0))
    context, validation_logs, transition_plans, failures = bundle_candidate_context(
        repo,
        validation_error=LooporaError("bundle is missing done_when"),
    )

    next_state = handle_alignment_bundle_candidate(context, "align_candidate", "version: 1")

    assert next_state == AlignmentExecutionState(
        mode="repair",
        validation_error="bundle is missing done_when",
        invalid_yaml="version: 1",
    )
    assert Path(repo.session["bundle_path"]).read_text(encoding="utf-8") == "version: 1\n"
    assert repo.session["status"] == "repairing"
    assert repo.session["repair_attempts"] == 1
    assert repo.session["error_message"] == "bundle is missing done_when"
    assert validation_logs[0]["validation"]["semantic_lint"] == {"ok": False, "issues": ["loop.done_when"]}
    assert [event["event_type"] for event in repo.events] == [
        "alignment_bundle_written",
        "alignment_validation_failed",
        "alignment_repair_started",
    ]
    assert transition_plans[0]["action"] == "repair"
    assert failures == []


def test_alignment_bundle_candidate_second_validation_failure_marks_session_failed(tmp_path: Path) -> None:
    repo = FakeAlignmentBundleCandidateRepository(candidate_session(tmp_path, repair_attempts=1))
    context, validation_logs, transition_plans, failures = bundle_candidate_context(
        repo,
        validation_error=LooporaError("bundle is still invalid"),
    )

    next_state = handle_alignment_bundle_candidate(context, "align_candidate", "version: 1\n")

    assert next_state is None
    assert repo.session["status"] == "failed"
    assert repo.session["clear_active_child_pid"] is True
    assert repo.session["error_message"] == "bundle is still invalid"
    assert validation_logs[0]["validation"]["error"] == "bundle is still invalid"
    assert transition_plans == []
    assert failures == [{"session_id": "align_candidate", "error": "bundle is still invalid"}]
    assert [event["event_type"] for event in repo.events] == [
        "alignment_bundle_written",
        "alignment_validation_failed",
        "alignment_failed",
    ]
