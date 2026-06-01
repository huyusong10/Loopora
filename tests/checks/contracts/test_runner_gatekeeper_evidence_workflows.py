from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor
from loopora.run_takeaways import build_run_key_takeaways

from runner_helpers import (
    _create_loop,
    _read_jsonl,
    _step_outputs_by_archetype,
)


def test_gatekeeper_pass_without_evidence_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class UnsupportedPassingExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype != "gatekeeper":
                raise AssertionError("Only GateKeeper should run in this fixture.")
            payload = {
                "passed": True,
                "decision_summary": "Looks good from a quick read.",
                "feedback_to_builder": "No code change is required.",
                "blocking_issues": [],
                "metrics": [],
                "failed_check_ids": [],
                "priority_failures": [],
                "composite_score": 1.0,
            }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = UnsupportedPassingExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Unsupported Gate Loop",
        max_iters=1,
        workflow={"preset": "benchmark_loop"},
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "failed"
    assert gatekeeper_output["passed"] is False
    assert "gatekeeper_pass_requires_evidence_refs" in gatekeeper_output["blocking_issues"]
    assert gatekeeper_output["evidence_gate_status"] == "blocked"


def test_gatekeeper_pass_with_claims_but_no_measured_evidence_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class ClaimOnlyExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype != "gatekeeper":
                raise AssertionError("Only GateKeeper should run in this fixture.")
            payload = {
                "passed": True,
                "decision_summary": "Looks finished from the visible description.",
                "feedback_to_builder": "No code change is required.",
                "blocking_issues": [],
                "metrics": [],
                "failed_check_ids": [],
                "priority_failures": [],
                "composite_score": 1.0,
                "evidence_refs": ["self"],
                "evidence_claims": ["The task appears complete based on a prose inspection without a measured proof path."],
            }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = ClaimOnlyExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Claim Only Gate Loop",
        max_iters=1,
        workflow={"preset": "benchmark_loop"},
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "failed"
    assert run["run_status"] == "failed"
    assert run["task_verdict"]["status"] == "failed"
    assert "blocking" in run["task_verdict"]["buckets"]
    assert gatekeeper_output["passed"] is False
    assert "gatekeeper_pass_requires_upstream_or_measured_evidence" in gatekeeper_output["blocking_issues"]
    assert gatekeeper_output["evidence_refs"] == ["ev_000_00_gatekeeper_step"]


def test_gatekeeper_pass_with_uncovered_required_targets_does_not_pass_task_verdict(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class UncoveredRequiredTargetsExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Left a generic implementation handoff.",
                    "abandoned": "",
                    "assumption": "",
                    "summary": "No required coverage target was directly verified.",
                    "changed_files": [],
                }
            elif request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 0,
                        "passed": 0,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 1,
                    },
                    "check_results": [],
                    "dynamic_checks": [],
                    "tester_observations": "This produced an upstream observation without verifying required targets.",
                    "coverage_results": [],
                }
            else:
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper accepted a generic upstream observation.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True},
                    ],
                    "metric_scores": {
                        "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
                    },
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": ["ev_000_01_inspector_step"],
                    "evidence_claims": ["The inspector produced an observation, but no required target was verified."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = UncoveredRequiredTargetsExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Uncovered Required Target Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]
    latest_iteration_summary = json.loads((run_dir / "context" / "latest_iteration_summary.json").read_text(encoding="utf-8"))
    takeaways = build_run_key_takeaways(service.get_run(run["id"]))
    latest_takeaway = takeaways["iterations"][0]

    assert run["status"] == "succeeded"
    assert gatekeeper_output["evidence_gate_status"] == "passed"
    assert "Task verdict passes" not in gatekeeper_output["decision_summary"]
    assert "Loopora Core still derives the task verdict" in gatekeeper_output["decision_summary"]
    assert "Task verdict passes" not in latest_iteration_summary["gatekeeper_verdict"]["decision_summary"]
    assert coverage["status"] == "partial"
    assert run["task_verdict"]["status"] == "insufficient_evidence"
    assert run["task_verdict"]["source"] == "gatekeeper"
    assert latest_takeaway["status"] == "blocked"
    assert "Task verdict insufficient evidence" in latest_takeaway["summary"]
    assert "Required coverage targets still lack direct evidence" in latest_takeaway["summary"]
    events = service.stream_events(run["id"], limit=200)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"]["status"] == "succeeded"
        and event["payload"]["task_verdict_status"] == "insufficient_evidence"
        and event["payload"]["task_verdict_source"] == "gatekeeper"
        and event["payload"]["task_verdict_summary"] == run["task_verdict"]["summary"]
        for event in events
    )


def test_gatekeeper_pass_with_residual_risk_projects_task_verdict(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class ResidualRiskPassingExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 2,
                        "passed": 2,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 50,
                    },
                    "check_results": [
                        {
                            "id": "check_001",
                            "title": "Primary experience",
                            "status": "passed",
                            "notes": "Primary path is proven.",
                        },
                        {
                            "id": "check_002",
                            "title": "Edge path",
                            "status": "passed",
                            "notes": "Edge path is proven with a named follow-up.",
                        },
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "Both required checks are covered.",
                    "coverage_results": [],
                }
            else:
                evidence_refs = [item["id"] for item in request.extra_context["step_instruction_context"]["evidence"]["items"]]
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper passed with a named acceptable follow-up risk.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True},
                    ],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": ["The inspector evidence covers both required checks."],
                    "residual_risks": ["Manual copy polish remains a visible follow-up."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = ResidualRiskPassingExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Residual Risk Gate Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    gatekeeper_entry = next(item for item in ledger if item["archetype"] == "gatekeeper")

    assert run["status"] == "succeeded"
    assert run["task_verdict"]["status"] == "passed_with_residual_risk"
    assert run["task_verdict"]["buckets"]["residual_risk"] == [{"label": "Manual copy polish remains a visible follow-up.", "managed": True}]
    assert gatekeeper_entry["residual_risk"] == "Manual copy polish remains a visible follow-up."


def test_loop_rejects_gatekeeper_residual_risk_when_contract_disallows_acceptance(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class DisallowedResidualRiskExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 1,
                        "passed": 1,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 50,
                    },
                    "check_results": [
                        {
                            "id": "check_001",
                            "title": "Primary experience",
                            "status": "passed",
                            "notes": "Primary path is proven.",
                        },
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "The required check is covered.",
                    "coverage_results": [],
                }
            else:
                evidence_refs = [item["id"] for item in request.extra_context["step_instruction_context"]["evidence"]["items"]]
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper accepted a managed residual risk.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True},
                    ],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": ["The inspector evidence covers the required check."],
                    "residual_risks": ["Manual billing export remains visible as a follow-up owned by Support."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = DisallowedResidualRiskExecutor
    spec_file = sample_spec_file.with_name("no_residual_risk_spec.md")
    spec_file.write_text(
        sample_spec_file.read_text(encoding="utf-8").replace(
            "Minor copy polish can wait, but unverifiable completion should fail closed.",
            "No residual risk is acceptable; any remaining risk must fail closed.",
        ),
        encoding="utf-8",
    )
    workflow = {
        "version": 1,
        "roles": [
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        spec_file,
        sample_workdir,
        name="No Residual Risk Gate Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "failed"
    assert run["task_verdict"]["status"] == "failed"
    assert gatekeeper_output["passed"] is False
    assert gatekeeper_output["blocking_issues"][0].startswith("gatekeeper_pass_violates_no_residual_risk_policy:")
    assert "Manual billing export remains visible as a follow-up owned by Support." in gatekeeper_output["blocking_issues"][0]
    assert gatekeeper_output["residual_risks"] == ["Manual billing export remains visible as a follow-up owned by Support."]


def test_round_mode_carries_gatekeeper_residual_risk_into_next_iteration_prompt(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    second_builder_prompt = ""
    second_builder_context: dict = {}

    class ResidualRiskCarryForwardExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            nonlocal second_builder_prompt, second_builder_context
            set_child_pid(None)
            iter_id = request.extra_context["iter_id"]
            if request.role_archetype == "builder":
                if iter_id == 1:
                    second_builder_prompt = request.prompt
                    second_builder_context = request.extra_context["step_instruction_context"]
                payload = {
                    "attempted": "Built the primary slice.",
                    "summary": "Builder changed only the focused primary slice.",
                    "changed_files": [],
                    "proof_files": [],
                    "proof_artifacts": [],
                    "artifact_paths": [],
                }
            elif request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 1,
                        "passed": 1,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 20,
                    },
                    "check_results": [
                        {
                            "id": "primary_slice_check",
                            "title": "Primary slice check",
                            "status": "passed",
                            "notes": "Inspector produced direct evidence for the primary slice.",
                        }
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "Inspector evidence covers the primary slice.",
                    "coverage_results": [],
                }
            else:
                step_instruction_context = request.extra_context["step_instruction_context"]
                evidence_refs = [item["id"] for item in step_instruction_context["evidence"]["items"] if item.get("archetype") == "inspector"]
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper passed with a managed residual risk in round mode.",
                    "feedback_to_builder": "Keep the named residual risk visible while continuing the next round.",
                    "blocking_issues": [],
                    "hard_constraint_violations": [],
                    "metrics": [],
                    "metric_scores": {
                        "check_pass_rate": {"value": 1.0, "threshold": 0.9, "passed": True},
                        "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
                    },
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": ["Inspector proof covers the primary slice."],
                    "residual_risks": ["Manual copy polish remains visible as a follow-up owned by docs."],
                    "coverage_results": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = ResidualRiskCarryForwardExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Residual Risk Carry Forward Loop",
        workflow=workflow,
        completion_mode="rounds",
        max_iters=2,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    first_iteration_summary = json.loads((run_dir / "iterations" / "iter_000" / "summary.json").read_text(encoding="utf-8"))
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    second_builder_request = next(item for item in role_requests if item["role_archetype"] == "builder" and item["iter"] == 1)

    assert second_builder_prompt
    assert first_iteration_summary["gatekeeper_verdict"]["residual_risks"] == [
        "Manual copy polish remains visible as a follow-up owned by docs."
    ]
    assert second_builder_context["upstream"]["previous_iteration_summary"]["gatekeeper_verdict"]["residual_risks"] == [
        "Manual copy polish remains visible as a follow-up owned by docs."
    ]
    assert 'GateKeeper residual risks: ["Manual copy polish remains visible as a follow-up owned by docs."]' in second_builder_prompt
    assert "residual_risk=Manual copy polish remains visible as a follow-up owned by docs." in second_builder_prompt
    assert second_builder_request["context_summary"]["previous_iteration_summary"]["gatekeeper_residual_risk_count"] == 1


def test_gatekeeper_pass_citing_plain_builder_handoff_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class BuilderHandoffOnlyExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Produced a candidate without proof artifacts.",
                    "abandoned": "",
                    "assumption": "",
                    "summary": "Builder says the task is done.",
                    "changed_files": [],
                    "proof_files": [],
                    "proof_artifacts": [],
                    "artifact_paths": [],
                }
            else:
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper accepted the Builder handoff as proof.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": ["ev_000_00_builder_step"],
                    "evidence_claims": ["The Builder handoff says the task is complete."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = BuilderHandoffOnlyExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Builder Handoff Only Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "failed"
    assert run["task_verdict"]["status"] == "failed"
    assert gatekeeper_output["passed"] is False
    assert gatekeeper_output["evidence_gate_status"] == "blocked"
    assert gatekeeper_output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]
    assert coverage["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert coverage["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_000_00_builder_step"]


def test_gatekeeper_pass_citing_missing_builder_proof_artifact_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    proof_path = sample_workdir / "tests" / "evidence" / "proof.json"

    class MissingProofArtifactExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "builder":
                proof_path.parent.mkdir(parents=True, exist_ok=True)
                proof_path.write_text('{"ok": true}\n', encoding="utf-8")
                payload = {
                    "attempted": "Produced a candidate with a proof artifact.",
                    "abandoned": "",
                    "assumption": "",
                    "summary": "Builder left proof for the task.",
                    "changed_files": [],
                    "proof_files": ["tests/evidence/proof.json"],
                    "proof_artifacts": [],
                    "artifact_paths": [],
                }
            else:
                proof_path.unlink()
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper accepted a proof artifact that is no longer available.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": ["ev_000_00_builder_step"],
                    "evidence_claims": ["The proof artifact path should remain readable at close time."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = MissingProofArtifactExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Missing Proof Artifact Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "evidence" / "manifest.json").read_text(encoding="utf-8"))
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]
    builder_claim = next(item for item in manifest["claims"] if item["id"] == "ev_000_00_builder_step")

    assert run["status"] == "failed"
    assert gatekeeper_output["passed"] is False
    assert gatekeeper_output["evidence_gate_status"] == "blocked"
    assert gatekeeper_output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]
    assert coverage["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert coverage["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_000_00_builder_step"]
    assert builder_claim["verification_status"] == "run_artifact"
    assert builder_claim["workspace_backed"] is False
    assert any(problem["code"] == "claim_artifact_missing" for problem in manifest["problems"])


