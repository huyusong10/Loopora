from __future__ import annotations

from dataclasses import dataclass

from loopora.executor import CodexExecutor
from loopora.recovery import RetryConfig
from loopora.run_artifacts import RunArtifactLayout


@dataclass(frozen=True)
class RunnerStepRuntimeRequest:
    executor: CodexExecutor
    run: dict
    compiled_spec: dict
    layout: RunArtifactLayout
    iter_id: int
    step: dict
    step_order: int
    role: dict
    prompt_files: dict[str, str]
    execution_settings: dict[str, object]
    run_contract: dict
    current_outputs_by_step: dict[str, dict]
    current_outputs_by_role: dict[str, dict]
    current_outputs_by_archetype: dict[str, dict]
    current_handoffs: list[dict]
    previous_outputs_by_step: dict[str, dict]
    previous_outputs_by_role: dict[str, dict]
    previous_outputs_by_archetype: dict[str, dict]
    previous_handoffs_by_step: dict[str, dict]
    previous_handoffs_by_role: dict[str, dict]
    previous_iteration_summary: dict | None
    previous_session_refs_by_step: dict[str, dict]
    previous_composite: float | None
    stagnation_mode: str
    evidence_progress_mode: str
    covered_check_count: int
    missing_check_count: int
    consecutive_no_required_coverage_delta: int
    retry_config: RetryConfig
    evidence_items_snapshot: list[dict] | None = None
