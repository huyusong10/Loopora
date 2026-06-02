from __future__ import annotations

from pathlib import Path

from task_verdict_test_support import (
    build_passed_task_verdict,
    gatekeeper_finish_target,
    gatekeeper_pass_evidence,
    required_proof_target,
    task_verdict_coverage_target,
    write_task_verdict_coverage,
    write_task_verdict_covered_gatekeeper_coverage,
)


def test_task_verdict_fails_when_advisory_fake_done_target_is_blocked_after_gatekeeper_pass(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run_blocked_advisory_fake_done"
    write_task_verdict_coverage(
        run_dir,
        {
            "status": "blocked",
            "summary": {"reason": "GateKeeper or target evidence reported a blocker."},
            "targets": [
                required_proof_target(),
                gatekeeper_finish_target(),
                task_verdict_coverage_target(
                    "fake_done.risk_001",
                    "Fake Done risk",
                    status="blocked",
                    required=False,
                    reason="Inspector found a fake-done shortcut.",
                ),
            ],
        },
    )

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper tried to pass despite a fake-done blocker.",
    )

    assert task_verdict["status"] == "failed"
    assert task_verdict["source"] == "gatekeeper"
    assert task_verdict["summary"] == "GateKeeper or target evidence reported a blocker."
    assert task_verdict["buckets"]["blocking"] == [
        {
            "id": "fake_done.risk_001",
            "label": "Fake Done risk",
            "text": "",
            "reason": "Inspector found a fake-done shortcut.",
            "evidence_refs": [],
            "artifact_refs": [],
            "required": False,
        }
    ]


def test_task_verdict_fails_when_gatekeeper_pass_reports_blocking_issues(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_contradictory_gatekeeper_pass"
    write_task_verdict_covered_gatekeeper_coverage(run_dir)

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper said pass, but also named a blocker.",
        verdict_updates={"blocking_issues": ["permission_path_unproven"]},
    )

    assert task_verdict["status"] == "failed"
    assert task_verdict["source"] == "gatekeeper"
    assert task_verdict["summary"] == "GateKeeper reported blocking issues while also marking the task passed."
    assert task_verdict["buckets"]["blocking"] == [
        {
            "label": "permission_path_unproven",
            "reason": "Reported by the latest raw verdict.",
        }
    ]


def test_task_verdict_fails_when_required_coverage_is_blocked_after_gatekeeper_pass(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_blocked_required_coverage"
    write_task_verdict_coverage(
        run_dir,
        {
            "summary": {"reason": "GateKeeper or target evidence reported a blocker."},
            "targets": [
                required_proof_target(status="blocked"),
                gatekeeper_finish_target(),
            ],
            "risk_signals": [],
            "latest_gatekeeper": gatekeeper_pass_evidence(evidence_refs=["ev_inspector"]),
        },
    )

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper passed from an upstream evidence ref.",
        verdict_updates={"evidence_refs": ["ev_inspector"]},
    )

    assert task_verdict["status"] == "failed"
    assert task_verdict["source"] == "gatekeeper"
    assert [item["label"] for item in task_verdict["buckets"]["blocking"]] == ["Required proof"]


def test_task_verdict_fails_when_gatekeeper_finish_coverage_is_blocked_after_gatekeeper_pass(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run_blocked_gatekeeper_finish"
    write_task_verdict_coverage(
        run_dir,
        {
            "summary": {"reason": "GateKeeper pass cited only non-supporting upstream evidence refs."},
            "targets": [
                required_proof_target(),
                gatekeeper_finish_target(status="blocked"),
            ],
            "risk_signals": [],
            "latest_gatekeeper": gatekeeper_pass_evidence(
                evidence_refs=["ev_blocked"],
                supporting_evidence_refs=[],
                non_supporting_evidence_refs=["ev_blocked"],
            ),
        },
    )

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper tried to pass from a blocked inspection.",
        verdict_updates={"evidence_refs": ["ev_blocked"]},
    )

    assert task_verdict["status"] == "failed"
    assert task_verdict["source"] == "gatekeeper"
    assert [item["label"] for item in task_verdict["buckets"]["blocking"]] == ["GateKeeper finish"]
