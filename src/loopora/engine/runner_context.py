from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from loopora.recovery import RetryConfig
from loopora.run_artifacts import read_jsonl


def evidence_context_with_canonical_items(context_packet: dict, layout: object) -> dict:
    evidence_context = context_packet.get("evidence") if isinstance(context_packet.get("evidence"), dict) else {}
    known_ids = {str(item).strip() for item in list(evidence_context.get("known_ids") or []) if str(item).strip()}
    current_items = [item for item in list(evidence_context.get("items") or []) if isinstance(item, dict)]
    current_ids = {str(item.get("id") or "").strip() for item in current_items if str(item.get("id") or "").strip()}
    if not known_ids or known_ids.issubset(current_ids):
        return dict(evidence_context)
    canonical_items = [item for item in read_jsonl(layout.evidence_ledger_path) if isinstance(item, dict) and str(item.get("id") or "").strip() in known_ids]
    return {**dict(evidence_context), "items": canonical_items}


@dataclass
class RunnerRunContext:
    run_id: str
    run: dict
    run_dir: Path
    strategy_source: dict
    executor: object
    compiled_spec: dict
    retry_config: RetryConfig
    prompt_files: dict[str, str]
    layout: object
    run_contract: dict
    strategy_steps: list[dict]
    strategy_controls: list[dict]
    control_fire_counts: dict[str, int]
    runner_started_at: float
    role_by_id: dict[str, dict]
    completion_mode: str
    last_gatekeeper_result: dict | None = None


@dataclass
class RunnerIterationState:
    iter_id: int
    previous_composite: object
    stagnation: dict
    previous_outputs_by_step: dict[str, dict]
    previous_outputs_by_role: dict[str, dict]
    previous_outputs_by_archetype: dict[str, dict]
    previous_handoffs_by_step: dict[str, dict]
    previous_handoffs_by_role: dict[str, dict]
    previous_iteration_summary: dict | None
    previous_session_refs_by_step: dict[str, dict]
    step_results: list[dict] = field(default_factory=list)
    current_outputs_by_step: dict[str, dict] = field(default_factory=dict)
    current_outputs_by_role: dict[str, dict] = field(default_factory=dict)
    current_outputs_by_archetype: dict[str, dict] = field(default_factory=dict)
    current_handoffs: list[dict] = field(default_factory=list)
    current_session_refs_by_step: dict[str, dict] = field(default_factory=dict)
    current_gatekeeper_result: dict | None = None
    current_guide_result: dict | None = None

    def snapshot(self) -> dict[str, object]:
        return {
            "current_outputs_by_step": dict(self.current_outputs_by_step),
            "current_outputs_by_role": dict(self.current_outputs_by_role),
            "current_outputs_by_archetype": dict(self.current_outputs_by_archetype),
            "current_handoffs": list(self.current_handoffs),
        }
