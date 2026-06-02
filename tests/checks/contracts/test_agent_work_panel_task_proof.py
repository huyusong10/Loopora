from __future__ import annotations

from loopora.cli_agent_work_panel import agent_work_panel


def test_agent_work_panel_distinguishes_terminal_unproven_and_proven_next_actions() -> None:
    terminal_unproven = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "insufficient_evidence"}},
            "complete": True,
            "task_next_action": {
                "kind": "continue_evidence",
                "guidance": "Run lifecycle is complete, but the task is not proven.",
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
    assert terminal_unproven["next_action"] == (
        "Task proof is still missing; run /loopora-run again in this Agent session to continue evidence."
    )
    assert "complete" not in terminal_unproven["next_action"].lower()
    assert proven["state"] == "task_proven"
    assert proven["next_action"] == "Task verdict passed; no new evidence pass starts unless the task scope changes."


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
    assert "repair the managed role agent config" in panel["next_action"]


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
