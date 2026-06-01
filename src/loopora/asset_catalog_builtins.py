from __future__ import annotations

from loopora.strategy_source import (
    STRATEGY_SOURCE_ARCHETYPES,
    build_preset_strategy_source,
    builtin_strategy_prompt_markdown,
    default_strategy_role_execution_settings,
    resolve_strategy_prompt_files,
    strategy_archetype_display_name,
    strategy_source_preset_copy,
    strategy_source_preset_names,
    strategy_source_warnings,
)


def build_builtin_orchestration_records() -> list[dict]:
    records = []
    for preset_name in strategy_source_preset_names(include_hidden=True):
        strategy_source = build_preset_strategy_source(preset_name)
        prompt_files = resolve_strategy_prompt_files(strategy_source)
        copy = strategy_source_preset_copy(preset_name)
        parallel_groups = strategy_parallel_groups(strategy_source)
        records.append(
            {
                "id": f"builtin:{preset_name}",
                "name": copy["label_en"],
                "description": copy["description_en"],
                "description_zh": copy["description_zh"],
                "description_en": copy["description_en"],
                "scenario_zh": copy["scenario_zh"],
                "scenario_en": copy["scenario_en"],
                "choice_zh": copy["choice_zh"],
                "choice_en": copy["choice_en"],
                "decision_zh": copy["decision_zh"],
                "decision_en": copy["decision_en"],
                "spec_practice_summary_zh": copy["spec_practice_summary_zh"],
                "spec_practice_summary_en": copy["spec_practice_summary_en"],
                "spec_practice_markdown_zh": copy["spec_practice_markdown_zh"],
                "spec_practice_markdown_en": copy["spec_practice_markdown_en"],
                "visible": copy["visible"] == "true",
                "source": "builtin",
                "preset": preset_name,
                "editable": False,
                "deletable": False,
                "strategy_source": strategy_source,
                "workflow_json": strategy_source,
                "parallel_groups": parallel_groups,
                "parallel_group_count": len(parallel_groups),
                "prompt_files_json": prompt_files,
                "workflow_warnings": strategy_source_warnings(strategy_source),
            }
        )
    return records


def build_builtin_role_definition_records() -> list[dict]:
    descriptions = {
        "builder": "Edits the workspace and pushes implementation forward.",
        "inspector": "Collects evidence, checks, and benchmark results.",
        "gatekeeper": "Decides whether the evidence is strong enough to pass.",
        "guide": "Suggests the next direction when progress stalls.",
        "custom": "A low-permission custom support role that can read, analyze, and recommend, but cannot close the run.",
    }
    records = []
    for archetype in STRATEGY_SOURCE_ARCHETYPES:
        prompt_ref = {
            "gatekeeper": "gatekeeper.md",
        }.get(archetype, f"{archetype}.md")
        default_name = strategy_archetype_display_name(archetype, locale="en")
        if archetype == "custom":
            default_name = "Custom (Restricted)"
        records.append(
            {
                "id": f"builtin:{archetype}",
                "name": default_name,
                "description": descriptions.get(archetype, ""),
                "archetype": archetype,
                "prompt_ref": prompt_ref,
                "prompt_markdown": builtin_strategy_prompt_markdown(prompt_ref),
                "posture_notes": "",
                **default_strategy_role_execution_settings(),
                "source": "builtin",
                "editable": False,
                "deletable": False,
            }
        )
    return records


def strategy_parallel_groups(strategy_source: dict | None) -> list[str]:
    if not isinstance(strategy_source, dict):
        return []
    counts: dict[str, int] = {}
    for step in list(strategy_source.get("steps") or []):
        if not isinstance(step, dict):
            continue
        group = str(step.get("parallel_group") or "").strip()
        if group:
            counts[group] = counts.get(group, 0) + 1
    return [group for group, count in counts.items() if count >= 2]
