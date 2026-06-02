from __future__ import annotations

from pathlib import Path

from loopora.asset_catalog import StrategyTemplateAssetCatalog
from loopora.db import LooporaRepository


def test_asset_catalog_lists_builtin_and_custom_assets_with_stable_flags(tmp_path: Path) -> None:
    catalog, role_definition, orchestration = _catalog_with_custom_assets(tmp_path)

    role_definitions = catalog.list_role_definitions()
    orchestrations = catalog.list_orchestrations()
    builtin_orchestrations = [item for item in orchestrations if item["source"] == "builtin"]

    _assert_role_catalog_flags(
        builtin_role=_item_by_id(role_definitions, "builtin:builder"),
        custom_role=_item_by_id(role_definitions, role_definition["id"]),
    )
    _assert_orchestration_catalog_flags(
        builtin_orchestration=_item_by_id(orchestrations, "builtin:quality_gate"),
        custom_orchestration=_item_by_id(orchestrations, orchestration["id"]),
    )
    _assert_builtin_practice_assets(builtin_orchestrations)
    _assert_hidden_legacy_orchestrations_remain_addressable(catalog)


def _catalog_with_custom_assets(tmp_path: Path) -> tuple[StrategyTemplateAssetCatalog, dict, dict]:
    repository = LooporaRepository(tmp_path / "app.db")
    catalog = StrategyTemplateAssetCatalog(repository)
    role_definition = catalog.create_role_definition(
        name="Release Builder",
        description="Ships focused release work.",
        archetype="builder",
        prompt_ref="release-builder.md",
        prompt_markdown=_prompt_markdown("builder", "Focus on release work."),
        executor_kind="claude",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )
    orchestration = catalog.create_orchestration(
        name="Custom Inspect First",
        description="Inspector before Builder.",
        workflow={"preset": "inspect_first"},
    )
    return catalog, role_definition, orchestration


def _item_by_id(items: list[dict], item_id: str) -> dict:
    return next(item for item in items if item["id"] == item_id)


def _assert_role_catalog_flags(builtin_role: dict, custom_role: dict) -> None:
    assert builtin_role["source"] == "builtin"
    assert builtin_role["editable"] is False
    assert builtin_role["deletable"] is False
    assert custom_role["source"] == "custom"
    assert custom_role["editable"] is True
    assert custom_role["deletable"] is True
    assert custom_role["executor_kind"] == "claude"


def _assert_orchestration_catalog_flags(
    builtin_orchestration: dict,
    custom_orchestration: dict,
) -> None:
    assert builtin_orchestration["source"] == "builtin"
    assert builtin_orchestration["strategy_source"] == builtin_orchestration["workflow_json"]
    assert builtin_orchestration["workflow_json"]["preset"] == "quality_gate"
    assert builtin_orchestration["workflow_json"]["steps"][0]["inherit_session"] is True
    assert builtin_orchestration["workflow_json"]["steps"][1]["inherit_session"] is False
    assert builtin_orchestration["workflow_json"]["steps"][0]["extra_cli_args"] == ""
    assert builtin_orchestration["parallel_groups"] == []
    assert builtin_orchestration["parallel_group_count"] == 0
    assert builtin_orchestration["scenario_zh"]
    assert builtin_orchestration["scenario_en"]

    assert custom_orchestration["source"] == "custom"
    assert custom_orchestration["strategy_source"] == custom_orchestration["workflow_json"]
    assert custom_orchestration["workflow_json"]["preset"] == "inspect_first"
    assert custom_orchestration["parallel_groups"] == []
    assert custom_orchestration["parallel_group_count"] == 0
    assert isinstance(custom_orchestration["workflow_warnings"], list)


def _assert_builtin_practice_assets(builtin_orchestrations: list[dict]) -> None:
    zh_sections = (
        "## 场景",
        "## 需求",
        "## 适合这个流程，因为",
        "## 示例 spec",
        "# Task",
        "# Role Notes",
        "Builder Notes",
        "GateKeeper Notes",
    )
    en_sections = (
        "## Scenario",
        "## Request",
        "## Why this workflow fits",
        "## Example spec",
        "# Task",
        "# Role Notes",
        "Builder Notes",
        "GateKeeper Notes",
    )
    for item in builtin_orchestrations:
        assert item["spec_practice_summary_zh"].startswith("场景：")
        assert item["spec_practice_summary_en"].startswith("Scenario:")
        assert all(section in item["spec_practice_markdown_zh"] for section in zh_sections)
        assert all(section in item["spec_practice_markdown_en"] for section in en_sections)
    assert {item["id"] for item in builtin_orchestrations} == {
        "builtin:benchmark_gate",
        "builtin:evidence_first",
        "builtin:quality_gate",
    }


def _assert_hidden_legacy_orchestrations_remain_addressable(catalog: StrategyTemplateAssetCatalog) -> None:
    expectations = {
        "builtin:fast_lane": ("Fast Lane", "fast_lane"),
        "builtin:build_then_parallel_review": ("Build + Parallel Review", "build_then_parallel_review"),
        "builtin:build_first": ("Build First", "build_first"),
        "builtin:repair_loop": ("Repair Loop", "repair_loop"),
    }
    for orchestration_id, (name, preset) in expectations.items():
        orchestration = catalog.get_orchestration(orchestration_id)
        assert orchestration["name"] == name
        assert orchestration["strategy_source"] == orchestration["workflow_json"]
        assert orchestration["workflow_json"]["preset"] == preset


def _prompt_markdown(archetype: str, body: str) -> str:
    return f"""---
version: 1
archetype: {archetype}
---

{body}
"""
