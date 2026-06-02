from __future__ import annotations

from loopora.events import CORE_EVENT_AGGREGATE_TYPES, CORE_EVENT_TYPES

from kernel_architecture_test_support import REPO_ROOT, design_contracts_source, loopora_source


def test_core_event_schema_excludes_surface_observability_events() -> None:
    surface_events = {
        "WebPageOpened",
        "AgentCommandRendered",
        "CliJsonPrinted",
        "HostTraceObserved",
        "TodoUpdated",
        "AdapterCheckPassed",
        "StatuslineRead",
    }

    assert CORE_EVENT_TYPES.isdisjoint(surface_events)


def test_core_event_schema_binds_event_types_to_aggregate_families() -> None:
    schemas_source = loopora_source("events/schemas.py")
    append_source = loopora_source("events/append_requests.py")
    invariants_source = loopora_source("events/run_event_invariants.py")
    invariants_dir = REPO_ROOT / "src" / "loopora" / "events" / "invariants"
    db_event_source = loopora_source("db_domain_event_records.py")
    artifact_index_source = loopora_source("db_artifact_index_records.py")
    contracts_source = design_contracts_source()

    assert set(CORE_EVENT_AGGREGATE_TYPES) == CORE_EVENT_TYPES
    assert CORE_EVENT_AGGREGATE_TYPES["LoopActivated"] == "loop"
    assert CORE_EVENT_AGGREGATE_TYPES["RunStarted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["StepPlanned"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["StepClaimed"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["StepInstructionIssued"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["EvidenceAccepted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["VerdictIssued"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["ResidualRiskAccepted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["IterationStarted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["NextGapSelected"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["StrategyAdvanced"] == "run"
    assert "def require_core_event_family" in schemas_source
    assert "def require_core_event_stream_boundary" in schemas_source
    assert "require_core_event_family" in append_source
    assert "def require_run_event_append_invariants" in invariants_source
    assert "require_run_event_append_invariants" in db_event_source
    assert "require_core_event_stream_boundary" in db_event_source
    assert "from loopora.db_artifact_index_records import" in db_event_source
    assert "def record_artifact_index_for_connection" in artifact_index_source
    assert "def list_artifact_index_for_connection" in artifact_index_source
    assert "INSERT OR REPLACE INTO artifact_index" not in db_event_source
    assert "db_artifact_index_records.py" in contracts_source
    assert {path.name for path in invariants_dir.glob("*.py")} >= {
        "lifecycle.py",
        "step.py",
        "evidence.py",
        "coverage.py",
        "verdict.py",
        "causation.py",
        "causation_lifecycle.py",
        "causation_step.py",
        "causation_evidence.py",
        "causation_verdict.py",
    }
    assert "require_run_lifecycle_append_allowed" in invariants_source
    assert "require_step_result_event_identity" in invariants_source
    assert "require_evidence_accepted_identity" in invariants_source
    assert "require_coverage_payload_status_consistency" in invariants_source
    assert "require_verdict_status_known" in invariants_source
    assert "require_next_gap_selected_causation" in invariants_source
    assert "require_next_gap_selected_shape" in invariants_source
    assert "require_residual_risk_accepted_causation" in invariants_source
    assert "require_residual_risk_accepted_shape" in invariants_source
    assert "require_strategy_advanced_causation" in invariants_source
    assert "require_run_closed_causation_references_passing_verdict" in invariants_source
    causation_source = (invariants_dir / "causation.py").read_text(encoding="utf-8")
    assert "from loopora.events.invariants.causation_lifecycle import" in causation_source
    assert "from loopora.events.invariants.causation_step import" in causation_source
    assert "from loopora.events.invariants.causation_evidence import" in causation_source
    assert "from loopora.events.invariants.causation_verdict import" in causation_source
    assert "def require_" not in causation_source
