from __future__ import annotations

from agent_run_recovery_test_support import AgentRecoveryRepository
from loopora.service_alignment_run_recovery import agent_run_context_source_entries


def test_agent_run_context_source_entries_filter_by_workdir_adapter_and_agent_entry_event(tmp_path) -> None:
    root = tmp_path / "project"
    other = tmp_path / "other"
    sessions = [
        {"id": "align_codex", "workdir": str(root), "executor_kind": "claude"},
        {"id": "align_claude", "workdir": str(root), "executor_kind": "claude"},
        {"id": "align_other_workdir", "workdir": str(other), "executor_kind": "codex"},
        {"id": "align_web_candidate", "workdir": str(root), "executor_kind": "codex"},
    ]
    repo = AgentRecoveryRepository(
        sessions=sessions,
        events_by_session={
            "align_codex": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "adapter": "codex", "entry_source": "codex_project_skill"},
                }
            ],
            "align_claude": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "entry_source": "claude_project_command"},
                }
            ],
            "align_other_workdir": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "adapter": "codex"},
                }
            ],
            "align_web_candidate": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "web", "adapter": "codex"},
                }
            ],
        },
    )

    entries = agent_run_context_source_entries(
        repo,
        root=root,
        adapter="codex",
        same_workdir=lambda workdir, expected: str(workdir) == str(expected),
    )

    assert [(session["id"], payload["entry_source"], adapter) for session, payload, adapter in entries] == [
        ("align_codex", "codex_project_skill", "codex")
    ]
