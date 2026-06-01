from __future__ import annotations

from pathlib import Path

import pytest

from loopora.bundles import lint_alignment_bundle_semantics, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


@pytest.mark.parametrize("review_archetype", ["inspector", "custom"])
def test_alignment_semantic_lint_requires_review_after_builder_to_read_builder_inputs(
    sample_workdir: Path,
    review_archetype: str,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    if review_archetype == "custom":
        _make_contract_inspector_custom_review(bundle)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    if review_archetype == "custom":
        steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"].append("custom")
    assert not any("review step after Builder" in issue for issue in lint_alignment_bundle_semantics(bundle))

    steps_by_id["contract_inspection_step"].pop("inputs")
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("review step after Builder must name a Builder handoff in inputs.handoffs_from: contract_inspection_step") in issues
    assert ("review step after Builder must query Builder evidence in inputs.evidence_query: contract_inspection_step") in issues


def test_alignment_semantic_lint_preserves_expert_parallel_review_guards(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
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


def test_alignment_semantic_lint_rejects_generic_role_names(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("task-specific role name" in issue for issue in lint_alignment_bundle_semantics(bundle))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["name"] = "Inspector 1"
    role_by_key["evidence-inspector"]["name"] = "Inspector 2"
    issues = lint_alignment_bundle_semantics(bundle)

    assert "role_definition contract-inspector must use a task-specific role name" in issues
    assert "role_definition evidence-inspector must use a task-specific role name" in issues
def test_alignment_semantic_lint_uses_graph_contract_for_custom_review_roles(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["archetype"] = "custom"
    role_by_key["contract-inspector"]["prompt_markdown"] = role_by_key["contract-inspector"]["prompt_markdown"].replace(
        "archetype: inspector", "archetype: custom"
    )

    issues = lint_alignment_bundle_semantics(bundle)

    assert not any("Custom read-only specialized review" in issue for issue in issues)
    assert "finishing GateKeeper after review must query review evidence in inputs.evidence_query: custom" in issues


def _add_repair_guide_flow(bundle: dict) -> dict:
    bundle["role_definitions"].append(
        {
            "key": "repair-guide",
            "name": "Repair Direction Guide",
            "description": "Turns inspection evidence into a focused repair direction.",
            "archetype": "guide",
            "prompt_ref": "repair-guide.md",
            "prompt_markdown": """---
version: 1
archetype: guide
---

Use the inspection evidence to narrow the next Builder step. Leave a handoff that names the repair direction, the evidence behind it, and the scope that must not expand.""",
            "posture_notes": "Narrow the repair target from review evidence instead of offering broad advice.",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_cli": "",
            "command_args_text": "",
            "model": "",
            "reasoning_effort": "",
        }
    )
    bundle["workflow"]["roles"].append({"id": "repair_guide", "role_definition_key": "repair-guide"})
    gatekeeper_step = bundle["workflow"]["steps"][-1]
    bundle["workflow"]["steps"].insert(
        -1,
        {
            "id": "repair_guide_step",
            "role_id": "repair_guide",
            "inputs": {
                "handoffs_from": ["contract_inspection_step", "evidence_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "limit": 12},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
    )
    gatekeeper_step["inputs"]["handoffs_from"].append("repair_guide_step")
    gatekeeper_step["inputs"]["evidence_query"]["archetypes"].append("guide")
    return bundle
def test_alignment_semantic_lint_requires_guide_after_review_to_read_review_inputs(
    sample_workdir: Path,
) -> None:
    bundle = _add_repair_guide_flow(load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve()))))
    assert not any("Guide step after review" in issue for issue in lint_alignment_bundle_semantics(bundle))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["repair_guide_step"]["inputs"]["handoffs_from"] = ["builder_step"]
    steps_by_id["repair_guide_step"]["inputs"].pop("evidence_query")

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("Guide step after review must include review handoffs in inputs.handoffs_from: repair_guide_step") in issues
    assert ("Guide step after review must query review evidence in inputs.evidence_query: inspector") in issues


def _make_contract_inspector_custom_review(bundle: dict) -> None:
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    contract_role = role_by_key["contract-inspector"]
    contract_role["archetype"] = "custom"
    contract_role["prompt_markdown"] = contract_role["prompt_markdown"].replace(
        "archetype: inspector",
        "archetype: custom",
    )
    contract_role["prompt_markdown"] += (
        "\n\n      Act as a read-only specialized Custom reviewer for contract evidence; do not edit files, and leave a focused handoff."
    )
    contract_role["posture_notes"] += " As a low-permission Custom reviewer, provide only specialized contract review signal."


def test_alignment_semantic_lint_treats_custom_as_review_before_builder(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    _make_contract_inspector_custom_review(bundle)
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


def test_alignment_semantic_lint_treats_custom_as_review_before_gatekeeper(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    _make_contract_inspector_custom_review(bundle)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] = ["evidence_inspection_step"]
    steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"] = ["builder", "inspector"]

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("finishing GateKeeper after review must include review handoffs in inputs.handoffs_from: contract_inspection_step") in issues
    assert ("finishing GateKeeper after review must query review evidence in inputs.evidence_query: custom") in issues


def test_alignment_semantic_lint_requires_guide_after_review_iteration_memory(
    sample_workdir: Path,
) -> None:
    bundle = _add_repair_guide_flow(load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve()))))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["repair_guide_step"]["inputs"].pop("iteration_memory")

    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "Guide step after review must declare inputs.iteration_memory so repair guidance can use prior iteration evidence explicitly: repair_guide_step"
    ) in issues


def test_alignment_semantic_lint_requires_guide_after_review_summary_memory(
    sample_workdir: Path,
) -> None:
    bundle = _add_repair_guide_flow(load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve()))))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["repair_guide_step"]["inputs"]["iteration_memory"] = "same_role"

    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "Guide step after review must use inputs.iteration_memory=summary_only so previous GateKeeper blockers and residual risks stay visible: repair_guide_step"
    ) in issues


def test_alignment_semantic_lint_requires_builder_after_guide_to_read_guide_handoff(
    sample_workdir: Path,
) -> None:
    bundle = _add_repair_guide_flow(load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve()))))
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


def test_alignment_semantic_lint_requires_builder_after_guide_iteration_memory(
    sample_workdir: Path,
) -> None:
    bundle = _add_repair_guide_flow(load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve()))))
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
    bundle = _add_repair_guide_flow(load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve()))))
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


def test_alignment_semantic_lint_requires_builder_after_review_to_read_review_handoff(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
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
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
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
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
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


def test_alignment_semantic_lint_requires_finishing_gatekeeper_to_read_handoff_and_evidence(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("finishing GateKeeper step" in issue for issue in lint_alignment_bundle_semantics(bundle))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"].pop("inputs")
    issues = lint_alignment_bundle_semantics(bundle)

    assert ("finishing GateKeeper step must name upstream handoffs in inputs.handoffs_from: gatekeeper_step") in issues
    assert ("finishing GateKeeper step must query upstream evidence in inputs.evidence_query: gatekeeper_step") in issues


def test_alignment_semantic_lint_requires_gatekeeper_after_review_to_read_review_evidence(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("GateKeeper after review" in issue for issue in lint_alignment_bundle_semantics(bundle))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] = ["builder_step"]
    steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"] = ["builder"]

    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "finishing GateKeeper after review must include review handoffs in inputs.handoffs_from: contract_inspection_step, evidence_inspection_step"
    ) in issues
    assert ("finishing GateKeeper after review must query review evidence in inputs.evidence_query: inspector") in issues
