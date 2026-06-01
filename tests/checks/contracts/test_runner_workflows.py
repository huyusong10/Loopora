from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import (
    _create_loop,
    _read_jsonl,
    _step_outputs_by_archetype,
)


def test_inspect_first_workflow_runs_inspector_before_builder(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Inspect First Loop",
        workflow={"preset": "inspect_first"},
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded" and run["strategy_source"] == run["workflow_json"]
    assert run["workflow_json"]["preset"] == "inspect_first"
    iteration_log = [json.loads(line) for line in (Path(run["runs_dir"]) / "iteration_log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    workflow_entry = next(entry for entry in iteration_log if entry["phase"] == "complete")
    assert [step["archetype"] for step in workflow_entry["strategy_steps"][:3]] == ["inspector", "builder", "gatekeeper"]


def test_workflow_role_events_include_step_metadata(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Repair Loop Metadata",
        workflow={"preset": "repair_loop"},
    )

    run = service.rerun(loop["id"])

    events = service.repository.list_events(run["id"], after_id=0, limit=5000)
    builder_starts = [
        event
        for event in events
        if event["event_type"] == "role_started"
        and event.get("role") == "generator"
        and event["payload"].get("step_id") in {"builder_step", "builder_repair_step"}
    ]
    assert {event["payload"]["step_id"] for event in builder_starts} == {"builder_step", "builder_repair_step"}
    assert {event["payload"]["step_order"] for event in builder_starts} == {0, 4}

    repair_summary = next(
        event
        for event in events
        if event["event_type"] == "role_execution_summary" and event.get("role") == "generator" and event["payload"].get("step_id") == "builder_repair_step"
    )
    assert repair_summary["payload"]["role_name"] == "Builder"
    assert repair_summary["payload"]["archetype"] == "builder"


def test_benchmark_loop_can_finish_before_builder_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class BenchmarkPassingExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "gatekeeper":
                payload = {
                    "passed": True,
                    "decision_summary": "Benchmark target already satisfied.",
                    "feedback_to_builder": "No code change is required.",
                    "blocking_issues": [],
                    "metrics": [],
                    "metric_scores": {
                        "check_pass_rate": {"value": 1.0, "threshold": 1.0, "passed": True},
                        "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
                    },
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": [],
                    "evidence_claims": ["The benchmark fixture is already satisfied by the existing project-owned proof output."],
                }
                request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return payload
            raise AssertionError("Builder should not run when benchmark loop already passes.")

    service = service_factory(scenario="success")
    service.executor_factory = BenchmarkPassingExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Benchmark Loop",
        workflow={"preset": "benchmark_loop"},
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    step_outputs = _step_outputs_by_archetype(run_dir)
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    targets = {target["id"]: target for target in coverage["targets"]}
    gatekeeper_entry = next(item for item in ledger if item["archetype"] == "gatekeeper")

    assert run["status"] == "succeeded"
    assert "builder" not in step_outputs
    assert step_outputs["gatekeeper"][-1]["output"]["passed"] is True
    assert gatekeeper_entry["measured_evidence"] is True
    assert gatekeeper_entry["concrete_evidence_claim_count"] == 1
    assert coverage["latest_gatekeeper"]["self_measured_evidence"] is True
    assert targets["gatekeeper.finish"]["status"] == "covered"


def test_workflow_step_can_resume_its_own_previous_session_and_append_extra_cli_args(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    recorded_requests: list[dict] = []

    class SessionAwareExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            recorded_requests.append(
                {
                    "step_id": request.step_id,
                    "iter": request.extra_context.get("iter_id"),
                    "inherit_session": request.inherit_session,
                    "resume_session_id": request.resume_session_id,
                    "extra_cli_args_text": request.extra_cli_args_text,
                    "role_archetype": request.role_archetype,
                }
            )
            if request.role_archetype == "builder":
                request.extra_context["session_ref"] = {
                    "session_id": f"builder-session-{request.extra_context.get('iter_id')}",
                }
                payload = {
                    "attempted": "Made a targeted implementation change.",
                    "summary": "Builder progressed the workspace.",
                    "changed_files": [],
                }
            else:
                payload = {
                    "passed": False,
                    "decision_summary": "Keep iterating for the contract test.",
                    "feedback_to_builder": "Continue the workflow.",
                    "blocking_issues": [],
                    "metrics": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.4,
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = SessionAwareExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Session Carry Loop",
        completion_mode="rounds",
        max_iters=2,
        workflow={
            "version": 1,
            "preset": "",
            "roles": [
                {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            "steps": [
                {
                    "id": "builder_step",
                    "role_id": "builder",
                    "inherit_session": True,
                    "extra_cli_args": "--verbose",
                },
                {
                    "id": "gatekeeper_step",
                    "role_id": "gatekeeper",
                    "on_pass": "continue",
                    "inherit_session": False,
                },
            ],
        },
    )

    run = service.rerun(loop["id"])
    role_requests = _read_jsonl(Path(run["runs_dir"]) / "context" / "role_requests.jsonl")

    assert run["status"] == "succeeded"
    builder_calls = [item for item in recorded_requests if item["step_id"] == "builder_step"]
    gatekeeper_calls = [item for item in recorded_requests if item["step_id"] == "gatekeeper_step"]
    assert [item["resume_session_id"] for item in builder_calls] == ["", "builder-session-0"]
    assert all(item["inherit_session"] is True for item in builder_calls)
    assert all(item["extra_cli_args_text"] == "--verbose" for item in builder_calls)
    assert all(item["inherit_session"] is False for item in gatekeeper_calls)
    assert all(item["resume_session_id"] == "" for item in gatekeeper_calls)

    second_builder_request = next(item for item in role_requests if item["step_id"] == "builder_step" and item["iter"] == 1)
    assert second_builder_request["inherit_session"] is True
    assert second_builder_request["resume_session_id"] == "builder-session-0"
    assert second_builder_request["extra_cli_args_text"] == "--verbose"


def test_parallel_inspection_group_fans_out_then_gatekeeper_sees_all_evidence(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class ParallelInspectionExecutor(CodexExecutor):
        def __init__(self) -> None:
            self.barrier = threading.Barrier(2)
            self.timings: dict[str, dict[str, float]] = {}
            self.lock = threading.Lock()

        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Prepared the first working slice.",
                    "summary": "Builder produced a concrete candidate for inspection.",
                    "changed_files": [],
                }
            elif request.role_archetype == "inspector":
                with self.lock:
                    self.timings[request.step_id] = {"start": time.perf_counter()}
                self.barrier.wait(timeout=2)
                time.sleep(0.1)
                with self.lock:
                    self.timings[request.step_id]["end"] = time.perf_counter()
                payload = {
                    "execution_summary": {
                        "total_checks": 1,
                        "passed": 1,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 100,
                    },
                    "check_results": [
                        {
                            "id": request.step_id,
                            "title": f"{request.step_id} evidence",
                            "status": "passed",
                            "notes": "Parallel inspector collected direct evidence.",
                        }
                    ],
                    "dynamic_checks": [],
                    "tester_observations": f"{request.step_id} completed its independent inspection.",
                }
            else:
                step_instruction_context = request.extra_context["step_instruction_context"]
                evidence_refs = [
                    item["id"]
                    for item in step_instruction_context["evidence"]["items"]
                    if item.get("archetype") == "inspector"
                ]
                payload = {
                    "passed": True,
                    "decision_summary": "Both inspection branches passed.",
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

    executor = ParallelInspectionExecutor()
    service = service_factory(scenario="success")
    service.executor_factory = lambda: executor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "accessibility", "name": "Accessibility Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "contract", "name": "Contract Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "accessibility_step", "role_id": "accessibility", "parallel_group": "inspection_pack"},
            {"id": "contract_step", "role_id": "contract", "parallel_group": "inspection_pack"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Parallel Inspection Loop", workflow=workflow)

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    evidence_ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "succeeded"
    assert max(item["start"] for item in executor.timings.values()) < min(item["end"] for item in executor.timings.values())
    assert {entry["step_id"] for entry in evidence_ledger if entry["archetype"] == "inspector"} == {
        "accessibility_step",
        "contract_step",
    }
    assert set(gatekeeper_output["evidence_refs"]) >= {
        "ev_000_01_accessibility_step",
        "ev_000_02_contract_step",
    }
    events = service.stream_events(run["id"], limit=500)
    assert any(event["event_type"] == "parallel_group_started" for event in events)
    assert any(event["event_type"] == "parallel_group_finished" for event in events)


def test_triage_first_workflow_runs_inspector_then_guide_then_builder(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Triage First Loop",
        workflow={"preset": "triage_first"},
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert run["workflow_json"]["preset"] == "triage_first"
    assert [step["role_id"] for step in run["workflow_json"]["steps"][:4]] == ["inspector", "guide", "builder", "gatekeeper"]
    iteration_log = [json.loads(line) for line in (Path(run["runs_dir"]) / "iteration_log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    workflow_entry = next(entry for entry in iteration_log if entry["phase"] == "complete")
    assert [step["archetype"] for step in workflow_entry["strategy_steps"][:4]] == [
        "inspector",
        "guide",
        "builder",
        "gatekeeper",
    ]


def test_fast_lane_workflow_runs_builder_before_gatekeeper(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Fast Lane Loop",
        workflow={"preset": "fast_lane"},
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert run["workflow_json"]["preset"] == "fast_lane"
    iteration_log = [json.loads(line) for line in (Path(run["runs_dir"]) / "iteration_log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    workflow_entry = next(entry for entry in iteration_log if entry["phase"] == "complete")
    assert [step["archetype"] for step in workflow_entry["strategy_steps"][:2]] == ["builder", "gatekeeper"]


def test_workflow_step_model_override_is_used_for_role_requests(
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
            {"id": "builder_step", "role_id": "builder", "model": "gpt-5.4-mini"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Step Model Loop", workflow=workflow)

    run = service.rerun(loop["id"])

    role_requests = _read_jsonl(Path(run["runs_dir"]) / "context" / "role_requests.jsonl")
    builder_request = next(item for item in role_requests if item.get("step_id") == "builder_step")
    assert builder_request["model"] == "gpt-5.4-mini"


def test_workflow_roles_can_use_distinct_executor_snapshots(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    workflow = {
        "version": 1,
        "roles": [
            {
                "id": "builder",
                "name": "Builder",
                "archetype": "builder",
                "prompt_ref": "builder.md",
                "executor_kind": "codex",
                "executor_mode": "preset",
                "model": "gpt-5.4-mini",
                "reasoning_effort": "high",
            },
            {
                "id": "custom_helper",
                "name": "Custom Helper",
                "archetype": "custom",
                "prompt_ref": "custom.md",
                "executor_kind": "claude",
                "executor_mode": "preset",
                "model": "",
                "reasoning_effort": "high",
            },
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "custom_step", "role_id": "custom_helper"},
        ],
    }

    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Per Role Executor Loop",
        workflow=workflow,
        completion_mode="rounds",
        max_iters=1,
    )
    run = service.rerun(loop["id"])

    role_requests = _read_jsonl(Path(run["runs_dir"]) / "context" / "role_requests.jsonl")
    builder_request = next(item for item in role_requests if item.get("step_id") == "builder_step")
    custom_request = next(item for item in role_requests if item.get("step_id") == "custom_step")

    assert builder_request["executor_kind"] == "codex"
    assert builder_request["model"] == "gpt-5.4-mini"
    assert custom_request["executor_kind"] == "claude"
    assert custom_request["role_archetype"] == "custom"


def test_custom_role_outputs_platform_takeaway_fields(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    class CustomTakeawayExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "custom":
                payload = {
                    "status": "blocked",
                    "summary": "Custom Helper found one unresolved integration assumption.",
                    "blocking_items": ["The landing copy claims analytics-backed evidence without a matching source file."],
                    "recommended_next_action": "Either add the missing evidence source or tone down the claim before GateKeeper runs.",
                    "observations": [
                        "The current draft reads as if telemetry already exists.",
                    ],
                    "recommendations": [
                        "Tighten the claim to match the current workspace evidence.",
                    ],
                    "risks": [
                        "GateKeeper may reject unsupported claims.",
                    ],
                    "handoff_note": "Pass this to Builder before the next verification step.",
                }
            else:
                payload = {
                    "passed": False,
                    "decision_summary": "The custom helper surfaced a blocker that still needs a fix.",
                    "feedback_to_builder": "Resolve the unsupported claim first.",
                    "blocking_issues": ["unsupported_claim"],
                    "metrics": [],
                    "metric_scores": {},
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.35,
                    "hard_constraint_violations": [],
                    "feedback_to_generator": "Resolve the unsupported claim first.",
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = CustomTakeawayExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "custom_helper", "name": "Custom Helper", "archetype": "custom", "prompt_ref": "custom.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "custom_step", "role_id": "custom_helper"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Custom Takeaway Loop",
        workflow=workflow,
        completion_mode="rounds",
        max_iters=1,
    )

    run = service.rerun(loop["id"])
    custom_handoff = json.loads((Path(run["runs_dir"]) / "iterations" / "iter_000" / "steps" / "00__custom_step" / "handoff.json").read_text(encoding="utf-8"))

    assert custom_handoff["status"] == "blocked"
    assert custom_handoff["summary"] == "Custom Helper found one unresolved integration assumption."
    assert custom_handoff["blocking_items"] == ["The landing copy claims analytics-backed evidence without a matching source file."]
    assert custom_handoff["recommended_next_action"] == ("Either add the missing evidence source or tone down the claim before GateKeeper runs.")


def test_round_completion_mode_can_finish_without_gatekeeper(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Round Loop",
        workflow=workflow,
        completion_mode="rounds",
        max_iters=2,
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert run["run_status"] == "succeeded"
    assert run["task_verdict"]["status"] == "insufficient_evidence"
    assert run["task_verdict"]["source"] == "rounds_completion"
    iteration_log = _read_jsonl(Path(run["runs_dir"]) / "iteration_log.jsonl")
    assert len([entry for entry in iteration_log if entry["phase"] == "complete"]) == 2
    events = service.stream_events(run["id"], limit=200)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"].get("reason") == "rounds_completed"
        and event["payload"]["task_verdict_status"] == "insufficient_evidence"
        and event["payload"]["task_verdict_source"] == "rounds_completion"
        and event["payload"]["task_verdict_summary"] == run["task_verdict"]["summary"]
        for event in events
    )
