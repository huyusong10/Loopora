from __future__ import annotations

from web_timeline_projection_test_support import formatted_timeline_event


def test_timeline_formatter_defaults_malformed_numeric_event_payloads() -> None:
    malformed_checks = formatted_timeline_event(
        "checks_resolved",
        {"count": "7", "source": "auto_generated"},
    )
    malformed_wait = formatted_timeline_event(
        "iteration_wait_started",
        {"duration_seconds": "30"},
    )
    malformed_abort = formatted_timeline_event(
        "run_aborted",
        {"role": "Builder", "attempts": "2"},
    )
    malformed_guard = formatted_timeline_event(
        "workspace_guard_triggered",
        {"deleted_original_count": "3"},
    )

    assert malformed_checks["detail"] == "0 checks, auto-generated"
    assert malformed_wait["detail"] == "0s"
    assert malformed_abort["detail"] == ""
    assert malformed_guard["detail"] == "deleted=0"
