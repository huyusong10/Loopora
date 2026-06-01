from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopora.executor import CodexExecutor
from loopora.run_takeaways import build_run_key_takeaways

from runner_helpers import (
    _create_loop,
    _read_jsonl,
    _step_outputs_by_archetype,
)


def test_workflow_control_records_runtime_evidence_and_respects_fire_limit(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="plateau")
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "guide", "name": "Guide", "archetype": "guide", "prompt_ref": "guide.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
        "controls": [
            {
                "id": "gatekeeper_rejection_guidance",
                "when": {"signal": "gatekeeper_rejected", "after": "0s"},
                "call": {"role_id": "guide"},
                "mode": "repair_guidance",
                "max_fires_per_run": 1,
            }
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Controlled Rejection Loop",
        workflow=workflow,
        max_iters=3,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    events = service.stream_events(run["id"], limit=500)
    evidence_ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")

    assert run["status"] == "failed"
    assert [event["event_type"] for event in events].count("control_triggered") == 1
    assert [event["event_type"] for event in events].count("control_completed") == 1
    assert any(event["event_type"] == "control_skipped" for event in events)
    control_entries = [entry for entry in evidence_ledger if entry["evidence_kind"] == "control"]
    assert len(control_entries) == 1
    assert control_entries[0]["source"] == "workflow_control"
    assert "control:gatekeeper_rejected" in control_entries[0]["verifies"]


def test_workflow_control_triggers_when_required_coverage_stalls(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class CoverageStallExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            iter_id = int(request.extra_context.get("iter_id") or 0)
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Kept changing the story without adding required proof.",
                    "abandoned": "",
                    "assumption": "",
                    "summary": "No required coverage target was verified.",
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
                    "tester_observations": "No required Done When target has direct evidence yet.",
                    "coverage_results": [],
                }
            elif request.role_archetype == "guide":
                payload = {
                    "created_at_iter": iter_id,
                    "mode": "coverage_stalled",
                    "consumed": False,
                    "analysis": {
                        "recommended_shift": "Stop changing the narrative and produce one required proof target.",
                        "risk_note": "Coverage stalled while required checks remain missing.",
                    },
                    "seed_question": "Which missing Done When target can be proved next?",
                    "meta_note": "Coverage control fired.",
                }
            else:
                payload = {
                    "passed": False,
                    "decision_summary": "Composite improved, but required evidence coverage did not.",
                    "feedback_to_builder": "Produce direct proof for a required Done When target.",
                    "blocking_issues": [],
                    "metrics": [
                        {
                            "name": "quality_score",
                            "value": 0.5 + iter_id * 0.1,
                            "threshold": 0.9,
                            "passed": False,
                        }
                    ],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.5 + iter_id * 0.1,
                    "evidence_refs": [],
                    "evidence_claims": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = CoverageStallExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "guide", "name": "Guide", "archetype": "guide", "prompt_ref": "guide.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
        "controls": [
            {
                "id": "coverage_stall_guidance",
                "when": {"signal": "no_evidence_progress", "after": "0s"},
                "call": {"role_id": "guide"},
                "mode": "repair_guidance",
                "max_fires_per_run": 1,
            }
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Coverage Stall Control Loop",
        workflow=workflow,
        max_iters=2,
        trigger_window=1,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    stagnation = json.loads((run_dir / "timeline" / "stagnation.json").read_text(encoding="utf-8"))
    latest_iteration_summary = json.loads((run_dir / "context" / "latest_iteration_summary.json").read_text(encoding="utf-8"))
    events = service.stream_events(run["id"], limit=500)
    evidence_ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    guide_request = next(item for item in role_requests if item["role_archetype"] == "guide")
    guide_prompt = (run_dir / guide_request["prompt_path"]).read_text(encoding="utf-8")
    takeaways = build_run_key_takeaways(service.get_run(run["id"]))
    latest_takeaway = takeaways["iterations"][0]

    assert run["status"] == "failed"
    assert stagnation["stagnation_mode"] == "none"
    assert stagnation["evidence_progress_mode"] == "stalled"
    assert stagnation["latest_missing_check_count"] == 2
    assert latest_iteration_summary["stagnation"]["evidence_progress_mode"] == "stalled"
    assert latest_iteration_summary["stagnation"]["coverage_status"] == "blocked"
    assert latest_iteration_summary["stagnation"]["covered_check_count"] == 0
    assert latest_iteration_summary["stagnation"]["missing_check_count"] == 2
    assert latest_iteration_summary["stagnation"]["missing_check_ids"] == ["check_001", "check_002"]
    assert any(item["target_id"] == "done_when.check_001" for item in latest_iteration_summary["stagnation"]["coverage_top_gaps"])
    assert (prompt_context := guide_request["context_summary"]["headless_prompt_context"])["evidence_progress_mode"] == "stalled"
    assert prompt_context["coverage_status"] == "blocked"
    assert prompt_context["covered_check_count"] == 0
    assert prompt_context["missing_check_count"] == 2
    assert prompt_context["missing_check_ids"] == ["check_001", "check_002"]
    assert any(item["target_id"] == "done_when.check_001" for item in prompt_context["coverage_top_gaps"])
    assert "Evidence progress mode: stalled" in guide_prompt
    assert 'Missing required check ids: ["check_001", "check_002"]' in guide_prompt
    assert '"target_id": "done_when.check_001"' in guide_prompt
    assert "Required coverage: 0 covered, 2 missing" in guide_prompt
    assert latest_takeaway["evidence_progress_mode"] == "stalled"
    assert latest_takeaway["coverage_status"] == "blocked"
    assert latest_takeaway["covered_check_count"] == 0
    assert latest_takeaway["missing_check_count"] == 2
    assert latest_takeaway["missing_check_ids"] == ["check_001", "check_002"]
    assert any(item["target_id"] == "done_when.check_001" for item in latest_takeaway["coverage_top_gaps"])
    assert latest_takeaway["consecutive_no_required_coverage_delta"] == 1
    assert any(
        event["event_type"] == "control_triggered"
        and event["payload"]["signal"] == "no_evidence_progress"
        and "Required coverage did not improve" in event["payload"]["reason"]
        for event in events
    )
    assert any(entry["evidence_kind"] == "control" and "control:no_evidence_progress" in entry["verifies"] for entry in evidence_ledger)


@pytest.mark.parametrize("max_fires_per_run", [0, True, "2"])
def test_workflow_run_rejects_invalid_persisted_control_fire_limit(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    max_fires_per_run: object,
) -> None:
    service = service_factory(scenario="success")
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "guide", "name": "Guide", "archetype": "guide", "prompt_ref": "guide.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
        "controls": [
            {
                "id": "stale_evidence_check",
                "when": {"signal": "no_evidence_progress", "after": "0s"},
                "call": {"role_id": "guide"},
                "mode": "repair_guidance",
                "max_fires_per_run": 1,
            }
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Corrupted Control Loop",
        workflow=workflow,
    )
    corrupted_workflow = json.loads(json.dumps(loop["workflow_json"]))
    corrupted_workflow["controls"][0]["max_fires_per_run"] = max_fires_per_run
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_definitions SET workflow_json = ? WHERE id = ?",
            (json.dumps(corrupted_workflow, ensure_ascii=False), loop["id"]),
        )

    run = service.rerun(loop["id"])
    events = service.stream_events(run["id"], limit=100)

    assert run["status"] == "failed"
    assert "max_fires_per_run" in run["error_message"]
    assert not any(event["event_type"] == "control_triggered" for event in events)


@pytest.mark.parametrize("limit", [True, "12"])
def test_workflow_run_rejects_invalid_persisted_evidence_query_limit(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    limit: object,
) -> None:
    service = service_factory(scenario="success")
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "inputs": {"evidence_query": {"archetypes": ["builder"], "limit": 12}},
                "on_pass": "finish_run",
            },
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Corrupted Evidence Query Loop",
        workflow=workflow,
    )
    corrupted_workflow = json.loads(json.dumps(loop["workflow_json"]))
    corrupted_workflow["steps"][1]["inputs"]["evidence_query"]["limit"] = limit
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_definitions SET workflow_json = ? WHERE id = ?",
            (json.dumps(corrupted_workflow, ensure_ascii=False), loop["id"]),
        )

    run = service.rerun(loop["id"])
    events = service.stream_events(run["id"], limit=100)

    assert run["status"] == "failed"
    assert "evidence_query.limit must be an integer" in run["error_message"]
    assert not any(event["event_type"] == "role_execution_summary" and event["payload"].get("archetype") == "gatekeeper" for event in events)


def test_workflow_run_rejects_invalid_persisted_step_action_policy(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
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
        name="Corrupted Step Policy Loop",
        workflow=workflow,
    )
    corrupted_workflow = json.loads(json.dumps(loop["workflow_json"]))
    corrupted_workflow["steps"][1]["action_policy"]["workspace"] = "workspace_write"
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_definitions SET workflow_json = ? WHERE id = ?",
            (json.dumps(corrupted_workflow, ensure_ascii=False), loop["id"]),
        )

    run = service.rerun(loop["id"])
    events = service.stream_events(run["id"], limit=100)

    assert run["status"] == "failed"
    assert "only Builder steps may set action_policy.workspace=workspace_write" in run["error_message"]
    assert not any(event["event_type"] == "role_execution_summary" and event["payload"].get("archetype") == "gatekeeper" for event in events)


def test_step_input_policy_filters_handoffs_and_evidence_context(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    recorded_gate_context: dict = {}

    class InputPolicyExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Built a candidate.",
                    "summary": "Builder completed the candidate.",
                    "changed_files": [],
                }
            elif request.role_archetype == "inspector":
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
                            "id": request.step_id,
                            "title": request.step_id,
                            "status": "passed",
                            "notes": "Filtered evidence path.",
                        }
                    ],
                    "dynamic_checks": [],
                    "tester_observations": f"{request.step_id} evidence.",
                }
            else:
                step_instruction_context = request.extra_context["step_instruction_context"]
                recorded_gate_context.update(step_instruction_context)
                evidence_refs = [item["id"] for item in step_instruction_context["evidence"]["items"]]
                payload = {
                    "passed": True,
                    "decision_summary": "Filtered context was enough.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = InputPolicyExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "ux", "name": "UX Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "contract", "name": "Contract Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "ux_step", "role_id": "ux"},
            {"id": "contract_step", "role_id": "contract"},
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "on_pass": "finish_run",
                "inputs": {
                    "handoffs_from": ["contract_step"],
                    "evidence_query": {"archetypes": ["inspector"], "limit": 1},
                },
            },
        ],
    }
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Filtered Context Loop", workflow=workflow)

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert [item["source"]["step_id"] for item in recorded_gate_context["upstream"]["completed_steps_this_iteration"]] == ["contract_step"]
    assert [item["step_id"] for item in recorded_gate_context["evidence"]["items"]] == ["contract_step"]
    assert recorded_gate_context["evidence"]["known_ids"] == ["ev_000_02_contract_step"]
    assert recorded_gate_context["evidence"]["manifest_summary"]["claim_count"] == 1
    assert [item["id"] for item in recorded_gate_context["evidence"]["manifest_claims"]] == ["ev_000_02_contract_step"]
    assert recorded_gate_context["evidence"]["manifest_claims"][0]["verification_status"] == "run_artifact"


def test_evidence_query_filters_canonical_ledger_before_recent_prompt_window(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    recorded_gate_context: dict = {}
    recorded_gate_prompt = ""

    class CanonicalEvidenceQueryExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            nonlocal recorded_gate_prompt
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
                            "id": "early_inspector_evidence",
                            "title": "Early inspector evidence",
                            "status": "passed",
                            "notes": "The early inspector evidence remains the selected evidence query result.",
                        }
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "Early inspector evidence.",
                    "coverage_results": [],
                }
            elif request.role_archetype == "builder":
                payload = {
                    "attempted": f"Produced filler step {request.step_id}.",
                    "summary": f"Filler step {request.step_id} completed.",
                    "changed_files": [],
                }
            else:
                step_instruction_context = request.extra_context["step_instruction_context"]
                recorded_gate_context.update(step_instruction_context)
                recorded_gate_prompt = request.prompt
                payload = {
                    "passed": False,
                    "decision_summary": "The test only inspects filtered context.",
                    "feedback_to_builder": "No follow-up required for this context projection test.",
                    "blocking_issues": ["context_projection_test"],
                    "metrics": [],
                    "metric_scores": {},
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.0,
                    "evidence_refs": [],
                    "evidence_claims": [],
                    "residual_risks": [],
                    "coverage_results": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = CanonicalEvidenceQueryExecutor
    filler_steps = [{"id": f"filler_builder_{index:02d}", "role_id": "builder"} for index in range(45)]
    workflow = {
        "version": 1,
        "roles": [
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "inspector_step", "role_id": "inspector"},
            *filler_steps,
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "on_pass": "finish_run",
                "inputs": {
                    "handoffs_from": ["inspector_step"],
                    "evidence_query": {"archetypes": ["inspector"], "limit": 1},
                },
            },
        ],
    }
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Canonical Evidence Query Loop", workflow=workflow, max_iters=1)

    service.rerun(loop["id"])

    assert [item["step_id"] for item in recorded_gate_context["evidence"]["items"]] == ["inspector_step"]
    assert recorded_gate_context["evidence"]["known_ids"] == ["ev_000_00_inspector_step"]
    assert recorded_gate_context["evidence"]["manifest_summary"]["claim_count"] == 1
    assert [item["id"] for item in recorded_gate_context["evidence"]["manifest_claims"]] == ["ev_000_00_inspector_step"]
    assert 'Known ids: ["ev_000_00_inspector_step"]' in recorded_gate_prompt
    assert "gatekeeper_support=supporting" in recorded_gate_prompt
    assert "ev_000_01_filler_builder_00" not in recorded_gate_prompt


def test_gatekeeper_validates_older_known_evidence_ref_from_canonical_ledger(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    target_ref = "ev_000_00_inspector_step"

    class OlderEvidenceRefExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            iter_id = int(request.extra_context.get("iter_id") or 0)
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
                            "notes": "The first run already proved the primary experience.",
                        },
                        {
                            "id": "check_002",
                            "title": "Edge path",
                            "status": "passed",
                            "notes": "The first run already proved the edge path.",
                        },
                    ],
                    "dynamic_checks": [],
                    "tester_observations": f"Inspector evidence for iteration {iter_id}.",
                    "coverage_results": [],
                }
            else:
                passed = iter_id >= 21
                payload = {
                    "passed": passed,
                    "decision_summary": "Older inspector evidence remains valid." if passed else "Keep accumulating iterations.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0 if passed else 0.4, "threshold": 0.9, "passed": passed},
                    ],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0 if passed else 0.4,
                    "evidence_refs": [target_ref] if passed else [],
                    "evidence_claims": ["The older inspector evidence id was cited after it fell out of the prompt item summary."] if passed else [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = OlderEvidenceRefExecutor
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
        name="Older Evidence Ref Loop",
        max_iters=22,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]
    final_context = json.loads((run_dir / "iterations" / "iter_021" / "steps" / "01__gatekeeper_step" / "step_instruction_context.json").read_text(encoding="utf-8"))

    assert target_ref in final_context["evidence"]["known_ids"]
    assert target_ref not in {item["id"] for item in final_context["evidence"]["items"]}
    assert run["status"] == "succeeded"
    assert gatekeeper_output["passed"] is True
    assert gatekeeper_output["evidence_gate_status"] == "passed"
    assert gatekeeper_output["evidence_refs"] == [target_ref]


