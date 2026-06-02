from __future__ import annotations

from pathlib import Path

from loopora.bundles import lint_alignment_bundle_semantics
from bundle_semantic_lint_workflow_support import load_default_alignment_bundle, make_contract_inspector_custom_review


def test_alignment_semantic_lint_treats_custom_as_review_before_gatekeeper(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    make_contract_inspector_custom_review(bundle)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] = ["evidence_inspection_step"]
    steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"] = ["builder", "inspector"]

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("finishing GateKeeper after review must include review handoffs in inputs.handoffs_from: contract_inspection_step") in issues
    assert ("finishing GateKeeper after review must query review evidence in inputs.evidence_query: custom") in issues


def test_alignment_semantic_lint_requires_finishing_gatekeeper_to_read_handoff_and_evidence(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    assert not any("finishing GateKeeper step" in issue for issue in lint_alignment_bundle_semantics(bundle))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"].pop("inputs")
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("finishing GateKeeper step must name upstream handoffs in inputs.handoffs_from: gatekeeper_step") in issues
    assert ("finishing GateKeeper step must query upstream evidence in inputs.evidence_query: gatekeeper_step") in issues


def test_alignment_semantic_lint_requires_gatekeeper_after_review_to_read_review_evidence(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    assert not any("GateKeeper after review" in issue for issue in lint_alignment_bundle_semantics(bundle))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] = ["builder_step"]
    steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"] = ["builder"]

    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "finishing GateKeeper after review must include review handoffs in inputs.handoffs_from: contract_inspection_step, evidence_inspection_step"
    ) in issues
    assert ("finishing GateKeeper after review must query review evidence in inputs.evidence_query: inspector") in issues
