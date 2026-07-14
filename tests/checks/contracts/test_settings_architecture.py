from __future__ import annotations

from pathlib import Path


def test_settings_facade_keeps_paths_and_recent_workdirs_in_dedicated_boundaries() -> None:
    root = Path(__file__).resolve().parents[3]
    settings_source = (root / "src/loopora/settings.py").read_text(encoding="utf-8")
    payloads_source = (root / "src/loopora/settings_payloads.py").read_text(encoding="utf-8")
    paths_source = (root / "src/loopora/settings_paths.py").read_text(encoding="utf-8")
    recent_source = (root / "src/loopora/settings_recent_workdirs.py").read_text(encoding="utf-8")
    types_source = (root / "src/loopora/settings_types.py").read_text(encoding="utf-8")
    design_source = (root / "design/contracts.md").read_text(encoding="utf-8")

    assert "from loopora.settings_payloads import normalize_settings_payload" in settings_source
    assert "from loopora.settings_paths import app_home as app_home" in settings_source
    assert "from loopora.settings_recent_workdirs import load_recent_workdirs as load_recent_workdirs" in settings_source
    assert "from loopora.settings_recent_workdirs import remember_recent_workdir as remember_recent_workdir" in settings_source
    assert "from loopora.settings_types import AppSettings as AppSettings" in settings_source
    assert "def normalize_settings_payload" in payloads_source
    assert "def app_home" in paths_source
    assert "def recent_workdirs_path" in paths_source
    assert "def load_recent_workdirs" in recent_source
    assert "def remember_recent_workdir" in recent_source
    assert "def save_recent_workdirs" in recent_source
    assert "class AppSettings" in types_source
    assert "def _normalize_recent_workdirs" not in settings_source
    assert "def _coerce_setting_number" not in settings_source
    assert "settings_recent_workdirs.py" in design_source
    assert "settings_payloads.py" in design_source
