from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from loopora.settings import AppSettings, app_home, load_settings, save_settings


def use_loopora_home(monkeypatch, tmp_path: Path) -> Path:
    home = tmp_path / "loopora-home"
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    return home


def settings_json_text(settings: AppSettings | None = None) -> str:
    return json.dumps(asdict(settings or AppSettings()), ensure_ascii=False, indent=2) + "\n"


def test_load_settings_resets_invalid_json_to_defaults(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    storage_path.write_text("{not json}\n", encoding="utf-8")

    settings = load_settings()

    assert settings == AppSettings()
    assert storage_path.read_text(encoding="utf-8") == settings_json_text()


def test_read_only_settings_load_keeps_invalid_storage_unchanged(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    invalid_storage = b"{not json}\n"
    storage_path.write_bytes(invalid_storage)

    assert load_settings(read_only=True) == AppSettings()
    assert storage_path.read_bytes() == invalid_storage


def test_load_settings_resets_non_utf8_payload_to_defaults(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    storage_path.write_bytes(b"\xff")

    settings = load_settings()

    assert settings == AppSettings()
    assert storage_path.read_text(encoding="utf-8") == settings_json_text()


def test_load_settings_coerces_valid_numbers_and_drops_unknown_fields(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    storage_path.write_text(
        (
            "{\n"
            '  "max_concurrent_runs": "4",\n'
            '  "polling_interval_seconds": "0.25",\n'
            '  "stop_grace_period_seconds": -1,\n'
            '  "role_idle_timeout_seconds": true,\n'
            '  "unknown_field": "ignored"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    settings = load_settings()
    expected = AppSettings(
        max_concurrent_runs=4,
        polling_interval_seconds=0.25,
        stop_grace_period_seconds=2.0,
        role_idle_timeout_seconds=300.0,
    )

    assert settings == expected
    assert storage_path.read_text(encoding="utf-8") == settings_json_text(expected)


def test_load_settings_rejects_non_finite_numeric_values(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    storage_path.write_text(
        (
            "{\n"
            '  "max_concurrent_runs": Infinity,\n'
            '  "polling_interval_seconds": "nan",\n'
            '  "stop_grace_period_seconds": "inf",\n'
            '  "role_idle_timeout_seconds": "-inf"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings == AppSettings()
    assert storage_path.read_text(encoding="utf-8") == settings_json_text()


def test_load_settings_rejects_fractional_integer_values(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    storage_path.write_text(
        (
            "{\n"
            '  "max_concurrent_runs": 3.5,\n'
            '  "polling_interval_seconds": 0.25,\n'
            '  "stop_grace_period_seconds": 1.0,\n'
            '  "role_idle_timeout_seconds": 120.0\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    settings = load_settings()
    expected = AppSettings(
        max_concurrent_runs=2,
        polling_interval_seconds=0.25,
        stop_grace_period_seconds=1.0,
        role_idle_timeout_seconds=120.0,
    )

    assert settings == expected
    assert storage_path.read_text(encoding="utf-8") == settings_json_text(expected)


def test_load_settings_keeps_running_when_default_writeback_fails(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)

    def explode(*_args, **_kwargs):
        raise PermissionError("blocked")

    monkeypatch.setattr(Path, "write_text", explode)

    assert load_settings() == AppSettings()


def test_save_settings_preserves_existing_file_when_replacement_fails(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    original_text = settings_json_text(AppSettings(max_concurrent_runs=3))
    storage_path.write_text(original_text, encoding="utf-8")
    private_path = tmp_path / "private" / "settings.json"
    original_replace = Path.replace

    def fail_settings_replace(path: Path, target: Path) -> Path:
        if Path(target) == storage_path:
            raise PermissionError(f"permission denied: {private_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_settings_replace)

    with pytest.raises(PermissionError):
        save_settings(AppSettings(max_concurrent_runs=7))

    assert storage_path.read_text(encoding="utf-8") == original_text
    assert list(storage_path.parent.glob(".settings.json.tmp.*")) == []
