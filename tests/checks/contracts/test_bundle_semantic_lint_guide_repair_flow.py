from __future__ import annotations

from pathlib import Path

from loopora.bundles import lint_alignment_bundle_semantics
from bundle_semantic_lint_workflow_support import add_repair_guide_flow, load_default_alignment_bundle


def test_alignment_semantic_lint_requires_guide_after_review_to_read_review_inputs(
    sample_workdir: Path,
) -> None:
    bundle = add_repair_guide_flow(load_default_alignment_bundle(sample_workdir))
    assert not any("Guide step after review" in issue for issue in lint_alignment_bundle_semantics(bundle))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["repair_guide_step"]["inputs"]["handoffs_from"] = ["builder_step"]
    steps_by_id["repair_guide_step"]["inputs"].pop("evidence_query")

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Guide step after review must include review handoffs in inputs.handoffs_from: repair_guide_step") in issues
    assert ("Guide step after review must query review evidence in inputs.evidence_query: inspector") in issues


def test_alignment_semantic_lint_requires_guide_after_review_iteration_memory(
    sample_workdir: Path,
) -> None:
    bundle = add_repair_guide_flow(load_default_alignment_bundle(sample_workdir))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["repair_guide_step"]["inputs"].pop("iteration_memory")

    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "Guide step after review must declare inputs.iteration_memory so repair guidance can use prior iteration evidence explicitly: repair_guide_step"
    ) in issues


def test_alignment_semantic_lint_requires_guide_after_review_summary_memory(
    sample_workdir: Path,
) -> None:
    bundle = add_repair_guide_flow(load_default_alignment_bundle(sample_workdir))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["repair_guide_step"]["inputs"]["iteration_memory"] = "same_role"

    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "Guide step after review must use inputs.iteration_memory=summary_only so previous GateKeeper blockers and residual risks stay visible: repair_guide_step"
    ) in issues


def test_alignment_semantic_lint_requires_builder_after_guide_to_read_guide_handoff(
    sample_workdir: Path,
) -> None:
    bundle = add_repair_guide_flow(load_default_alignment_bundle(sample_workdir))
    gatekeeper_step = bundle["workflow"]["steps"].pop()
    bundle["workflow"]["steps"].append(
        {
            "id": "builder_repair_step",
            "role_id": "builder",
            "inputs": {
                "handoffs_from": ["builder_step"],
                "iteration_memory": "same_step",
            },
            "on_pass": "continue",
        }
    )
    gatekeeper_step["inputs"]["handoffs_from"].append("builder_repair_step")
    bundle["workflow"]["steps"].append(gatekeeper_step)

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after Guide must name a Guide handoff in inputs.handoffs_from: builder_repair_step") in issues


def test_alignment_semantic_lint_requires_builder_after_guide_to_read_review_handoff(
    sample_workdir: Path,
) -> None:
    bundle = add_repair_guide_flow(load_default_alignment_bundle(sample_workdir))
    gatekeeper_step = bundle["workflow"]["steps"].pop()
    bundle["workflow"]["steps"].append(
        {
            "id": "builder_repair_step",
            "role_id": "builder",
            "inputs": {
                "handoffs_from": ["repair_guide_step"],
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        }
    )
    gatekeeper_step["inputs"]["handoffs_from"].append("builder_repair_step")
    bundle["workflow"]["steps"].append(gatekeeper_step)

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after Guide must also include review handoffs in inputs.handoffs_from: builder_repair_step") in issues


def test_alignment_semantic_lint_requires_builder_after_guide_iteration_memory(
    sample_workdir: Path,
) -> None:
    bundle = add_repair_guide_flow(load_default_alignment_bundle(sample_workdir))
    gatekeeper_step = bundle["workflow"]["steps"].pop()
    bundle["workflow"]["steps"].append(
        {
            "id": "builder_repair_step",
            "role_id": "builder",
            "inputs": {
                "handoffs_from": ["repair_guide_step"],
            },
            "on_pass": "continue",
        }
    )
    gatekeeper_step["inputs"]["handoffs_from"].append("builder_repair_step")
    bundle["workflow"]["steps"].append(gatekeeper_step)

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after Guide must declare inputs.iteration_memory so repair pass does not rely on ambient context: builder_repair_step") in issues


def test_alignment_semantic_lint_requires_builder_after_guide_summary_memory(
    sample_workdir: Path,
) -> None:
    bundle = add_repair_guide_flow(load_default_alignment_bundle(sample_workdir))
    gatekeeper_step = bundle["workflow"]["steps"].pop()
    bundle["workflow"]["steps"].append(
        {
            "id": "builder_repair_step",
            "role_id": "builder",
            "inputs": {
                "handoffs_from": ["repair_guide_step"],
                "iteration_memory": "same_step",
            },
            "on_pass": "continue",
        }
    )
    gatekeeper_step["inputs"]["handoffs_from"].append("builder_repair_step")
    bundle["workflow"]["steps"].append(gatekeeper_step)

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after Guide must use inputs.iteration_memory=summary_only so previous GateKeeper verdict stays visible: builder_repair_step") in issues
