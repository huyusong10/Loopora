from __future__ import annotations

from loopora.context_iteration_summary import IterationSummaryContext, build_iteration_summary, derive_latest_state
from loopora.run_artifacts import append_jsonl_with_mirrors
from loopora.runner_summary_projection import (
    build_runner_iteration_entry,
    build_runner_summary,
    summary_line_for_step,
)
from loopora.service_runner_gatekeeper_output import ServiceRunnerGatekeeperOutputMixin
from loopora.service_prompts import BUILDER_SCHEMA, CUSTOM_SCHEMA, GATEKEEPER_SCHEMA, GUIDE_SCHEMA, INSPECTOR_SCHEMA
from loopora.utils import read_json, utc_now, write_json
from loopora.runner_support_requests import (
    IterationContextPersistRequest,
    RunnerSummaryRequest,
    StepOutputNormalizationRequest,
    StepOutputsWriteRequest,
)
from loopora.strategy_source import LEGACY_STRATEGY_ROLE_BY_ARCHETYPE


def _safe_read_json_object(path) -> dict:
    try:
        payload = read_json(path)
    except (OSError, UnicodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


class ServiceRunnerSupportMixin(ServiceRunnerGatekeeperOutputMixin):
    def _output_schema_for_archetype(self, archetype: str) -> dict:
        if archetype == "builder":
            return BUILDER_SCHEMA
        if archetype == "inspector":
            return INSPECTOR_SCHEMA
        if archetype == "gatekeeper":
            return GATEKEEPER_SCHEMA
        if archetype == "custom":
            return CUSTOM_SCHEMA
        return GUIDE_SCHEMA

    def _normalize_step_output(
        self,
        request: StepOutputNormalizationRequest,
    ) -> dict:
        if request.archetype == "inspector":
            return self._enrich_tester_result(request.output)
        if request.archetype == "gatekeeper":
            gatekeeper_output = self._coerce_gatekeeper_output(
                request.output,
                evidence_context=request.evidence_context,
                current_evidence_id=request.current_evidence_id,
                compiled_spec=request.compiled_spec,
            )
            return self._enrich_verifier_result(gatekeeper_output, request.compiled_spec, request.inspector_output or {})
        return dict(request.output)

    def _write_step_outputs(
        self,
        request: StepOutputsWriteRequest,
    ) -> None:
        step_dir = request.layout.step_dir(request.iter_id, request.step_order, request.step["id"])
        step_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            request.layout.step_output_normalized_path(request.iter_id, request.step_order, request.step["id"]),
            request.output,
        )
        write_json(
            request.layout.step_metadata_path(request.iter_id, request.step_order, request.step["id"]),
            {
                "step_id": request.step["id"],
                "step_order": request.step_order,
                "role_id": request.role["id"],
                "role_name": request.role["name"],
                "runtime_role": request.runtime_role,
                "archetype": request.role["archetype"],
                "iter": request.iter_id,
                "inherit_session": bool(request.step.get("inherit_session")),
                "extra_cli_args": str(request.step.get("extra_cli_args") or ""),
                "parallel_group": str(request.step.get("parallel_group") or ""),
                "inputs": dict(request.step.get("inputs") or {}),
                "action_policy": dict(request.step.get("action_policy") or {}),
                "control_id": str(request.step.get("control_id") or ""),
                "control": dict(request.step.get("control") or {}) if isinstance(request.step.get("control"), dict) else {},
            },
        )
        write_json(
            request.layout.step_handoff_path(request.iter_id, request.step_order, request.step["id"]),
            request.handoff,
        )

        for alias_path in request.layout.legacy_role_output_paths(request.role["archetype"]):
            write_json(alias_path, request.output)

    def _persist_iteration_context(
        self,
        request: IterationContextPersistRequest,
    ) -> dict:
        iteration_summary = build_iteration_summary(
            IterationSummaryContext(
                layout=request.layout,
                iter_id=request.iter_id,
                step_results=request.step_results,
                stagnation=request.stagnation,
                previous_composite=request.previous_composite,
                timestamp=utc_now(),
            )
        )
        write_json(request.layout.iteration_summary_path(request.iter_id), iteration_summary)
        append_jsonl_with_mirrors(request.layout.timeline_iterations_path, iteration_summary)
        latest_state = derive_latest_state(_safe_read_json_object(request.layout.latest_state_path), iteration_summary)
        write_json(request.layout.latest_iteration_summary_path, iteration_summary)
        write_json(request.layout.latest_state_path, latest_state)
        self.append_run_event(
            request.run_id,
            "iteration_summary_written",
            {
                "iter": request.iter_id,
                "summary_path": request.layout.relative(request.layout.iteration_summary_path(request.iter_id)),
                "latest_state_path": request.layout.relative(request.layout.latest_state_path),
                "executed_step_count": len(request.step_results),
                "composite_score": iteration_summary["score"]["composite"],
                "passed": iteration_summary["score"]["passed"],
            },
        )
        return iteration_summary

    def _build_runner_iteration_entry(
        self,
        iter_id: int,
        step_results: list[dict],
        stagnation: dict,
        *,
        previous_composite: float | None,
    ) -> dict:
        return build_runner_iteration_entry(
            iter_id,
            step_results,
            stagnation,
            previous_composite=previous_composite,
        )

    def _build_runner_summary(
        self,
        request: RunnerSummaryRequest,
    ) -> str:
        return build_runner_summary(request)

    def _summary_line_for_step(self, archetype: str, output: dict) -> str:
        return summary_line_for_step(archetype, output)

    def _runtime_role_key(self, role: dict) -> str:
        if role.get("id") == role.get("archetype"):
            return LEGACY_STRATEGY_ROLE_BY_ARCHETYPE.get(role["archetype"], role["id"])
        return role["id"]
