from __future__ import annotations

from pathlib import Path

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import alignment_system_prompt_asset_ref, load_alignment_guidance_assets
from loopora.system_prompt_assets import SYSTEM_PROMPT_ASSET_DIR


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "src" / "loopora"
ALIGNMENT_ASSET_ROOT = SOURCE_ROOT / "assets" / "alignment"
ALIGNMENT_SYSTEM_PROMPT_PATH = SYSTEM_PROMPT_ASSET_DIR / alignment_system_prompt_asset_ref()


def test_alignment_system_prompt_text_lives_in_markdown_assets() -> None:
    service_source = (SOURCE_ROOT / "service_alignment.py").read_text(encoding="utf-8")
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
    assert ALIGNMENT_SYSTEM_PROMPT_PATH.is_file()
    assert not (ALIGNMENT_ASSET_ROOT / "system-prompt.md").exists()
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


def test_alignment_guidance_asset_long_lines_do_not_reappear_in_python_source() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(SOURCE_ROOT.rglob("*.py")))
    conflicts: list[str] = []
    for path in sorted(ALIGNMENT_ASSET_ROOT.rglob("*.md")):
        asset_ref = path.relative_to(ALIGNMENT_ASSET_ROOT)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            text = line.strip()
            if len(text) < 100 or "{{" in text or text.startswith(("---", "|")):
                continue
            if text in source:
                conflicts.append(f"{asset_ref}:{line_number}")

    assert conflicts == []
