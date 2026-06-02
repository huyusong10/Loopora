from __future__ import annotations

import tomllib
from pathlib import Path


def test_alignment_guidance_is_packaged_without_skill_assets() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["loopora"]
    assert "assets/alignment/*.md" in package_data
    assert not any(str(item).startswith("skills/assets") for item in package_data)
