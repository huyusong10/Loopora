from __future__ import annotations

from agent_run_recovery_test_support import AgentRecoveryRepository, FallbackAgentRecoveryRepository
from loopora.service_alignment_run_recovery import (
    agent_recovery_alignment_sessions,
    agent_recovery_session_has_candidate_yaml,
)


def test_agent_recovery_alignment_sessions_prefers_full_repository_lookup() -> None:
    repo = AgentRecoveryRepository(
        sessions=[{"id": "align_1"}, {"id": "align_2"}],
        events_by_session={},
    )

    assert agent_recovery_alignment_sessions(repo) == [{"id": "align_1"}, {"id": "align_2"}]
    assert repo.used_all_sessions is True
    assert repo.list_sessions_limits == []


def test_agent_recovery_alignment_sessions_falls_back_to_bounded_lookup() -> None:
    repo = FallbackAgentRecoveryRepository(
        sessions=[{"id": "align_1"}, {"id": "align_2"}],
        events_by_session={},
    )

    assert agent_recovery_alignment_sessions(repo) == [{"id": "align_1"}, {"id": "align_2"}]
    assert repo.list_sessions_limits == [100]


def test_agent_recovery_session_has_candidate_yaml_reads_bounded_events() -> None:
    repo = AgentRecoveryRepository(
        sessions=[],
        events_by_session={
            "align_1": [
                {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": True}},
            ]
        },
    )

    assert agent_recovery_session_has_candidate_yaml(repo, "align_1") is True
    assert repo.event_limits == [("align_1", 50)]
