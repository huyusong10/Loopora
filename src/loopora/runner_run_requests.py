from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunnerExhaustionRequest:
    run_id: str
    run: dict
    run_dir: Path
    completion_mode: str
    last_iter_id: int
    summary: str


@dataclass(frozen=True)
class RunnerIterationCheckpointRequest:
    layout: object
    iter_id: int
    step_results: list[dict]
    current_outputs_by_step: dict[str, dict]
    current_outputs_by_role: dict[str, dict]
    current_outputs_by_archetype: dict[str, dict]
    current_session_refs_by_step: dict[str, dict]
    stagnation: dict
    previous_composite: float | None
    run_id: str
