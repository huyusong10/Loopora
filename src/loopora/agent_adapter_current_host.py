from __future__ import annotations

from collections.abc import Mapping
import os

CURRENT_AGENT_HOST_ENV_VARS = {
    "codex": ("CODEX_SESSION_ID", "CODEX_THREAD_ID"),
    "claude": ("CLAUDE_SESSION_ID",),
    "opencode": ("OPENCODE_SESSION_ID",),
}


def current_agent_host_detection(environ: Mapping[str, str] | None = None) -> dict[str, object]:
    source = os.environ if environ is None else environ
    detected = [
        adapter
        for adapter, names in CURRENT_AGENT_HOST_ENV_VARS.items()
        if any(str(source.get(name) or "").strip() for name in names)
    ]
    if len(detected) == 1:
        state = "detected"
        adapter = detected[0]
        blocker = ""
    elif detected:
        state = "ambiguous"
        adapter = ""
        blocker = "current_agent_host_ambiguous"
    else:
        state = "unavailable"
        adapter = ""
        blocker = "current_agent_host_unavailable"
    return {
        "state": state,
        "adapter": adapter,
        "detected_adapters": detected,
        "selection_required": state != "detected",
        "command_ready": state == "detected",
        "command_blockers": [blocker] if blocker else [],
    }


__all__ = ["CURRENT_AGENT_HOST_ENV_VARS", "current_agent_host_detection"]
