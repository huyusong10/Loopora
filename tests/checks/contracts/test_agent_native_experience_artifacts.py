from __future__ import annotations

import json
from pathlib import Path

from loopora.agent_native_experience_artifacts import write_agent_v3_experience_artifact


def test_agent_v3_experience_artifact_persists_work_panel_without_raw_payload(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run_agent"
    panel = {
        "state": "awaiting_agent",
        "run_id": "run_agent",
        "task_proven": False,
        "task_outcome": "not_yet_evaluated",
        "current_role": "Builder",
        "current_step_id": "builder_step",
        "target_agent": "loopora-builder",
        "role_handoff_status": "ready_for_host_dispatch",
        "role_handoff_owner": "current_host_agent",
        "next_action": "Dispatch loopora-builder.",
        "evidence_focus": "Builder proof file.",
        "top_gaps": [],
        "ask_user": "",
        "todo_items": ["Claim current step", "Submit result"],
        "run_url": "/runs/run_agent",
    }
    envelope = {
        "schema_version": 3,
        "kind": "agent_run",
        "status": "active",
        "summary": {
            "run_id": "run_agent",
            "agent_work_panel": panel,
            "task_proven": False,
            "task_outcome": "not_yet_evaluated",
            "lifecycle_vs_task": "active_run_task_unproven",
            "run_url": "/runs/run_agent",
        },
        "technical_handoff": {"submit_command": "loopora agent claude submit ..."},
        "diagnostics": {},
        "raw": {"legacy": {"prompt": "large role prompt should not be copied"}},
    }

    write_agent_v3_experience_artifact({"run": {"id": "run_agent", "runs_dir": str(run_dir)}}, envelope)

    latest = json.loads((run_dir / "agent_native" / "experience" / "latest.json").read_text(encoding="utf-8"))
    by_kind = json.loads((run_dir / "agent_native" / "experience" / "latest_agent_run.json").read_text(encoding="utf-8"))
    assert latest == by_kind
    assert latest["agent_work_panel"] == panel
    assert latest["technical_handoff"]["submit_command"] == "loopora agent claude submit ..."
    assert "raw" not in latest
    assert "prompt" not in json.dumps(latest)
