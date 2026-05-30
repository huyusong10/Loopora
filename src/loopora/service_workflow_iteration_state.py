from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from loopora.diagnostics import get_logger, log_event
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineCompleteIterationRequest,
)
from loopora.evidence_coverage import summarize_evidence_coverage_projection
from loopora.kernel import ActorRef
from loopora.run_artifacts import append_jsonl_with_mirrors, write_json_with_mirrors
from loopora.service_run_finalization import TerminalRunFinalizationRequest
from loopora.service_workflow_support import IterationContextPersistRequest, WorkflowSummaryRequest
from loopora.stagnation import StagnationUpdateRequest, update_stagnation
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import append_jsonl, read_json, utc_now

logger = get_logger(__name__)


@dataclass(frozen=True)
class WorkflowIterationCheckpointRequest:
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


@dataclass(frozen=True)
class GatekeeperIterationRecordRequest:
    layout: object
    stagnation: dict
    normalized_output: dict
    iter_id: int
    previous_composite: float | None
    run: dict
    run_id: str


@dataclass(frozen=True)
class WorkflowGatekeeperSuccessRequest:
    run_id: str
    run: dict
    run_dir: Path
    workflow: dict
    compiled_spec: dict
    iter_id: int
    step: dict
    runtime_role: str
    normalized_output: dict
    stagnation: dict
    previous_composite: float | None
    layout: object
    step_results: list[dict]
    current_outputs_by_step: dict[str, dict]
    current_outputs_by_role: dict[str, dict]
    current_outputs_by_archetype: dict[str, dict]
    current_session_refs_by_step: dict[str, dict]


class ServiceWorkflowIterationStateMixin:
    def _checkpoint_workflow_iteration_state(
        self,
        request: WorkflowIterationCheckpointRequest,
    ) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict], dict[str, dict], dict[str, dict], dict[str, dict], dict | None]:
        previous_outputs_by_step = dict(request.current_outputs_by_step)
        previous_outputs_by_role = dict(request.current_outputs_by_role)
        previous_outputs_by_archetype = dict(request.current_outputs_by_archetype)
        previous_handoffs_by_step = {item["step"]["id"]: item["handoff"] for item in request.step_results}
        previous_handoffs_by_role = {item["role"]["id"]: item["handoff"] for item in request.step_results}
        previous_handoffs_by_archetype = {item["role"]["archetype"]: item["handoff"] for item in request.step_results}
        append_jsonl(
            request.layout.legacy_iterations_path,
            self._build_workflow_iteration_entry(
                request.iter_id,
                request.step_results,
                request.stagnation,
                previous_composite=request.previous_composite,
            ),
        )
        previous_iteration_summary = self._persist_iteration_context(
            IterationContextPersistRequest(
                layout=request.layout,
                run_id=request.run_id,
                iter_id=request.iter_id,
                step_results=request.step_results,
                stagnation=request.stagnation,
                previous_composite=request.previous_composite,
            )
        )
        RepositoryRunEngine(self.repository).complete_iteration(
            RunEngineCompleteIterationRequest(
                run_id=request.run_id,
                iteration=request.iter_id,
                actor=ActorRef.system(),
                completed_step_count=len(request.step_results),
                reason="checkpointed",
            )
        )
        return (
            previous_outputs_by_step,
            previous_outputs_by_role,
            previous_outputs_by_archetype,
            previous_handoffs_by_step,
            previous_handoffs_by_role,
            previous_handoffs_by_archetype,
            previous_iteration_summary,
        )

    def _record_gatekeeper_iteration_result(
        self,
        request: GatekeeperIterationRecordRequest,
    ) -> dict:
        stagnation = update_stagnation(
            StagnationUpdateRequest(
                stagnation=request.stagnation,
                composite=request.normalized_output["composite_score"],
                current_iter=request.iter_id,
                delta_threshold=request.run["delta_threshold"],
                trigger_window=request.run["trigger_window"],
                regression_window=request.run["regression_window"],
            )
        )
        stagnation = self._update_evidence_progress_stagnation(request, stagnation)
        write_json_with_mirrors(
            request.layout.timeline_stagnation_path,
            stagnation,
            mirror_paths=[request.layout.run_dir / "stagnation.json"],
        )
        append_jsonl_with_mirrors(
            request.layout.timeline_metrics_path,
            {
                "iter": request.iter_id,
                "timestamp": utc_now(),
                "composite": request.normalized_output["composite_score"],
                "score_delta": round(
                    request.normalized_output["composite_score"] - request.previous_composite,
                    6,
                )
                if request.previous_composite is not None
                else None,
                "passed": request.normalized_output["passed"],
                "metric_scores": request.normalized_output.get("metric_scores", {}),
                "failed_check_ids": request.normalized_output.get("failed_check_ids", []),
                "failed_check_titles": request.normalized_output.get("failed_check_titles", []),
                "evidence_refs": request.normalized_output.get("evidence_refs", []),
                "evidence_gate_status": request.normalized_output.get("evidence_gate_status", ""),
                "stagnation_mode": stagnation["stagnation_mode"],
                "evidence_progress_mode": stagnation.get("evidence_progress_mode", "none"),
                "covered_check_count": stagnation.get("latest_covered_check_count", 0),
                "missing_check_count": stagnation.get("latest_missing_check_count", 0),
            },
            mirror_paths=[request.layout.legacy_metrics_path],
        )
        self.repository.update_run(request.run_id, last_verdict=request.normalized_output)
        return stagnation

    @staticmethod
    def _update_evidence_progress_stagnation(
        request: GatekeeperIterationRecordRequest,
        stagnation: dict,
    ) -> dict:
        try:
            coverage = read_json(request.layout.evidence_coverage_path)
        except (OSError, UnicodeError, ValueError):
            coverage = {}
        if not isinstance(coverage, dict):
            coverage = {}
        coverage_summary = summarize_evidence_coverage_projection(
            coverage,
            coverage_path_available=request.layout.evidence_coverage_path.exists(),
        )
        covered_checks = structured_non_negative_int(coverage_summary.get("covered_check_count"))
        missing_checks = structured_non_negative_int(coverage_summary.get("missing_check_count"))
        raw_recent_counts = stagnation.get("recent_covered_check_counts", [])
        recent_counts = (
            [structured_non_negative_int(item) for item in raw_recent_counts]
            if isinstance(raw_recent_counts, list)
            else []
        )
        previous_covered_checks = structured_non_negative_int(recent_counts[-1]) if recent_counts else 0
        no_progress = bool(recent_counts) and covered_checks <= previous_covered_checks
        consecutive_no_progress = structured_non_negative_int(stagnation.get("consecutive_no_required_coverage_delta"))
        consecutive_no_progress = consecutive_no_progress + 1 if no_progress and missing_checks > 0 else 0
        trigger_window = structured_non_negative_int(request.run.get("trigger_window"), default=1) or 1
        evidence_progress_mode = "stalled" if missing_checks > 0 and consecutive_no_progress >= trigger_window else "none"
        return {
            **stagnation,
            "recent_covered_check_counts": [*recent_counts, covered_checks][-20:],
            "latest_coverage_status": str(coverage_summary.get("status") or "pending"),
            "latest_covered_check_count": covered_checks,
            "latest_missing_check_count": missing_checks,
            "latest_covered_check_ids": list(coverage_summary.get("covered_check_ids") or [])[:20],
            "latest_missing_check_ids": list(coverage_summary.get("missing_check_ids") or [])[:20],
            "latest_coverage_top_gaps": list(coverage_summary.get("top_gaps") or [])[:5],
            "consecutive_no_required_coverage_delta": consecutive_no_progress,
            "evidence_progress_mode": evidence_progress_mode,
        }

    def _finish_workflow_gatekeeper_success(
        self,
        request: WorkflowGatekeeperSuccessRequest,
    ) -> dict:
        self._checkpoint_workflow_iteration_state(
            WorkflowIterationCheckpointRequest(
                layout=request.layout,
                iter_id=request.iter_id,
                step_results=request.step_results,
                current_outputs_by_step=request.current_outputs_by_step,
                current_outputs_by_role=request.current_outputs_by_role,
                current_outputs_by_archetype=request.current_outputs_by_archetype,
                current_session_refs_by_step=request.current_session_refs_by_step,
                stagnation=request.stagnation,
                previous_composite=request.previous_composite,
                run_id=request.run_id,
            )
        )
        summary = self._build_workflow_summary(
            WorkflowSummaryRequest(
                run=request.run,
                workflow=request.workflow,
                compiled_spec=request.compiled_spec,
                iter_id=request.iter_id,
                step_results=request.step_results,
                stagnation=request.stagnation,
                exhausted=False,
                previous_composite=request.previous_composite,
            )
        )
        finished = self._finalize_terminal_run(
            TerminalRunFinalizationRequest(
                run_id=request.run_id,
                run_dir=request.run_dir,
                status="succeeded",
                summary=summary,
                last_verdict=request.normalized_output,
                final_reason="gatekeeper_passed",
                hydrate=True,
            )
        )
        self.append_run_event(
            request.run_id,
            "run_finished",
            self._run_finished_event_payload(finished, status="succeeded", iter_id=request.iter_id),
        )
        log_event(
            logger,
            logging.INFO,
            "service.run.execution.finished",
            "Workflow run finished successfully",
            **self._run_log_context(
                request.run,
                status="succeeded",
                iter=request.iter_id,
                reason="gatekeeper_passed",
                step_id=request.step["id"],
                role=request.runtime_role,
            ),
        )
        return finished
