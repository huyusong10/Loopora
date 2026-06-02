from __future__ import annotations

from pathlib import Path

from bundle_semantic_lint_long_chain_support import long_chain_multi_builder_bundle
from loopora.bundles import lint_alignment_bundle_semantics


def test_alignment_semantic_lint_accepts_long_chain_multi_builder_workflows(
    sample_workdir: Path,
) -> None:
    bundle = long_chain_multi_builder_bundle(sample_workdir)

    issues = lint_alignment_bundle_semantics(bundle)

    assert issues == []


def test_alignment_semantic_lint_requires_long_chain_gatekeeper_to_read_phase_handoffs(
    sample_workdir: Path,
) -> None:
    bundle = long_chain_multi_builder_bundle(sample_workdir)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] = ["evidence_hardening_builder_step"]

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("long-chain GateKeeper must include an earlier phase, review, or Guide handoff in inputs.handoffs_from: gatekeeper_step") in issues
