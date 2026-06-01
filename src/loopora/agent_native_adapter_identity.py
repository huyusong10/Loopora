from __future__ import annotations

from loopora.service_types import LooporaError


AGENT_ADAPTER_KINDS = ("codex", "claude", "opencode")


def normalize_agent_adapter_kind(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    aliases = {
        "codex": "codex",
        "openai-codex": "codex",
        "claude": "claude",
        "claude-code": "claude",
        "claudecode": "claude",
        "opencode": "opencode",
        "open-code": "opencode",
    }
    if normalized in aliases:
        return aliases[normalized]
    supported = ", ".join(AGENT_ADAPTER_KINDS)
    raise LooporaError(f"unsupported agent adapter: {value!r}. Expected one of: {supported}")
