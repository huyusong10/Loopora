from __future__ import annotations

from agent_run_recovery_test_support import AgentRecoveryRepository
from loopora.service_alignment_run_recovery import (
    agent_candidate_events_include_yaml,
    agent_recovery_agent_entry_candidate_event,
    agent_recovery_agent_entry_ready_event,
    agent_recovery_bundle_sync_failed_event,
    latest_agent_entry_event,
    latest_alignment_bundle_sync_failed_event,
)


def test_agent_recovery_event_lookup_uses_agent_entry_semantics() -> None:
    repo = AgentRecoveryRepository(
        sessions=[],
        events_by_session={
            "align_1": [
                {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "web", "id": "ignored"}},
                {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "agent_entry", "id": "plan"}},
                {"event_type": "agent_candidate_ready_content", "payload": {"candidate_origin": "agent_entry", "id": "ready"}},
                {"event_type": "alignment_bundle_sync_failed", "payload": {"error": "failed"}},
            ]
        },
    )

    assert agent_recovery_agent_entry_candidate_event(repo, "align_1")["payload"]["id"] == "plan"
    assert agent_recovery_agent_entry_ready_event(repo, "align_1")["payload"]["id"] == "ready"
    assert agent_recovery_bundle_sync_failed_event(repo, "align_1")["payload"]["error"] == "failed"
    assert repo.event_limits == [("align_1", 50), ("align_1", 50), ("align_1", 50)]


def test_latest_alignment_bundle_sync_failed_event_returns_last_payload_event() -> None:
    latest = latest_alignment_bundle_sync_failed_event(
        [
            {"event_type": "alignment_bundle_sync_failed", "payload": {"error": "first"}},
            {"event_type": "alignment_bundle_sync_failed", "payload": "not-a-dict"},
            {"event_type": "other", "payload": {"error": "ignored"}},
            {"event_type": "alignment_bundle_sync_failed", "payload": {"error": "last"}},
        ]
    )

    assert latest["payload"] == {"error": "last"}
    assert latest_alignment_bundle_sync_failed_event([{"event_type": "other", "payload": {}}]) == {}


def test_latest_agent_entry_event_returns_last_matching_agent_entry_event() -> None:
    latest = latest_agent_entry_event(
        [
            {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "agent_entry", "id": "first"}},
            {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "web", "id": "ignored"}},
            {"event_type": "agent_candidate_received", "payload": "not-a-dict"},
            {"event_type": "agent_candidate_ready_content", "payload": {"candidate_origin": "agent_entry", "id": "ready"}},
            {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "agent_entry", "id": "last"}},
        ],
        "agent_candidate_received",
    )

    assert latest["payload"]["id"] == "last"
    assert latest_agent_entry_event(
        [{"event_type": "agent_candidate_received", "payload": {"candidate_origin": "web"}}], "agent_candidate_received"
    ) == {}


def test_agent_candidate_events_include_yaml_requires_received_payload_flag() -> None:
    assert agent_candidate_events_include_yaml(
        [
            {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": False}},
            {"event_type": "agent_candidate_ready_content", "payload": {"has_candidate_yaml": True}},
            {"event_type": "agent_candidate_received", "payload": "not-a-dict"},
            {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": True}},
        ]
    )
    assert not agent_candidate_events_include_yaml(
        [
            {"event_type": "agent_candidate_ready_content", "payload": {"has_candidate_yaml": True}},
            {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": False}},
        ]
    )
