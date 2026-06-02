from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RepositoryRunEngine, RunEngineRecordStepEvidenceRequest
from loopora.events import run_stream_id

from run_engine_evidence_event_test_support import (
    covered_projection,
    create_run_engine_evidence_run,
    headless_runner_actor,
)


def test_run_engine_records_step_evidence_and_coverage_as_one_command(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_run_engine_evidence_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)

    result = engine.record_step_evidence(
        RunEngineRecordStepEvidenceRequest(
            run_id=run["id"],
            actor=headless_runner_actor(),
            correlation_id="corr-step-evidence",
            evidence_entry={
                "id": "ev_step_001",
                "step_id": "builder",
                "role_id": "builder",
                "archetype": "builder",
                "claim": "Step proof exists.",
                "method": "pytest",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
                "artifact_refs": [
                    {
                        "kind": "workspace",
                        "label": "proof",
                        "uri": "proof.txt",
                        "content_hash": "sha256:def",
                    }
                ],
            },
            coverage_projection=covered_projection(),
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    cached_ledger = repository.get_projection_record("evidence_ledger", run["id"])
    cached_coverage = repository.get_projection_record("coverage", run["id"])
    artifacts = repository.list_artifact_index(run_id=run["id"])

    assert [event.event_type for event in events[-4:]] == [
        "EvidenceSubmitted",
        "EvidenceAccepted",
        "EvidenceLinkedToTarget",
        "CoverageRecomputed",
    ]
    assert result.submitted_event is not None
    assert result.submitted_event.event_id == events[-4].event_id
    assert result.evidence_event.event_id == events[-3].event_id
    assert result.linked_event is not None
    assert result.linked_event.event_id == events[-2].event_id
    assert result.coverage_event.event_id == events[-1].event_id
    assert events[-4].correlation_id == "corr-step-evidence"
    assert events[-3].correlation_id == "corr-step-evidence"
    assert events[-2].correlation_id == "corr-step-evidence"
    assert events[-1].correlation_id == "corr-step-evidence"
    assert events[-3].causation_id == events[-4].event_id
    assert events[-2].causation_id == events[-3].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert events[-2].payload["target_refs"] == ["target:done_when.proof:covered"]
    assert events[-3].payload["artifact_refs"] == [
        {"kind": "workspace", "label": "proof", "uri": "proof.txt", "content_hash": "sha256:def"}
    ]
    assert cached_ledger["payload"]["entries"][0]["evidence_id"] == "ev_step_001"
    assert cached_ledger["payload"]["entries"][0]["artifact_refs"] == events[-3].payload["artifact_refs"]
    assert cached_coverage["payload"]["status"] == "covered"
    assert cached_coverage["payload"]["source_sequence"] == events[-1].sequence
    assert artifacts[0]["uri"] == "proof.txt"
    assert artifacts[0]["created_by_event_id"] == result.evidence_event.event_id
