from __future__ import annotations

# Merged from test_asset_catalog_architecture.py
from pathlib import Path

from loopora.asset_catalog import StrategyTemplateAssetCatalog, WorkflowAssetCatalog


def test_workflow_asset_catalog_remains_legacy_import_alias() -> None:
    assert WorkflowAssetCatalog is StrategyTemplateAssetCatalog


def test_asset_catalog_splits_pure_asset_helpers_from_repository_facade() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog_source = (repo_root / "src" / "loopora" / "asset_catalog.py").read_text(encoding="utf-8")
    builtins_source = (repo_root / "src" / "loopora" / "asset_catalog_builtins.py").read_text(encoding="utf-8")
    decoration_source = (repo_root / "src" / "loopora" / "asset_catalog_decoration.py").read_text(encoding="utf-8")
    inputs_source = (repo_root / "src" / "loopora" / "asset_catalog_inputs.py").read_text(encoding="utf-8")
    resolution_source = (repo_root / "src" / "loopora" / "asset_catalog_orchestration_resolution.py").read_text(encoding="utf-8")
    role_facade_source = (repo_root / "src" / "loopora" / "asset_catalog_role_facade.py").read_text(encoding="utf-8")
    role_payloads_source = (repo_root / "src" / "loopora" / "asset_catalog_role_payloads.py").read_text(encoding="utf-8")
    role_snapshots_source = (repo_root / "src" / "loopora" / "asset_catalog_role_snapshots.py").read_text(encoding="utf-8")
    contracts_source = (repo_root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "class StrategyTemplateAssetCatalog" in catalog_source
    assert "RoleDefinitionAssetCatalogMixin" in catalog_source
    assert "class RoleDefinitionAssetCatalogMixin" in role_facade_source
    assert "def build_builtin_orchestration_records" in builtins_source
    assert "def decorate_orchestration_record" in decoration_source
    assert "def decorate_role_definition_record" in decoration_source
    assert "def sanitize_persisted_prompt_files" in decoration_source
    assert "def role_definition_payload_input_from_args" in inputs_source
    assert "def create_role_definition" in role_facade_source
    assert "def update_role_definition" in role_facade_source
    assert "def delete_role_definition" in role_facade_source
    assert "def resolve_orchestration_input" in resolution_source
    assert "def normalize_role_definition_payload" in role_payloads_source
    assert "def hydrate_strategy_role_snapshots" in role_snapshots_source
    assert "return _resolve_orchestration_input(" in catalog_source
    assert "def create_role_definition" not in catalog_source
    assert "hydrate_strategy_role_snapshots(" not in catalog_source
    assert "def decorate_orchestration_record" not in catalog_source
    assert "def sanitize_persisted_prompt_files" not in catalog_source
    assert "def _normalize_role_definition_payload" not in catalog_source
    assert "def _hydrate_strategy_role_snapshots" not in catalog_source
    assert "asset_catalog_builtins.py" in contracts_source
    assert "asset_catalog_decoration.py" in contracts_source
    assert "asset_catalog_inputs.py" in contracts_source
    assert "asset_catalog_orchestration_resolution.py" in contracts_source
    assert "asset_catalog_role_facade.py" in contracts_source
    assert "asset_catalog_role_payloads.py" in contracts_source
    assert "asset_catalog_role_snapshots.py" in contracts_source

# Merged from test_asset_catalog_orchestration_resolution.py

from loopora.db import LooporaRepository
from loopora.strategy_source import default_strategy_role_execution_settings


def test_asset_catalog_accepts_strategy_source_for_orchestration_templates(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    catalog = StrategyTemplateAssetCatalog(repository)

    created = catalog.create_orchestration(
        name="Strategy Source Inspect First",
        description="Creates through the Strategy Source mutation boundary.",
        strategy_source={"preset": "inspect_first"},
    )
    updated = catalog.update_orchestration(
        created["id"],
        name="Strategy Source Build First",
        description="Updates through the Strategy Source mutation boundary.",
        strategy_source={"preset": "build_first"},
    )

    assert created["workflow_json"]["preset"] == "inspect_first"
    assert created["strategy_source"] == created["workflow_json"]
    assert updated["workflow_json"]["preset"] == "build_first"
    assert updated["strategy_source"] == updated["workflow_json"]


def test_asset_catalog_resolves_builtin_orchestration_input_and_applies_role_overrides(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    catalog = StrategyTemplateAssetCatalog(repository)

    resolved = catalog.resolve_orchestration_input(
        orchestration_id="builtin:inspect_first",
        workflow=None,
        prompt_files=None,
        role_models={"builder": "gpt-5.4-mini"},
    )

    builder_role = next(role for role in resolved["workflow"]["roles"] if role["id"] == "builder")

    assert resolved["id"] == "builtin:inspect_first"
    assert resolved["name"] == "Inspect First"
    assert resolved["workflow"]["preset"] == "inspect_first"
    assert builder_role["model"] == "gpt-5.4-mini"
    assert "builder.md" in resolved["prompt_files"]


def test_asset_catalog_persists_role_execution_defaults_for_model_only_snapshots(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    catalog = StrategyTemplateAssetCatalog(repository)

    orchestration = catalog.create_orchestration(
        name="Model Override Workflow",
        description="Carries role-level model overrides.",
        workflow={
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md", "model": "gpt-5.4-mini"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
            ],
        },
    )

    builder_role = orchestration["workflow_json"]["roles"][0]
    defaults = default_strategy_role_execution_settings()

    assert builder_role["model"] == "gpt-5.4-mini"
    assert builder_role["executor_kind"] == defaults["executor_kind"]
    assert builder_role["executor_mode"] == defaults["executor_mode"]
    assert builder_role["command_cli"] == defaults["command_cli"]
    assert builder_role["reasoning_effort"] == defaults["reasoning_effort"]

# Merged from test_asset_catalog_role_definition_lifecycle.py

import pytest

from asset_catalog_test_support import asset_catalog, prompt_markdown


def test_asset_catalog_role_definition_crud_normalizes_archetypes_and_protects_builtins(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)

    created = catalog.create_role_definition(
        name="Legacy Generator",
        description="Uses the legacy alias on input.",
        archetype="generator",
        prompt_markdown=prompt_markdown("builder", "Keep changes scoped."),
        executor_kind="codex",
        model="gpt-5.4-mini",
    )

    assert created["archetype"] == "builder"
    assert created["prompt_ref"].endswith(".md")
    original_prompt_ref = created["prompt_ref"]

    updated = catalog.update_role_definition(
        created["id"],
        name="Legacy Generator v2",
        description="Updated description.",
        archetype="builder",
        prompt_markdown=prompt_markdown("builder", "Keep changes very scoped."),
        executor_kind="opencode",
        model="gpt-5.4",
        reasoning_effort="max",
    )
    assert updated["name"] == "Legacy Generator v2"
    assert updated["model"] == "gpt-5.4"
    assert updated["executor_kind"] == "opencode"
    assert updated["prompt_ref"] == original_prompt_ref

    with pytest.raises(ValueError, match="saved role definitions cannot change archetype"):
        catalog.update_role_definition(
            created["id"],
            name="Legacy Generator v3",
            description="Should fail.",
            archetype="inspector",
            prompt_markdown=prompt_markdown("inspector", "Inspect instead of building."),
            executor_kind="codex",
            model="",
        )

    with pytest.raises(ValueError, match="saved role definitions cannot change prompt_ref"):
        catalog.update_role_definition(
            created["id"],
            name="Legacy Generator v4",
            description="Should fail.",
            archetype="builder",
            prompt_ref="renamed-builder.md",
            prompt_markdown=prompt_markdown("builder", "Keep changes scoped."),
            executor_kind="codex",
            model="",
        )

    with pytest.raises(ValueError, match="built-in role definitions cannot be updated in place"):
        catalog.update_role_definition(
            "builtin:builder",
            name="Nope",
            description="",
            archetype="builder",
            prompt_markdown=prompt_markdown("builder", "Should fail."),
            model="",
        )

    deleted = catalog.delete_role_definition(created["id"])
    assert deleted == {"id": created["id"], "deleted": True}

# Merged from test_asset_catalog_role_definition_payload_guards.py




def test_asset_catalog_rejects_duplicate_role_definition_prompt_refs(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)

    with pytest.raises(ValueError, match=r"prompt_ref already in use: builder\.md"):
        catalog.create_role_definition(
            name="Custom Builder Alias",
            description="Should not shadow the built-in builder prompt ref.",
            archetype="builder",
            prompt_ref="builder.md",
            prompt_markdown=prompt_markdown("builder", "Use a custom builder prompt."),
            executor_kind="codex",
            model="gpt-5.4-mini",
        )

    created = catalog.create_role_definition(
        name="Release Builder",
        description="Ships focused release work.",
        archetype="builder",
        prompt_ref="release-builder.md",
        prompt_markdown=prompt_markdown("builder", "Focus on safe release work."),
        executor_kind="claude",
        model="gpt-5.4-mini",
    )

    with pytest.raises(ValueError, match=r"prompt_ref already in use: release-builder\.md"):
        catalog.create_role_definition(
            name="Another Release Builder",
            description="Should not reuse the same prompt ref.",
            archetype="builder",
            prompt_ref="release-builder.md",
            prompt_markdown=prompt_markdown("builder", "Use a different release strategy."),
            executor_kind="claude",
            model="gpt-5.4",
        )

    assert created["prompt_ref"] == "release-builder.md"


def test_asset_catalog_rejects_unsafe_role_definition_prompt_ref(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)

    with pytest.raises(ValueError, match="prompt_ref must be a safe relative path"):
        catalog.create_role_definition(
            name="Escaping Builder",
            description="Should not write outside the prompt asset root.",
            archetype="builder",
            prompt_ref="../escape.md",
            prompt_markdown=prompt_markdown("builder", "Keep prompt refs inside the asset root."),
            executor_kind="codex",
            model="gpt-5.4-mini",
        )


def test_asset_catalog_rejects_custom_executor_preset_mode(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)

    with pytest.raises(ValueError, match="only supports command mode"):
        catalog.create_role_definition(
            name="Custom Wrapper",
            description="Uses a wrapper command.",
            archetype="custom",
            prompt_ref="custom-wrapper.md",
            prompt_markdown=prompt_markdown("custom", "Observe and summarize."),
            executor_kind="custom",
            executor_mode="preset",
            command_cli="wrapper",
            command_args_text="--output\n{output_path}\n{prompt}\n",
        )

# Merged from test_asset_catalog_role_definition_snapshot_conflicts.py


from loopora.asset_catalog import AssetCatalogNotFoundError
from loopora.strategy_source import StrategySourceError

from asset_catalog_test_support import (
    create_role_definition,
    resolve_role_definition_workflow,
    workflow_for_role_definition,
)


def test_asset_catalog_rejects_unknown_role_definition_ids_in_workflow(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)

    with pytest.raises(AssetCatalogNotFoundError, match="unknown role definition: role_missing"):
        catalog.resolve_orchestration_input(
            orchestration_id=None,
            workflow=workflow_for_role_definition("role_missing"),
            prompt_files=None,
            role_models=None,
        )


def test_asset_catalog_rejects_conflicting_role_snapshot_fields_for_role_definition_id(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    role_definition = create_role_definition(
        catalog,
        executor_kind="claude",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )

    with pytest.raises(
        StrategySourceError,
        match=f"workflow role builder conflicts with role_definition_id {role_definition['id']} on model",
    ):
        resolve_role_definition_workflow(
            catalog,
            role_definition["id"],
            role_overrides={"model": "gpt-5.4"},
        )


def test_asset_catalog_rejects_conflicting_prompt_files_for_role_definition_id(tmp_path: Path) -> None:
    catalog = asset_catalog(tmp_path)
    role_definition = create_role_definition(
        catalog,
        executor_kind="claude",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )

    with pytest.raises(
        StrategySourceError,
        match=f"workflow role builder conflicts with role_definition_id {role_definition['id']} on prompt_markdown",
    ):
        resolve_role_definition_workflow(
            catalog,
            role_definition["id"],
            prompt_files={"release-builder.md": prompt_markdown("builder", "Focus on risky release work.")},
        )
