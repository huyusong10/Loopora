from __future__ import annotations

from pathlib import Path

from loopora.run_takeaways import build_minimal_run_takeaway_projection


MINIMAL_TAKEAWAY_SOURCE_EVENT_ID = 42


def test_minimal_run_takeaway_projection_keeps_status_verdict_and_empty_evidence_shape(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    runs_dir = workdir / ".loopora" / "runs" / "run_minimal"
    task_verdict = {
        "status": "insufficient_evidence",
        "source": "rounds_completion",
        "summary": "Evidence did not cross the bar.",
        "buckets": {
            "proven": [],
            "weak": [],
            "unproven": [{"label": "manual review"}],
            "blocking": [],
            "residual_risk": [],
        },
    }

    projection = build_minimal_run_takeaway_projection(
        {
            "id": "run_minimal",
            "status": "succeeded",
            "run_status": "succeeded",
            "task_verdict": task_verdict,
            "workdir": str(workdir),
            "runs_dir": str(runs_dir),
            "summary_md": "# Loopora Run Summary\n\nEvidence did not cross the bar.",
        },
        source_event_id=MINIMAL_TAKEAWAY_SOURCE_EVENT_ID,
    )

    assert projection["run_status"] == "succeeded"
    assert projection["task_verdict"]["status"] == "insufficient_evidence"
    assert projection["task_verdict_path"] == ""
    assert projection["evidence_buckets"]["unproven"] == [{"label": "manual review"}]
    assert projection["build_dir"] == str(workdir.resolve())
    assert projection["log_dir"] == str(runs_dir.resolve())
    assert projection["evidence_coverage"]["status"] == "pending"
    assert projection["evidence_manifest"]["claim_count"] == 0
    assert projection["evidence_manifest"]["manifest_path"] == ""
    assert projection["evidence_count"] == 0
    assert projection["iteration_count"] == 0
    assert projection["source_event_id"] == MINIMAL_TAKEAWAY_SOURCE_EVENT_ID
