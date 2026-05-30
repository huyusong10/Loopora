from __future__ import annotations

from dataclasses import dataclass

from loopora.run_artifacts import RunArtifactLayout


@dataclass(frozen=True)
class StepOutputNormalizationRequest:
    archetype: str
    output: dict
    compiled_spec: dict
    inspector_output: dict | None
    evidence_context: dict | None = None
    current_evidence_id: str = ""


@dataclass(frozen=True)
class StepOutputsWriteRequest:
    layout: RunArtifactLayout
    iter_id: int
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    output: dict
    handoff: dict


@dataclass(frozen=True)
class IterationContextPersistRequest:
    layout: RunArtifactLayout
    run_id: str
    iter_id: int
    step_results: list[dict]
    stagnation: dict
    previous_composite: float | None


@dataclass(frozen=True)
class RunnerSummaryRequest:
    run: dict
    strategy_source: dict
    compiled_spec: dict
    iter_id: int
    step_results: list[dict]
    stagnation: dict
    exhausted: bool
    previous_composite: float | None
