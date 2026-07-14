from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DESIGN_BOUNDARY_FILES = ("contracts.md", "domain-workflow-contracts.md", "service-boundaries.md")


def loopora_source(relative_path: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / relative_path).read_text(encoding="utf-8")


def design_contracts_source() -> str:
    return "\n\n".join(
        (REPO_ROOT / "design" / filename).read_text(encoding="utf-8")
        for filename in DESIGN_BOUNDARY_FILES
    )
