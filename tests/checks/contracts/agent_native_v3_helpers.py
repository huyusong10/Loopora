from __future__ import annotations


def assert_agent_v3_envelope(payload: dict, *, kind: str, summary_key: str, status: str | None = None) -> tuple[dict, dict]:
    assert payload["schema_version"] == 3
    assert payload["kind"] == kind
    if status is not None:
        assert payload["status"] == status
    summary = payload["summary"]
    assert isinstance(payload["technical_handoff"], dict)
    assert payload["diagnostics"]["legacy_summary_key"] == summary_key
    legacy = payload["raw"]["legacy"]
    assert legacy[summary_key] == summary
    assert summary_key not in payload
    assert "agent_v2_envelope" not in payload
    return summary, legacy
