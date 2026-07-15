from __future__ import annotations

from loopora.events import CORE_EVENT_TYPES



def test_core_event_schema_excludes_surface_observability_events() -> None:
    surface_events = {
        "WebPageOpened",
        "AgentCommandRendered",
        "CliJsonPrinted",
        "HostTraceObserved",
        "TodoUpdated",
        "AdapterCheckPassed",
        "StatuslineRead",
    }

    assert CORE_EVENT_TYPES.isdisjoint(surface_events)
