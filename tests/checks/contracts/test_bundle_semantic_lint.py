from __future__ import annotations

import re
from pathlib import Path

import pytest

from loopora.bundles import (
    lint_alignment_bundle_generation_metadata,
    lint_alignment_bundle_generation_text,
    lint_alignment_bundle_semantics,
    load_bundle_text,
)
from loopora.executor_fake_payloads import alignment_bundle_yaml


def test_alignment_semantic_lint_requires_residual_risk(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert "spec must include Residual Risk guidance" not in lint_alignment_bundle_semantics(valid_bundle)

    yaml_without_residual_risk = re.sub(
        r"\n    # Residual Risk\n\n    .+?(?=\n\n    # Role Notes)",
        "\n",
        alignment_bundle_yaml(str(sample_workdir.resolve())),
        flags=re.DOTALL,
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_without_residual_risk))

    assert "spec must include Residual Risk guidance" in issues


def test_alignment_semantic_lint_rejects_vague_residual_risk(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert "spec Residual Risk guidance must name accepted risk handling or fail closed" not in lint_alignment_bundle_semantics(valid_bundle)

    yaml_with_vague_residual_risk = re.sub(
        r"\n    # Residual Risk\n\n    .+?(?=\n\n    # Role Notes)",
        "\n    # Residual Risk\n\n    Some risk is fine.",
        alignment_bundle_yaml(str(sample_workdir.resolve())),
        flags=re.DOTALL,
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_with_vague_residual_risk))

    assert "spec Residual Risk guidance must name accepted risk handling or fail closed" in issues

    yaml_with_vague_chinese_residual_risk = re.sub(
        r"\n    # Residual Risk\n\n    .+?(?=\n\n    # Role Notes)",
        "\n    # Residual Risk\n\n    有些风险可以接受。",
        alignment_bundle_yaml(str(sample_workdir.resolve())),
        flags=re.DOTALL,
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_with_vague_chinese_residual_risk))

    assert "spec Residual Risk guidance must name accepted risk handling or fail closed" in issues


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


@pytest.mark.parametrize(
    "generic_task",
    [
        "Do the task.",
        "Ship the focused starter experience described only by the alignment agreement.",
    ],
)
def test_alignment_semantic_lint_requires_specific_task_contract(sample_workdir: Path, generic_task: str) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert "spec Task must describe the concrete user-facing task" not in lint_alignment_bundle_semantics(valid_bundle)

    yaml_with_generic_task = re.sub(
        r"\n    # Task\n\n    .+?(?=\n\n    # Done When)",
        f"\n    # Task\n\n    {generic_task}",
        alignment_bundle_yaml(str(sample_workdir.resolve())),
        flags=re.DOTALL,
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_with_generic_task))

    assert "spec Task must describe the concrete user-facing task" in issues


def test_alignment_semantic_lint_requires_done_when_checks(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert "spec must include at least one Done When bullet" not in lint_alignment_bundle_semantics(valid_bundle)

    yaml_without_done_when = re.sub(
        r"\n    # Done When\n\n    - .+?(?=\n\n    # Guardrails)",
        "",
        alignment_bundle_yaml(str(sample_workdir.resolve())),
        flags=re.DOTALL,
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_without_done_when))

    assert "spec must include at least one Done When bullet" in issues


@pytest.mark.parametrize(
    ("section", "expected_issue"),
    [
        ("Success Surface", "spec must include at least one Success Surface bullet"),
        ("Fake Done", "spec must include at least one Fake Done bullet"),
        ("Evidence Preferences", "spec must include at least one Evidence Preferences bullet"),
    ],
)
def test_alignment_semantic_lint_requires_judgment_contract_sections(
    sample_workdir: Path,
    section: str,
    expected_issue: str,
) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert expected_issue not in lint_alignment_bundle_semantics(valid_bundle)

    heading_pattern = rf"\n    # {re.escape(section)}\n\n    - .+?(?=\n\n    # )"
    yaml_without_section = re.sub(
        heading_pattern,
        "",
        alignment_bundle_yaml(str(sample_workdir.resolve())),
        flags=re.DOTALL,
    )
    issues = lint_alignment_bundle_semantics(load_bundle_text(yaml_without_section))

    assert expected_issue in issues


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


def test_alignment_generated_metadata_omits_lineage_fields(sample_workdir: Path) -> None:
    valid_yaml = alignment_bundle_yaml(str(sample_workdir.resolve()))
    assert lint_alignment_bundle_generation_text(valid_yaml) == []
    assert lint_alignment_bundle_generation_metadata(valid_yaml) == []

    lineage_yaml = valid_yaml.replace(
        '  description: "Bundle generated by the Web alignment flow."\n',
        '  description: "Bundle generated by the Web alignment flow."\n  source_bundle_id: "source_bundle_old"\n  revision: 2\n',
        1,
    )

    assert lint_alignment_bundle_generation_metadata(lineage_yaml) == [
        "Web alignment generated bundles must omit metadata.source_bundle_id and metadata.revision; "
        "source context is temporary and final bundles are standalone candidates"
    ]
    semantic_issues = lint_alignment_bundle_semantics(load_bundle_text(lineage_yaml))
    assert (
        "Web alignment bundles must not encode metadata.source_bundle_id; source context is temporary and final bundles are standalone candidates"
    ) in semantic_issues


def test_alignment_generated_bundle_text_must_be_raw_yaml(sample_workdir: Path) -> None:
    valid_yaml = alignment_bundle_yaml(str(sample_workdir.resolve()))
    yaml_with_internal_fence = valid_yaml.replace(
        "Leave concrete handoffs and evidence references for downstream review.",
        "Leave concrete handoffs and evidence references for downstream review.\n\n      ```text\n      internal example\n      ```",
        1,
    )

    fenced_issues = lint_alignment_bundle_generation_text(f"```yaml\n{valid_yaml}```")
    prefixed_issues = lint_alignment_bundle_generation_text("Here is the bundle:\n" + valid_yaml)
    comment_prefixed_issues = lint_alignment_bundle_generation_text("# Here is the bundle\n" + valid_yaml)

    assert lint_alignment_bundle_generation_text(yaml_with_internal_fence) == []
    assert "Web alignment generated bundle_yaml must be one raw YAML document, not markdown-fenced output" in fenced_issues
    assert "Web alignment generated bundle_yaml must start with version: 1" in fenced_issues
    assert prefixed_issues == ["Web alignment generated bundle_yaml must start with version: 1"]
    assert comment_prefixed_issues == ["Web alignment generated bundle_yaml must start with version: 1"]
def test_alignment_semantic_lint_rejects_personality_memory_bundle(sample_workdir: Path) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("personality memory" in issue for issue in lint_alignment_bundle_semantics(valid_bundle))

    valid_bundle["collaboration_summary"] = (
        "This bundle maps the user's permanent preference memory into spec, roles, and workflow "
        "so Builder always follows the user's global personality, Inspector gathers browser "
        "and test evidence, and GateKeeper signs off only after that evidence supports the "
        "preferred behavior."
    )
    issues = lint_alignment_bundle_semantics(valid_bundle)

    assert "alignment bundle must stay task-scoped, not personality memory or global preferences" in issues


@pytest.mark.parametrize(
    "antipattern_phrase",
    [
        "prompt pack",
        "role zoo",
        "loop script",
        "benchmark grinder",
        "chat wrapper",
    ],
)
def test_alignment_semantic_lint_rejects_named_loopora_antipatterns(
    sample_workdir: Path,
    antipattern_phrase: str,
) -> None:
    valid_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("prompt pack" in issue for issue in lint_alignment_bundle_semantics(valid_bundle))

    valid_bundle["collaboration_summary"] = (
        f"This {antipattern_phrase} maps the user's task into spec, roles, and workflow. "
        "Builder follows the role prose, Inspector gathers browser and test evidence, "
        "and GateKeeper signs off only after proof supports the promised task surface."
    )
    issues = lint_alignment_bundle_semantics(valid_bundle)

    assert ("alignment bundle must not present prompt pack, role zoo, loop script, benchmark grinder, or chat wrapper as Loopora governance") in issues


def test_alignment_semantic_lint_rejects_duplicate_role_responsibilities(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("distinct task evidence responsibilities" in issue for issue in lint_alignment_bundle_semantics(bundle))

    roles_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    roles_by_key["contract-inspector"]["prompt_markdown"] = roles_by_key["evidence-inspector"]["prompt_markdown"]
    roles_by_key["contract-inspector"]["posture_notes"] = roles_by_key["evidence-inspector"]["posture_notes"]
    for step in bundle["workflow"]["steps"]:
        step.pop("parallel_group", None)

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("role_definitions must have distinct task evidence responsibilities: contract-inspector, evidence-inspector") in issues


def test_alignment_semantic_lint_allows_antipatterns_named_as_fake_done_risks(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += (
        " The spec also avoids prompt pack and personality memory failures by keeping the judgment task-scoped and evidence-owned."
    )

    issues = lint_alignment_bundle_semantics(bundle)

    assert not any("prompt pack" in issue for issue in issues)
    assert not any("personality memory" in issue for issue in issues)


def test_alignment_semantic_lint_rejects_final_bundle_loop_fit_contradictions(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("single pass" in issue for issue in lint_alignment_bundle_semantics(bundle))

    bundle["collaboration_summary"] += " A single Agent pass is sufficient, and direct chat would be enough for this task."
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " 这个任务跑一遍就行，不需要多轮。"
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " 一次 Agent 执行加人工 review 已经足够，后续不会产生新证据。"
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " One Agent pass plus human review would be sufficient here."
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " A future round would not produce new evidence for this task."
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " 不用 Loopora，直接让 Agent 做完再人工看一眼就行。"
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " This is a one-off task; no Loopora loop is needed."
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " 这是一次性任务，不要长期循环，直接处理完即可。"
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues

    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " The stable proof harness already fully captures the judgment."
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues
