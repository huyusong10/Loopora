from __future__ import annotations

from pathlib import Path


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
