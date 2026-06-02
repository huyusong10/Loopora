from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.context_flow import StepInstructionContextRequest, build_step_instruction_context
from loopora.run_artifacts import RunArtifactLayout


def build_step_context(tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    layout_name = overrides.pop("layout_name", "run_prompt")
    layout = RunArtifactLayout(tmp_path / layout_name)
    layout.initialize()
    role = overrides.pop("role", gatekeeper_role())
    step = overrides.pop("step", {"id": f"{role['id']}_step", "role_id": role["id"]})
    request_kwargs = {
        "run_contract": overrides.pop("run_contract"),
        "layout": layout,
        "iter_id": 0,
        "step": step,
        "step_order": overrides.pop("step_order", 1),
        "role": role,
        "execution_settings": {},
        "immediate_previous_step": None,
        "completed_steps_this_iteration": [],
        "previous_iteration_same_step": None,
        "previous_iteration_same_role": None,
        "previous_iteration_summary": None,
        "previous_composite": None,
        "stagnation_mode": "none",
    }
    request_kwargs.update(overrides)
    return build_step_instruction_context(StepInstructionContextRequest(**request_kwargs))


def gatekeeper_role() -> dict[str, str]:
    return {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"}


def builder_role() -> dict[str, str]:
    return {"id": "builder", "name": "Builder", "archetype": "builder"}
