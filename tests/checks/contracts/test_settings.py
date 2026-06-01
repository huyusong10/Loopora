from __future__ import annotations

from pathlib import Path

from loopora.settings import AppSettings, app_home, load_recent_workdirs, load_settings, save_recent_workdirs


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
    assert "from loopora.settings_types import AppSettings as AppSettings" in settings_source
    assert "def normalize_settings_payload" in payloads_source
    assert "def app_home" in paths_source
    assert "def recent_workdirs_path" in paths_source
    assert "def load_recent_workdirs" in recent_source
    assert "def save_recent_workdirs" in recent_source
    assert "class AppSettings" in types_source
    assert "def _normalize_recent_workdirs" not in settings_source
    assert "def _coerce_setting_number" not in settings_source
    assert "settings_recent_workdirs.py" in design_source
    assert "settings_payloads.py" in design_source


def test_app_home_uses_loopora_home_override(monkeypatch, tmp_path: Path) -> None:
    custom_home = tmp_path / "custom-home"
    monkeypatch.setenv("LOOPORA_HOME", str(custom_home))

    assert app_home() == custom_home
    assert custom_home.is_dir()

def test_recent_workdirs_round_trip_filters_duplicates_and_limits(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))

    save_recent_workdirs(
        [
            "",
            " /tmp/alpha ",
            "/tmp/beta",
            "/tmp/alpha",
            "/tmp/gamma",
        ],
        limit=2,
    )

    assert load_recent_workdirs() == ["/tmp/alpha", "/tmp/beta"]


def test_recent_workdirs_ignores_invalid_saved_payload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
    storage_path = app_home() / "recent_workdirs.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{not json}\n", encoding="utf-8")

    assert load_recent_workdirs() == []


def test_recent_workdirs_ignores_non_utf8_saved_payload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
    storage_path = app_home() / "recent_workdirs.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(b"\xff")

    assert load_recent_workdirs() == []


def test_recent_workdirs_ignore_non_string_entries_but_keep_valid_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
    storage_path = app_home() / "recent_workdirs.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(
        (
            "[\n"
            '  " /tmp/alpha ",\n'
            "  null,\n"
            "  42,\n"
            "  true,\n"
            "  {},\n"
            '  "/tmp/beta"\n'
            "]\n"
        ),
        encoding="utf-8",
    )

    assert load_recent_workdirs() == ["/tmp/alpha", "/tmp/beta"]


def test_recent_workdirs_save_is_best_effort_on_write_errors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))

    def explode(*_args, **_kwargs):
        raise PermissionError("blocked")

    monkeypatch.setattr(Path, "write_text", explode)

    save_recent_workdirs(["/tmp/alpha"])


def test_load_settings_resets_invalid_json_to_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
    storage_path = app_home() / "settings.json"
    storage_path.write_text("{not json}\n", encoding="utf-8")

    settings = load_settings()

    assert settings == AppSettings()
    assert storage_path.read_text(encoding="utf-8") == (
        "{\n"
        '  "max_concurrent_runs": 2,\n'
        '  "polling_interval_seconds": 0.5,\n'
        '  "stop_grace_period_seconds": 2.0,\n'
        '  "role_idle_timeout_seconds": 300.0\n'
        "}\n"
    )


def test_load_settings_resets_non_utf8_payload_to_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
    storage_path = app_home() / "settings.json"
    storage_path.write_bytes(b"\xff")

    settings = load_settings()

    assert settings == AppSettings()
    assert storage_path.read_text(encoding="utf-8") == (
        "{\n"
        '  "max_concurrent_runs": 2,\n'
        '  "polling_interval_seconds": 0.5,\n'
        '  "stop_grace_period_seconds": 2.0,\n'
        '  "role_idle_timeout_seconds": 300.0\n'
        "}\n"
    )


def test_load_settings_coerces_valid_numbers_and_drops_unknown_fields(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
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

    assert settings == AppSettings(
        max_concurrent_runs=4,
        polling_interval_seconds=0.25,
        stop_grace_period_seconds=2.0,
        role_idle_timeout_seconds=300.0,
    )
    assert storage_path.read_text(encoding="utf-8") == (
        "{\n"
        '  "max_concurrent_runs": 4,\n'
        '  "polling_interval_seconds": 0.25,\n'
        '  "stop_grace_period_seconds": 2.0,\n'
        '  "role_idle_timeout_seconds": 300.0\n'
        "}\n"
    )


def test_load_settings_rejects_non_finite_numeric_values(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
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
    assert storage_path.read_text(encoding="utf-8") == (
        "{\n"
        '  "max_concurrent_runs": 2,\n'
        '  "polling_interval_seconds": 0.5,\n'
        '  "stop_grace_period_seconds": 2.0,\n'
        '  "role_idle_timeout_seconds": 300.0\n'
        "}\n"
    )


def test_load_settings_rejects_fractional_integer_values(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))
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

    assert settings == AppSettings(
        max_concurrent_runs=2,
        polling_interval_seconds=0.25,
        stop_grace_period_seconds=1.0,
        role_idle_timeout_seconds=120.0,
    )
    assert storage_path.read_text(encoding="utf-8") == (
        "{\n"
        '  "max_concurrent_runs": 2,\n'
        '  "polling_interval_seconds": 0.25,\n'
        '  "stop_grace_period_seconds": 1.0,\n'
        '  "role_idle_timeout_seconds": 120.0\n'
        "}\n"
    )


def test_load_settings_keeps_running_when_default_writeback_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "loopora-home"))

    def explode(*_args, **_kwargs):
        raise PermissionError("blocked")

    monkeypatch.setattr(Path, "write_text", explode)

    assert load_settings() == AppSettings()
