from loopora.service_alignment_execution import AlignmentSessionTransitionPlan
from loopora.service_alignment_session_state import (
    AlignmentSessionStateContext,
    apply_alignment_session_transition_plan,
    alignment_session_state_callbacks,
    fail_alignment_session,
)


class FakeAlignmentSessionStateRepository:
    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.events: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        self.updates.append({"session_id": session_id, "fields": fields})
        return {"id": session_id, **fields}

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        event = {"session_id": session_id, "event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def test_apply_alignment_session_transition_plan_applies_terminal_fields_and_event() -> None:
    repo, context = state_case("2026-05-30T00:00:00Z")
    plan = AlignmentSessionTransitionPlan(
        action="waiting_user",
        update_fields={"status": "waiting_user", "error_message": ""},
        event_type="alignment_waiting_user",
        event_payload={"status": "waiting_user"},
        finish_session=True,
        clear_active_child_pid=True,
    )

    apply_alignment_session_transition_plan(context, "align_state", plan)

    assert repo.updates == [
        update_record(
            {
                "status": "waiting_user",
                "error_message": "",
                "finished_at": "2026-05-30T00:00:00Z",
                "clear_active_child_pid": True,
            }
        )
    ]
    assert repo.events == [event_record("alignment_waiting_user", {"status": "waiting_user"})]


def test_apply_alignment_session_transition_plan_preserves_non_terminal_updates() -> None:
    repo, context = state_case("unused")
    plan = AlignmentSessionTransitionPlan(
        action="repair",
        update_fields={"status": "repairing", "repair_attempts": 1, "error_message": "invalid bundle"},
        event_type="alignment_repair_started",
        event_payload={"status": "repairing", "error": "invalid bundle"},
    )

    apply_alignment_session_transition_plan(context, "align_state", plan)

    assert repo.updates == [update_record({"status": "repairing", "repair_attempts": 1, "error_message": "invalid bundle"})]
    assert repo.events == [event_record("alignment_repair_started", {"status": "repairing", "error": "invalid bundle"})]


def test_fail_alignment_session_records_failed_status_and_event_type() -> None:
    repo, context = state_case("2026-05-30T00:00:01Z")

    fail_alignment_session(context, "align_state", "Cancelled by user.", event_type="alignment_cancelled")

    assert repo.updates == [failed_update("Cancelled by user.", "2026-05-30T00:00:01Z")]
    assert repo.events == [failed_event("alignment_cancelled", "Cancelled by user.")]


def test_alignment_session_state_callbacks_delegate_to_state_commands() -> None:
    repo, context = state_case("2026-05-30T00:00:02Z")
    callbacks = alignment_session_state_callbacks(context)
    plan = AlignmentSessionTransitionPlan(
        action="waiting_user",
        update_fields={"status": "waiting_user"},
        event_type="alignment_waiting_user",
        event_payload={"status": "waiting_user"},
    )

    callbacks.apply_transition_plan("align_state", plan)
    callbacks.fail_session("align_state", "No bundle.", event_type="alignment_failed")

    assert repo.updates == [
        update_record({"status": "waiting_user"}),
        failed_update("No bundle.", "2026-05-30T00:00:02Z"),
    ]
    assert repo.events == [event_record("alignment_waiting_user", {"status": "waiting_user"}), failed_event("alignment_failed", "No bundle.")]


def state_case(now: str) -> tuple[FakeAlignmentSessionStateRepository, AlignmentSessionStateContext]:
    repo = FakeAlignmentSessionStateRepository()
    return repo, AlignmentSessionStateContext(repository=repo, now=lambda: now)


def update_record(fields: dict) -> dict:
    return {"session_id": "align_state", "fields": fields}


def event_record(event_type: str, payload: dict) -> dict:
    return {"session_id": "align_state", "event_type": event_type, "payload": payload}


def failed_update(error: str, finished_at: str) -> dict:
    return update_record(
        {
            "status": "failed",
            "finished_at": finished_at,
            "clear_active_child_pid": True,
            "error_message": error,
        }
    )


def failed_event(event_type: str, error: str) -> dict:
    return event_record(event_type, {"status": "failed", "error": error})
