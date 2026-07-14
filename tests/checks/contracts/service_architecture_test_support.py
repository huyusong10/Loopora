from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_PRIVATE_IMPORT_ALLOWLIST: set[tuple[str, str, str]] = set()


def design_contracts_source() -> str:
    return design_boundary_source()


def loopora_source(*parts: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / Path(*parts)).read_text(encoding="utf-8")


def assert_markers_present(source: str, *markers: str) -> None:
    assert all(marker in source for marker in markers)


def assert_markers_absent(source: str, *markers: str) -> None:
    assert all(marker not in source for marker in markers)


def assert_design_mentions(*filenames: str) -> None:
    assert_markers_present(design_contracts_source(), *filenames)
