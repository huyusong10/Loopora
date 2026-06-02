from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_session_projection import decorate_alignment_session


def test_decorate_alignment_session_projects_runtime_flags_and_defaults(tmp_path: Path) -> None:
    session = {
        "id": "align_1",
        "status": "running",
        "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
        "working_agreement": "invalid",
        "executor_session_ref": {"session_id": "native-session"},
    }

    decorated = decorate_alignment_session(session, active_statuses={"running", "repairing"})

    assert decorated["artifact_dir"] == str(tmp_path / "align_1")
    assert decorated["is_active"] is True
    assert decorated["is_ready"] is False
    assert decorated["alignment_stage"] == "clarifying"
    assert decorated["working_agreement"] == {}
    assert decorated["native_resume_available"] is True
