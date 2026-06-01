from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.agent_adapters import read_agent_binding
from loopora.service_alignment_run_context_choices import (
    agent_run_context_choice_summary,
)
from loopora.service_alignment_run_context_recovery_fields import (
    agent_exact_binding_recovery_action,
    agent_redacted_context_binding,
)
from loopora.service_alignment_run_recovery import (
    agent_run_context_choice_from_session,
    agent_run_context_choices,
)
from loopora.service_types import LooporaError


class AlignmentAgentBindingReader(Protocol):
    def __call__(self, adapter: str, workdir: Path, *, context_id: str = "") -> dict: ...


@dataclass(frozen=True)
class AlignmentRunContextResolverContext:
    repository: object
    get_alignment_session: Callable[[str], dict]
    get_run: Callable[[str], dict]
    same_workdir: Callable[[object, object], bool]
    read_binding: AlignmentAgentBindingReader = read_agent_binding


def resolve_alignment_run_context(
    context: AlignmentRunContextResolverContext,
    root: Path,
    *,
    adapter: str,
    context_id: str,
) -> dict:
    normalized_adapter = str(adapter or "").strip()
    base = alignment_run_context_base(root, adapter=normalized_adapter, context_id=context_id)
    if normalized_adapter:
        try:
            binding = context.read_binding(normalized_adapter, root, context_id=str(context_id or "").strip())
        except LooporaError as exc:
            return {
                **base,
                "action": "repair_context_card",
                "confidence": "damaged_context_card",
                "binding_error": str(exc),
                "context_card_error": str(exc),
                "message": "Agent context card is unreadable; repair it or choose a recoverable context before /loopora-run starts.",
            }
        if binding:
            return resolve_alignment_run_context_from_exact_binding(context, root, base=base, binding=binding)
    choices = agent_run_context_choices(
        context.repository,
        root=root,
        adapter=normalized_adapter,
        same_workdir=context.same_workdir,
        get_run=context.get_run,
    )
    if choices:
        return {
            **base,
            "action": "choose_recoverable_context",
            "confidence": "single_recoverable" if len(choices) == 1 else "ambiguous",
            "requires_user_choice": True,
            **agent_run_context_choice_summary(choices),
            "choices": choices,
            "message": "Choose a recoverable Loopora run context before /loopora-run starts.",
        }
    return {
        **base,
        "action": "plan_first",
        "confidence": "no_context_card",
        "message": "No Loopora run context is bound to this Agent session/workdir; run /loopora-plan first.",
    }


def alignment_run_context_base(root: Path, *, adapter: str, context_id: str) -> dict:
    return {
        "schema_version": 1,
        "intent": "run",
        "workdir": str(root),
        "adapter": str(adapter or "").strip(),
        "context_id": str(context_id or "").strip(),
        "requires_user_choice": False,
        "choices": [],
    }


def resolve_alignment_run_context_from_exact_binding(
    context: AlignmentRunContextResolverContext,
    root: Path,
    *,
    base: dict,
    binding: dict,
) -> dict:
    session_id = str(binding.get("alignment_session_id") or "").strip()
    if not session_id:
        return {
            **base,
            "action": "blocked",
            "confidence": "stale_context_card",
            "binding": agent_redacted_context_binding(binding),
            "message": "Agent context card exists but does not reference a Loop preview; run /loopora-plan again.",
        }
    try:
        session = context.get_alignment_session(session_id)
    except LooporaError:
        return {
            **base,
            "action": "blocked",
            "confidence": "stale_context_card",
            "binding": agent_redacted_context_binding(binding),
            "alignment_session_id": session_id,
            "message": "Agent context card references a missing Loop preview; run /loopora-plan again.",
        }
    if not context.same_workdir(binding.get("workdir") or session.get("workdir"), root):
        return {
            **base,
            "action": "blocked",
            "confidence": "workdir_mismatch",
            "binding": agent_redacted_context_binding(binding),
            "alignment_session_id": session_id,
            "message": "Agent context card belongs to a different workdir; run /loopora-plan again.",
        }
    choice = agent_run_context_choice_from_session(
        context.repository,
        session,
        adapter=str(base.get("adapter") or ""),
        get_run=context.get_run,
    )
    return {
        **base,
        "action": agent_exact_binding_recovery_action(choice),
        "confidence": "exact_context_card",
        "alignment_session_id": session_id,
        "binding": agent_redacted_context_binding(binding),
        "choice": choice,
        "message": "Exact Agent context card found.",
    }
