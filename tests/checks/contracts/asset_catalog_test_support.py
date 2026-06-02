from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.asset_catalog import StrategyTemplateAssetCatalog
from loopora.db import LooporaRepository


def asset_catalog(tmp_path: Path) -> StrategyTemplateAssetCatalog:
    return StrategyTemplateAssetCatalog(LooporaRepository(tmp_path / "app.db"))


def create_role_definition(
    catalog: StrategyTemplateAssetCatalog,
    **overrides: Any,
) -> dict:
    options = dict(overrides)
    body = options.pop("body", "Focus on safe release work.")
    archetype = options.get("archetype", "builder")
    payload = {
        "name": "Release Builder",
        "description": "Ships focused release work.",
        "archetype": archetype,
        "prompt_ref": "release-builder.md",
        "prompt_markdown": prompt_markdown(archetype, body),
    }
    payload.update(options)
    return catalog.create_role_definition(**payload)


def resolve_role_definition_workflow(
    catalog: StrategyTemplateAssetCatalog,
    role_definition_id: str,
    *,
    role_id: str = "builder",
    role_overrides: dict[str, Any] | None = None,
    prompt_files: dict[str, str] | None = None,
) -> dict:
    return catalog.resolve_orchestration_input(
        orchestration_id=None,
        workflow=workflow_for_role_definition(
            role_definition_id,
            role_id=role_id,
            role_overrides=role_overrides,
        ),
        prompt_files=prompt_files,
        role_models=None,
    )


def workflow_for_role_definition(
    role_definition_id: str,
    *,
    role_id: str = "builder",
    role_overrides: dict[str, Any] | None = None,
) -> dict:
    role = {"id": role_id, "role_definition_id": role_definition_id}
    role.update(role_overrides or {})
    return {
        "version": 1,
        "roles": [role],
        "steps": [{"id": f"{role_id}_step", "role_id": role_id}],
    }


def prompt_markdown(archetype: str, body: str) -> str:
    return f"""---
version: 1
archetype: {archetype}
---

{body}
"""
