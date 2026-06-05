from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.context_step_results import StepEvidenceEntryRequest, StepResultContext, build_step_evidence_entry
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_blocks_gatekeeper_finish_when_pass_cites_only_non_supporting_evidence(tmp_path: Path) -> None:
    projection, targets = coverage_projection(
        tmp_path,
        evidence_entry("ev_blocked", archetype="inspector", result="blocked", claim="The requested proof is blocked."),
        gatekeeper_pass("GateKeeper tried to pass from the blocked inspection.", "ev_blocked"),
    )

    assert projection["status"] == "blocked"
    assert targets["gatekeeper.finish"]["status"] == "blocked"
    assert targets["gatekeeper.finish"]["reason"] == "GateKeeper pass cited only non-supporting upstream evidence refs."
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_blocked", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_blocked"]


def test_coverage_blocks_gatekeeper_finish_when_pass_cites_plain_builder_handoff(tmp_path: Path) -> None:
    projection, targets = coverage_projection(
        tmp_path,
        evidence_entry(
            "ev_builder",
            archetype="builder",
            evidence_kind="handoff",
            result="completed",
            claim="Builder says the required proof is complete.",
            verifies=["target:done_when.check_001:covered"],
            artifact_refs=[],
        ),
        gatekeeper_pass("GateKeeper tried to pass from a Builder handoff without proof.", "ev_builder"),
    )

    assert projection["status"] == "blocked"
    assert targets["done_when.check_001"]["status"] == "weak"
    assert targets["done_when.check_001"]["reason"] == "Coverage was reported as positive without supporting evidence."
    assert targets["gatekeeper.finish"]["status"] == "blocked"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_builder", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_builder"]


def test_coverage_blocks_gatekeeper_finish_when_pass_cites_plain_inspector_observation(tmp_path: Path) -> None:
    projection, targets = coverage_projection(
        tmp_path,
        evidence_entry(
            "ev_inspector",
            archetype="inspector",
            result="passed",
            claim="Inspector says the required proof is complete, but left no structured check or artifact.",
            verifies=[],
            artifact_refs=[],
        ),
        gatekeeper_pass("GateKeeper tried to pass from a plain inspector observation.", "ev_inspector"),
    )

    assert projection["status"] == "blocked"
    assert targets["gatekeeper.finish"]["status"] == "blocked"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_inspector", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_inspector"]


def test_coverage_accepts_gatekeeper_finish_when_pass_has_supporting_ref(tmp_path: Path) -> None:
    projection, targets = coverage_projection(
        tmp_path,
        evidence_entry(
            "ev_supporting",
            archetype="inspector",
            result="passed",
            claim="The required proof is covered.",
            verifies=["target:done_when.check_001:covered"],
        ),
        evidence_entry("ev_blocked", archetype="inspector", result="blocked", claim="An earlier inspection found a stale blocker."),
        gatekeeper_pass(
            "GateKeeper passed from the supporting inspection while preserving the stale blocker ref.",
            "ev_blocked",
            "ev_supporting",
        ),
    )

    assert projection["status"] == "covered"
    assert targets["gatekeeper.finish"]["status"] == "covered"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_supporting", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == ["ev_supporting"]
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_blocked"]


def test_check_result_verify_refs_cover_stable_done_when_targets(tmp_path: Path) -> None:
    projection, targets = coverage_projection(
        tmp_path,
        evidence_entry(
            "ev_check",
            archetype="inspector",
            result="passed",
            claim="The stable check passed.",
            verifies=["check_results:check_001:passed"],
        ),
    )

    assert projection["check_count"] == 1
    assert targets["done_when.check_001"]["status"] == "covered"
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_check"]


def test_dynamic_check_verify_refs_do_not_create_done_when_targets(tmp_path: Path) -> None:
    projection, targets = coverage_projection(
        tmp_path,
        evidence_entry(
            "ev_dynamic",
            archetype="inspector",
            result="passed",
            claim="An ad hoc dynamic check passed.",
            verifies=["dynamic_checks:dyn_measured_rerun:passed"],
        ),
    )

    assert projection["check_count"] == 1
    assert "done_when.dyn_measured_rerun" not in targets
    assert targets["done_when.check_001"]["status"] == "missing"


def test_generated_gatekeeper_entry_keeps_supporting_refs_when_coverage_rows_hit_verify_limit(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    gatekeeper_entry = build_step_evidence_entry(
        StepEvidenceEntryRequest(
            result=StepResultContext(
                layout=layout,
                iter_id=0,
                step={"id": "gatekeeper_step"},
                step_order=1,
                role={"id": "gatekeeper", "name": "Task GateKeeper", "archetype": "gatekeeper"},
                runtime_role="verifier",
                output={
                    "passed": True,
                    "decision_summary": "GateKeeper passed from Inspector's supporting evidence.",
                    "composite_score": 1.0,
                    "metrics": [],
                    "metric_scores": {
                        "check_pass_rate": {"value": 1.0, "threshold": 1.0, "passed": True},
                        "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
                    },
                    "blocking_issues": [],
                    "hard_constraint_violations": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "feedback_to_builder": "",
                    "feedback_to_generator": "",
                    "evidence_refs": ["ev_supporting"],
                    "evidence_claims": ["The supporting inspection covered the required proof."],
                    "residual_risks": [],
                    "coverage_results": _many_gatekeeper_coverage_results(),
                },
            ),
            handoff={"status": "passed", "summary": "GateKeeper passed."},
        )
    )
    _write_ledger(
        layout.evidence_ledger_path,
        [
            evidence_entry(
                "ev_supporting",
                archetype="inspector",
                result="passed",
                claim="The required proof is covered.",
                verifies=["target:done_when.check_001:covered"],
            ),
            gatekeeper_entry,
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert "evidence:ev_supporting" in gatekeeper_entry["verifies"]
    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "covered"
    assert targets["gatekeeper.finish"]["status"] == "covered"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_supporting", "ev_000_01_gatekeeper_step"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == ["ev_supporting"]


def test_coverage_recovers_gatekeeper_finish_from_legacy_related_refs_when_verify_limit_dropped_evidence_refs(
    tmp_path: Path,
) -> None:
    projection, targets = coverage_projection(
        tmp_path,
        evidence_entry(
            "ev_supporting",
            archetype="inspector",
            result="passed",
            claim="The required proof is covered.",
            verifies=["target:done_when.check_001:covered"],
        ),
        evidence_entry(
            "ev_gatekeeper",
            archetype="gatekeeper",
            evidence_kind="verdict",
            result="passed",
            claim="GateKeeper passed, but an older projection clipped evidence refs out of verifies.",
            verifies=[f"target:advisory.target_{idx:03d}:covered" for idx in range(20)],
            related_evidence_ids=["ev_supporting"],
        ),
    )

    assert projection["status"] == "covered"
    assert targets["gatekeeper.finish"]["status"] == "covered"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_supporting", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == ["ev_supporting"]


def coverage_projection(tmp_path: Path, *entries: dict) -> tuple[dict, dict]:
    layout = _coverage_layout(tmp_path)
    _write_ledger(layout.evidence_ledger_path, list(entries))
    projection = build_evidence_coverage_projection(layout)
    return projection, {target["id"]: target for target in projection["targets"]}


def evidence_entry(
    evidence_id: str,
    *,
    archetype: str,
    result: str,
    claim: str,
    evidence_kind: str = "inspection",
    **overrides: object,
) -> dict:
    entry = {"id": evidence_id, "archetype": archetype, "evidence_kind": evidence_kind, "result": result, "claim": claim}
    entry.update(overrides)
    return entry


def gatekeeper_pass(claim: str, *evidence_refs: str) -> dict:
    return evidence_entry(
        "ev_gatekeeper",
        archetype="gatekeeper",
        evidence_kind="verdict",
        result="passed",
        claim=claim,
        verifies=[f"evidence:{evidence_ref}" for evidence_ref in evidence_refs],
    )


def _many_gatekeeper_coverage_results() -> list[dict]:
    rows = [
        {
            "target_id": "done_when.check_001",
            "status": "covered",
            "evidence_refs": ["ev_supporting"],
            "note": "The required proof is covered.",
        }
    ]
    rows.extend(
        {
            "target_id": f"advisory.target_{idx:03d}",
            "status": "covered",
            "evidence_refs": ["ev_supporting"],
            "note": "Additional advisory coverage row.",
        }
        for idx in range(19)
    )
    return rows
