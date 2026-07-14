from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.agent_adapters import write_agent_binding
from loopora.agent_adapter_context_binding import AGENT_CONTEXT_CARD_SAVE_ERROR
from loopora.agent_entry_candidate import ready_candidate_yaml_provenance_from_validation
from loopora.agent_entry_run_projection import agent_loop_result, append_agent_entry_invocation


@dataclass(frozen=True)
class AgentLoopStartContext:
    adapter: str
    root: Path
    session_id: str
    context_id: str
    entry_source: str
    binding_extra: dict[str, Any] | None = None


def write_agent_loop_running_binding(
    start_context: AgentLoopStartContext,
    binding: dict[str, Any],
    session: dict[str, Any],
    native: dict[str, Any],
) -> dict[str, Any]:
    ready_candidate_provenance = ready_candidate_yaml_provenance_from_validation(session)
    payload = {
        **binding,
        **ready_candidate_provenance,
        **(start_context.binding_extra or {}),
        "alignment_status": session["status"],
        "requires_web_alignment": False,
        "requires_candidate_repair": False,
        "loopora_fit_contradiction": False,
        "linked_run_id": native["run"]["id"],
        "run_path": f"/runs/{native['run']['id']}",
        "execution_plane": "agent_native",
        "entry_invocations": append_agent_entry_invocation(
            binding,
            action="run",
            entry_source=start_context.entry_source,
        ),
    }
    try:
        return write_agent_binding(
            start_context.adapter,
            start_context.root,
            payload,
            context_id=start_context.context_id,
        )
    except OSError:
        payload_without_path = {key: value for key, value in payload.items() if key != "path"}
        return {
            "adapter": start_context.adapter,
            "workdir": str(start_context.root),
            **payload_without_path,
            "context_binding_error": AGENT_CONTEXT_CARD_SAVE_ERROR,
        }


def agent_loop_result_from_native(
    start_context: AgentLoopStartContext,
    session: dict[str, Any],
    binding: dict[str, Any],
    native: dict[str, Any],
    *,
    started_new_run: bool,
) -> dict[str, Any]:
    run_result = {
        "run": native["run"],
        "started_new_run": started_new_run,
        "next_step": native.get("next_step"),
        "complete": native.get("complete", False),
        "task_next_action": native.get("task_next_action"),
    }
    if binding.get("context_binding_error"):
        run_result["context_binding_error"] = binding.get("context_binding_error")
    return agent_loop_result(
        start_context.adapter,
        start_context.root,
        session,
        binding,
        run_result,
    )
