from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
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
