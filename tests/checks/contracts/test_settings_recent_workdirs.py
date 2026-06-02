from __future__ import annotations

from pathlib import Path

from loopora.settings import app_home, load_recent_workdirs, save_recent_workdirs
from settings_contract_test_support import use_loopora_home


def test_recent_workdirs_round_trip_filters_duplicates_and_limits(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)

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
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "recent_workdirs.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{not json}\n", encoding="utf-8")

    assert load_recent_workdirs() == []


def test_recent_workdirs_ignores_non_utf8_saved_payload(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "recent_workdirs.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(b"\xff")

    assert load_recent_workdirs() == []


def test_recent_workdirs_ignore_non_string_entries_but_keep_valid_paths(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
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
    use_loopora_home(monkeypatch, tmp_path)

    def explode(*_args, **_kwargs):
        raise PermissionError("blocked")

    monkeypatch.setattr(Path, "write_text", explode)

    save_recent_workdirs(["/tmp/alpha"])
