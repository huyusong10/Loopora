from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection

EV_BUILDER = "ev_builder"
EV_GATEKEEPER = "ev_gatekeeper"
PROOF_REF_PATH = "tests/evidence/proof.json"


def test_coverage_accepts_gatekeeper_finish_when_pass_cites_builder_proof_artifact(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    proof_path = tmp_path / "project" / PROOF_REF_PATH
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text('{"ok": true}\n', encoding="utf-8")
    _write_gatekeeper_proof_ledger(
        layout.evidence_ledger_path,
        builder_claim="Builder left a proof artifact for the required target.",
        gatekeeper_claim="GateKeeper passed from the Builder proof artifact.",
        proof_ref=_proof_ref(proof_path),
    )

    projection = build_evidence_coverage_projection(layout)

    _assert_gatekeeper_finish(projection, status="covered", supporting=[EV_BUILDER], non_supporting=[])


def test_coverage_blocks_gatekeeper_finish_when_builder_proof_artifact_is_missing(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_gatekeeper_proof_ledger(
        layout.evidence_ledger_path,
        builder_claim="Builder cited a proof artifact that no longer exists.",
        gatekeeper_claim="GateKeeper tried to pass from a missing Builder proof artifact.",
        proof_ref=_proof_ref(tmp_path / "project" / PROOF_REF_PATH),
    )

    projection = build_evidence_coverage_projection(layout)

    _assert_gatekeeper_finish(projection, status="blocked", supporting=[], non_supporting=[EV_BUILDER])


def test_coverage_blocks_gatekeeper_finish_when_builder_proof_artifact_lacks_absolute_path(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_gatekeeper_proof_ledger(
        layout.evidence_ledger_path,
        builder_claim="Builder cited a proof artifact without a checkable absolute path.",
        gatekeeper_claim="GateKeeper tried to pass from an unchecked proof artifact ref.",
        proof_ref=_proof_ref(),
    )

    projection = build_evidence_coverage_projection(layout)

    _assert_gatekeeper_finish(projection, status="blocked", supporting=[], non_supporting=[EV_BUILDER])


def _proof_ref(absolute_path: Path | None = None) -> dict:
    ref = {
        "kind": "workspace",
        "label": f"proof-file:{PROOF_REF_PATH}",
        "relative_path": PROOF_REF_PATH,
        "workspace_path": PROOF_REF_PATH,
    }
    if absolute_path is not None:
        ref["absolute_path"] = str(absolute_path)
    return ref


def _write_gatekeeper_proof_ledger(
    ledger_path: Path,
    *,
    builder_claim: str,
    gatekeeper_claim: str,
    proof_ref: dict,
) -> None:
    _write_ledger(
        ledger_path,
        [
            {
                "id": EV_BUILDER,
                "archetype": "builder",
                "evidence_kind": "handoff",
                "result": "completed",
                "claim": builder_claim,
                "verifies": ["target:done_when.check_001:covered"],
                "artifact_refs": [proof_ref],
            },
            {
                "id": EV_GATEKEEPER,
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": gatekeeper_claim,
                "verifies": [f"evidence:{EV_BUILDER}"],
            },
        ],
    )


def _assert_gatekeeper_finish(projection: dict, *, status: str, supporting: list[str], non_supporting: list[str]) -> None:
    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == status
    assert targets["gatekeeper.finish"]["status"] == status
    assert targets["gatekeeper.finish"]["evidence_refs"] == [EV_BUILDER, EV_GATEKEEPER]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == supporting
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == non_supporting
