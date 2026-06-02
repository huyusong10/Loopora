from __future__ import annotations

from bundle_service_architecture_test_support import design_contracts_source, loopora_source


def test_bundle_control_local_governance_trace_has_dedicated_rule_boundary() -> None:
    trace_mining_source = loopora_source("service_bundle_control_trace_mining.py")
    local_governance_source = loopora_source("service_bundle_control_local_governance.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_bundle_control_local_governance import" in trace_mining_source
    assert "def select_local_governance_trace" in local_governance_source
    assert "def local_governance_trace_priority" in local_governance_source
    assert "LOCAL_GOVERNANCE_MARKER_PATTERN" in local_governance_source
    assert "_LOCAL_GOVERNANCE_MARKER_PATTERN" not in trace_mining_source
    assert "service_bundle_control_local_governance.py" in contracts_source


def test_bundle_control_diagnostics_have_split_input_boundary() -> None:
    diagnostics_source = loopora_source("service_bundle_control_diagnostics.py")
    input_diagnostics_source = loopora_source("service_bundle_control_input_diagnostics.py")
    input_state_source = loopora_source("service_bundle_control_input_state.py")
    entries_source = loopora_source("service_bundle_control_diagnostic_entries.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_bundle_control_input_diagnostics import append_strategy_input_diagnostics" in diagnostics_source
    assert "from loopora.service_bundle_control_diagnostic_entries import" in diagnostics_source
    assert "from loopora.service_bundle_control_diagnostic_entries import" in input_diagnostics_source
    assert "from loopora.service_bundle_control_input_state import" in input_diagnostics_source
    for marker in (
        "def append_strategy_input_diagnostics",
        "def _diagnose_gatekeeper_parallel_review_fan_in",
    ):
        assert marker in input_diagnostics_source
        assert marker not in diagnostics_source
    for marker in (
        "def initial_strategy_input_diagnostic_state",
        "def advance_strategy_diagnostic_state",
        "def input_missing_handoffs",
        "def input_queries_any_archetype",
    ):
        assert marker in input_state_source
        assert marker not in input_diagnostics_source
        assert marker not in diagnostics_source
    for marker in ("def build_bundle_control_diagnostics", "def _append_traceability_diagnostics"):
        assert marker in diagnostics_source
        assert marker not in input_diagnostics_source
    assert "def append_bundle_control_diagnostic" in entries_source
    assert "def _append_diagnostic" not in diagnostics_source
    assert "service_bundle_control_input_diagnostics.py" in contracts_source
    assert "service_bundle_control_input_state.py" in contracts_source
    assert "service_bundle_control_diagnostic_entries.py" in contracts_source


def test_bundle_control_trace_mining_has_split_input_and_pattern_boundaries() -> None:
    traces_source = loopora_source("service_bundle_control_traces.py")
    trace_mining_source = loopora_source("service_bundle_control_trace_mining.py")
    trace_projection_source = loopora_source("service_bundle_control_trace_projection.py")
    trace_inputs_source = loopora_source("service_bundle_control_trace_inputs.py")
    trace_patterns_source = loopora_source("service_bundle_control_trace_patterns.py")
    trace_preview_source = loopora_source("service_bundle_control_trace_preview.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_bundle_control_trace_inputs import" in trace_mining_source
    assert "from loopora.service_bundle_control_trace_patterns import" in trace_mining_source
    assert "from loopora.service_bundle_control_trace_preview import" in trace_mining_source
    assert "from loopora.service_bundle_control_trace_preview import" in traces_source
    assert "from loopora.service_bundle_control_trace_projection import" in traces_source
    for marker in ("class TraceTextSource", "def trace_text_candidates", "def strategy_source_payload"):
        assert marker in trace_inputs_source
        assert marker not in trace_mining_source
    for marker in ("TRADEOFF_PATTERNS = (", "EXECUTION_STRATEGY_PATTERNS = ("):
        assert marker in trace_patterns_source
        assert marker not in trace_mining_source
    for marker in ("def preview_list_items", "def build_role_posture_trace", "def role_posture_preview"):
        assert marker in trace_preview_source
        assert marker not in trace_mining_source
    for marker in ("def append_trace_item", "def coverage_trace", "def gatekeeper_trace", "def control_trace"):
        assert marker in trace_projection_source
        assert marker not in traces_source
    assert "def _judgment_tradeoff_trace" in trace_mining_source
    assert "def _judgment_tradeoff_trace" not in trace_inputs_source
    assert "service_bundle_control_trace_inputs.py" in contracts_source
    assert "service_bundle_control_trace_patterns.py" in contracts_source
    assert "service_bundle_control_trace_preview.py" in contracts_source
    assert "service_bundle_control_trace_projection.py" in contracts_source
