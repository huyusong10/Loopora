from __future__ import annotations

from pathlib import Path

from loopora.settings import app_home
from loopora.branding import APP_STATE_DIRNAME, state_dir_for_workdir


def test_app_home_uses_loopora_home_override(monkeypatch, tmp_path: Path) -> None:
    custom_home = tmp_path / "custom-home"
    monkeypatch.setenv("LOOPORA_HOME", str(custom_home))

    assert app_home() == custom_home
    assert custom_home.is_dir()


def test_app_home_normalizes_relative_loopora_home_for_reusable_identity(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOOPORA_HOME", "relative home")

    resolved_home = tmp_path / "relative home"

    assert app_home() == resolved_home
    assert resolved_home.is_dir()


def test_state_dir_for_workdir_uses_resolved_project_directory(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(tmp_path)

    assert state_dir_for_workdir("project") == project / APP_STATE_DIRNAME
