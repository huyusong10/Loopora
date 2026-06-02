from __future__ import annotations

from pathlib import Path

import pytest

from loopora.bundles import lint_alignment_bundle_semantics
from bundle_semantic_lint_workflow_support import load_default_alignment_bundle, make_contract_inspector_custom_review


@pytest.mark.parametrize("review_archetype", ["inspector", "custom"])
def test_alignment_semantic_lint_requires_review_after_builder_to_read_builder_inputs(
    sample_workdir: Path,
    review_archetype: str,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    if review_archetype == "custom":
        make_contract_inspector_custom_review(bundle)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    if review_archetype == "custom":
        steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"].append("custom")
    assert not any("review step after Builder" in issue for issue in lint_alignment_bundle_semantics(bundle))

    steps_by_id["contract_inspection_step"].pop("inputs")
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("review step after Builder must name a Builder handoff in inputs.handoffs_from: contract_inspection_step") in issues
    assert ("review step after Builder must query Builder evidence in inputs.evidence_query: contract_inspection_step") in issues


def test_alignment_semantic_lint_preserves_expert_parallel_review_guards(sample_workdir: Path) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["contract_inspection_step"]["parallel_group"] = "inspection_pack"
    steps_by_id["evidence_inspection_step"]["parallel_group"] = "inspection_pack"
    assert not any("parallel review step must query Builder evidence" in issue for issue in lint_alignment_bundle_semantics(bundle))

    steps_by_id["evidence_inspection_step"]["inputs"]["handoffs_from"] = ["contract_inspection_step"]
    steps_by_id["contract_inspection_step"]["inputs"].pop("evidence_query")
    steps_by_id["contract_inspection_step"]["inputs"].pop("iteration_memory")
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("parallel review steps must read the same upstream handoffs: contract_inspection_step, evidence_inspection_step") in issues
    assert ("parallel review step must query Builder evidence in inputs.evidence_query: contract_inspection_step") in issues
    assert ("parallel review step must declare inputs.iteration_memory so cross-iteration evidence flow is explicit: contract_inspection_step") in issues


def test_alignment_semantic_lint_uses_graph_contract_for_custom_review_roles(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["archetype"] = "custom"
    role_by_key["contract-inspector"]["prompt_markdown"] = role_by_key["contract-inspector"]["prompt_markdown"].replace(
        "archetype: inspector", "archetype: custom"
    )

    issues = lint_alignment_bundle_semantics(bundle)

    assert not any("Custom read-only specialized review" in issue for issue in issues)
    assert "finishing GateKeeper after review must query review evidence in inputs.evidence_query: custom" in issues


def test_alignment_semantic_lint_treats_custom_as_review_before_builder(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    make_contract_inspector_custom_review(bundle)
    bundle["workflow"]["steps"].insert(
        0,
        {
            "id": "preflight_custom_review_step",
            "role_id": "contract_inspector",
            "on_pass": "continue",
        },
    )
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["builder_step"]["inputs"] = {
        "handoffs_from": ["preflight_custom_review_step"],
        "iteration_memory": "summary_only",
    }
    steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"].append("custom")
    assert not any("Builder step after review" in issue for issue in lint_alignment_bundle_semantics(bundle))

    steps_by_id["builder_step"]["inputs"] = {"handoffs_from": []}
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after review must include review handoffs in inputs.handoffs_from: builder_step") in issues
    assert ("Builder step after review must declare inputs.iteration_memory so evidence-first repair does not rely on ambient context: builder_step") in issues
