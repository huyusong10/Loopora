from __future__ import annotations

import re
from pathlib import Path

from cli_first_use_docs_test_support import (
    assert_alignment_language_assets,
    assert_documented_cli_entries_available,
    assert_public_anchor_default_language,
    assert_readme_entry_points,
)


def test_readme_first_use_commands_match_cli_entries() -> None:
    root = Path(__file__).resolve().parents[3]
    english_readme = (root / "README.md").read_text(encoding="utf-8")
    chinese_readme = (root / "README.zh-CN.md").read_text(encoding="utf-8")
    readmes = [english_readme, chinese_readme]
    human_shaped_loop_docs = [
        (root / "HUMAN-SHAPED-LOOP.md").read_text(encoding="utf-8"),
        (root / "HUMAN-SHAPED-LOOP.zh-CN.md").read_text(encoding="utf-8"),
    ]
    design_docs = {
        "readme": (root / "design" / "README.md").read_text(encoding="utf-8"),
        "contracts": (root / "design" / "contracts.md").read_text(encoding="utf-8"),
    }
    governance_scenario = (root / "tests" / "scenarios" / "long_running_governance_loop.md").read_text(
        encoding="utf-8"
    )
    documented_adapters = [set(re.findall(r"\bloopora init ([a-z]+)\b", readme)) for readme in readmes]

    assert_readme_entry_points(readmes, documented_adapters)
    assert_public_anchor_default_language(english_readme, chinese_readme, human_shaped_loop_docs)
    assert_alignment_language_assets(design_docs, governance_scenario)
    assert_documented_cli_entries_available(documented_adapters)
