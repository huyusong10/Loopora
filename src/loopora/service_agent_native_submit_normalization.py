from __future__ import annotations

from typing import Any

from loopora.agent_native_evidence_contracts import agent_native_unknown_evidence_refs
from loopora.agent_native_submit_result_payloads import (
    AgentNativeStepResultPayloadRequest,
    agent_native_step_result_payload,
    agent_native_submitted_session_ref,
)
from loopora.agent_native_submit_validation import validate_agent_native_step_output_contract
from loopora.agent_native_submitted_step import AgentNativeSubmittedStepResultRequest
from loopora.context_step_results import evidence_entry_id
from loopora.engine.runner_context import evidence_context_with_canonical_items
from loopora.run_artifacts import RunArtifactLayout
from loopora.runner_support_requests import StepOutputNormalizationRequest
from loopora.service_agent_native_requests import (
    AgentNativeNormalizedSubmit,
    AgentNativeStepSubmitRequest,
    AgentNativeSubmitContext,
    agent_native_submit_guard_message,
)
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.utils import write_json


class ServiceAgentNativeSubmitNormalizationMixin:
    def _agent_native_normalized_submit(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        run: dict[str, Any],
        layout: RunArtifactLayout,
        output: dict[str, Any],
        submit_context: AgentNativeSubmitContext,
    ) -> AgentNativeNormalizedSubmit:
        active = submit_context.active
        step = submit_context.step
        iter_id = submit_context.iter_id
        step_order = submit_context.step_order
        step_id = submit_context.step_id
        context = submit_context.context
        iteration = submit_context.iteration
        role = submit_context.role
        runtime_role = submit_context.runtime_role
        step_instruction_context = submit_context.step_instruction_context
        host_dispatch = submit_context.host_dispatch
        self._validate_agent_native_step_output_contract(output, active=active)
        if role["archetype"] != "gatekeeper":
            unknown_refs = agent_native_unknown_evidence_refs(
                output,
                active=active,
                step_instruction_context=step_instruction_context,
            )
            if unknown_refs:
                raise LooporaError(
                    "agent-native evidence_refs_unknown: "
                    + ", ".join(unknown_refs[:4])
                    + ("..." if len(unknown_refs) > 4 else "")
                )
        normalized_output = self._normalize_step_output(
            StepOutputNormalizationRequest(
                archetype=role["archetype"],
                output=output,
                compiled_spec=context.compiled_spec,
                inspector_output=dict(iteration.current_outputs_by_archetype).get("inspector"),
                evidence_context=evidence_context_with_canonical_items(step_instruction_context, context.layout),
                current_evidence_id=evidence_entry_id(iter_id, step_order, step_id),
            )
        )
        result = agent_native_step_result_payload(
            AgentNativeStepResultPayloadRequest(
                kind=submit_context.kind,
                active=active,
                step=step,
                role=role,
                runtime_role=runtime_role,
                normalized_output=normalized_output,
                step_instruction_context=step_instruction_context,
                iter_id=iter_id,
                step_order=step_order,
                session_ref=agent_native_submitted_session_ref(request.session_ref, output),
            )
        )
        try:
            self.require_runner_step_result_submittable(context, iteration, result)
        except ValueError as exc:
            raise LooporaConflictError(agent_native_submit_guard_message(str(exc))) from exc
        write_json(layout.step_output_raw_path(iter_id, step_order, step_id), output)
        finish_result = self.submit_runner_step_result(context, iteration, result)
        submitted_step = self._agent_native_submitted_step_result(
            AgentNativeSubmittedStepResultRequest(
                layout=layout,
                iter_id=iter_id,
                step=step,
                step_order=step_order,
                role=role,
                runtime_role=runtime_role,
                normalized_output=normalized_output,
                handoff=iteration.current_handoffs[-1] if iteration.current_handoffs else {},
            )
        )
        submitted_step["host_dispatch"] = host_dispatch
        is_control_step = self._agent_native_record_control_completion(run, result)
        return AgentNativeNormalizedSubmit(
            submitted_step=submitted_step,
            finish_result=finish_result,
            is_control_step=is_control_step,
        )

    @staticmethod
    def _validate_agent_native_step_output_contract(output: dict[str, Any], *, active: dict[str, Any]) -> None:
        validate_agent_native_step_output_contract(output, active=active)
