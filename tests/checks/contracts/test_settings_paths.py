from __future__ import annotations

from pathlib import Path

from loopora.settings import app_home


def test_app_home_uses_loopora_home_override(monkeypatch, tmp_path: Path) -> None:
    custom_home = tmp_path / "custom-home"
    monkeypatch.setenv("LOOPORA_HOME", str(custom_home))

    assert app_home() == custom_home
    assert custom_home.is_dir()
