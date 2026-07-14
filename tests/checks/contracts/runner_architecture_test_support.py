from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def loopora_source(*parts: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / Path(*parts)).read_text(encoding="utf-8")


def loopora_path(*parts: str) -> Path:
    return REPO_ROOT / "src" / "loopora" / Path(*parts)


def design_contracts_source() -> str:
    return design_boundary_source()
