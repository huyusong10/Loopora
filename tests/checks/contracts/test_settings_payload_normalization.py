from __future__ import annotations

from pathlib import Path

from loopora.settings import AppSettings, app_home, load_settings
from settings_contract_test_support import settings_json_text, use_loopora_home


def test_load_settings_resets_invalid_json_to_defaults(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "settings.json"
    storage_path.write_text("{not json}\n", encoding="utf-8")

    settings = load_settings()

    assert settings == AppSettings()
    assert storage_path.read_text(encoding="utf-8") == settings_json_text()


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
