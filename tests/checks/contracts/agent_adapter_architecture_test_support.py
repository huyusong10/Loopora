from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def loopora_source(module_name: str) -> str:
    filename = module_name if module_name.endswith(".py") else f"{module_name}.py"
    return (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")


def design_contracts_source() -> str:
    return design_boundary_source()


def assert_markers_present(source: str, markers: tuple[str, ...]) -> None:
    for marker in markers:
        assert marker in source


def assert_markers_absent(source: str, markers: tuple[str, ...]) -> None:
    for marker in markers:
        assert marker not in source


def assert_design_mentions(*filenames: str) -> None:
    design_source = design_contracts_source()
    for filename in filenames:
        assert filename in design_source
