from __future__ import annotations

from loopora.service_alignment_artifacts import alignment_assistant_message_record, alignment_user_message_record


def test_alignment_assistant_message_record_projects_transcript_entry_and_event_payload() -> None:
    record = alignment_assistant_message_record(
        "Need one more decision.",
        created_at="2026-05-29T00:00:00Z",
        decision_options=[
            {
                "id": "go",
                "label": "Continue",
                "description": "Proceed with the recommended direction.",
                "recommended": True,
                "user_reply": "Continue with the recommended direction.",
            },
            {
                "id": "adjust",
                "label": "Adjust",
                "description": "Revise one of the judgments before continuing.",
                "recommended": False,
                "user_reply": "I want to adjust one judgment.",
            },
            {"id": "bad", "label": "Missing fields"},
        ],
        missing_items=["task_scope"],
    )

    assert record.entry == {
        "role": "assistant",
        "content": "Need one more decision.",
        "created_at": "2026-05-29T00:00:00Z",
        "decision_options": [
            {
                "id": "go",
                "label": "Continue",
                "description": "Proceed with the recommended direction.",
                "recommended": True,
                "user_reply": "Continue with the recommended direction.",
            },
            {
                "id": "adjust",
                "label": "Adjust",
                "description": "Revise one of the judgments before continuing.",
                "recommended": False,
                "user_reply": "I want to adjust one judgment.",
            },
        ],
        "missing_items": ["task_scope"],
    }
    assert record.event_payload == {
        "role": "assistant",
        "content": "Need one more decision.",
        "decision_options": record.entry["decision_options"],
        "missing_items": ["task_scope"],
    }


def test_alignment_assistant_message_record_omits_empty_optional_fields() -> None:
    record = alignment_assistant_message_record("Done.", created_at="now", decision_options=[], missing_items=[])

    assert record.entry == {"role": "assistant", "content": "Done.", "created_at": "now"}
    assert record.event_payload == {"role": "assistant", "content": "Done."}


def test_alignment_user_message_record_projects_transcript_entry_and_event_payload() -> None:
    record = alignment_user_message_record("Please continue.", created_at="2026-05-29T00:01:00Z")

    assert record.entry == {
        "role": "user",
        "content": "Please continue.",
        "created_at": "2026-05-29T00:01:00Z",
    }
    assert record.event_payload == {"role": "user", "content": "Please continue."}
