from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loopora.run_artifact_layout_setup import initialize_run_artifact_layout, legacy_role_output_alias_paths
from loopora.structured_numbers import coerced_non_negative_int


@dataclass(frozen=True)
class RunArtifactLayout:
    run_dir: Path

    @property
    def workdir_path(self) -> Path:
        try:
            return self.run_dir.parents[2]
        except IndexError:
            return self.run_dir.parent

    @property
    def summary_path(self) -> Path:
        return self.run_dir / "summary.md"

    @property
    def contract_dir(self) -> Path:
        return self.run_dir / "contract"

    @property
    def contract_spec_path(self) -> Path:
        return self.contract_dir / "spec.md"

    @property
    def contract_compiled_spec_path(self) -> Path:
        return self.contract_dir / "compiled_spec.json"

    @property
    def contract_strategy_source_path(self) -> Path:
        return self.contract_dir / "strategy_source.json"

    @property
    def contract_workflow_path(self) -> Path:
        return self.contract_dir / "workflow.json"

    @property
    def run_contract_path(self) -> Path:
        return self.contract_dir / "run_contract.json"

    @property
    def contract_auto_checks_path(self) -> Path:
        return self.contract_dir / "auto_checks.json"

    @property
    def workspace_baseline_path(self) -> Path:
        return self.contract_dir / "workspace_baseline.json"

    @property
    def contract_prompts_dir(self) -> Path:
        return self.contract_dir / "prompts"

    @property
    def context_dir(self) -> Path:
        return self.run_dir / "context"

    @property
    def role_requests_path(self) -> Path:
        return self.context_dir / "role_requests.jsonl"

    @property
    def latest_state_path(self) -> Path:
        return self.context_dir / "latest_state.json"

    @property
    def latest_iteration_summary_path(self) -> Path:
        return self.context_dir / "latest_iteration_summary.json"

    @property
    def check_planner_dir(self) -> Path:
        return self.context_dir / "check_planner"

    @property
    def check_planner_output_raw_path(self) -> Path:
        return self.check_planner_dir / "output.raw.json"

    @property
    def check_planner_prompt_path(self) -> Path:
        return self.check_planner_dir / "prompt.md"

    @property
    def timeline_dir(self) -> Path:
        return self.run_dir / "timeline"

    @property
    def timeline_events_path(self) -> Path:
        return self.timeline_dir / "events.jsonl"

    @property
    def timeline_iterations_path(self) -> Path:
        return self.timeline_dir / "iterations.jsonl"

    @property
    def timeline_metrics_path(self) -> Path:
        return self.timeline_dir / "metrics.jsonl"

    @property
    def timeline_stagnation_path(self) -> Path:
        return self.timeline_dir / "stagnation.json"

    @property
    def timeline_workspace_guard_path(self) -> Path:
        return self.timeline_dir / "workspace_guard.json"

    @property
    def evidence_dir(self) -> Path:
        return self.run_dir / "evidence"

    @property
    def evidence_ledger_path(self) -> Path:
        return self.evidence_dir / "ledger.jsonl"

    @property
    def evidence_coverage_path(self) -> Path:
        return self.evidence_dir / "coverage.json"

    @property
    def evidence_manifest_path(self) -> Path:
        return self.evidence_dir / "manifest.json"

    @property
    def task_verdict_path(self) -> Path:
        return self.evidence_dir / "task_verdict.json"

    @property
    def iterations_dir(self) -> Path:
        return self.run_dir / "iterations"

    @property
    def legacy_events_path(self) -> Path:
        return self.run_dir / "events.jsonl"

    @property
    def legacy_iterations_path(self) -> Path:
        return self.run_dir / "iteration_log.jsonl"

    @property
    def legacy_metrics_path(self) -> Path:
        return self.run_dir / "metrics_history.jsonl"

    @property
    def legacy_auto_checks_path(self) -> Path:
        return self.run_dir / "auto_checks.json"

    @property
    def legacy_workspace_guard_path(self) -> Path:
        return self.run_dir / "workspace_guard.json"

    def contract_prompt_path(self, prompt_ref: str) -> Path:
        return self.contract_prompts_dir / prompt_ref

    def iteration_dir(self, iter_id: int) -> Path:
        return self.iterations_dir / f"iter_{coerced_non_negative_int(iter_id):03d}"

    def iteration_summary_path(self, iter_id: int) -> Path:
        return self.iteration_dir(iter_id) / "summary.json"

    def step_dir(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.iteration_dir(iter_id) / "steps" / f"{coerced_non_negative_int(step_order):02d}__{step_id}"

    def step_metadata_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "metadata.json"

    def step_instruction_context_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "step_instruction_context.json"

    def step_agent_view_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "agent_step_view.json"

    def step_contract_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "step_contract.json"

    def step_prompt_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "prompt.md"

    def step_output_raw_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "output.raw.json"

    def step_output_normalized_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "output.normalized.json"

    def step_handoff_path(self, iter_id: int, step_order: int, step_id: str) -> Path:
        return self.step_dir(iter_id, step_order, step_id) / "handoff.json"

    def relative(self, path: Path) -> str:
        return path.relative_to(self.run_dir).as_posix()

    def workspace_relative(self, path: Path) -> str:
        try:
            return path.relative_to(self.workdir_path).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    def initialize(self) -> None:
        initialize_run_artifact_layout(self)

    def legacy_role_output_paths(self, archetype: str) -> list[Path]:
        return legacy_role_output_alias_paths(self.run_dir, archetype)


def artifact_ref(layout: RunArtifactLayout, path: Path, *, kind: str, label: str = "") -> dict[str, str]:
    return {
        "kind": kind,
        "label": label,
        "relative_path": layout.relative(path),
        "workspace_path": layout.workspace_relative(path),
        "absolute_path": str(path.resolve()),
    }
