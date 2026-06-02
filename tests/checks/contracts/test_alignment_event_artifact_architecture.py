from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_event_artifact_io_has_dedicated_boundary() -> None:
    records_source = (REPO_ROOT / "src/loopora/db_alignment_records.py").read_text(encoding="utf-8")
    event_records_source = (REPO_ROOT / "src/loopora/db_alignment_event_records.py").read_text(encoding="utf-8")
    artifact_source = (REPO_ROOT / "src/loopora/db_alignment_event_artifacts.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design/contracts.md").read_text(encoding="utf-8")

    assert "from loopora.db_alignment_event_records import RepositoryAlignmentEventRecordsMixin" in records_source
    assert "class RepositoryAlignmentRecordsMixin(RepositoryAlignmentEventRecordsMixin)" in records_source
    assert "def append_alignment_event" not in records_source
    assert "from loopora.db_alignment_event_artifacts import append_alignment_event_artifact" in event_records_source
    assert "def append_alignment_event" in event_records_source
    assert "def list_alignment_events_for_redaction_audit" in event_records_source
    assert "def append_alignment_event_artifact" in artifact_source
    assert "def alignment_event_artifact_root" in artifact_source
    assert "events.jsonl" in artifact_source
    assert "events.jsonl" not in records_source
    assert "db_alignment_event_records.py" in design_source
    assert "db_alignment_event_artifacts.py" in design_source
