from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


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


def test_service_agent_entry_loop_projection_has_dedicated_boundary() -> None:
    adapter_source = (REPO_ROOT / "src" / "loopora" / "service_agent_adapters.py").read_text(encoding="utf-8")
    projection_source = (REPO_ROOT / "src" / "loopora" / "service_agent_entry_projection.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

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


def test_service_agent_adapter_facade_preserves_explicit_workdir_boundary() -> None:
    adapter_source = (REPO_ROOT / "src" / "loopora" / "service_agent_adapters.py").read_text(encoding="utf-8")
    context_binding_source = (REPO_ROOT / "src" / "loopora" / "agent_adapter_context_binding.py").read_text(encoding="utf-8")

    assert "Path.cwd()" not in adapter_source
    assert 'normalize_recoverable_workdir(workdir, action="agent")' in context_binding_source


def test_service_agent_continuation_helpers_have_dedicated_boundary() -> None:
    adapter_source = (REPO_ROOT / "src" / "loopora" / "service_agent_adapters.py").read_text(encoding="utf-8")
    continuation_source = (REPO_ROOT / "src" / "loopora" / "service_agent_continuation.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

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
    loop_start_source = (REPO_ROOT / "src" / "loopora" / "service_agent_loop_start.py").read_text(encoding="utf-8")
    loop_start_bindings_source = (REPO_ROOT / "src" / "loopora" / "service_agent_loop_start_bindings.py").read_text(encoding="utf-8")
    run_binding_source = (REPO_ROOT / "src" / "loopora" / "service_agent_run_context_binding.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

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
    candidate_facade_source = (REPO_ROOT / "src" / "loopora" / "service_agent_bundle_candidates.py").read_text(encoding="utf-8")
    intake_source = (REPO_ROOT / "src" / "loopora" / "service_agent_bundle_candidate_intake.py").read_text(encoding="utf-8")
    continuation_source = (REPO_ROOT / "src" / "loopora" / "service_agent_bundle_candidate_continuation.py").read_text(encoding="utf-8")
    recovery_source = (REPO_ROOT / "src" / "loopora" / "service_agent_bundle_candidate_recovery.py").read_text(encoding="utf-8")
    review_source = (REPO_ROOT / "src" / "loopora" / "service_agent_bundle_candidate_review.py").read_text(encoding="utf-8")
    types_source = (REPO_ROOT / "src" / "loopora" / "service_agent_bundle_candidate_types.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_agent_bundle_candidates import" in adapter_source
    assert "AgentBundleCandidateRequest as AgentBundleCandidateRequest" in adapter_source
    _assert_agent_adapter_mixin_composes_boundaries(adapter_source)
    assert "from loopora.service_agent_bundle_candidate_intake import ServiceAgentBundleCandidateMixin" in (candidate_facade_source)
    for marker in (
        "def create_agent_bundle_candidate",
        "candidate_yaml_provenance(",
    ):
        assert marker in intake_source
        assert marker not in adapter_source
        assert marker not in candidate_facade_source
    for marker in (
        "class AgentBundleCandidateRequest",
        "class AgentAlignmentContinuationRequest",
        "AGENT_CANDIDATE_PLAN_FILE_SAVE_ERROR",
    ):
        assert marker in types_source
        assert marker not in intake_source
    for marker in (
        "def _continue_agent_alignment_from_binding",
        "def _agent_alignment_continuation_session",
        "def _agent_message_requests_fresh_alignment",
    ):
        assert marker in continuation_source
        assert marker not in intake_source
    for marker in (
        "def _save_and_sync_agent_candidate",
        "def _write_agent_candidate_binding",
        "AGENT_CONTEXT_CARD_SAVE_ERROR",
    ):
        assert marker in recovery_source
        assert marker not in intake_source
    for marker in (
        "def _append_missing_agent_candidate_message",
        "def _missing_agent_candidate_notice",
        "alignment_notice_appender",
    ):
        assert marker in review_source
        assert marker not in intake_source
    assert "service_agent_bundle_candidates.py" in design_source
    assert "service_agent_bundle_candidate_intake.py" in design_source
    assert "service_agent_bundle_candidate_continuation.py" in design_source
    assert "service_agent_bundle_candidate_recovery.py" in design_source
    assert "service_agent_bundle_candidate_review.py" in design_source
