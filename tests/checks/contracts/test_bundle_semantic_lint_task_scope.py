from __future__ import annotations

from pathlib import Path

import pytest

from loopora.bundles import lint_alignment_bundle_semantics, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


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


@pytest.mark.parametrize(
    "contradiction",
    [
        "A single Agent pass is sufficient, and direct chat would be enough for this task.",
        "这个任务跑一遍就行，不需要多轮。",
        "一次 Agent 执行加人工 review 已经足够，后续不会产生新证据。",
        "One Agent pass plus human review would be sufficient here.",
        "A future round would not produce new evidence for this task.",
        "不用 Loopora，直接让 Agent 做完再人工看一眼就行。",
        "This is a one-off task; no Loopora loop is needed.",
        "这是一次性任务，不要长期循环，直接处理完即可。",
        "The stable proof harness already fully captures the judgment.",
    ],
)
def test_alignment_semantic_lint_rejects_final_bundle_loop_fit_contradictions(
    sample_workdir: Path,
    contradiction: str,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    assert not any("single pass" in issue for issue in lint_alignment_bundle_semantics(bundle))

    bundle["collaboration_summary"] += f" {contradiction}"
    issues = lint_alignment_bundle_semantics(bundle)

    assert (
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ) in issues
