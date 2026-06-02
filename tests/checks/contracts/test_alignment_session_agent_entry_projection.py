from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_session_projection import alignment_session_detail_projection


READY_CANDIDATE_BYTES = 84


def test_alignment_session_detail_projection_attaches_agent_entry_views(tmp_path: Path) -> None:
    session = {
        "id": "align_1",
        "status": "idle",
        "workdir": str(tmp_path),
        "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
        "transcript": [{"role": "user", "content": "Shape this Loop from the Agent entry."}],
        "executor_kind": "codex",
        "working_agreement": {},
    }
    candidate_event = {
        "event_type": "agent_candidate_received",
        "payload": {
            "candidate_origin": "agent_entry",
            "requires_web_alignment": True,
            "requires_candidate_repair": True,
            "adapter": "codex",
            "entry_source": "codex_project_skill",
            "host_context_id": "thread-a",
            "source_path": str(tmp_path / "loopora-plan.yml"),
            "has_candidate_yaml": True,
            "candidate_sha256": "candidate-sha",
            "candidate_bytes": 42,
        },
    }
    ready_event = {
        "event_type": "agent_candidate_ready_content",
        "payload": {
            "candidate_origin": "agent_entry",
            "ready_candidate_sha256": "ready-sha",
            "ready_candidate_bytes": 84,
        },
    }

    detail = alignment_session_detail_projection(
        session,
        active_statuses={"running"},
        candidate_event=candidate_event,
        ready_event=ready_event,
        missing_judgment_item_ids=["task_scope"],
    )

    assert detail["agent_entry_review"]["source"] == "agent_entry"
    assert detail["agent_entry_review"]["missing_judgment_item_ids"] == ["task_scope"]
    assert detail["agent_entry_review"]["task_message"] == "Shape this Loop from the Agent entry."
    assert detail["agent_entry_launch"]["source"] == "agent_entry"
    assert detail["agent_entry_launch"]["slash_command"] == "/loopora-run"
    assert detail["agent_entry_launch"]["host_context_id"] == "thread-a"
    assert detail["agent_entry_launch"]["ready_candidate_sha256"] == "ready-sha"
    assert detail["agent_entry_launch"]["ready_candidate_bytes"] == READY_CANDIDATE_BYTES
