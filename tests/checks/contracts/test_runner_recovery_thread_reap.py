from __future__ import annotations

import threading
from pathlib import Path

from loopora.engine import RepositoryRunEngine, RunEngineIssueVerdictRequest, RunEngineRecordStepEvidenceRequest
from loopora.kernel import ActorRef
from loopora.service import LooporaService

from runner_helpers import _create_loop


def test_get_run_reaps_finished_thread_handle(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Reap Thread Loop")
    run = service.start_run(loop["id"])
    _issue_minimal_passing_verdict(service, run["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        finished_at="2026-04-18T11:00:00+00:00",
        summary_md="# done",
    )

    completed = threading.Thread(target=lambda: None, name="completed-run-thread")
    completed.start()
    completed.join()
    service._threads[run["id"]] = completed

    finished = service.get_run(run["id"])

    assert finished["status"] == "succeeded"
    assert run["id"] not in service._threads


def _issue_minimal_passing_verdict(service: LooporaService, run_id: str) -> None:
    engine = RepositoryRunEngine(service.repository)
    actor = ActorRef.verdict_engine()
    engine.record_step_evidence(
        RunEngineRecordStepEvidenceRequest(
            run_id=run_id,
            actor=actor,
            evidence_entry={
                "id": "ev_thread_reap_fixture",
                "step_id": "fixture",
                "role_id": "fixture",
                "claim": "The run completed before the thread handle was reaped.",
                "result": "passed",
                "verifies": ["target:done_when.thread_reaped:covered"],
            },
            coverage_projection={"status": "covered", "target_count": 1, "covered_target_count": 1},
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run_id,
            actor=actor,
            verdict={"status": "passed", "source": "gatekeeper", "summary": "Thread reap fixture completed."},
        )
    )
