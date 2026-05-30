from pathlib import Path

from loopora.service_alignment_bundle_candidate import AlignmentBundleCandidateContext, handle_alignment_bundle_candidate
from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext
from loopora.service_alignment_execution import AlignmentExecutionState
from loopora.service_types import LooporaError


class FakeAlignmentBundleCandidateRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def bundle_candidate_context(
    repo: FakeAlignmentBundleCandidateRepository,
    *,
    validation_error: Exception | None = None,
) -> tuple[AlignmentBundleCandidateContext, list[dict], list[dict], list[dict]]:
    validation_logs: list[dict] = []
    transition_plans: list[dict] = []
    failures: list[dict] = []

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def load_validated_bundle_text(_session: dict, raw_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
        if validation_error is not None:
            semantic_issues.append("loop.done_when")
            raise validation_error
        return {"loop": {"name": "Candidate Loop"}}, raw_yaml.rstrip() + "\n# normalized\n"

    def write_validation_log(session: dict, validation: dict) -> None:
        validation_logs.append({"session": session, "validation": validation})

    def lifecycle_context() -> AlignmentBundleLifecycleContext:
        return AlignmentBundleLifecycleContext(
            repository=repo,
            get_session=get_session,
            write_validation_log=write_validation_log,
        )

    def apply_transition_plan(session_id: str, plan) -> None:
        fields = dict(plan.update_fields)
        if plan.finish_session:
            fields["finished_at"] = "2026-05-30T00:00:01Z"
        if plan.clear_active_child_pid:
            fields["clear_active_child_pid"] = True
        repo.update_alignment_session(session_id, **fields)
        repo.append_alignment_event(session_id, plan.event_type, plan.event_payload)
        transition_plans.append({"action": plan.action, "fields": fields, "event_type": plan.event_type, "payload": plan.event_payload})

    def fail_session(session_id: str, error: str) -> None:
        repo.update_alignment_session(
            session_id,
            status="failed",
            finished_at="2026-05-30T00:00:02Z",
            clear_active_child_pid=True,
            error_message=error,
        )
        repo.append_alignment_event(session_id, "alignment_failed", {"status": "failed", "error": error})
        failures.append({"session_id": session_id, "error": error})

    context = AlignmentBundleCandidateContext(
        repository=repo,
        get_session=get_session,
        load_validated_bundle_text=load_validated_bundle_text,
        bundle_lifecycle_context=lifecycle_context,
        apply_transition_plan=apply_transition_plan,
        fail_session=fail_session,
        now=lambda: "2026-05-30T00:00:00Z",
    )
    return context, validation_logs, transition_plans, failures


def candidate_session(tmp_path: Path, *, repair_attempts: object = 0) -> dict:
    return {
        "id": "align_candidate",
        "status": "running",
        "bundle_path": str(tmp_path / "align_candidate" / "artifacts" / "bundle.yml"),
        "repair_attempts": repair_attempts,
    }


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
