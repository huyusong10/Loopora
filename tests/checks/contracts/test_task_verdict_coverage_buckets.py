from __future__ import annotations

from pathlib import Path

from loopora.task_verdicts import build_task_verdict

from task_verdict_test_support import write_task_verdict_coverage as _write_coverage


def test_task_verdict_projects_coverage_targets_into_semantic_buckets(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_coverage"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is still incomplete."},
            "targets": [
                {
                    "id": "done_when.check_001",
                    "label": "Required proof",
                    "status": "covered",
                    "required": True,
                    "artifact_refs": [{"kind": "workspace", "workspace_path": "proof.md"}],
                },
                {"id": "fake_done.risk_001", "label": "Weak screenshot", "status": "weak"},
                {"id": "evidence.pref_001", "label": "Benchmark output", "status": "missing"},
                {"id": "gatekeeper.required_refs", "label": "Gatekeeper refs", "status": "blocked"},
            ],
            "risk_signals": ["Manual review still recommended."],
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "failed",
            "last_verdict_json": {
                "passed": False,
                "blocking_issues": ["missing_contract_evidence"],
            },
        },
        run_dir=run_dir,
    )

    assert task_verdict["status"] == "failed"
    assert task_verdict["source"] == "gatekeeper"
    assert task_verdict["summary"] == "Required evidence is still incomplete."
    buckets = task_verdict["buckets"]
    assert {item["label"] for item in buckets["proven"]} == {"Required proof"}
    assert buckets["proven"][0]["artifact_refs"] == [{"kind": "workspace", "workspace_path": "proof.md"}]
    assert {item["label"] for item in buckets["weak"]} == {"Weak screenshot"}
    assert {item["label"] for item in buckets["unproven"]} == {"Benchmark output"}
    assert {item["label"] for item in buckets["blocking"]} == {"Gatekeeper refs", "missing_contract_evidence"}
    assert {item["label"] for item in buckets["residual_risk"]} == {"Manual review still recommended."}


def test_task_verdict_drops_malformed_coverage_trace_shapes(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_malformed_coverage_trace"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required target is covered."},
            "targets": [
                {
                    "id": "done_when.check_001",
                    "label": "Required proof",
                    "status": "covered",
                    "required": True,
                    "evidence_refs": "ev_001",
                    "artifact_refs": {"kind": "workspace", "workspace_path": "proof.md"},
                }
            ],
            "risk_signals": "Manual review still recommended.",
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {"passed": True},
        },
        run_dir=run_dir,
    )

    buckets = task_verdict["buckets"]
    assert task_verdict["status"] == "passed"
    assert buckets["proven"][0]["evidence_refs"] == []
    assert buckets["proven"][0]["artifact_refs"] == []
    assert buckets["residual_risk"] == []
