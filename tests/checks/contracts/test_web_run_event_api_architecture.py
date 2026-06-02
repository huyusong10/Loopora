from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_run_event_api_routes_have_dedicated_boundary() -> None:
    run_api_source = (REPO_ROOT / "src" / "loopora" / "web_route_run_api.py").read_text(encoding="utf-8")
    run_event_api_source = (REPO_ROOT / "src" / "loopora" / "web_run_event_api.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_run_event_api import register_run_event_api_routes" in run_api_source
    assert "def register_run_event_api_routes" in run_event_api_source
    assert '"/api/runs/{run_id}/events"' in run_event_api_source
    assert '"/api/runs/{run_id}/stream"' in run_event_api_source
    assert "stream_error_payload" in run_event_api_source
    assert "web_run_event_api.py" in design_source
