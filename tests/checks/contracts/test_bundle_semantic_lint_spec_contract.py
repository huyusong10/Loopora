from __future__ import annotations

import re
from pathlib import Path

import pytest

from loopora.bundles import lint_alignment_bundle_semantics, load_bundle_text
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
