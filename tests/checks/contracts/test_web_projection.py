from __future__ import annotations

from pathlib import Path

from loopora.web_projection import web_run_detail_projection

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_timeline_event_formatting_has_dedicated_boundary() -> None:
    overview_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    timeline_source = (REPO_ROOT / "src" / "loopora" / "web_timeline_overviews.py").read_text(encoding="utf-8")
    run_event_source = (REPO_ROOT / "src" / "loopora" / "web_timeline_run_events.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_timeline_overviews import format_timeline_event as _format_timeline_event" in overview_source
    assert "from loopora.web_timeline_run_events import format_run_finished" in timeline_source
    assert "def format_timeline_event" in timeline_source
    assert "TIMELINE_EVENT_FORMATTERS" in timeline_source
    assert "def format_run_finished" in run_event_source
    assert "def format_run_result_accepted" in run_event_source
    assert "TIMELINE_EVENT_FORMATTERS" not in overview_source
    assert "def format_run_result_accepted" not in timeline_source
    assert "web_timeline_overviews.py" in contracts_source
    assert "web_timeline_run_events.py" in contracts_source


def test_web_task_verdict_overview_helpers_have_dedicated_boundary() -> None:
    overview_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    verdict_source = (REPO_ROOT / "src" / "loopora" / "web_task_verdict_overviews.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_task_verdict_overviews import build_run_summary_snapshot as _build_run_summary_snapshot" in overview_source
    assert "def build_run_summary_snapshot" in verdict_source
    assert "def verdict_safe_excerpt_pair" in verdict_source
    assert "def _first_task_bucket_text" in verdict_source
    assert "def _first_task_bucket_text" not in overview_source
    assert "web_task_verdict_overviews.py" in contracts_source


def test_web_run_detail_core_state_prefers_event_projection_bundle_over_legacy_run_record() -> None:
    projection = web_run_detail_projection(
        {
            "id": "run_projection_first",
            "loop_id": "loop_legacy",
            "status": "failed",
            "run_status": "failed",
            "current_iter": 0,
            "active_role": "legacy-role",
        },
        event_projections={
            "run_snapshot": {
                "schema_version": 1,
                "kind": "event_replayed_run_snapshot",
                "source_sequence": 9,
                "run_id": "run_projection_first",
                "loop_id": "loop_from_events",
                "lifecycle_status": "closed",
                "current_iteration": 3,
                "current_step_id": None,
                "pending_actor": None,
                "verdict_status": "passed",
            },
            "task_verdict": {
                "schema_version": 1,
                "kind": "event_replayed_task_verdict",
                "source_sequence": 9,
                "status": "passed",
                "source": "gatekeeper",
                "summary": "Projection verdict wins.",
            },
        },
    )

    assert projection["summary"]["loop_id"] == "loop_from_events"
    assert projection["summary"]["run_status"] == "succeeded"
    assert projection["summary"]["current_iter"] == 3
    assert projection["lifecycle"]["run_status"] == "succeeded"
    assert projection["task_verdict"]["status"] == "passed"
    assert projection["diagnostics"]["source_shape"] == "projection_bundle"
    assert projection["diagnostics"]["projection_source_sequence"] == 9


def test_web_run_detail_preserves_legacy_numeric_compatibility_without_negative_progress() -> None:
    projection = web_run_detail_projection(
        {
            "id": "run_legacy_numeric",
            "loop_id": "loop_legacy",
            "status": "running",
            "current_iter": "2",
            "active_role": "builder",
        }
    )

    assert projection["summary"]["current_iter"] == 2
    assert projection["lifecycle"]["current_iter"] == 2

    invalid_projection = web_run_detail_projection(
        {
            "id": "run_invalid_numeric",
            "loop_id": "loop_legacy",
            "status": "running",
            "current_iter": -1,
        },
        event_projections={
            "run_snapshot": {
                "schema_version": 1,
                "kind": "event_replayed_run_snapshot",
                "source_sequence": "-4",
                "run_id": "run_invalid_numeric",
                "loop_id": "loop_event",
                "lifecycle_status": "running",
                "current_iteration": -3,
            },
        },
    )

    assert invalid_projection["summary"]["current_iter"] is None
    assert invalid_projection["lifecycle"]["current_iter"] is None
    assert invalid_projection["diagnostics"]["projection_source_sequence"] is None
