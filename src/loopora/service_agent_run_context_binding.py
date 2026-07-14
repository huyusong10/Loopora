from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.agent_adapters import read_agent_binding, resolved_agent_context_id, write_agent_binding
from loopora.agent_adapter_context_binding import AGENT_CONTEXT_CARD_SAVE_ERROR
from loopora.agent_entry_run_projection import append_agent_entry_invocation
from loopora.service_alignment_run_recovery import agent_run_context_choices
from loopora.service_alignment_workdir_snapshot import alignment_same_workdir
from loopora.service_types import LooporaConflictError, LooporaError

AGENT_CONTEXT_CARD_DAMAGED_ERROR = (
    "agent context card is damaged; rerun /loopora-plan or choose a recoverable context before /loopora-run can start"
)


@dataclass(frozen=True)
class AgentRunContextBindingContext:
    repository: object
    get_session: Callable[[str], dict[str, Any]]
    get_run: Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class AgentRunContextBindingRequest:
    adapter: str
    root: Path
    context_id: str
    entry_source: str
    source_option_id: str


def selected_agent_run_binding(
    context: AgentRunContextBindingContext,
    request: AgentRunContextBindingRequest,
) -> dict[str, Any]:
    option_id = str(request.source_option_id or "").strip()
    if option_id:
        return bind_selected_agent_run_context(
            context,
            AgentRunContextBindingRequest(
                adapter=request.adapter,
                root=request.root,
                context_id=request.context_id,
                entry_source=request.entry_source,
                source_option_id=option_id,
            ),
        )
    try:
        return read_agent_binding(request.adapter, request.root, context_id=request.context_id)
    except LooporaError as exc:
        raise LooporaConflictError(AGENT_CONTEXT_CARD_DAMAGED_ERROR) from exc


def bind_selected_agent_run_context(
    context: AgentRunContextBindingContext,
    request: AgentRunContextBindingRequest,
) -> dict[str, Any]:
    choices = [
        choice
        for choice in agent_run_context_choices(
            context.repository,
            root=request.root,
            adapter=request.adapter,
            same_workdir=alignment_same_workdir,
            get_run=context.get_run,
        )
        if isinstance(choice, dict)
    ]
    selected = next((choice for choice in choices if str(choice.get("option_id") or "") == request.source_option_id), None)
    if not selected:
        raise LooporaConflictError(
            f"selected recoverable context {request.source_option_id!r} is not available for /loopora-run in this workdir"
        )
    session_id = str(selected.get("alignment_session_id") or "").strip()
    if not session_id:
        raise LooporaConflictError("selected recoverable context does not reference a Loop preview; run /loopora-plan first")
    session = context.get_session(session_id)
    assert_agent_binding_matches_workdir({"workdir": str(request.root)}, session, expected_workdir=request.root)
    try:
        existing_binding = read_agent_binding(request.adapter, request.root, context_id=request.context_id)
    except LooporaError:
        existing_binding = {}
    try:
        return write_agent_binding(
            request.adapter,
            request.root,
            {
                **existing_binding,
                "alignment_session_id": session_id,
                "alignment_status": str(session.get("status") or ""),
                "bundle_path": session.get("bundle_path", ""),
                "candidate_origin": "agent_entry",
                "candidate_adapter": request.adapter,
                "candidate_entry_source": str(request.entry_source or selected.get("entry_source") or "").strip() or "direct_cli",
                "host_context_id": resolved_agent_context_id(request.adapter, context_id=request.context_id),
                "requires_web_alignment": str(session.get("status") or "") not in {"ready", "imported"},
                "requires_candidate_repair": False,
                "loopora_fit_contradiction": False,
                "selected_option_id": request.source_option_id,
                "linked_run_id": str(selected.get("linked_run_id") or ""),
                "preview_path": f"/loops/new/bundle?alignment_session_id={session_id}",
                "entry_invocations": append_agent_entry_invocation(
                    existing_binding,
                    action="run_select",
                    entry_source=request.entry_source,
                ),
            },
            context_id=request.context_id,
        )
    except OSError as exc:
        raise LooporaConflictError(
            f"{AGENT_CONTEXT_CARD_SAVE_ERROR}; repair target project .loopora agent state before /loopora-run can start"
        ) from exc


def assert_agent_binding_matches_workdir(binding: dict, session: dict, *, expected_workdir: Path) -> None:
    expected = expected_workdir.expanduser().resolve()
    binding_workdir = str(binding.get("workdir") or "").strip()
    if binding_workdir and Path(binding_workdir).expanduser().resolve() != expected:
        raise LooporaConflictError("agent context card belongs to a different workdir; run /loopora-plan again")
    session_workdir = str(session.get("workdir") or "").strip()
    if not session_workdir or Path(session_workdir).expanduser().resolve() != expected:
        raise LooporaConflictError("agent context card references a Loop preview from a different workdir; run /loopora-plan again")
