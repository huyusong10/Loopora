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
