from __future__ import annotations

from pathlib import Path

from asset_catalog_test_support import asset_catalog, create_role_definition, resolve_role_definition_workflow


def test_asset_catalog_hydrates_role_snapshots_from_role_definition_id(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    role_definition = create_role_definition(
        catalog,
        executor_kind="claude",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )

    resolved = resolve_role_definition_workflow(catalog, role_definition["id"])

    builder_role = resolved["workflow"]["roles"][0]
    assert builder_role["name"] == "Release Builder"
    assert builder_role["archetype"] == "builder"
    assert builder_role["prompt_ref"] == "release-builder.md"
    assert builder_role["executor_kind"] == "claude"
    assert builder_role["model"] == "gpt-5.4-mini"
    assert builder_role["reasoning_effort"] == "high"
    assert resolved["prompt_files"]["release-builder.md"].startswith("---\nversion: 1")


def test_asset_catalog_hydrates_role_posture_notes_from_role_definition_id(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    role_definition = create_role_definition(
        catalog,
        name="Focused Builder",
        prompt_ref="focused-builder.md",
        posture_notes="Treat maintainability debt as first-class in this task.",
    )

    resolved = resolve_role_definition_workflow(catalog, role_definition["id"])

    assert resolved["workflow"]["roles"][0]["posture_notes"] == "Treat maintainability debt as first-class in this task."


def test_asset_catalog_allows_task_scoped_posture_notes_with_role_definition_id(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    role_definition = create_role_definition(
        catalog,
        name="Focused Builder",
        prompt_ref="focused-builder.md",
        posture_notes="Treat maintainability debt as first-class in this task.",
    )

    resolved = resolve_role_definition_workflow(
        catalog,
        role_definition["id"],
        role_overrides={"posture_notes": "Create an inspectable handoff for two reviewers."},
    )

    assert resolved["workflow"]["roles"][0]["posture_notes"] == "Create an inspectable handoff for two reviewers."


def test_asset_catalog_allows_workflow_role_label_with_role_definition_id(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    role_definition = create_role_definition(
        catalog,
        name="Generic Inspector",
        description="Checks evidence.",
        archetype="inspector",
        prompt_ref="generic-inspector.md",
        body="Inspect the result.",
    )

    resolved = resolve_role_definition_workflow(
        catalog,
        role_definition["id"],
        role_id="contract_inspector",
        role_overrides={"name": "Contract Inspector"},
    )

    assert resolved["workflow"]["roles"][0]["name"] == "Contract Inspector"
    assert resolved["workflow"]["roles"][0]["archetype"] == "inspector"
