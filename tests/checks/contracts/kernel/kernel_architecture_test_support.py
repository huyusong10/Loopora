from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def loopora_source(relative_path: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / relative_path).read_text(encoding="utf-8")


def design_contracts_source() -> str:
    return (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
