from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext
from loopora.run_artifacts import RunArtifactLayout
from loopora.structured_numbers import coerced_non_negative_int


@dataclass(frozen=True)
class AgentNativeStepClaimRequest:
    adapter: str
    workdir: Path | str | None = None
    context_id: str = ""
    run_id: str = ""
    entry_source: str = ""


@dataclass(frozen=True)
class AgentNativeStepSubmitRequest:
    adapter: str
    output: dict[str, Any]
    host_dispatch: dict[str, Any] | None = None
    workdir: Path | str | None = None
    context_id: str = ""
    run_id: str = ""
    step_id: str = ""
    session_ref: dict[str, Any] | None = None
    entry_source: str = ""


@dataclass(frozen=True)
class AgentNativeRuntimeClaimRequest:
    kind: str
    run: dict
    state: dict[str, Any]
    context: RunnerRunContext
    iteration: RunnerIterationState
    step: dict
    step_order: int
    entry_source: str = ""
    claim_request: object | None = None


@dataclass(frozen=True)
class AgentNativeSubmitResponseRequest:
    kind: str
    run: dict[str, Any]
    state: dict[str, Any]
    layout: RunArtifactLayout
    finish_result: dict[str, Any] | None
    submitted_step: dict[str, Any]
    entry_source: str


@dataclass(frozen=True)
class AgentNativeSubmitContext:
    kind: str
    run: dict[str, Any]
    layout: RunArtifactLayout
    state: dict[str, Any]
    active: dict[str, Any]
    step: dict[str, Any]
    step_id: str
    iter_id: int
    step_order: int
    context: RunnerRunContext
    iteration: RunnerIterationState
    role: dict[str, Any]
    runtime_role: str
    step_instruction_context: dict[str, Any]
    host_dispatch: dict[str, Any]


@dataclass(frozen=True)
class AgentNativeNormalizedSubmit:
    submitted_step: dict[str, Any]
    finish_result: dict[str, Any] | None
    is_control_step: bool


def agent_native_first_present_int(*values: object, default: int = 0) -> int:
    for value in values:
        if value is None or value == "":
            continue
        normalized = coerced_non_negative_int(value, default=-1)
        if normalized >= 0:
            return normalized
    return default


def agent_native_submit_guard_message(error: str) -> str:
    if "already committed" in error:
        return "agent-native step was already submitted; rerun agent next --json if the run advanced or this result file is stale"
    if "does not match current StepInstruction" in error:
        return "submitted step_id does not match the claimed agent-native step"
    return error
