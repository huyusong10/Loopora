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
    repo = FakeAlignmentSessionStateRepository()
    context = AlignmentSessionStateContext(repository=repo, now=lambda: "2026-05-30T00:00:00Z")
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
        {
            "session_id": "align_state",
            "fields": {
                "status": "waiting_user",
                "error_message": "",
                "finished_at": "2026-05-30T00:00:00Z",
                "clear_active_child_pid": True,
            },
        }
    ]
    assert repo.events == [
        {
            "session_id": "align_state",
            "event_type": "alignment_waiting_user",
            "payload": {"status": "waiting_user"},
        }
    ]


def test_apply_alignment_session_transition_plan_preserves_non_terminal_updates() -> None:
    repo = FakeAlignmentSessionStateRepository()
    context = AlignmentSessionStateContext(repository=repo, now=lambda: "unused")
    plan = AlignmentSessionTransitionPlan(
        action="repair",
        update_fields={"status": "repairing", "repair_attempts": 1, "error_message": "invalid bundle"},
        event_type="alignment_repair_started",
        event_payload={"status": "repairing", "error": "invalid bundle"},
    )

    apply_alignment_session_transition_plan(context, "align_state", plan)

    assert repo.updates == [
        {
            "session_id": "align_state",
            "fields": {"status": "repairing", "repair_attempts": 1, "error_message": "invalid bundle"},
        }
    ]
    assert repo.events == [
        {
            "session_id": "align_state",
            "event_type": "alignment_repair_started",
            "payload": {"status": "repairing", "error": "invalid bundle"},
        }
    ]


def test_fail_alignment_session_records_failed_status_and_event_type() -> None:
    repo = FakeAlignmentSessionStateRepository()
    context = AlignmentSessionStateContext(repository=repo, now=lambda: "2026-05-30T00:00:01Z")

    fail_alignment_session(context, "align_state", "Cancelled by user.", event_type="alignment_cancelled")

    assert repo.updates == [
        {
            "session_id": "align_state",
            "fields": {
                "status": "failed",
                "finished_at": "2026-05-30T00:00:01Z",
                "clear_active_child_pid": True,
                "error_message": "Cancelled by user.",
            },
        }
    ]
    assert repo.events == [
        {
            "session_id": "align_state",
            "event_type": "alignment_cancelled",
            "payload": {"status": "failed", "error": "Cancelled by user."},
        }
    ]


def test_alignment_session_state_callbacks_delegate_to_state_commands() -> None:
    repo = FakeAlignmentSessionStateRepository()
    context = AlignmentSessionStateContext(repository=repo, now=lambda: "2026-05-30T00:00:02Z")
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
        {"session_id": "align_state", "fields": {"status": "waiting_user"}},
        {
            "session_id": "align_state",
            "fields": {
                "status": "failed",
                "finished_at": "2026-05-30T00:00:02Z",
                "clear_active_child_pid": True,
                "error_message": "No bundle.",
            },
        },
    ]
    assert repo.events == [
        {
            "session_id": "align_state",
            "event_type": "alignment_waiting_user",
            "payload": {"status": "waiting_user"},
        },
        {
            "session_id": "align_state",
            "event_type": "alignment_failed",
            "payload": {"status": "failed", "error": "No bundle."},
        },
    ]
