from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_event_redaction_audit_has_db_file_and_result_boundaries() -> None:
    audit_source = (REPO_ROOT / "src/loopora/event_redaction_audit.py").read_text(encoding="utf-8")
    db_source = (REPO_ROOT / "src/loopora/event_redaction_audit_db.py").read_text(encoding="utf-8")
    files_source = (REPO_ROOT / "src/loopora/event_redaction_audit_files.py").read_text(encoding="utf-8")
    results_source = (REPO_ROOT / "src/loopora/event_redaction_audit_results.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design/contracts.md").read_text(encoding="utf-8")

    assert "from loopora.event_redaction_audit_db import" in audit_source
    assert "from loopora.event_redaction_audit_files import" in audit_source
    assert "from loopora.event_redaction_audit_results import combine_event_redaction_reports" in audit_source
    assert "def audit_db_events" in db_source
    assert "def audit_alignment_db_events" in db_source
    assert "def audit_timeline_files" in files_source
    assert "def audit_alignment_event_files" in files_source
    assert "def combine_event_redaction_reports" in results_source
    assert "state_dir_for_workdir" not in audit_source
    assert "event_redaction_audit_files.py" in design_source
