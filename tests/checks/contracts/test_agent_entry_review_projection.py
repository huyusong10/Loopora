from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_agent_entry_review import (
    agent_entry_candidate_adapter,
    agent_entry_candidate_payload,
    agent_entry_launch_projection,
    agent_entry_review_projection,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
READY_CANDIDATE_BYTES = 42


def test_agent_entry_review_projection_has_dedicated_boundary() -> None:
    recovery_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_run_recovery.py").read_text(
        encoding="utf-8"
    )
    review_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_agent_entry_review.py").read_text(
        encoding="utf-8"
    )
    session_projection_source = (
        REPO_ROOT / "src" / "loopora" / "service_alignment_session_projection.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_alignment_agent_entry_review import" in recovery_source
    assert "from loopora.service_alignment_agent_entry_review import" in session_projection_source
    for marker in (
        "def agent_entry_review_projection",
        "def agent_entry_launch_projection",
        "def agent_entry_review_decision_options",
    ):
        assert marker in review_source
        assert marker not in recovery_source
    assert "service_alignment_agent_entry_review.py" in design_source


def test_agent_entry_candidate_payload_and_adapter_preserve_event_priority() -> None:
    payload = agent_entry_candidate_payload({"payload": {"adapter": "codex", "entry_source": "codex_project_skill"}})

    assert payload == {"adapter": "codex", "entry_source": "codex_project_skill"}
    assert agent_entry_candidate_payload({"payload": "not-a-dict"}) == {}
    assert agent_entry_candidate_adapter({"executor_kind": "claude"}, payload) == "codex"
    assert agent_entry_candidate_adapter({"executor_kind": "claude"}, {}) == "claude"


def test_agent_entry_review_projection_exposes_web_review_decision_payload() -> None:
    session = {
        "id": "align_1",
        "status": "idle",
        "alignment_stage": "clarifying",
        "executor_kind": "codex",
        "transcript": [{"role": "user", "content": "为退款治理准备 Loop。"}],
    }
    candidate_event = {
        "payload": {
            "candidate_origin": "agent_entry",
            "requires_web_alignment": True,
            "requires_candidate_repair": False,
            "has_candidate_yaml": False,
            "adapter": "codex",
            "entry_source": "codex_project_skill",
            "candidate_bytes": "bad",
        }
    }

    review = agent_entry_review_projection(
        session,
        candidate_event=candidate_event,
        task_message="为退款治理准备 Loop。",
        missing_judgment_item_ids=["success_surface"],
    )

    assert review["source"] == "agent_entry"
    assert review["review_mode"] == "missing_candidate_plan"
    assert review["not_runnable"] is True
    assert review["candidate_bytes"] == 0
    assert review["missing_judgment_item_ids"] == ["success_surface"]
    assert review["decision_options"][0]["id"] == "continue_web_review_evidence_first"
    assert review["decision_options"][0]["recommended"] is True
    assert "证据优先" in review["suggested_reply"]
    assert agent_entry_review_projection(
        {**session, "working_agreement": {"summary": "already started"}},
        candidate_event=candidate_event,
        task_message="为退款治理准备 Loop。",
        missing_judgment_item_ids=["success_surface"],
    ) == {}


def test_agent_entry_launch_projection_prefers_ready_event_fingerprint(tmp_path) -> None:
    candidate_event = {
        "payload": {
            "candidate_origin": "agent_entry",
            "adapter": "codex",
            "entry_source": "codex_project_skill",
            "host_context_id": "thread-a",
            "candidate_sha256": "candidate-sha",
            "candidate_bytes": 12,
            "ready_candidate_sha256": "stale-ready-sha",
            "ready_candidate_bytes": 11,
        }
    }
    ready_event = {
        "payload": {
            "ready_candidate_sha256": "ready-sha",
            "ready_candidate_bytes": READY_CANDIDATE_BYTES,
        }
    }

    launch = agent_entry_launch_projection(
        {"id": "align_1", "workdir": str(tmp_path), "executor_kind": "codex"},
        candidate_event=candidate_event,
        ready_event=ready_event,
    )

    assert launch["source"] == "agent_entry"
    assert launch["slash_command"] == "/loopora-run"
    assert launch["loop_command"].endswith("--json")
    assert "--context-id thread-a" in launch["loop_command"]
    assert launch["ready_candidate_sha256"] == "ready-sha"
    assert launch["ready_candidate_bytes"] == READY_CANDIDATE_BYTES
