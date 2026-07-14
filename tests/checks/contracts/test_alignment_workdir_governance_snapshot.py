from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_workdir_snapshot import (
    alignment_workdir_snapshot,
    alignment_workdir_snapshot_has_governance_markers,
)


def test_alignment_workdir_snapshot_detects_applicable_parent_agents_file(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workdir = project / "packages" / "app"
    workdir.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")

    snapshot = alignment_workdir_snapshot(workdir)

    assert "AGENTS.md exists: no" in snapshot
    assert "Applicable AGENTS.md exists: yes" in snapshot
    assert "Applicable AGENTS.md paths: ../../AGENTS.md" in snapshot
    assert alignment_workdir_snapshot_has_governance_markers(snapshot)


def test_alignment_workdir_snapshot_redacts_low_level_read_errors(tmp_path: Path, monkeypatch) -> None:
    workdir = tmp_path / "project"
    local_path = tmp_path / "private" / "project"
    workdir.mkdir()
    resolved_workdir = workdir.resolve()
    original_iterdir = Path.iterdir

    def fail_iterdir(path: Path):
        if path == resolved_workdir:
            raise OSError(f"permission denied: {local_path}")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_iterdir)

    snapshot = alignment_workdir_snapshot(workdir)

    assert snapshot == "Workdir could not be inspected."
    assert str(local_path) not in snapshot
    assert "permission denied" not in snapshot


def test_alignment_workdir_snapshot_redacts_unavailable_workdir_paths(tmp_path: Path) -> None:
    missing_workdir = tmp_path / "private missing project"
    file_workdir = tmp_path / "private file project"
    file_workdir.write_text("not a directory\n", encoding="utf-8")

    for path in (missing_workdir, file_workdir):
        snapshot = alignment_workdir_snapshot(path)

        assert snapshot == "Workdir could not be inspected."
        assert str(path) not in snapshot
        assert str(path.resolve()) not in snapshot


def test_alignment_workdir_snapshot_redacts_governance_marker_probe_errors(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    workdir = project / "packages" / "app"
    private_path = tmp_path / "private" / "AGENTS.md"
    workdir.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    original_is_file = Path.is_file

    def fail_is_file(path: Path) -> bool:
        if path == project / "AGENTS.md":
            raise OSError(f"permission denied: {private_path}")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", fail_is_file)

    snapshot = alignment_workdir_snapshot(workdir)

    assert snapshot == "Workdir could not be inspected."
    assert str(private_path) not in snapshot
    assert "permission denied" not in snapshot
