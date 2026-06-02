from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_event_api_routes_have_dedicated_boundary() -> None:
    alignment_api_source = (REPO_ROOT / "src" / "loopora" / "web_route_alignment_api.py").read_text(encoding="utf-8")
    alignment_event_api_source = (REPO_ROOT / "src" / "loopora" / "web_alignment_event_api.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_alignment_event_api import register_alignment_event_api_routes" in alignment_api_source
    assert "def register_alignment_event_api_routes" in alignment_event_api_source
    assert '"/api/alignments/sessions/{session_id}/events"' in alignment_event_api_source
    assert '"/api/alignments/sessions/{session_id}/stream"' in alignment_event_api_source
    assert "ALIGNMENT_ACTIVE_STATUSES" in alignment_event_api_source
    assert "web_alignment_event_api.py" in design_source
