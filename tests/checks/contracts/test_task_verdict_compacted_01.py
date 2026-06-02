from __future__ import annotations

# Merged from test_task_verdict_accepted_residual_risk.py
from pathlib import Path

from task_verdict_test_support import (
    build_passed_task_verdict,
    gatekeeper_residual_risk,
    write_task_verdict_covered_gatekeeper_coverage as _write_covered_coverage,
)


def test_task_verdict_distinguishes_gatekeeper_pass_with_residual_risk(tmp_path: Path) -> None:
    risk = "Manual billing export remains a visible follow-up."
    run_dir = tmp_path / "run_residual_risk"
    _write_covered_coverage(
        run_dir,
        summary_reason="GateKeeper accepted the named residual risk.",
        risk_signals=[
            "Earlier GateKeeper blocker was resolved by the next Builder pass.",
            risk,
        ],
        latest_gatekeeper=gatekeeper_residual_risk(risk),
    )

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper passed with a named follow-up risk.",
    )

    assert task_verdict["status"] == "passed_with_residual_risk"
    assert task_verdict["source"] == "gatekeeper"
    assert task_verdict["summary"] == "GateKeeper passed with a named follow-up risk."
    assert [item["label"] for item in task_verdict["buckets"]["residual_risk"]] == [risk]


def test_task_verdict_projects_raw_gatekeeper_residual_risks_into_bucket(tmp_path: Path) -> None:
    risk = "Manual copy polish remains visible as a follow-up."
    run_dir = tmp_path / "run_raw_residual_risk"
    _write_covered_coverage(run_dir)

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper accepted a visible follow-up risk.",
        residual_risks=[risk],
    )

    assert task_verdict["status"] == "passed_with_residual_risk"
    assert [item["label"] for item in task_verdict["buckets"]["residual_risk"]] == [risk]

# Merged from test_task_verdict_fallback_status.py
from loopora.task_verdicts import build_task_verdict


def test_task_verdict_falls_back_to_raw_evidence_when_no_projection_exists() -> None:
    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "evidence_claims": ["The benchmark and regression suite both passed."],
                "evidence_refs": ["ev_001", "ev_001"],
            },
        },
        legacy=True,
    )

    assert task_verdict["status"] == "passed"
    assert task_verdict["source"] == "legacy"
    assert [item["label"] for item in task_verdict["buckets"]["proven"]] == [
        "The benchmark and regression suite both passed.",
        "ev_001",
    ]


def test_task_verdict_does_not_pass_nonlegacy_gatekeeper_without_coverage_projection() -> None:
    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "Raw GateKeeper passed, but coverage projection is unavailable.",
                "evidence_refs": ["ev_001"],
            },
        }
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["source"] == "gatekeeper"


def test_task_verdict_does_not_reuse_summary_from_malformed_gatekeeper_pass() -> None:
    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": "true",
                "decision_summary": "GateKeeper says this passed from a string-shaped verdict.",
            },
        }
    )

    assert task_verdict["status"] == "not_evaluated"
    assert task_verdict["source"] == "run_status"
    assert task_verdict["summary"] == "The run is succeeded, and no evidence-based task verdict is available."

# Merged from test_task_verdict_normalization.py
from loopora.task_verdicts import normalize_task_verdict


def test_normalize_task_verdict_drops_non_string_bucket_items() -> None:
    task_verdict = normalize_task_verdict(
        {
            "status": "failed",
            "source": "gatekeeper",
            "summary": "Stored verdict should keep only stable bucket entries.",
            "buckets": {
                "blocking": [True, 7, "real blocker", {"label": "structured blocker"}],
                "residual_risk": [False],
            },
        }
    )

    assert task_verdict["buckets"]["blocking"] == [
        {"label": "real blocker"},
        {"label": "structured blocker"},
    ]
    assert task_verdict["buckets"]["residual_risk"] == []

# Merged from test_task_verdict_raw_verdict_sanitization.py


from task_verdict_test_support import write_task_verdict_coverage as _write_coverage


def test_task_verdict_drops_non_string_raw_verdict_list_items(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_non_string_raw_verdict_items"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {"id": "done_when.check_001", "label": "Required proof", "status": "covered", "required": True},
                {"id": "gatekeeper.finish", "label": "GateKeeper finish", "status": "covered", "required": True},
            ],
            "risk_signals": [],
        },
    )

    passed_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "residual_risks": [True, 7],
            },
        },
        run_dir=run_dir,
    )
    failed_verdict = build_task_verdict(
        {
            "status": "failed",
            "last_verdict_json": {
                "passed": False,
                "blocking_issues": [True, "real_blocker"],
                "hard_constraint_violations": [7],
                "failed_check_ids": [False],
            },
        },
        run_dir=run_dir,
    )

    assert passed_verdict["status"] == "passed"
    assert passed_verdict["buckets"]["residual_risk"] == []
    assert [item["label"] for item in failed_verdict["buckets"]["blocking"]] == ["real_blocker"]

# Merged from test_task_verdict_required_coverage_status.py

from task_verdict_test_support import (
    gatekeeper_finish_target,
    gatekeeper_pass_evidence,
    required_proof_target,
    write_task_verdict_coverage,
)


def test_task_verdict_does_not_pass_when_required_coverage_is_missing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_missing_required_coverage"
    write_task_verdict_coverage(
        run_dir,
        {
            "summary": {"reason": "Required coverage targets still lack direct evidence."},
            "targets": [
                required_proof_target(status="missing"),
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

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["source"] == "gatekeeper"
    assert task_verdict["summary"] == "Required coverage targets still lack direct evidence."
    assert [item["label"] for item in task_verdict["buckets"]["unproven"]] == ["Required proof"]


def test_task_verdict_treats_intrinsic_required_targets_as_required_when_marker_is_malformed(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run_malformed_required_marker"
    write_task_verdict_coverage(
        run_dir,
        {
            "summary": {"reason": "A Done When target is still missing."},
            "targets": [
                required_proof_target(
                    status="missing",
                    kind="done_when",
                    required="true",
                ),
                gatekeeper_finish_target(
                    kind="gatekeeper",
                    required=False,
                ),
            ],
            "risk_signals": [],
        },
    )

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper passed, but a required target marker was malformed.",
        verdict_updates={"evidence_refs": ["ev_inspector"]},
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert [item["label"] for item in task_verdict["buckets"]["unproven"]] == ["Required proof"]
    assert task_verdict["buckets"]["unproven"][0]["required"] is True
