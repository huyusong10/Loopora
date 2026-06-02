from __future__ import annotations

from pathlib import Path

from runner_helpers import _create_loop, _read_jsonl


ROUND_COMPLETION_ITERATION_COUNT = 2


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
        max_iters=ROUND_COMPLETION_ITERATION_COUNT,
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert run["run_status"] == "succeeded"
    assert run["task_verdict"]["status"] == "insufficient_evidence"
    assert run["task_verdict"]["source"] == "rounds_completion"
    iteration_log = _read_jsonl(Path(run["runs_dir"]) / "iteration_log.jsonl")
    assert len([entry for entry in iteration_log if entry["phase"] == "complete"]) == ROUND_COMPLETION_ITERATION_COUNT
    events = service.stream_events(run["id"], limit=200)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"].get("reason") == "rounds_completed"
        and event["payload"]["task_verdict_status"] == "insufficient_evidence"
        and event["payload"]["task_verdict_source"] == "rounds_completion"
        and event["payload"]["task_verdict_summary"] == run["task_verdict"]["summary"]
        for event in events
    )
