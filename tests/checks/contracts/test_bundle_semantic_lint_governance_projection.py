from __future__ import annotations

import re
from pathlib import Path

from loopora.bundles import lint_alignment_bundle_semantics, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


def test_alignment_semantic_lint_requires_summary_governance_story(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert "collaboration_summary must explain the governance story" not in lint_alignment_bundle_semantics(valid_bundle)

    yaml_without_governance_summary = re.sub(
        r"collaboration_summary: \|\n(?:  .+\n)+loop:",
        'collaboration_summary: "Build the requested task."\nloop:',
        alignment_bundle_yaml(str(sample_workdir.resolve())),
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_without_governance_summary))

    assert "collaboration_summary must explain the governance story" in issues


def test_alignment_semantic_lint_requires_loop_fit_in_summary(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert "collaboration_summary must explain why this task needs multi-round Loopora governance" not in lint_alignment_bundle_semantics(valid_bundle)

    bundle_without_loop_fit = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle_without_loop_fit["collaboration_summary"] = (
        "Project the working agreement into a spec task contract, role handoffs from Builder / Inspectors / GateKeeper, "
        "and a workflow that routes evidence before final judgment. Prefer a smaller proven flow over polished but "
        "unproven breadth, and let GateKeeper reject speed or surface completeness when evidence is weak. GateKeeper "
        "closes only when the spec, role evidence, and workflow handoffs prove the task is truly done."
    )

    issues = lint_alignment_bundle_semantics(bundle_without_loop_fit)

    assert "collaboration_summary must explain why this task needs multi-round Loopora governance" in issues


def test_alignment_semantic_lint_requires_evidence_bucket_projection(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("must project task verdict evidence" in issue for issue in lint_alignment_bundle_semantics(valid_bundle))

    yaml_without_bucket_projection = (
        alignment_bundle_yaml(str(sample_workdir.resolve()))
        .replace(
            " Evidence projection must distinguish Proven direct run proof, Weak indirect evidence, "
            "Unproven promised surfaces, Blocking fake-done findings, and visible Residual risk.",
            "",
        )
        .replace(
            "    - Final evidence should be bucketed as Proven, Weak, Unproven, Blocking, or Residual risk instead of flattened into one summary.\n",
            "",
        )
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_without_bucket_projection))

    assert ("alignment bundle must project task verdict evidence into Proven, Weak, Unproven, Blocking, and Residual risk buckets") in issues


def test_alignment_semantic_lint_does_not_count_metadata_as_evidence_bucket_projection(sample_workdir: Path) -> None:
    yaml_without_bucket_projection = (
        alignment_bundle_yaml(str(sample_workdir.resolve()))
        .replace(
            " Evidence projection must distinguish Proven direct run proof, Weak indirect evidence, "
            "Unproven promised surfaces, Blocking fake-done findings, and visible Residual risk.",
            "",
        )
        .replace(
            "    - Final evidence should be bucketed as Proven, Weak, Unproven, Blocking, or Residual risk instead of flattened into one summary.\n",
            "",
        )
    )
    bundle = load_bundle_text(yaml_without_bucket_projection)
    bucket_words = "Proven Weak Unproven Blocking Residual risk"
    bundle["metadata"]["description"] = bucket_words
    bundle["loop"]["name"] = bucket_words

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("alignment bundle must project task verdict evidence into Proven, Weak, Unproven, Blocking, and Residual risk buckets") in issues


def test_alignment_semantic_lint_requires_gatekeeper_completion_mode(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("must use gatekeeper completion_mode" in issue for issue in lint_alignment_bundle_semantics(valid_bundle))

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["loop"]["completion_mode"] = "rounds"
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Web alignment bundles must use gatekeeper completion_mode so task verdict is evidence-based, not only run lifecycle completion") in issues


def test_alignment_semantic_lint_requires_workflow_intent_to_explain_evidence_governance(
    sample_workdir: Path,
) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    expected_issue = "workflow.collaboration_intent must explain evidence flow, GateKeeper closure, and weak-evidence or fake-done exposure"
    assert expected_issue not in lint_alignment_bundle_semantics(valid_bundle)

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["workflow"]["collaboration_intent"] = (
        "Builder implements the billing refund path, Inspector reviews the approval journey, "
        "and GateKeeper gives the final decision for this task-specific sequence after each role completes its part."
    )

    issues = lint_alignment_bundle_semantics(bundle)

    assert expected_issue in issues
