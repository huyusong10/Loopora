from __future__ import annotations

from loopora.agent_native_next_step_summary import agent_next_step_summary
from loopora.cli_agent_work_panel import agent_work_panel


def test_agent_work_panel_distinguishes_terminal_unproven_and_proven_next_actions() -> None:
    terminal_unproven = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "insufficient_evidence"}},
            "complete": True,
            "task_next_action": {
                "kind": "continue_evidence",
                "guidance": "Run lifecycle is complete, but the task is not proven. Run /loopora-run again in the same Agent session to start the next evidence pass from this verdict.",
            },
        }
    )
    proven = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "passed"}},
            "complete": True,
        }
    )

    assert terminal_unproven["state"] == "needs_more_evidence"
    assert terminal_unproven["role_handoff_status"] == "not_applicable"
    assert terminal_unproven["next_action"] == "Run lifecycle is complete, but the task is not proven. Run /loopora-run again in the same Agent session to start the next evidence pass from this verdict."
    assert "/loopora-run" in terminal_unproven["next_action"]
    assert proven["state"] == "task_proven"
    assert proven["role_handoff_status"] == "not_applicable"
    assert proven["next_action"] == "Task verdict passed; no new evidence pass starts unless the task scope changes."


def test_agent_work_panel_distinguishes_lifecycle_retry_from_evidence_gap() -> None:
    panel = agent_work_panel(
        {
            "run": {"id": "run_panel", "status": "failed", "task_verdict": {"status": "not_evaluated"}},
            "complete": True,
            "task_next_action": {
                "kind": "retry_lifecycle_failure",
                "guidance": "Run failed before a recordable evidence result.",
                "recording_blocked_reason": "cannot accept lifecycle failure as a run result",
            },
        }
    )

    assert panel["state"] == "retry_lifecycle_failure"
    assert panel["task_outcome"] == "not_proven_retry_lifecycle_failure"
    assert panel["next_action"] == "Run failed before a recordable evidence result."
    assert panel["evidence_focus"] == ""


def test_agent_work_panel_prioritizes_dispatch_repair_before_submitted_blocker() -> None:
    panel = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "not_evaluated"}},
            "next_step": {
                "step_id": "builder_step",
                "role": {"name": "Builder"},
                "role_dispatch": {
                    "target_agent": "loopora-builder",
                    "target_agent_config_exists": False,
                    "target_agent_config_path": ".codex/agents/loopora-builder.toml",
                },
                "submit_hint": {"command": "loopora agent codex submit --run-id run_panel"},
            },
            "submitted_step": {
                "step_id": "gatekeeper_step",
                "status": "blocked",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                "recommended_next_action": "No action needed.",
            },
            "adapter": "codex",
            "workdir": "/tmp/project",
        }
    )

    assert panel["state"] == "dispatch_unavailable"
    assert panel["target_agent"] == "loopora-builder"
    assert panel["role_handoff_status"] == "blocked_before_dispatch"
    assert panel["role_handoff_owner"] == "current_host_agent"
    assert "repair the managed role agent config" in panel["next_action"]


def test_agent_work_panel_exposes_ready_role_handoff_and_evidence_focus() -> None:
    panel = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "not_evaluated"}},
            "next_step": {
                "step_id": "builder_step",
                "role": {"name": "Focused Builder"},
                "role_dispatch": {"target_agent": "loopora-builder", "target_agent_config_exists": True},
                "required_coverage": {
                    "status": "pending",
                    "top_gaps": [
                        {
                            "target_id": "done_when.check_001",
                            "status": "missing",
                            "text": "The primary user flow still needs direct proof.",
                        }
                    ],
                },
            },
            "adapter": "codex",
            "workdir": "/tmp/project",
        }
    )

    assert panel["state"] == "awaiting_agent"
    assert panel["target_agent"] == "loopora-builder"
    assert panel["role_handoff_status"] == "ready_for_host_dispatch"
    assert panel["role_handoff_owner"] == "current_host_agent"
    assert panel["evidence_focus"].startswith("done_when.check_001 [missing]")
    assert panel["top_gaps"][0]["text"] == "The primary user flow still needs direct proof."


def test_agent_work_panel_does_not_synthesize_dispatch_repair_workdir() -> None:
    next_step = {
        "step_id": "builder_step",
        "role": {"name": "Builder"},
        "role_dispatch": {
            "target_agent": "loopora-builder",
            "target_agent_config_exists": False,
            "target_agent_config_path": ".codex/agents/loopora-builder.toml",
        },
    }

    summary = agent_next_step_summary(next_step, adapter="codex", workdir="")
    panel = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "not_evaluated"}},
            "next_step": next_step,
            "adapter": "codex",
        }
    )

    assert summary["dispatch_unavailable"]["workdir_available"] is False
    assert "check_command" not in summary["dispatch_unavailable"]
    assert "repair_command" not in summary["dispatch_unavailable"]
    assert panel["state"] == "dispatch_unavailable"
    assert panel["next_action"] == "Recover the project workdir before repairing the managed role agent config."


def test_agent_work_panel_derives_blocked_submit_action_from_blocker() -> None:
    panel = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "failed"}},
            "submitted_step": {
                "step_id": "gatekeeper_step",
                "status": "blocked",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                "recommended_next_action": "No action needed.",
            },
        }
    )

    assert panel["state"] == "blocked"
    assert panel["next_action"].startswith("Produce new project-owned proof")
    assert "No action needed" not in panel["next_action"]
