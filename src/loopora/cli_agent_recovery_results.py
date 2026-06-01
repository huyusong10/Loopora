from __future__ import annotations

import shlex
from pathlib import Path

from loopora.agent_adapters import (
    prefix_loopora_command,
    read_agent_binding,
    resolve_adapter_project_root,
)
from loopora.cli_agent_recovery_active_runs import (
    AgentActiveRunConflictRecoveryRequest,
    _agent_active_run_conflict_recovery_result as _agent_active_run_conflict_recovery_result,
    _attach_agent_next_commands_to_recovery_choices as _attach_agent_next_commands_to_recovery_choices,
)
from loopora.cli_agent_plan_recovery_results import (
    _attach_agent_gen_recovery_fields,
    _attach_agent_web_review_recovery_fields,
)
from loopora.cli_agent_plan_recovery import (
    agent_plan_context_guidance_fields as _agent_plan_context_guidance_fields,
)
from loopora.cli_agent_runtime_support import attach_recoverable_context_preview_urls as _attach_recoverable_context_preview_urls
from loopora.cli_agent_runtime_support import attach_web_url as _attach_web_url
from loopora.service import LooporaError


def _agent_next_recovery_result(
    exc: Exception,
    *,
    service,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    error = str(exc)
    if service is None or "no Loopora run is associated with this agent session/workdir" not in error:
        return {}
    root = resolve_adapter_project_root(workdir)
    result = _agent_loop_unbound_recovery_result(
        service,
        adapter=adapter,
        root=root,
        context_id=context_id,
        entry_source=entry_source,
        no_web=no_web,
    )
    if not result:
        return {}
    result["recovery_source"] = "agent_next_missing_binding"
    result["error"] = error
    if result.get("loop_recovery") == "choose_recoverable_context":
        result["message"] = (
            "Current Agent context is not bound to a Loopora run, but recoverable contexts exist; "
            "choose the intended run or pass --run-id to claim its current step."
        )
        _attach_agent_next_commands_to_recovery_choices(
            result,
            adapter=adapter,
            workdir=root,
            context_id=context_id,
            entry_source=entry_source,
        )
    elif result.get("loop_recovery") == "plan_first":
        result["message"] = "No Loopora run is bound to this Agent context/workdir; plan and start a Loop before claiming a step."
        result["next"] = "Ask the user for task context, run /loopora-plan, review the READY preview, then run /loopora-run."
    return result


def _agent_loop_unready_recovery_result(
    exc: Exception,
    *,
    service,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    error = str(exc)
    if service is None or not _agent_loop_error_supports_recovery(error):
        return {}
    root = resolve_adapter_project_root(workdir)
    if "another active run is already using" in error:
        return _agent_active_run_conflict_recovery_result(
            AgentActiveRunConflictRecoveryRequest(
                service=service,
                adapter=adapter,
                root=root,
                context_id=context_id,
                entry_source=entry_source,
                no_web=no_web,
                error=error,
            )
        )
    return _agent_bound_preview_recovery_result(
        service,
        adapter=adapter,
        root=root,
        context_id=context_id,
        entry_source=entry_source,
        no_web=no_web,
    )


def _agent_loop_error_supports_recovery(error: str) -> bool:
    return (
        "/loopora-run" in error
        or "run /loopora-plan first" in error
        or "no ready Loop preview" in error
        or "does not reference a ready Loop preview" in error
        or "another active run is already using" in error
    )


def _agent_bound_preview_recovery_result(
    service,
    *,
    adapter: str,
    root: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    try:
        binding = read_agent_binding(adapter, root, context_id=context_id)
        session_id = str(binding.get("alignment_session_id") or "").strip()
        session = service.get_alignment_session(session_id) if session_id else {}
    except LooporaError as binding_exc:
        if not _agent_context_card_error_is_repairable(str(binding_exc)):
            return {}
        return {
            "adapter": adapter,
            "workdir": str(root),
            "ready": False,
            "loop_recovery": "repair_agent_binding",
            "binding_error": str(binding_exc),
            "context_card_error": str(binding_exc),
            "check_command": prefix_loopora_command(f"loopora init {adapter} --check --workdir {shlex.quote(str(root))}"),
        }
    except Exception:  # noqa: BLE001 - error recovery must never replace the primary domain error.
        return {}
    if not binding or not session:
        return _agent_loop_unbound_recovery_result(
            service,
            adapter=adapter,
            root=root,
            context_id=context_id,
            entry_source=entry_source,
            no_web=no_web,
        )
    result = {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "status": session.get("status"),
        "requires_web_alignment": binding.get("requires_web_alignment") is True,
        "requires_candidate_repair": binding.get("requires_candidate_repair") is True,
        "loopora_fit_contradiction": binding.get("loopora_fit_contradiction") is True,
        "session": session,
        "binding": binding,
        "preview_path": str(binding.get("preview_path") or f"/loops/new/bundle?alignment_session_id={session_id}"),
    }
    _attach_web_url(result, path_key="preview_path", url_key="preview_url", no_web=no_web)
    if result["requires_candidate_repair"]:
        _attach_agent_gen_recovery_fields(result)
    elif result["requires_web_alignment"]:
        _attach_agent_web_review_recovery_fields(result)
    else:
        result["loop_recovery"] = "preview_not_ready"
    return result


def _agent_loop_unbound_recovery_result(
    service,
    *,
    adapter: str,
    root: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    try:
        resolution = service.resolve_loopora_context(root, intent="run", adapter=adapter, context_id=context_id)
    except Exception:  # noqa: BLE001 - error recovery must never replace the primary domain error.
        return {}
    if resolution.get("action") == "plan_first":
        result = {
            "adapter": adapter,
            "workdir": str(root),
            "ready": False,
            "loop_recovery": "plan_first",
            "context_resolution": resolution,
            "next_plan_command": "/loopora-plan",
            "message": (
                "No ready Loop preview or recoverable run context is bound to this Agent session/workdir; "
                "run /loopora-plan first."
            ),
            "next": "Ask the user the ask_user question, then run /loopora-plan with the user's task context.",
        }
        result.update(
            _agent_plan_context_guidance_fields(
                adapter=adapter,
                workdir=root,
                context_id=context_id,
                entry_source=entry_source,
            )
        )
        return result
    if resolution.get("action") != "choose_recoverable_context":
        return {}
    result = {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "loop_recovery": "choose_recoverable_context",
        "context_resolution": resolution,
    }
    _attach_recoverable_context_preview_urls(result, no_web=no_web)
    return result


def _agent_context_card_error_is_repairable(error: str) -> bool:
    return any(
        marker in error
        for marker in (
            "agent context card is unreadable",
            "agent context card is invalid",
            "agent binding is unreadable",
            "agent binding is invalid",
        )
    )
