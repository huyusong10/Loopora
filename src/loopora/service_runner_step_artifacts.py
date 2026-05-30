from __future__ import annotations

from dataclasses import dataclass
import logging

from loopora.context_flow import StepEvidenceEntryRequest, StepResultContext, build_step_evidence_entry, build_step_handoff
from loopora.diagnostics import get_logger, log_event
from loopora.evidence_coverage import write_evidence_coverage_projection
from loopora.evidence_manifest import write_evidence_manifest_projection
from loopora.run_artifacts import append_jsonl_with_mirrors
from loopora.runner_support_requests import StepOutputsWriteRequest
from loopora.step_instruction_context import STEP_INSTRUCTION_CONTEXT_KEY

logger = get_logger(__name__)


@dataclass(frozen=True)
class RunnerStepWriteRequest:
    run_id: str
    layout: object
    iter_id: int
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    normalized_output: dict


@dataclass(frozen=True)
class RunnerStepWriteResult:
    handoff: dict
    evidence_entry: dict
    coverage_projection: dict
    manifest_projection: dict


@dataclass(frozen=True)
class RunnerStepResultEntryRequest:
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    execution_settings: dict
    normalized_output: dict
    handoff: dict
    step_instruction_context: dict


@dataclass(frozen=True)
class RunnerStepCompletionLogRequest:
    run: dict
    iter_id: int
    step: dict
    runtime_role: str
    role: dict
    duration_ms: int
    normalized_output: dict


class ServiceRunnerStepArtifactsMixin:
    def write_runner_step_result_artifacts(
        self,
        request: RunnerStepWriteRequest,
    ) -> RunnerStepWriteResult:
        step_result = StepResultContext(
            layout=request.layout,
            iter_id=request.iter_id,
            step=request.step,
            step_order=request.step_order,
            role=request.role,
            runtime_role=request.runtime_role,
            output=request.normalized_output,
        )
        handoff = build_step_handoff(step_result)
        evidence_entry = build_step_evidence_entry(StepEvidenceEntryRequest(result=step_result, handoff=handoff))
        handoff["evidence_refs"] = [evidence_entry["id"]]
        self._write_step_outputs(
            StepOutputsWriteRequest(
                layout=request.layout,
                iter_id=request.iter_id,
                step=request.step,
                step_order=request.step_order,
                role=request.role,
                runtime_role=request.runtime_role,
                output=request.normalized_output,
                handoff=handoff,
            )
        )
        append_jsonl_with_mirrors(request.layout.evidence_ledger_path, evidence_entry)
        coverage_projection = write_evidence_coverage_projection(request.layout)
        manifest_projection = write_evidence_manifest_projection(
            request.layout,
            coverage_projection=coverage_projection,
        )
        self.append_run_event(
            request.run_id,
            "step_handoff_written",
            {
                "iter": request.iter_id,
                "step_id": request.step["id"],
                "step_order": request.step_order,
                "role_name": request.role["name"],
                "archetype": request.role["archetype"],
                "handoff_path": request.layout.relative(request.layout.step_handoff_path(request.iter_id, request.step_order, request.step["id"])),
                "evidence_ledger_path": request.layout.relative(request.layout.evidence_ledger_path),
                "evidence_coverage_path": coverage_projection.get("coverage_path", ""),
                "evidence_manifest_path": manifest_projection.get("manifest_path", ""),
                "evidence_refs": handoff["evidence_refs"],
                "status": handoff["status"],
                "summary": handoff["summary"],
                "blocking_count": len(handoff["blocking_items"]),
            },
            role=request.runtime_role,
        )
        return RunnerStepWriteResult(
            handoff=handoff,
            evidence_entry=evidence_entry,
            coverage_projection=coverage_projection,
            manifest_projection=manifest_projection,
        )

    def _build_runner_step_result_entry(
        self,
        request: RunnerStepResultEntryRequest,
    ) -> dict:
        return {
            "step": request.step,
            "step_order": request.step_order,
            "role": request.role,
            "runtime_role": request.runtime_role,
            "resolved_model": request.execution_settings["model"],
            "resolved_executor_kind": request.execution_settings["executor_kind"],
            "output": request.normalized_output,
            "handoff": request.handoff,
            STEP_INSTRUCTION_CONTEXT_KEY: request.step_instruction_context,
        }

    def _log_runner_step_completion(
        self,
        request: RunnerStepCompletionLogRequest,
    ) -> None:
        log_event(
            logger,
            logging.INFO,
            "service.runner.step.completed",
            "Completed runner step",
            **self._run_log_context(
                request.run,
                iter=request.iter_id,
                step_id=request.step["id"],
                role=request.runtime_role,
                archetype=request.role["archetype"],
                duration_ms=request.duration_ms,
                passed=request.normalized_output.get("passed"),
                composite_score=request.normalized_output.get("composite_score"),
            ),
        )
