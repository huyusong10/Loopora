from __future__ import annotations

from dataclasses import dataclass

from loopora.context_step_evidence_entries import (
    build_step_evidence_entry as _build_step_evidence_entry,
    evidence_entry_id as _evidence_entry_id,
)
from loopora.context_step_handoffs import build_step_handoff as _build_step_handoff
from loopora.run_artifacts import RunArtifactLayout


@dataclass(frozen=True)
class StepResultContext:
    layout: RunArtifactLayout
    iter_id: int
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    output: dict
    task_language: str = "en"


@dataclass(frozen=True)
class StepEvidenceEntryRequest:
    result: StepResultContext
    handoff: dict


def build_step_handoff(result: StepResultContext) -> dict:
    return _build_step_handoff(result)


def evidence_entry_id(iter_id: int, step_order: int, step_id: str) -> str:
    return _evidence_entry_id(iter_id, step_order, step_id)


def build_step_evidence_entry(request: StepEvidenceEntryRequest) -> dict:
    return _build_step_evidence_entry(request)
