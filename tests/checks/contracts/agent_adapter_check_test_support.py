from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_envelope


def assert_agent_check_payload(payload: dict, *, status: str) -> tuple[dict, dict]:
    return assert_agent_v3_envelope(payload, kind="agent_check", summary_key="agent_check_summary", status=status)
