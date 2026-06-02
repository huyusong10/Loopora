from __future__ import annotations

from pathlib import Path

from loopora.bundles import lint_alignment_bundle_semantics
from bundle_semantic_lint_workflow_support import load_default_alignment_bundle


def test_alignment_semantic_lint_requires_builder_after_review_to_read_review_handoff(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    bundle["workflow"]["steps"].insert(
        0,
        {
            "id": "preflight_inspection_step",
            "role_id": "contract_inspector",
            "on_pass": "continue",
        },
    )
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["builder_step"]["inputs"] = {
        "handoffs_from": ["preflight_inspection_step"],
        "iteration_memory": "summary_only",
    }
    assert not any("Builder step after review" in issue for issue in lint_alignment_bundle_semantics(bundle))

    steps_by_id["builder_step"]["inputs"]["handoffs_from"] = []
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after review must include review handoffs in inputs.handoffs_from: builder_step") in issues


def test_alignment_semantic_lint_requires_builder_after_review_iteration_memory(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    bundle["workflow"]["steps"].insert(
        0,
        {
            "id": "preflight_inspection_step",
            "role_id": "contract_inspector",
            "on_pass": "continue",
        },
    )
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["builder_step"]["inputs"] = {
        "handoffs_from": ["preflight_inspection_step"],
    }

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after review must declare inputs.iteration_memory so evidence-first repair does not rely on ambient context: builder_step") in issues


def test_alignment_semantic_lint_requires_builder_after_review_summary_memory(
    sample_workdir: Path,
) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    bundle["workflow"]["steps"].insert(
        0,
        {
            "id": "preflight_inspection_step",
            "role_id": "contract_inspector",
            "on_pass": "continue",
        },
    )
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["builder_step"]["inputs"] = {
        "handoffs_from": ["preflight_inspection_step"],
        "iteration_memory": "same_step",
    }

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Builder step after review must use inputs.iteration_memory=summary_only so previous GateKeeper repair direction stays visible: builder_step") in issues
