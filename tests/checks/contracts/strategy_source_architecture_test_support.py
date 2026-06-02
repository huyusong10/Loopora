from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOOPORA_SRC = REPO_ROOT / "src" / "loopora"


def loopora_path(*parts: str) -> Path:
    return LOOPORA_SRC / Path(*parts)


def loopora_source(*parts: str) -> str:
    return loopora_path(*parts).read_text(encoding="utf-8")


def loopora_sources(*source_names: str) -> dict[str, str]:
    return {source_name: loopora_source(source_name) for source_name in source_names}


def assert_contains(source: str, *markers: str) -> None:
    for marker in markers:
        assert marker in source


def assert_contains_all(sources: list[str], marker: str) -> None:
    for source in sources:
        assert marker in source


def assert_excludes(source: str, *markers: str) -> None:
    for marker in markers:
        assert marker not in source


def assert_excludes_all(sources: list[str], marker: str) -> None:
    for source in sources:
        assert marker not in source
