from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.utils import write_json


def write_agent_v3_experience_artifact(result: dict[str, Any], envelope: dict[str, Any]) -> None:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    runs_dir = str(run.get("runs_dir") or "").strip()
    if not runs_dir:
        return
    summary = envelope.get("summary") if isinstance(envelope.get("summary"), dict) else {}
    agent_work_panel = summary.get("agent_work_panel") if isinstance(summary.get("agent_work_panel"), dict) else {}
    payload = {
        "schema_version": 1,
        "kind": str(envelope.get("kind") or "").strip(),
        "status": str(envelope.get("status") or "").strip(),
        "run_id": str(run.get("id") or summary.get("run_id") or "").strip(),
        "agent_work_panel": agent_work_panel,
        "task_proven": summary.get("task_proven"),
        "task_outcome": summary.get("task_outcome"),
        "lifecycle_vs_task": summary.get("lifecycle_vs_task"),
        "run_url": summary.get("run_url"),
        "technical_handoff": envelope.get("technical_handoff") if isinstance(envelope.get("technical_handoff"), dict) else {},
    }
    experience_dir = Path(runs_dir) / "agent_native" / "experience"
    write_json(experience_dir / "latest.json", payload)
    kind = payload["kind"]
    if kind:
        write_json(experience_dir / f"latest_{kind}.json", payload)
