from __future__ import annotations

from loopora.web_streaming import MAX_EVENT_CURSOR_ID, parse_sse_last_event_id, stream_error_payload


VALID_EVENT_CURSOR_ID = 42


def test_streaming_cursor_helpers_require_strict_integer_boundaries() -> None:
    assert parse_sse_last_event_id(str(VALID_EVENT_CURSOR_ID)) == VALID_EVENT_CURSOR_ID
    assert parse_sse_last_event_id(f" {VALID_EVENT_CURSOR_ID} ") == VALID_EVENT_CURSOR_ID
    assert parse_sse_last_event_id("+42") is None
    assert parse_sse_last_event_id("42.0") is None
    assert parse_sse_last_event_id(str(MAX_EVENT_CURSOR_ID + 1)) is None

    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id=VALID_EVENT_CURSOR_ID)["after_id"] == VALID_EVENT_CURSOR_ID
    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id="42")["after_id"] == 0
    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id=True)["after_id"] == 0
    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id=MAX_EVENT_CURSOR_ID + 1)["after_id"] == 0
