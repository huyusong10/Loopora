from __future__ import annotations


AGENT_V3_ENVELOPE_SCHEMA_VERSION = 3


def assert_agent_v3_envelope(payload: dict, *, kind: str, summary_key: str, status: str | None = None) -> tuple[dict, dict]:
    assert payload["schema_version"] == AGENT_V3_ENVELOPE_SCHEMA_VERSION
    assert payload["kind"] == kind
    if status is not None:
        assert payload["status"] == status
    summary = payload["summary"]
    assert isinstance(payload["technical_handoff"], dict)
    assert payload["diagnostics"]["legacy_summary_key"] == summary_key
    legacy = payload["raw"]["legacy"]
    expected_legacy_summary = dict(summary)
    if "agent_surface" in expected_legacy_summary:
        expected_legacy_summary["native_surface"] = expected_legacy_summary["agent_surface"]
    assert legacy[summary_key] == expected_legacy_summary
    assert summary_key not in payload
    assert "agent_v2_envelope" not in payload
    return summary, legacy


def assert_agent_v3_compact_envelope(payload: dict, *, kind: str, summary_key: str, status: str | None = None) -> dict:
    assert payload["schema_version"] == AGENT_V3_ENVELOPE_SCHEMA_VERSION
    assert payload["kind"] == kind
    if status is not None:
        assert payload["status"] == status
    assert isinstance(payload["summary"], dict)
    assert isinstance(payload["technical_handoff"], dict)
    assert payload["diagnostics"]["legacy_summary_key"] == summary_key
    assert "raw" not in payload
    assert summary_key not in payload
    assert "agent_v2_envelope" not in payload
    return payload["summary"]
