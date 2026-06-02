from __future__ import annotations

# Merged from test_runner_workflow_control_fire_limits.py
from pathlib import Path

from runner_helpers import (
    _create_loop,
    _read_jsonl,
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

# Merged from test_runner_workflow_event_metadata.py



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
        if event["event_type"] == "role_execution_summary"
        and event.get("role") == "generator"
        and event["payload"].get("step_id") == "builder_repair_step"
    )
    assert repair_summary["payload"]["role_name"] == "Builder"
    assert repair_summary["payload"]["archetype"] == "builder"

# Merged from test_runner_workflow_no_evidence_progress_control.py

from compacted_contract_support import (
    CoverageStallExecutor,
    MISSING_REQUIRED_CHECK_COUNT,
    assert_guide_prompt_mentions_stalled_coverage,
    assert_no_evidence_progress_control_recorded,
    assert_required_coverage_stalled,
    coverage_stall_artifacts,
    coverage_stall_workflow,
)


def test_workflow_control_triggers_when_required_coverage_stalls(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    service.executor_factory = CoverageStallExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Coverage Stall Control Loop",
        workflow=coverage_stall_workflow(),
        max_iters=2,
        trigger_window=1,
    )

    run = service.rerun(loop["id"])
    artifacts = coverage_stall_artifacts(service, run)

    assert run["status"] == "failed"
    assert artifacts["stagnation"]["stagnation_mode"] == "none"
    assert artifacts["stagnation"]["evidence_progress_mode"] == "stalled"
    assert artifacts["stagnation"]["latest_missing_check_count"] == MISSING_REQUIRED_CHECK_COUNT
    assert_required_coverage_stalled(artifacts["latest_iteration_summary"]["stagnation"])
    assert_required_coverage_stalled(artifacts["guide_request"]["context_summary"]["headless_prompt_context"])
    assert_guide_prompt_mentions_stalled_coverage(artifacts["guide_prompt"])
    assert_required_coverage_stalled(artifacts["latest_takeaway"])
    assert artifacts["latest_takeaway"]["consecutive_no_required_coverage_delta"] == 1
    assert_no_evidence_progress_control_recorded(artifacts["events"], artifacts["evidence_ledger"])

# Merged from test_runner_workflow_role_executor_settings.py



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

# Merged from test_runner_workflow_step_model_settings.py



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
