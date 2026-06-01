from __future__ import annotations

from typing import Any

from loopora.agent_native_adapter_contracts import agent_adapter_native_run_surface_summary
from loopora.agent_native_surface_lines import native_surface_plain_lines

__all__ = [
    "agent_native_run_surface_for_result",
    "attach_native_run_surface",
    "native_surface_plain_lines",
]


def attach_native_run_surface(summary: dict[str, Any], result: dict | None = None, *sources: object, adapter: str = "") -> None:
    surface = (
        agent_adapter_native_run_surface_summary(adapter)
        if str(adapter or "").strip()
        else agent_native_run_surface_for_result(result or {}, *sources)
    )
    if surface:
        summary["agent_surface"] = surface


def agent_native_run_surface_for_result(result: dict, *sources: object) -> dict[str, Any]:
    adapter = _surface_adapter_from_sources(result, *sources)
    return agent_adapter_native_run_surface_summary(adapter)


def _surface_adapter_from_sources(result: dict, *sources: object) -> str:
    for source in (result, *sources):
        if not isinstance(source, dict):
            continue
        adapter = str(source.get("adapter") or "").strip()
        if adapter:
            return adapter
    return "codex"
