from __future__ import annotations

from pathlib import Path

from loopora.context_flow import (
    render_handoff_list_section,
    render_previous_iteration_summary,
)
from loopora.context_iteration_summary import IterationSummaryContext, build_iteration_summary
from loopora.context_step_results import (
    StepEvidenceEntryRequest,
    StepResultContext,
    build_step_evidence_entry,
    build_step_handoff,
)
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_runner_support import ServiceRunnerSupportMixin
from loopora.stagnation import StagnationUpdateRequest, update_stagnation
from loopora.runner_support_requests import RunnerSummaryRequest

def test_gatekeeper_output_rejects_unknown_evidence_refs() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "Looks good.",
            "composite_score": 1.0,
            "evidence_refs": ["missing_ev"],
            "evidence_claims": ["A concrete claim that still points to an unknown evidence ref."],
        },
        evidence_context={"items": [{"id": "known_ev", "archetype": "inspector"}]},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_evidence_refs_unknown: missing_ev"]


def test_previous_iteration_summary_keeps_blocking_items_as_next_round_inputs() -> None:
    handoff = {
        "source": {
            "step_order": 1,
            "role_name": "GateKeeper",
            "archetype": "gatekeeper",
        },
        "status": "blocked",
        "summary": "Evidence is still weak.",
        "blocking_items": ["permission proof missing", "audit trail unproven"],
        "evidence_refs": ["ev_000_01_gatekeeper"],
        "recommended_next_action": "Produce direct permission and audit evidence.",
    }
    summary = {
        "iter": 0,
        "workflow": [{"step_id": "builder_step"}, {"step_id": "gatekeeper_step"}],
        "step_handoffs": [handoff],
        "score": {"composite": 0.42, "delta": None, "passed": False},
        "stagnation": {
            "mode": "none",
            "evidence_progress_mode": "stalled",
            "covered_check_count": 0,
            "missing_check_count": 2,
            "consecutive_no_required_coverage_delta": 1,
        },
    }

    rendered = render_previous_iteration_summary(summary)

    assert 'blocking=["permission proof missing", "audit trail unproven"]' in rendered
    assert "evidence=[\"ev_000_01_gatekeeper\"]" in rendered
    assert "next=Produce direct permission and audit evidence." in rendered


def test_completed_handoff_list_keeps_blocking_items_for_downstream_roles() -> None:
    rendered = render_handoff_list_section(
        "Completed steps in this iteration",
        [
            {
                "source": {
                    "step_order": 0,
                    "role_name": "Contract Inspector",
                    "archetype": "inspector",
                },
                "status": "blocked",
                "summary": "Authorization check did not run.",
                "blocking_items": ["authorization coverage missing"],
                "evidence_refs": ["ev_000_00_inspector"],
                "recommended_next_action": "Run the authorization proof before GateKeeper.",
            }
        ],
        empty_text="No earlier steps have completed in this iteration yet.",
    )

    assert 'blocking=["authorization coverage missing"]' in rendered
    assert "evidence=[\"ev_000_00_inspector\"]" in rendered
    assert "next=Run the authorization proof before GateKeeper." in rendered


def test_builder_abandoned_note_is_residual_risk_not_blocking_item(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    result = StepResultContext(
        layout=layout,
        iter_id=0,
        step={"id": "builder_step"},
        step_order=0,
        role={"id": "builder", "name": "Builder", "archetype": "builder"},
        runtime_role="generator",
        output={
            "attempted": "Built the focused starter slice.",
            "abandoned": "Did not broaden the sandbox into a full application.",
            "assumption": "Inspect the starter check output before GateKeeper.",
            "summary": "Starter flow now has a project-owned check.",
            "changed_files": [],
            "proof_files": [],
            "proof_artifacts": [],
            "artifact_paths": [],
        },
    )

    handoff = build_step_handoff(result)
    evidence = build_step_evidence_entry(StepEvidenceEntryRequest(result=result, handoff=handoff))

    assert handoff["status"] == "completed"
    assert handoff["blocking_items"] == []
    assert "Out-of-scope or unfinished note: Did not broaden the sandbox into a full application." in handoff["summary"]
    assert evidence["residual_risk"] == "Did not broaden the sandbox into a full application." and evidence["verifies"] == ["step_result:builder_step:completed"]


def test_inspector_handoff_deduplicates_failed_items_and_check_results(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    handoff = build_step_handoff(
        StepResultContext(
            layout=layout,
            iter_id=0,
            step={"id": "contract_inspection_step"},
            step_order=1,
            role={"id": "contract_inspector", "name": "Contract Inspector", "archetype": "inspector"},
            runtime_role="contract_inspector",
            output={
                "tester_observations": "Primary-flow proof is still weak.",
                "failed_items": [
                    {"id": "contract.primary_flow", "title": "Primary flow evidence"},
                    {"id": "contract.project_evidence", "title": "Project-owned evidence"},
                ],
                "check_results": [
                    {"id": "contract.primary_flow", "title": "Primary flow evidence", "status": "failed"},
                    {"id": "contract.project_evidence", "title": "Project-owned evidence", "status": "failed"},
                ],
                "dynamic_checks": [],
            },
        )
    )

    assert handoff["status"] == "blocked"
    assert handoff["blocking_items"] == ["Primary flow evidence", "Project-owned evidence"]


def test_gatekeeper_handoff_projects_blocking_issues_and_hard_constraints(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()

    handoff = build_step_handoff(
        StepResultContext(
            layout=layout,
            iter_id=0,
            step={"id": "gatekeeper_step"},
            step_order=2,
            role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
            runtime_role="gatekeeper",
            output={
                "passed": False,
                "decision_summary": "Primary-flow evidence is not sufficient.",
                "feedback_to_builder": "Produce direct primary-flow proof before asking for closure.",
                "blocking_issues": ["primary_flow_unproven"],
                "hard_constraint_violations": ["audit_chain_missing"],
                "failed_check_ids": ["done_when.check_001"],
                "priority_failures": [{"summary": "Payment failure path has no traceable handoff."}],
            },
        )
    )

    assert handoff["status"] == "blocked"
    assert handoff["blocking_items"] == [
        "primary_flow_unproven",
        "audit_chain_missing",
        "done_when.check_001",
        "Payment failure path has no traceable handoff.",
    ]
    assert handoff["recommended_next_action"] == "Produce direct primary-flow proof before asking for closure."


def test_gatekeeper_pass_handoff_does_not_report_blocking_next_action(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()

    handoff = build_step_handoff(
        StepResultContext(
            layout=layout,
            iter_id=0,
            step={"id": "gatekeeper_step"},
            step_order=2,
            role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
            runtime_role="gatekeeper",
            output={
                "passed": True,
                "decision_summary": "Required evidence passed.",
                "feedback_to_builder": "",
                "feedback_to_generator": "",
                "blocking_issues": [],
                "hard_constraint_violations": [],
                "failed_check_ids": [],
                "priority_failures": [],
            },
        )
    )

    assert handoff["status"] == "passed"
    assert handoff["blocking_items"] == []
    assert handoff["recommended_next_action"] == "No further role action is required; the GateKeeper verdict passed."


def test_step_evidence_entry_deduplicates_related_and_coverage_refs(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    result = StepResultContext(
        layout=layout,
        iter_id=0,
        step={"id": "gatekeeper_step"},
        step_order=3,
        role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        runtime_role="gatekeeper",
        output={
            "passed": False,
            "decision_summary": "Known evidence still blocks the task.",
            "evidence_refs": ["ev_builder", "ev_inspector", "ev_builder", "ev_000_03_gatekeeper_step"],
            "coverage_results": [
                {
                    "target_id": "done_when.check_001",
                    "status": "blocked",
                    "evidence_refs": ["ev_inspector", "ev_builder", "ev_inspector"],
                    "note": "The primary flow is still blocked.",
                }
            ],
        },
    )

    entry = build_step_evidence_entry(
        StepEvidenceEntryRequest(
            result=result,
            handoff={"status": "blocked", "summary": "GateKeeper blocked the task.", "artifact_refs": []},
        )
    )

    assert entry["related_evidence_ids"] == ["ev_builder", "ev_inspector"]
    assert entry["coverage_results"][0]["evidence_refs"] == ["ev_inspector", "ev_builder"]


def test_gatekeeper_output_rejects_unknown_coverage_result_evidence_refs() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The top-level verdict cites real evidence, but target coverage cites an invented ref.",
            "composite_score": 1.0,
            "evidence_refs": ["known_ev"],
            "evidence_claims": ["A concrete claim that cites the known upstream inspection evidence."],
            "coverage_results": [
                {
                    "target_id": "fake_done.risk_001",
                    "status": "covered",
                    "evidence_refs": ["invented_ev"],
                    "note": "This target-specific evidence ref is not in the known evidence set.",
                }
            ],
        },
        evidence_context={
            "items": [
                {
                    "id": "known_ev",
                    "archetype": "inspector",
                    "result": "passed",
                    "verifies": ["check_results:known_ev_check:passed"],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_coverage_evidence_refs_unknown: invented_ev"]


def test_gatekeeper_output_allows_first_gate_measured_evidence_claim() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "",
            "metric_scores": {
                "quality_score": {"value": 0.95, "threshold": 0.9, "passed": True},
            },
            "evidence_claims": ["Measured benchmark evidence satisfied the first GateKeeper pass."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is True
    assert output["decision_summary"] == "All checks passed."
    assert output["evidence_refs"] == ["ev_gatekeeper"]
    assert output["evidence_gate_status"] == "passed"


def test_gatekeeper_output_requires_literal_boolean_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": "true",
            "decision_summary": "Looks good.",
            "metric_scores": {
                "quality_score": {"value": 0.95, "threshold": 0.9, "passed": "true"},
            },
            "evidence_claims": ["Measured benchmark evidence satisfied the first GateKeeper pass."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["metric_scores"]["quality_score"]["passed"] is False
    assert output["metrics"][0]["passed"] is False
    assert output["evidence_refs"] == []
    assert output["evidence_gate_status"] == "not_passed"


def test_gatekeeper_output_default_composite_requires_literal_boolean_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": "true",
            "decision_summary": "A string pass should not set the fallback score.",
            "evidence_claims": ["String boolean values are not measured proof."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.0
    assert output["evidence_gate_status"] == "not_passed"


def test_workflow_summary_requires_literal_gatekeeper_passed_boolean(tmp_path: Path) -> None:
    class RunnerSupportHarness(ServiceRunnerSupportMixin):
        @staticmethod
        def _truncate_text(value: str | None, max_length: int = 220) -> str:
            return str(value or "")[:max_length]

    service = RunnerSupportHarness()
    gatekeeper_step_result = {
        "step": {"id": "gatekeeper_step"},
        "step_order": 0,
        "role": {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        "runtime_role": "verifier",
        "output": {
            "passed": "true",
            "decision_summary": "String pass must remain blocked in summary projections.",
            "composite_score": 1.0,
            "evidence_refs": [],
        },
    }

    entry = service._build_runner_iteration_entry(
        0,
        [gatekeeper_step_result],
        {"stagnation_mode": "none"},
        previous_composite=None,
    )
    summary = service._build_runner_summary(
        RunnerSummaryRequest(
            run={"workdir": str(tmp_path), "completion_mode": "gatekeeper", "iteration_interval_seconds": 0.0},
            strategy_source={"preset": "custom"},
            compiled_spec={"checks": [], "check_mode": "specified"},
            iter_id=0,
            step_results=[gatekeeper_step_result],
            stagnation={"stagnation_mode": "none"},
            exhausted=False,
            previous_composite=None,
        )
    )

    assert entry["score"]["passed"] is False
    assert "- Passed: `False`" in summary and "- Strategy preset: `custom`" in summary
    assert "Still iterating." in summary
    assert "All checks passed in this iteration." not in summary and "- Workflow preset:" not in summary


def test_iteration_summaries_require_literal_score_numbers(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    gatekeeper_step_result = {
        "step": {"id": "gatekeeper_step"},
        "step_order": 0,
        "role": {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        "runtime_role": "verifier",
        "output": {
            "passed": False,
            "decision_summary": "String scores should not enter iteration context.",
            "composite_score": "0.95",
            "evidence_refs": [],
        },
        "handoff": {"status": "failed", "source": {"step_order": 0, "step_id": "gatekeeper_step"}},
    }
    stagnation = {
        "stagnation_mode": "plateau",
        "recent_composites": ["0.7", 0.8, True],
        "recent_deltas": ["0.1", 0.2, False],
        "consecutive_low_delta": "2",
    }
    service = ServiceRunnerSupportMixin()

    legacy_entry = service._build_runner_iteration_entry(
        0,
        [gatekeeper_step_result],
        stagnation,
        previous_composite=0.4,
    )
    summary = build_iteration_summary(
        IterationSummaryContext(
            layout=layout,
            iter_id=0,
            step_results=[gatekeeper_step_result],
            stagnation=stagnation,
            previous_composite=0.4,
            timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert legacy_entry["score"]["composite"] is None
    assert legacy_entry["score"]["delta"] is None
    assert legacy_entry["stagnation"]["recent_composites"] == [0.8]
    assert legacy_entry["stagnation"]["recent_deltas"] == [0.2]
    assert legacy_entry["stagnation"]["consecutive_low_delta"] == 0
    assert summary["score"]["composite"] is None
    assert summary["score"]["delta"] is None
    assert summary["stagnation"]["recent_composites"] == [0.8]
    assert summary["stagnation"]["recent_deltas"] == [0.2]
    assert summary["stagnation"]["consecutive_low_delta"] == 0


def test_stagnation_update_requires_literal_score_history() -> None:
    stagnation = update_stagnation(
        StagnationUpdateRequest(
            stagnation={
                "recent_composites": ["0.7", 0.8, True],
                "recent_deltas": ["0.1", 0.2, False],
            },
            composite=0.81,
            current_iter=1,
            delta_threshold=0.05,
            trigger_window=2,
            regression_window=2,
        )
    )

    assert stagnation["recent_composites"] == [0.8, 0.81]
    assert stagnation["recent_deltas"] == [0.2, 0.01]
    assert stagnation["consecutive_low_delta"] == 1
    assert stagnation["stagnation_mode"] == "none"


def test_gatekeeper_output_normalizes_metric_row_booleans() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": False,
            "decision_summary": "The measured check did not pass.",
            "metrics": [
                {"name": "quality_score", "value": 0.8, "threshold": 0.9, "passed": "false"},
            ],
            "evidence_claims": ["Measured benchmark evidence did not satisfy the first GateKeeper pass."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["metric_scores"]["quality_score"]["passed"] is False
    assert output["metrics"] == [{"name": "quality_score", "value": 0.8, "threshold": 0.9, "passed": False}]
