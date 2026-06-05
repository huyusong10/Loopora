from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_ignores_explicit_no_residual_risk_markers(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed without accepted residual risk.",
                "verifies": ["evidence:ev_supporting"],
                "residual_risk": "None",
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert projection["status"] == "covered"
    assert projection["residual_risk_count"] == 0
    assert projection["risk_signals"] == []
    assert projection["latest_gatekeeper"]["residual_risk"] == "None"


def test_coverage_ignores_chinese_no_meaningful_residual_risk_marker(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed without meaningful residual risk.",
                "verifies": ["evidence:ev_supporting"],
                "residual_risk": "无重大残余风险",
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert projection["status"] == "covered"
    assert projection["residual_risk_count"] == 0
    assert projection["risk_signals"] == []
    assert projection["latest_gatekeeper"]["residual_risk"] == "无重大残余风险"


def test_coverage_keeps_residual_risk_exception_after_no_risk_phrase(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper named a managed exception.",
                "verifies": ["evidence:ev_supporting"],
                "residual_risk": "No residual risk except mobile checkout remains a Support-owned follow-up.",
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert projection["status"] == "covered"
    assert projection["residual_risk_count"] == 1
    assert projection["risk_signals"] == [
        "No residual risk except mobile checkout remains a Support-owned follow-up."
    ]
    assert projection["latest_gatekeeper"]["residual_risk"] == (
        "No residual risk except mobile checkout remains a Support-owned follow-up."
    )


def test_coverage_keeps_full_gatekeeper_residual_risk_for_semantic_verdict_input(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    risk = (
        "The entitlement matrix has one accepted residual risk after the required proof is covered: "
        + "the SaaS catalog can add a new plan tier before the next release without this probe knowing about it. " * 3
        + "Owner: Product Operations. Follow-up: add the tier to entitlement_matrix_probe.py during catalog rollout. "
        + "Acceptance path: release checklist review must confirm no new tier exists before closure."
    )
    assert len(risk) > 240
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed with managed residual risk.",
                "verifies": ["evidence:ev_supporting"],
                "residual_risk": risk,
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert projection["status"] == "covered"
    assert projection["residual_risk_count"] == 1
    assert projection["risk_signals"] == [risk]
    assert projection["latest_gatekeeper"]["residual_risk"] == risk
