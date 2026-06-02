from __future__ import annotations

from pathlib import Path

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import load_alignment_guidance_assets


def test_alignment_system_prompt_text_lives_in_markdown_assets() -> None:
    service_source = (Path(__file__).resolve().parents[3] / "src" / "loopora" / "service_alignment.py").read_text(encoding="utf-8")
    for snippet in (
        "You are Loopora's built-in Web Loop alignment agent.",
        "Important output discipline:",
        "Current compiler gate: confirmed agreement.",
        "The previous bundle failed Loopora's hard validator.",
        "Selected Loopora Source Context",
        "Bundle Improvement Context",
    ):
        assert snippet not in service_source

    assets = load_alignment_guidance_assets()
    assert_contains_all(
        "\n".join(
            (
                assets.system_prompt_template,
                assets.compiler_gates,
                assets.repair_input_template,
                assets.current_bundle_template,
                assets.selected_source_context_template,
                assets.bundle_improvement_context_template,
            )
        ),
        (
            "You are Loopora's built-in Web Loop alignment agent.",
            "Important output discipline:",
            "Current compiler gate: confirmed agreement.",
            "The previous bundle failed Loopora's hard validator.",
            "Selected Loopora Source Context",
            "Bundle Improvement Context",
        ),
    )
