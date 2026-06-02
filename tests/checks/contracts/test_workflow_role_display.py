from __future__ import annotations

from loopora.workflows import display_name_for_archetype, normalize_workflow


def test_archetype_display_names_localize_web_labels_without_changing_contract_values() -> None:
    assert display_name_for_archetype("builder", locale="en") == "Builder"
    assert display_name_for_archetype("builder", locale="zh") == "构建者"
    assert display_name_for_archetype("inspector", locale="zh") == "巡检者"
    assert display_name_for_archetype("gatekeeper", locale="zh") == "守门者"
    assert display_name_for_archetype("guide", locale="zh") == "引导者"
    assert display_name_for_archetype("custom", locale="zh") == "自定义角色"

    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [{"id": "builder", "name": "构建者", "archetype": "builder", "prompt_ref": "builder.md"}],
            "steps": [{"id": "builder_step", "role_id": "builder"}],
        }
    )
    assert workflow["roles"][0]["archetype"] == "builder"
    assert workflow["roles"][0]["name"] == "Builder"
