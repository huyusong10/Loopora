from __future__ import annotations

from pathlib import Path

import pytest

from loopora.asset_catalog import StrategyTemplateAssetCatalog
from loopora.db import LooporaRepository
from loopora.strategy_source import StrategySourceError

from asset_catalog_test_support import asset_catalog, prompt_markdown


def test_asset_catalog_update_preserves_existing_workflow_and_prompt_files_when_omitted(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    orchestration = create_custom_builder_orchestration(catalog)

    updated = catalog.update_orchestration(
        orchestration["id"],
        name="Renamed Builder Flow",
        description="Updated description only.",
        workflow=None,
        prompt_files=None,
        role_models=None,
    )

    assert updated["name"] == "Renamed Builder Flow"
    assert updated["workflow_json"]["roles"][0]["prompt_ref"] == "custom-builder.md"
    assert updated["workflow_json"]["steps"][0]["id"] == "builder_step"
    assert updated["prompt_files_json"]["custom-builder.md"].startswith("---\nversion: 1")


def test_asset_catalog_update_prunes_prompt_files_not_used_by_current_workflow(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    orchestration = create_custom_builder_orchestration(catalog)

    updated = catalog.update_orchestration(
        orchestration["id"],
        name="Builtin Builder Flow",
        description="Now uses the built-in builder prompt.",
        workflow=builder_workflow("builder.md"),
        prompt_files=None,
        role_models=None,
    )

    assert updated["workflow_json"]["roles"][0]["prompt_ref"] == "builder.md"
    assert list(updated["prompt_files_json"].keys()) == ["builder.md"]
    assert "custom-builder.md" not in updated["prompt_files_json"]


def test_asset_catalog_rejects_invalid_prompt_file_keys(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)

    with pytest.raises(StrategySourceError, match="prompt_ref must be a safe relative path"):
        catalog.create_orchestration(
            name="Unsafe Prompt Files",
            description="Should reject invalid prompt_files keys instead of ignoring them.",
            workflow=builder_workflow("builder.md"),
            prompt_files={
                "../escape.md": prompt_markdown("builder", "This should never be silently dropped."),
            },
        )


def test_asset_catalog_sanitizes_invalid_persisted_prompt_file_keys(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    repository.create_orchestration(
        {
            "id": "orch_legacy",
            "name": "Legacy Builder Flow",
            "description": "Contains stale invalid prompt file keys.",
            "workflow": builder_workflow("builder.md"),
            "prompt_files": {
                "../escape.md": prompt_markdown("builder", "Legacy invalid key."),
                "builder.md": prompt_markdown("builder", "Legit builder prompt."),
            },
        }
    )
    catalog = StrategyTemplateAssetCatalog(repository)

    orchestration = catalog.get_orchestration("orch_legacy")
    resolved = catalog.resolve_orchestration_input(
        orchestration_id="orch_legacy",
        workflow=None,
        prompt_files=None,
        role_models=None,
    )

    assert list(orchestration["prompt_files_json"].keys()) == ["builder.md"]
    assert list(resolved["prompt_files"].keys()) == ["builder.md"]


def test_asset_catalog_resolves_saved_orchestration_before_prompt_file_overrides(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    orchestration = create_custom_builder_orchestration(catalog)
    override_prompt = prompt_markdown("builder", "Use the per-loop override prompt.")

    resolved = catalog.resolve_orchestration_input(
        orchestration_id=orchestration["id"],
        workflow=None,
        prompt_files={"custom-builder.md": override_prompt},
        role_models=None,
    )

    assert resolved["id"] == orchestration["id"]
    assert resolved["workflow"]["steps"][0]["id"] == "builder_step"
    assert resolved["workflow"]["roles"][0]["prompt_ref"] == "custom-builder.md"
    assert resolved["prompt_files"] == {"custom-builder.md": override_prompt}


def create_custom_builder_orchestration(catalog) -> dict:
    return catalog.create_orchestration(
        name="Custom Builder Flow",
        description="Uses a custom builder prompt.",
        workflow=builder_workflow("custom-builder.md"),
        prompt_files={"custom-builder.md": prompt_markdown("builder", "Keep the builder prompt stable.")},
    )


def builder_workflow(prompt_ref: str) -> dict:
    return {
        "version": 1,
        "roles": [{"id": "builder", "archetype": "builder", "prompt_ref": prompt_ref}],
        "steps": [{"id": "builder_step", "role_id": "builder"}],
    }
