from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopora.evidence_coverage import write_evidence_coverage_projection
from loopora.evidence_manifest import write_evidence_manifest_projection


@dataclass(frozen=True, slots=True)
class RunnerStepEvidenceArtifactsRequest:
    layout: Any


@dataclass(frozen=True, slots=True)
class RunnerStepEvidenceArtifactsResult:
    coverage_projection: dict
    manifest_projection: dict


def write_runner_step_evidence_artifacts(request: RunnerStepEvidenceArtifactsRequest) -> RunnerStepEvidenceArtifactsResult:
    coverage_projection = write_evidence_coverage_projection(request.layout)
    manifest_projection = write_evidence_manifest_projection(
        request.layout,
        coverage_projection=coverage_projection,
    )
    return RunnerStepEvidenceArtifactsResult(
        coverage_projection=coverage_projection,
        manifest_projection=manifest_projection,
    )
