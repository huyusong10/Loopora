from __future__ import annotations

from agent_native_contract_architecture_support import (
    REPO_ROOT,
    assert_design_mentions,
    assert_markers_owned_by,
    assert_markers_present,
    design_contracts_source,
    loopora_source,
)


EXPECTED_SERVICE_MIXIN_CLASS = "class ServiceAgentNativeMixin(ServiceAgentNativeClaimMixin, ServiceAgentNativeIterationMixin, ServiceAgentNativeSubmitMixin)"


def test_agent_native_projection_modules_do_not_depend_on_cli_modules() -> None:
    offenders = [
        path.name
        for path in sorted((REPO_ROOT / "src" / "loopora").glob("agent_native_*.py"))
        if "loopora.cli_" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_service_agent_native_keeps_request_dtos_in_dedicated_module() -> None:
    service_source = loopora_source("service_agent_native.py")
    requests_source = loopora_source("service_agent_native_requests.py")

    assert "from loopora.service_agent_native_requests import" in service_source
    assert "@dataclass" not in service_source
    assert_markers_present(requests_source, "class AgentNativeStepClaimRequest", "class AgentNativeSubmitContext")


def test_service_agent_native_claim_orchestration_has_dedicated_boundary() -> None:
    service_source = loopora_source("service_agent_native.py")
    claim_source = loopora_source("service_agent_native_claim.py")
    claim_active_step_source = loopora_source("agent_native_claim_active_step.py")
    claim_runtime_step_source = loopora_source("agent_native_claim_runtime_step.py")
    claim_events_source = loopora_source("agent_native_claim_events.py")

    assert "from loopora.service_agent_native_claim import ServiceAgentNativeClaimMixin" in service_source
    assert_markers_present(
        claim_source,
        "from loopora.agent_native_claim_active_step import",
        "from loopora.agent_native_claim_runtime_step import",
        "from loopora.agent_native_claim_events import",
    )
    assert EXPECTED_SERVICE_MIXIN_CLASS in service_source
    assert_markers_owned_by(
        claim_source,
        [service_source],
        "def claim_agent_native_step",
        "def _agent_native_claim_runtime_step",
        "runner_step_claim_plan",
        "AgentNativeRuntimeStepViewBuildRequest",
    )
    assert_markers_owned_by(
        claim_runtime_step_source,
        [claim_source],
        "def build_agent_native_runtime_step_view",
        "RunnerStepRuntimeRequestBuildRequest",
        "def agent_native_claimed_active_step_payload",
    )
    assert_markers_present(
        claim_active_step_source,
        "def refresh_agent_native_claimed_active_step",
        "agent_native_active_step_view_payload",
    )
    assert "agent_native_active_step_view_payload" not in claim_source
    assert_markers_present(claim_events_source, "def agent_native_step_claimed_event_payload", "agent_native_step_view_path_text")
    assert "agent_native_step_view_path_text" not in claim_source
    assert_design_mentions(
        design_contracts_source(),
        "service_agent_native_claim.py",
        "agent_native_claim_active_step.py",
        "agent_native_claim_runtime_step.py",
        "agent_native_claim_events.py",
    )


def test_service_agent_native_submit_orchestration_has_dedicated_boundary() -> None:
    service_source = loopora_source("service_agent_native.py")
    submit_source = loopora_source("service_agent_native_submit.py")
    payloads_source = loopora_source("agent_native_submit_result_payloads.py")
    normalization_source = loopora_source("service_agent_native_submit_normalization.py")
    response_source = loopora_source("service_agent_native_submit_response.py")

    assert "from loopora.service_agent_native_submit import ServiceAgentNativeSubmitMixin" in service_source
    assert "from loopora.service_agent_native_submit_normalization import" in submit_source
    assert "from loopora.service_agent_native_submit_response import ServiceAgentNativeSubmitResponseMixin" in submit_source
    assert "class ServiceAgentNativeSubmitNormalizationMixin" in normalization_source
    assert EXPECTED_SERVICE_MIXIN_CLASS in service_source
    assert "def submit_agent_native_step" in service_source
    assert "return self._submit_agent_native_step_impl(request)" in service_source
    assert_markers_owned_by(
        submit_source,
        [service_source],
        "def _submit_agent_native_step_impl",
        "def _agent_native_submit_context",
        "def _agent_native_commit_submit",
    )
    assert "def _agent_native_normalized_submit" in normalization_source
    assert "def _agent_native_normalized_submit" not in submit_source
    assert "def _validate_agent_native_step_output_contract" in normalization_source
    assert_markers_owned_by(
        response_source,
        [submit_source, service_source],
        "class ServiceAgentNativeSubmitResponseMixin",
        "def _agent_native_submit_response",
        "def _agent_native_submitted_step_result",
    )
    for marker in (
        "def agent_native_step_result_payload",
        "def agent_native_submitted_session_ref",
    ):
        assert marker in payloads_source
        assert marker not in submit_source
        assert marker.removeprefix("def ") in normalization_source
    assert_design_mentions(
        design_contracts_source(),
        "service_agent_native_submit.py",
        "service_agent_native_submit_normalization.py",
        "agent_native_submit_result_payloads.py",
        "service_agent_native_submit_response.py",
    )


def test_service_agent_native_iteration_lifecycle_has_dedicated_boundary() -> None:
    service_source = loopora_source("service_agent_native.py")
    iteration_source = loopora_source("service_agent_native_iteration.py")

    assert "from loopora.service_agent_native_iteration import ServiceAgentNativeIterationMixin" in service_source
    assert EXPECTED_SERVICE_MIXIN_CLASS in service_source
    assert_markers_owned_by(
        iteration_source,
        [service_source],
        "def _agent_native_finish_iteration_or_advance",
        "def _agent_native_claim_pending_control_step",
        "RunnerIterationCheckpointRequest",
        "AgentNativeControlQueueRequest",
        "agent_native_next_iteration_state_update",
    )
    assert "service_agent_native_iteration.py" in design_contracts_source()
