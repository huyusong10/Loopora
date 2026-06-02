from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop, _read_jsonl, _step_outputs_by_archetype


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
