from __future__ import annotations

from pathlib import Path

from loopora.settings import app_home, load_recent_workdirs, remember_recent_workdir, save_recent_workdirs
from runner_helpers import _create_loop


def use_loopora_home(monkeypatch, tmp_path: Path) -> Path:
    home = tmp_path / "loopora-home"
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    return home


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


def test_recent_workdirs_save_normalizes_relative_entries_to_reusable_identity(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)

    save_recent_workdirs([" project "])

    assert load_recent_workdirs() == [str((tmp_path / "project").resolve(strict=False))]


def test_recent_workdirs_load_drops_legacy_relative_entries(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "recent_workdirs.json"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text('[ ".", "project", "/tmp/alpha" ]\n', encoding="utf-8")

    assert load_recent_workdirs() == ["/tmp/alpha"]


def test_recent_workdirs_remember_promotes_target_and_preserves_existing(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    save_recent_workdirs(["/tmp/beta", "/tmp/alpha"])

    remember_recent_workdir(" /tmp/alpha ")
    assert load_recent_workdirs() == ["/tmp/alpha", "/tmp/beta"]

    remember_recent_workdir("/tmp/gamma", limit=2)
    assert load_recent_workdirs() == ["/tmp/gamma", "/tmp/alpha"]


def test_recent_workdirs_loop_refresh_preserves_non_loop_targets(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    adapter_target = tmp_path / "adapter-only"
    loop_target = tmp_path / "loop-target"
    adapter_target.mkdir()
    loop_target.mkdir()
    remember_recent_workdir(adapter_target)

    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, loop_target, name="Recent Workdir Loop")

    assert load_recent_workdirs()[:2] == [str(loop_target.resolve()), str(adapter_target)]

    service.delete_loop(loop["id"])
    assert str(adapter_target) in load_recent_workdirs()


def test_recent_workdirs_alignment_context_is_read_only_but_session_creation_is_remembered(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    service.get_alignment_workdir_context(sample_workdir)
    assert load_recent_workdirs() == []

    service.create_alignment_session(workdir=sample_workdir, message="", start_immediately=False)
    assert load_recent_workdirs() == [str(sample_workdir.resolve())]


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


def test_recent_workdirs_save_failure_preserves_existing_entries(monkeypatch, tmp_path: Path) -> None:
    use_loopora_home(monkeypatch, tmp_path)
    storage_path = app_home() / "recent_workdirs.json"
    save_recent_workdirs(["/tmp/original"])
    original_text = storage_path.read_text(encoding="utf-8")
    private_path = tmp_path / "private" / "recent_workdirs.json"
    original_replace = Path.replace

    def fail_recent_replace(path: Path, target: Path) -> Path:
        if Path(target) == storage_path:
            raise PermissionError(f"permission denied: {private_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_recent_replace)

    save_recent_workdirs(["/tmp/new"])

    assert storage_path.read_text(encoding="utf-8") == original_text
    assert load_recent_workdirs() == ["/tmp/original"]
    assert list(storage_path.parent.glob(".recent_workdirs.json.tmp.*")) == []
