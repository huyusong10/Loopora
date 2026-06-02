from __future__ import annotations

from pathlib import Path

from runner_helpers import _read_jsonl


def complete_strategy_archetypes(run: dict) -> list[str]:
    iteration_log = _read_jsonl(Path(run["runs_dir"]) / "iteration_log.jsonl")
    workflow_entry = next(entry for entry in iteration_log if entry["phase"] == "complete")
    return [step["archetype"] for step in workflow_entry["strategy_steps"]]
