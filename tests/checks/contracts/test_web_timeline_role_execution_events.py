from __future__ import annotations

from web_timeline_projection_test_support import formatted_timeline_event


def test_timeline_role_execution_formatter_keeps_stable_observation_titles() -> None:
    role_summary = formatted_timeline_event(
        "role_execution_summary",
        {"ok": True, "attempts": 2, "degraded": True, "duration_ms": 12},
        role="Builder",
    )
    string_ok_role_summary = formatted_timeline_event(
        "role_execution_summary",
        {"ok": "false", "error": "failed as string", "duration_ms": 12},
        role="Builder",
    )
    malformed_role_summary = formatted_timeline_event(
        "role_execution_summary",
        {"ok": True, "attempts": "2", "degraded": "false", "duration_ms": "not-a-duration"},
        role="Builder",
    )
    malformed_failure_summary = formatted_timeline_event(
        "role_execution_summary",
        {"ok": "false", "error": "failed as string", "duration_ms": "not-a-duration"},
        role="Builder",
    )
    list_payload_summary = formatted_timeline_event("role_execution_summary", ["not", "a", "mapping"], role="Builder")

    assert role_summary["title"] == "Builder completed"
    assert role_summary["detail"] == "attempts=2, degraded, 12ms"
    assert string_ok_role_summary["title"] == "Builder failed"
    assert string_ok_role_summary["detail"] == "failed as string, 12ms"
    assert malformed_role_summary["title"] == "Builder completed"
    assert malformed_role_summary["detail"] == "ok"
    assert malformed_failure_summary["title"] == "Builder failed"
    assert malformed_failure_summary["detail"] == "failed as string"
    assert list_payload_summary["title"] == "Builder failed"
    assert list_payload_summary["detail"] == ""
