from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def loopora_source(*parts: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / Path(*parts)).read_text(encoding="utf-8")


def design_contracts_source() -> str:
    return (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")


def assert_markers_present(source: str, *markers: str) -> None:
    assert all(marker in source for marker in markers)


def assert_markers_owned_by(owner_source: str, excluded_sources: list[str], *markers: str) -> None:
    for marker in markers:
        assert marker in owner_source
        assert all(marker not in source for source in excluded_sources)


def assert_design_mentions(design_source: str, *filenames: str) -> None:
    assert_markers_present(design_source, *filenames)
