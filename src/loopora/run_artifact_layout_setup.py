from __future__ import annotations

from pathlib import Path
from typing import Protocol

from loopora.run_artifact_io import INITIAL_STAGNATION_STATE
from loopora.utils import ensure_parent, write_json

INITIAL_LATEST_STATE = {
    "latest_iteration": None,
    "latest_by_step": {},
    "latest_by_role": {},
    "latest_by_archetype": {},
    "latest_gatekeeper": None,
    "latest_summary_path": "",
}


class RunArtifactLayoutSetup(Protocol):
    run_dir: Path
    contract_prompts_dir: Path
    context_dir: Path
    check_planner_dir: Path
    timeline_dir: Path
    evidence_dir: Path
    iterations_dir: Path
    timeline_events_path: Path
    timeline_iterations_path: Path
    timeline_metrics_path: Path
    evidence_ledger_path: Path
    legacy_events_path: Path
    legacy_iterations_path: Path
    legacy_metrics_path: Path
    role_requests_path: Path
    timeline_stagnation_path: Path
    latest_state_path: Path


def initialize_run_artifact_layout(layout: RunArtifactLayoutSetup) -> None:
    layout.run_dir.mkdir(parents=True, exist_ok=True)
    layout.contract_prompts_dir.mkdir(parents=True, exist_ok=True)
    layout.context_dir.mkdir(parents=True, exist_ok=True)
    layout.check_planner_dir.mkdir(parents=True, exist_ok=True)
    layout.timeline_dir.mkdir(parents=True, exist_ok=True)
    layout.evidence_dir.mkdir(parents=True, exist_ok=True)
    layout.iterations_dir.mkdir(parents=True, exist_ok=True)
    for path in (
        layout.timeline_events_path,
        layout.timeline_iterations_path,
        layout.timeline_metrics_path,
        layout.evidence_ledger_path,
        layout.legacy_events_path,
        layout.legacy_iterations_path,
        layout.legacy_metrics_path,
        layout.role_requests_path,
    ):
        ensure_parent(path)
        path.touch(exist_ok=True)
    if not layout.timeline_stagnation_path.exists():
        write_json(layout.timeline_stagnation_path, dict(INITIAL_STAGNATION_STATE))
    if not layout.latest_state_path.exists():
        write_json(layout.latest_state_path, dict(INITIAL_LATEST_STATE))


def legacy_role_output_alias_paths(run_dir: Path, archetype: str) -> list[Path]:
    if archetype == "builder":
        return [run_dir / "builder_output.json", run_dir / "generator_output.json"]
    if archetype == "inspector":
        return [run_dir / "inspector_output.json", run_dir / "tester_output.json"]
    if archetype == "gatekeeper":
        return [run_dir / "gatekeeper_verdict.json", run_dir / "verifier_verdict.json"]
    if archetype == "guide":
        return [run_dir / "guide_output.json", run_dir / "challenger_seed.json"]
    return []
