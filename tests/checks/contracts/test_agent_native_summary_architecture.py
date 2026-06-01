from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _assert_agent_adapter_mixin_composes_boundaries(adapter_source: str) -> None:
    assert "class ServiceAgentAdapterMixin(" in adapter_source
    for marker in (
        "ServiceAgentLoopStartMixin",
        "ServiceAgentContinuationMixin",
        "ServiceAgentBundleCandidateMixin",
        "ServiceAgentEntryProjectionMixin",
    ):
        assert marker in adapter_source


def test_agent_native_projection_modules_do_not_depend_on_cli_modules() -> None:
    offenders = [
        path.name
        for path in sorted((REPO_ROOT / "src" / "loopora").glob("agent_native_*.py"))
        if "loopora.cli_" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_service_agent_entry_loop_projection_has_dedicated_boundary() -> None:
    adapter_source = (REPO_ROOT / "src" / "loopora" / "service_agent_adapters.py").read_text(encoding="utf-8")
    projection_source = (REPO_ROOT / "src" / "loopora" / "service_agent_entry_projection.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_agent_entry_projection import ServiceAgentEntryProjectionMixin" in adapter_source
    _assert_agent_adapter_mixin_composes_boundaries(adapter_source)
    for marker in (
        "def agent_entry_loop_start_projection",
        "agent_recovery_agent_entry_candidate_event",
        "agent_entry_loop_json_command",
        "agent_entry_loop_projection_messages",
    ):
        assert marker in projection_source
        assert marker not in adapter_source
    assert "service_agent_entry_projection.py" in design_source


def test_service_agent_continuation_helpers_have_dedicated_boundary() -> None:
    adapter_source = (REPO_ROOT / "src" / "loopora" / "service_agent_adapters.py").read_text(encoding="utf-8")
    continuation_source = (REPO_ROOT / "src" / "loopora" / "service_agent_continuation.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_agent_continuation import ServiceAgentContinuationMixin" in adapter_source
    _assert_agent_adapter_mixin_composes_boundaries(adapter_source)
    for marker in (
        "def _seed_agent_native_continuation_context",
        "def _coverage_context_for_run",
        "agent_native_continuation_context_for_terminal_run",
        "coverage_context_for_run",
    ):
        assert marker in continuation_source
        assert marker not in adapter_source
    assert "service_agent_continuation.py" in design_source


def test_service_agent_loop_start_binding_has_dedicated_boundary() -> None:
    adapter_source = (REPO_ROOT / "src" / "loopora" / "service_agent_adapters.py").read_text(encoding="utf-8")
    loop_start_source = (REPO_ROOT / "src" / "loopora" / "service_agent_loop_start.py").read_text(
        encoding="utf-8"
    )
    loop_start_bindings_source = (REPO_ROOT / "src" / "loopora" / "service_agent_loop_start_bindings.py").read_text(
        encoding="utf-8"
    )
    run_binding_source = (REPO_ROOT / "src" / "loopora" / "service_agent_run_context_binding.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_agent_loop_start import ServiceAgentLoopStartMixin" in adapter_source
    _assert_agent_adapter_mixin_composes_boundaries(adapter_source)
    assert "from loopora.service_agent_loop_start_bindings import" in loop_start_source
    assert "from loopora.service_agent_run_context_binding import" in loop_start_source
    for marker in (
        "def start_agent_loop",
        "def _start_agent_loop_from_ready_session",
    ):
        assert marker in loop_start_source
        assert marker not in adapter_source
    for marker in (
        "class AgentLoopStartContext",
        "def write_agent_loop_running_binding",
        "def agent_loop_result_from_native",
        "ready_candidate_yaml_provenance_from_validation",
    ):
        assert marker in loop_start_bindings_source
        assert marker not in loop_start_source
        assert marker not in adapter_source
    for marker in (
        "def selected_agent_run_binding",
        "def bind_selected_agent_run_context",
        "agent_run_context_choices",
        "def assert_agent_binding_matches_workdir",
    ):
        assert marker in run_binding_source
        assert marker not in loop_start_source
        assert marker not in adapter_source
    assert "service_agent_loop_start.py" in design_source
    assert "service_agent_loop_start_bindings.py" in design_source
    assert "service_agent_run_context_binding.py" in design_source


def test_service_agent_bundle_candidate_intake_has_dedicated_boundary() -> None:
    adapter_source = (REPO_ROOT / "src" / "loopora" / "service_agent_adapters.py").read_text(encoding="utf-8")
    candidate_source = (REPO_ROOT / "src" / "loopora" / "service_agent_bundle_candidates.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_agent_bundle_candidates import" in adapter_source
    assert "AgentBundleCandidateRequest as AgentBundleCandidateRequest" in adapter_source
    _assert_agent_adapter_mixin_composes_boundaries(adapter_source)
    for marker in (
        "class AgentBundleCandidateRequest",
        "def create_agent_bundle_candidate",
        "def _append_missing_agent_candidate_message",
        "candidate_yaml_provenance(",
        "localized_alignment_system_message_appender",
    ):
        assert marker in candidate_source
        assert marker not in adapter_source
    assert "service_agent_bundle_candidates.py" in design_source


def test_service_agent_native_keeps_request_dtos_in_dedicated_module() -> None:
    service_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    requests_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_requests.py").read_text(encoding="utf-8")

    assert "from loopora.service_agent_native_requests import" in service_source
    assert "@dataclass" not in service_source
    assert "class AgentNativeStepClaimRequest" in requests_source
    assert "class AgentNativeSubmitContext" in requests_source


def test_service_agent_native_claim_orchestration_has_dedicated_boundary() -> None:
    service_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    claim_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_claim.py").read_text(encoding="utf-8")
    claim_active_step_source = (REPO_ROOT / "src" / "loopora" / "agent_native_claim_active_step.py").read_text(
        encoding="utf-8"
    )
    claim_runtime_step_source = (
        REPO_ROOT / "src" / "loopora" / "agent_native_claim_runtime_step.py"
    ).read_text(encoding="utf-8")
    claim_events_source = (REPO_ROOT / "src" / "loopora" / "agent_native_claim_events.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    expected_class = (
        "class ServiceAgentNativeMixin("
        "ServiceAgentNativeClaimMixin, ServiceAgentNativeIterationMixin, ServiceAgentNativeSubmitMixin)"
    )

    assert "from loopora.service_agent_native_claim import ServiceAgentNativeClaimMixin" in service_source
    assert "from loopora.agent_native_claim_active_step import" in claim_source
    assert "from loopora.agent_native_claim_runtime_step import" in claim_source
    assert "from loopora.agent_native_claim_events import" in claim_source
    assert expected_class in service_source
    for marker in (
        "def claim_agent_native_step",
        "def _agent_native_claim_runtime_step",
        "runner_step_claim_plan",
        "AgentNativeRuntimeStepViewBuildRequest",
    ):
        assert marker in claim_source
        assert marker not in service_source
    for marker in (
        "def build_agent_native_runtime_step_view",
        "RunnerStepRuntimeRequestBuildRequest",
        "def agent_native_claimed_active_step_payload",
    ):
        assert marker in claim_runtime_step_source
        assert marker not in claim_source
    assert "def refresh_agent_native_claimed_active_step" in claim_active_step_source
    assert "agent_native_active_step_view_payload" in claim_active_step_source
    assert "agent_native_active_step_view_payload" not in claim_source
    assert "def agent_native_step_claimed_event_payload" in claim_events_source
    assert "agent_native_step_view_path_text" in claim_events_source
    assert "agent_native_step_view_path_text" not in claim_source
    assert "service_agent_native_claim.py" in design_source
    assert "agent_native_claim_active_step.py" in design_source
    assert "agent_native_claim_runtime_step.py" in design_source
    assert "agent_native_claim_events.py" in design_source


def test_service_agent_native_submit_orchestration_has_dedicated_boundary() -> None:
    service_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    submit_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_submit.py").read_text(encoding="utf-8")
    payloads_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submit_result_payloads.py").read_text(
        encoding="utf-8"
    )
    normalization_source = (
        REPO_ROOT / "src" / "loopora" / "service_agent_native_submit_normalization.py"
    ).read_text(encoding="utf-8")
    response_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_submit_response.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    expected_class = (
        "class ServiceAgentNativeMixin("
        "ServiceAgentNativeClaimMixin, ServiceAgentNativeIterationMixin, ServiceAgentNativeSubmitMixin)"
    )

    assert "from loopora.service_agent_native_submit import ServiceAgentNativeSubmitMixin" in service_source
    assert "from loopora.service_agent_native_submit_normalization import" in submit_source
    assert "from loopora.service_agent_native_submit_response import ServiceAgentNativeSubmitResponseMixin" in submit_source
    assert "class ServiceAgentNativeSubmitNormalizationMixin" in normalization_source
    assert expected_class in service_source
    assert "def submit_agent_native_step" in service_source and "return self._submit_agent_native_step_impl(request)" in service_source
    for marker in (
        "def _submit_agent_native_step_impl",
        "def _agent_native_submit_context",
        "def _agent_native_commit_submit",
    ):
        assert marker in submit_source
        assert marker not in service_source
    assert "def _agent_native_normalized_submit" in normalization_source
    assert "def _agent_native_normalized_submit" not in submit_source
    assert "def _validate_agent_native_step_output_contract" in normalization_source
    for marker in (
        "class ServiceAgentNativeSubmitResponseMixin",
        "def _agent_native_submit_response",
        "def _agent_native_submitted_step_result",
    ):
        assert marker in response_source
        assert marker not in submit_source
        assert marker not in service_source
    for marker in (
        "def agent_native_step_result_payload",
        "def agent_native_submitted_session_ref",
    ):
        assert marker in payloads_source
        assert marker not in submit_source
        assert marker.removeprefix("def ") in normalization_source
    assert "service_agent_native_submit.py" in design_source
    assert "service_agent_native_submit_normalization.py" in design_source
    assert "agent_native_submit_result_payloads.py" in design_source
    assert "service_agent_native_submit_response.py" in design_source


def test_service_agent_native_iteration_lifecycle_has_dedicated_boundary() -> None:
    service_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    iteration_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_iteration.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    expected_class = (
        "class ServiceAgentNativeMixin("
        "ServiceAgentNativeClaimMixin, ServiceAgentNativeIterationMixin, ServiceAgentNativeSubmitMixin)"
    )

    assert "from loopora.service_agent_native_iteration import ServiceAgentNativeIterationMixin" in service_source
    assert expected_class in service_source
    for marker in (
        "def _agent_native_finish_iteration_or_advance",
        "def _agent_native_claim_pending_control_step",
        "RunnerIterationCheckpointRequest",
        "AgentNativeControlQueueRequest",
        "agent_native_next_iteration_state_update",
    ):
        assert marker in iteration_source
        assert marker not in service_source
    assert "service_agent_native_iteration.py" in design_source


def test_agent_native_result_schema_has_dedicated_boundary() -> None:
    contracts_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_contracts.py").read_text(
        encoding="utf-8"
    )
    schema_source = (REPO_ROOT / "src" / "loopora" / "agent_native_result_schema.py").read_text(encoding="utf-8")
    submit_validation_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submit_validation.py").read_text(
        encoding="utf-8"
    )
    result_template_source = (REPO_ROOT / "src" / "loopora" / "agent_native_result_template.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_native_result_schema import agent_native_schema_validation_issues" in submit_validation_source
    assert "from loopora.agent_native_result_schema import agent_native_result_scaffold_from_schema" in result_template_source
    for marker in (
        "def agent_native_schema_validation_issues",
        "def agent_native_result_scaffold_from_schema",
        "def _agent_native_schema_object_issues",
    ):
        assert marker in schema_source
        assert marker not in contracts_source
    assert "agent_native_result_schema.py" in design_source


def test_agent_native_host_dispatch_validation_has_dedicated_boundary() -> None:
    submit_service_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_submit.py").read_text(
        encoding="utf-8"
    )
    submit_validation_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submit_validation.py").read_text(
        encoding="utf-8"
    )
    host_dispatch_source = (
        REPO_ROOT / "src" / "loopora" / "agent_native_host_dispatch_validation.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_native_host_dispatch_validation import validate_agent_native_host_dispatch" in submit_service_source
    assert "from loopora.agent_native_host_dispatch_validation import" in submit_validation_source
    for marker in (
        "def validate_agent_native_host_dispatch",
        "def _agent_native_role_dispatch_for_submit",
        "def _agent_native_dispatch_trace",
        "def _agent_native_dispatch_position",
    ):
        assert marker in host_dispatch_source
        assert marker not in submit_validation_source
    assert "agent_native_accepted_native_tools" in host_dispatch_source
    assert "agent_native_accepted_native_tools" not in submit_validation_source
    assert "agent_native_host_dispatch_validation.py" in design_source


def test_agent_native_submit_hints_have_dedicated_boundary() -> None:
    contracts_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_contracts.py").read_text(
        encoding="utf-8"
    )
    hints_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submit_hints.py").read_text(encoding="utf-8")
    step_view_source = (REPO_ROOT / "src" / "loopora" / "agent_native_step_view.py").read_text(encoding="utf-8")
    refresh_source = (REPO_ROOT / "src" / "loopora" / "agent_native_step_view_refresh.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_native_submit_hints import agent_native_result_artifact_stem" in step_view_source
    assert "from loopora.agent_native_submit_hints import" in refresh_source
    for marker in (
        "def agent_native_submit_command",
        "def agent_native_result_artifact_stem",
        "def agent_native_submit_hint_with_scoped_result_paths",
        "def _agent_native_command_workdir_arg",
    ):
        assert marker in hints_source
        assert marker not in contracts_source
    assert "agent_native_submit_hints.py" in design_source


def test_agent_native_evidence_contracts_have_dedicated_boundary() -> None:
    contracts_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_contracts.py").read_text(
        encoding="utf-8"
    )
    evidence_source = (REPO_ROOT / "src" / "loopora" / "agent_native_evidence_contracts.py").read_text(
        encoding="utf-8"
    )
    known_refs_source = (REPO_ROOT / "src" / "loopora" / "agent_native_known_evidence_refs.py").read_text(
        encoding="utf-8"
    )
    submit_validation_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submit_validation.py").read_text(
        encoding="utf-8"
    )
    result_template_source = (REPO_ROOT / "src" / "loopora" / "agent_native_result_template.py").read_text(
        encoding="utf-8"
    )
    step_view_source = (REPO_ROOT / "src" / "loopora" / "agent_native_step_view.py").read_text(encoding="utf-8")
    refresh_source = (REPO_ROOT / "src" / "loopora" / "agent_native_step_view_refresh.py").read_text(
        encoding="utf-8"
    )
    submitted_step_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submitted_step.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    for source in (submit_validation_source, result_template_source, submitted_step_source):
        assert "from loopora.agent_native_evidence_contracts import" in source
    for source in (step_view_source, refresh_source):
        assert "from loopora.agent_native_known_evidence_refs import" in source
    for marker in (
        "def _agent_native_string_list",
        "def agent_native_unknown_evidence_refs",
        "def _agent_native_output_coverage_results",
        "AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS",
    ):
        assert marker in evidence_source
        assert marker not in contracts_source
    for marker in (
        "def _agent_native_compact_known_evidence_refs",
        "def _agent_native_compact_evidence_artifact_refs",
        "def _agent_native_gatekeeper_support_reason",
    ):
        assert marker in known_refs_source
        assert marker not in evidence_source
    assert "agent_native_evidence_contracts.py" in design_source
    assert "agent_native_known_evidence_refs.py" in design_source


def test_agent_native_next_step_sections_have_dedicated_boundary() -> None:
    from loopora.agent_native_next_step_sections import agent_dispatch_unavailable_summary

    next_step_source = (REPO_ROOT / "src" / "loopora" / "agent_native_next_step_summary.py").read_text(
        encoding="utf-8"
    )
    section_source = (REPO_ROOT / "src" / "loopora" / "agent_native_next_step_sections.py").read_text(
        encoding="utf-8"
    )
    current_step_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_output.py").read_text(
        encoding="utf-8"
    )
    evidence_output_source = (
        REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_evidence_output.py"
    ).read_text(encoding="utf-8")
    step_results_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_step_results.py").read_text(encoding="utf-8")
    entry_projection_source = (REPO_ROOT / "src" / "loopora" / "agent_entry_run_projection.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_native_next_step_sections import" in next_step_source
    for source in (current_step_source, evidence_output_source, step_results_source, entry_projection_source):
        assert "from loopora.agent_native_next_step_sections import" in source
    for marker in (
        "def agent_dispatch_unavailable_summary",
        "def agent_next_step_continuation_summary",
        "def agent_current_step_evidence_scope_summary",
        "def action_policy_summary",
        "def agent_native_todo_summary",
        "def agent_iteration_repair_summary",
    ):
        assert marker in section_source
        assert marker not in next_step_source
    assert "prefix_loopora_command" in section_source and "prefix_loopora_command" not in next_step_source
    dispatch_unavailable = agent_dispatch_unavailable_summary(
        adapter="codex",
        workdir="$PWD",
        role_dispatch={"target_agent": "loopora-builder", "target_agent_config_exists": False},
    )
    assert 'loopora agent codex check --workdir "$PWD"' in dispatch_unavailable["check_command"]
    assert 'loopora init codex --workdir "$PWD"' in dispatch_unavailable["repair_command"]
    assert "agent_native_next_step_sections.py" in design_source


def test_agent_adapter_templates_delegate_shared_entry_contracts() -> None:
    templates_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_templates.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_entry_contracts.py").read_text(encoding="utf-8")
    run_contract_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_run_contract.py").read_text(
        encoding="utf-8"
    )
    entry_sections_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_entry_sections.py").read_text(
        encoding="utf-8"
    )
    entry_templates_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_entry_templates.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_adapter_entry_contracts import" in templates_source
    assert "from loopora.agent_adapter_run_contract import agent_native_loop_body" in templates_source
    assert "from loopora.agent_adapter_entry_templates import" in templates_source
    assert "def managed_templates" in templates_source
    for marker in (
        "def agent_plan_contract",
        "def agent_recovery_matrix",
        "def agent_result_template_guide",
        "def agent_role_dispatch_guide",
    ):
        assert marker in contracts_source
        assert marker not in templates_source
    for marker in (
        "def agent_native_run_entry_contract",
        "def agent_native_loop_body",
        "def agent_run_section_overview",
    ):
        assert marker in run_contract_source
        assert marker not in contracts_source
        assert marker not in templates_source
    assert "def render_adapter_entry_sections" in entry_sections_source
    assert "from loopora.agent_adapter_entry_sections import" in contracts_source
    assert "from loopora.agent_adapter_entry_sections import" in run_contract_source
    for marker in (
        "def codex_loopora_gen_skill",
        "def codex_loopora_loop_skill",
        "def claude_loopora_loop_skill",
        "def opencode_loopora_loop_command",
    ):
        assert marker in entry_templates_source
        assert marker not in templates_source
    assert "## Detailed Contract" in contracts_source
    assert "## Detailed Contract" in run_contract_source
    assert "## Detailed Contract" not in entry_templates_source
    assert "## Detailed Contract" not in templates_source
    assert "agent_adapter_entry_contracts.py" in design_source
    assert "agent_adapter_run_contract.py" in design_source
    assert "agent_adapter_entry_sections.py" in design_source
    assert "agent_adapter_entry_templates.py" in design_source


def test_agent_adapter_lifecycle_has_dedicated_boundary() -> None:
    facade_source = (REPO_ROOT / "src" / "loopora" / "agent_adapters.py").read_text(encoding="utf-8")
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_lifecycle.py").read_text(encoding="utf-8")
    status_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_status.py").read_text(encoding="utf-8")
    check_recovery_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_check_recovery.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_adapter_lifecycle import" in facade_source
    assert "from loopora.agent_adapter_check_recovery import adapter_check_recovery as _adapter_check_recovery" in lifecycle_source
    for marker in (
        "def list_agent_adapter_statuses",
        "def agent_adapter_status",
        "def check_agent_adapter",
        "def install_agent_adapter",
        "def uninstall_agent_adapter",
    ):
        assert marker in lifecycle_source
        assert marker not in facade_source
    assert "from loopora.agent_adapter_status import" in lifecycle_source
    assert "def managed_adapter_status" in status_source
    assert "def not_implemented_adapter_status" in status_source
    assert "def managed_adapter_status" not in lifecycle_source
    assert "def _managed_adapter_status" not in lifecycle_source
    assert "def adapter_check_recovery" in check_recovery_source
    assert "def adapter_check_recovery" not in lifecycle_source
    for marker in (
        "def write_agent_binding",
        "def agent_loop_command",
        "def agent_loop_json_command",
    ):
        assert marker in facade_source
        assert marker not in lifecycle_source
    assert "agent_adapter_lifecycle.py" in design_source
    assert "agent_adapter_status.py" in design_source
    assert "agent_adapter_check_recovery.py" in design_source


def test_agent_adapter_manifest_has_dedicated_boundary() -> None:
    managed_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_managed_files.py").read_text(encoding="utf-8")
    manifest_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_manifest.py").read_text(encoding="utf-8")
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_lifecycle.py").read_text(encoding="utf-8")
    status_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_status.py").read_text(encoding="utf-8")
    dev_reset_source = (REPO_ROOT / "src" / "loopora" / "dev_reset.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_adapter_manifest import" in managed_source
    assert "from loopora.agent_adapter_manifest import" in lifecycle_source
    assert "from loopora.agent_adapter_manifest import" in status_source
    assert "from loopora.agent_adapter_manifest import" in dev_reset_source
    for marker in (
        "def manifest_payload",
        "def read_manifest",
        "def manifest_paths",
        "def manifest_hash_for_path",
        "def obsolete_managed_paths",
        "def managed_marker",
        "def manifest_relative_path",
        "OBSOLETE_MANAGED_PATHS = {",
    ):
        assert marker in manifest_source
        assert marker not in managed_source
    for marker in (
        "def managed_file_status",
        "def managed_status_paths",
        "def remove_obsolete_managed_files",
        "def assert_targets_are_replaceable",
    ):
        assert marker in managed_source
        assert marker not in manifest_source
    assert "agent_adapter_manifest.py" in design_source
    assert "agent_adapter_managed_files.py" in design_source


def test_cli_agent_outputs_use_guidance_instead_of_submitted_step_private_wrappers() -> None:
    offenders = []
    for name in ("cli_agent_current_step_output.py", "cli_agent_step_presenters.py"):
        path = REPO_ROOT / "src" / "loopora" / name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != "loopora.cli_agent_submitted_step_output":
                continue
            if any(alias.name in {"_actionable_blocking_item", "_actionable_next_action"} for alias in node.names):
                offenders.append(name)

    assert offenders == []


def test_cli_agent_current_step_known_evidence_output_has_dedicated_boundary() -> None:
    current_step_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_output.py").read_text(
        encoding="utf-8"
    )
    evidence_output_source = (
        REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_evidence_output.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_current_step_evidence_output import" in current_step_source
    for marker in (
        "def print_agent_current_step_evidence_scope",
        "def print_agent_current_step_known_evidence",
        "def print_agent_current_step_known_evidence_refs",
        "def _format_known_evidence_artifact_refs",
    ):
        assert marker in evidence_output_source
        assert marker not in current_step_source
    assert "agent_known_evidence_ref_summaries" in evidence_output_source
    assert "agent_known_evidence_ref_summaries" not in current_step_source
    assert "cli_agent_current_step_evidence_output.py" in design_source


def test_cli_agent_current_step_continuation_output_has_dedicated_boundary() -> None:
    current_step_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_output.py").read_text(
        encoding="utf-8"
    )
    continuation_output_source = (
        REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_continuation_output.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_current_step_continuation_output import" in current_step_source
    for marker in (
        "def print_agent_continuation",
        "def _print_continuation_coverage",
        "def _print_continuation_next_focus",
        "def _print_continuation_focus_items",
    ):
        assert marker in continuation_output_source
        assert marker not in current_step_source
    assert "continuation_previous_run" in continuation_output_source
    assert "continuation_previous_run" not in current_step_source
    assert "cli_agent_current_step_continuation_output.py" in design_source


def test_cli_agent_current_step_iteration_output_has_dedicated_boundary() -> None:
    current_step_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_output.py").read_text(
        encoding="utf-8"
    )
    iteration_output_source = (
        REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_iteration_output.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_current_step_iteration_output import" in current_step_source
    for marker in (
        "def print_agent_iteration_context",
        "def _print_agent_iteration_repair",
        "iteration_repair_next_action",
        "iteration_repair_evidence_refs",
    ):
        assert marker in iteration_output_source
        assert marker not in current_step_source
    assert "actionable_next_action" in iteration_output_source
    assert "actionable_next_action" not in current_step_source
    assert "cli_agent_current_step_iteration_output.py" in design_source


def test_cli_agent_step_results_have_dedicated_boundary() -> None:
    presenters_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_step_presenters.py").read_text(
        encoding="utf-8"
    )
    results_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_step_results.py").read_text(encoding="utf-8")
    submit_results_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_submit_results.py").read_text(
        encoding="utf-8"
    )
    adapter_commands_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(
        encoding="utf-8"
    )
    runtime_commands_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_step_results import" in presenters_source
    assert "from loopora.cli_agent_submit_results import" in presenters_source
    assert "from loopora import cli_agent_step_presenters as _agent_step_presenters" in adapter_commands_source
    assert "from loopora.cli_agent_step_presenters import" in runtime_commands_source
    for marker in (
        "def _attach_agent_run_summary",
        "def _agent_next_json_payload",
        "def _agent_next_summary",
    ):
        assert marker in results_source
        assert marker not in presenters_source
        assert marker not in submit_results_source
    for marker in (
        "def _agent_submit_json_payload",
        "def _agent_submit_summary",
        "def _agent_submitted_step_summary",
    ):
        assert marker in submit_results_source
        assert marker not in presenters_source
        assert marker not in results_source
    for marker in (
        "def _print_agent_loop_result",
        "def _print_agent_step_result",
        "def _print_agent_next_result",
    ):
        assert marker in presenters_source
        assert marker not in results_source
    assert "cli_agent_step_results.py" in design_source
    assert "cli_agent_submit_results.py" in design_source
    assert "cli_agent_runtime_commands.py" in design_source


def test_agent_native_surface_plain_lines_have_dedicated_boundary() -> None:
    surface_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface.py").read_text(encoding="utf-8")
    lines_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface_lines.py").read_text(encoding="utf-8")
    helper_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface_line_helpers.py").read_text(encoding="utf-8")
    section_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface_section_lines.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_native_surface_lines import native_surface_plain_lines" in surface_source
    assert "from loopora.agent_native_surface_line_helpers import" in lines_source
    assert "from loopora.agent_native_surface_section_lines import" in lines_source
    for marker in (
        "def native_surface_plain_lines",
        "def _native_surface_capability_lines",
    ):
        assert marker in lines_source
        assert marker not in surface_source
    for marker in (
        "def _native_surface_kv_line",
        "def _native_surface_target_agents",
        "def _native_surface_role_config_refs",
    ):
        assert marker in helper_source
        assert marker not in lines_source
    for marker in (
        "def _native_surface_packaging_lines",
        "def _native_surface_permission_boundary_lines",
        "def _native_surface_ownership_lines",
    ):
        assert marker in section_source
        assert marker not in lines_source
    for marker in (
        "def attach_native_run_surface",
        "def agent_native_run_surface_for_result",
        "def _surface_adapter_from_sources",
    ):
        assert marker in surface_source
        assert marker not in lines_source
    assert "agent_native_surface_lines.py" in design_source
    assert "agent_native_surface_line_helpers.py" in design_source
    assert "agent_native_surface_section_lines.py" in design_source
