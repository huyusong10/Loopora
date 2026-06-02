from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from loopora.settings import AppSettings


def use_loopora_home(monkeypatch, tmp_path: Path) -> Path:
    home = tmp_path / "loopora-home"
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    return home


def settings_json_text(settings: AppSettings | None = None) -> str:
    return json.dumps(asdict(settings or AppSettings()), ensure_ascii=False, indent=2) + "\n"
