from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_session_projection import decorate_alignment_session
from loopora.service_alignment_failure_recovery import ALIGNMENT_WORKER_INTERRUPTED_ERROR


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
    assert decorated["status_label"] == "running"
    assert decorated["working_agreement"] == {}
    assert decorated["native_resume_available"] is True
    assert decorated["failure_recovery"] == {}


def test_decorate_alignment_session_projects_cancelled_without_changing_stored_status(tmp_path: Path) -> None:
    decorated = decorate_alignment_session(
        {
            "id": "align_cancelled",
            "status": "failed",
            "stop_requested": True,
            "bundle_path": str(tmp_path / "align_cancelled" / "artifacts" / "bundle.yml"),
        },
        active_statuses={"running", "repairing"},
    )

    assert decorated["status"] == "failed"
    assert decorated["status_label"] == "cancelled"
    assert decorated["failure_recovery"]["kind"] == "user_cancelled"


def test_decorate_alignment_session_projects_interrupted_as_recoverable_status(tmp_path: Path) -> None:
    decorated = decorate_alignment_session(
        {
            "id": "align_interrupted",
            "status": "failed",
            "stop_requested": False,
            "error_message": ALIGNMENT_WORKER_INTERRUPTED_ERROR,
            "bundle_path": str(tmp_path / "align_interrupted" / "artifacts" / "bundle.yml"),
        },
        active_statuses={"running", "repairing"},
    )

    assert decorated["status_label"] == "interrupted"
    assert decorated["failure_recovery"]["failure_domain"] == "local_worker_interrupted"
    assert decorated["failure_recovery"]["retry_generation_available"] is True
