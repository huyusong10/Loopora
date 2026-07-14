from __future__ import annotations

from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.spec_recovery_commands import SpecInitStrategyContext, spec_init_recovery_command
from loopora.workdir_inputs import spec_path_state


def web_loop_create_spec_recovery_payload(
    spec_path: Path | str,
    *,
    action: str = "create_loop",
    orchestration_id: object = "",
    strategy_preset: object = "",
    strategy_context: SpecInitStrategyContext | None = None,
) -> dict[str, object]:
    state = _web_loop_spec_state(
        spec_path,
        orchestration_id=orchestration_id,
        strategy_preset=strategy_preset,
        strategy_context=strategy_context,
    )
    actions: list[dict[str, str]] = []
    commands = state.get("commands") if isinstance(state.get("commands"), dict) else {}
    init_command = str(commands.get("init") or "")
    retry_action = {"kind": "retry_web_compose", "target": "web_loop_create", "action": action}
    if init_command:
        actions.append({"kind": "create_spec", "command": init_command})
        retry_action["after_action"] = "create_spec"
        actions.append(retry_action)
        actions.append({"kind": "choose_spec"})
    else:
        actions.append({"kind": "choose_spec"})
        retry_action["after_action"] = "choose_spec"
        actions.append(retry_action)
    summary = str(state.get("summary") or "")
    payload = {
        "web_spec_recovery_summary": {
            "ready": False,
            "loop_recovery": "target_spec_unavailable",
            "status": "blocked_by_spec",
            "surface": "web_loop_create",
            "action": action,
            "spec_path": str(state.get("spec_path") or ""),
            "spec_state_status": str(state.get("status") or ""),
            "next_action_kinds": _web_action_kinds(actions),
        },
        "loop_recovery": "target_spec_unavailable",
        "status": "blocked_by_spec",
        "surface": "web_loop_create",
        "action": action,
        "spec_path": str(state.get("spec_path") or ""),
        "spec_state": state,
        "summary": summary,
        "error": _web_loop_spec_error(summary, init_command=init_command),
        "next_actions": actions,
    }
    _project_web_recovery_action_contract(payload, summary_key="web_spec_recovery_summary")
    return payload


def web_alignment_workdir_recovery_payload(workdir: Path | str, *, action: str) -> dict[str, object]:
    state = _web_alignment_workdir_state(workdir)
    return _web_compose_workdir_recovery_payload(state, surface="web_alignment", action=action)


def web_loop_create_workdir_recovery_payload(workdir: Path | str, *, action: str = "create_loop") -> dict[str, object]:
    state = _web_alignment_workdir_state(workdir)
    return _web_compose_workdir_recovery_payload(
        state,
        surface="web_loop_create",
        action=action,
        retry_before_readiness=True,
    )


def web_bundle_import_workdir_recovery_payload(
    workdir: Path | str,
    *,
    action: str = "import_bundle",
) -> dict[str, object]:
    state = _web_alignment_workdir_state(workdir)
    return _web_compose_workdir_recovery_payload(
        state,
        surface="web_bundle_import",
        action=action,
        retry_before_readiness=True,
    )


def web_loop_start_workdir_recovery_payload(
    loop_id: str,
    workdir: Path | str,
    *,
    action: str = "start_run",
) -> dict[str, object]:
    state = _web_alignment_workdir_state(workdir)
    payload = _web_compose_workdir_recovery_payload(state, surface="web_loop_start", action=action)
    payload["loop_id"] = loop_id
    return payload


def browser_recovery_submit_payload(
    payload: dict[str, object],
    *,
    form_id: str,
    form_action: str = "",
    action_kinds: tuple[str, ...] = ("retry_web_compose", "retry_web_run_start"),
) -> dict[str, object]:
    """Attach browser-only submit controls to retry actions without changing API recovery semantics."""
    resolved_form_id = str(form_id).strip()
    if not resolved_form_id:
        return payload
    projected = dict(payload)
    next_actions = projected.get("next_actions")
    if not isinstance(next_actions, list):
        return projected
    retry_kinds = {str(kind).strip() for kind in action_kinds if str(kind).strip()}
    projected_actions: list[dict[str, object]] = []
    for action in next_actions:
        if not isinstance(action, dict):
            continue
        projected_action = dict(action)
        if str(projected_action.get("kind") or "").strip() in retry_kinds:
            projected_action["form_id"] = resolved_form_id
            if form_action:
                projected_action["form_action"] = form_action
            projected_action["form_method"] = "POST"
        projected_actions.append(projected_action)
    projected["next_actions"] = projected_actions
    return projected


def _web_compose_workdir_recovery_payload(
    state: dict[str, object],
    *,
    surface: str,
    action: str,
    retry_before_readiness: bool = False,
) -> dict[str, object]:
    root = str(state.get("workdir") or "")
    actions: list[dict[str, str]] = []
    commands = state.get("commands") if isinstance(state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "")
    workdir_action = (
        {"kind": "create_workdir", "command": create_command}
        if create_command
        else {"kind": "choose_workdir"}
    )
    actions.append(workdir_action)
    workdir_action_kind = str(workdir_action.get("kind") or "")
    confirm_action = {"kind": "confirm_readiness"}
    if create_command:
        confirm_action["command"] = copyable_loopora_command(f"loopora doctor --workdir {shlex.quote(root)}")
    retry_kind = "retry_web_run_start" if surface == "web_loop_start" else "retry_web_compose"
    retry_action = {"kind": retry_kind, "target": surface, "action": action}
    if retry_before_readiness:
        retry_action["after_action"] = workdir_action_kind
        confirm_action["after_action"] = retry_kind
        actions.append(retry_action)
        actions.append(confirm_action)
    else:
        confirm_action["after_action"] = workdir_action_kind
        retry_action["after_action"] = "confirm_readiness"
        actions.append(confirm_action)
        actions.append(retry_action)
    summary = str(state.get("summary") or "")
    payload = {
        "web_workdir_recovery_summary": {
            "ready": False,
            "loop_recovery": "target_workdir_unavailable",
            "status": "blocked_by_workdir",
            "surface": surface,
            "action": action,
            "workdir": root,
            "workdir_state_status": str(state.get("status") or ""),
            "next_action_kinds": _web_action_kinds(actions),
        },
        "loop_recovery": "target_workdir_unavailable",
        "status": "blocked_by_workdir",
        "surface": surface,
        "action": action,
        "workdir": root,
        "workdir_state": state,
        "summary": summary,
        "error": _web_alignment_error(summary, create_command=create_command),
        "next_actions": actions,
    }
    _project_web_recovery_action_contract(payload, summary_key="web_workdir_recovery_summary")
    return payload


def _project_web_recovery_action_contract(payload: dict[str, object], *, summary_key: str) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    action_kinds = _web_action_kinds(actions)
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get(summary_key)
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)


def _web_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def web_alignment_workdir_ready(workdir: Path | str) -> bool:
    return _web_alignment_workdir_state(workdir)["status"] == "ready"


def web_loop_create_spec_ready(spec_path: Path | str) -> bool:
    return _web_loop_spec_state(spec_path)["status"] == "ready"


def _web_loop_spec_state(
    spec_path: Path | str,
    *,
    orchestration_id: object = "",
    strategy_preset: object = "",
    strategy_context: SpecInitStrategyContext | None = None,
) -> dict[str, object]:
    state = spec_path_state(spec_path)
    if state["status"] == "required":
        return {
            **state,
            "summary": "Spec path is required; choose an existing Markdown spec before composing a Loop.",
        }
    if state["status"] == "missing":
        path = str(state["spec_path"])
        return {
            **state,
            "summary": "Spec file does not exist yet; create a starter spec or choose an existing Markdown spec before composing a Loop.",
            "commands": {
                "init": spec_init_recovery_command(
                    path,
                    orchestration_id=orchestration_id,
                    strategy_preset=strategy_preset,
                    strategy_context=strategy_context,
                )
            },
        }
    if state["status"] == "not_file":
        return {
            **state,
            "summary": "Spec path exists but is not a file; choose an existing Markdown spec before composing a Loop.",
        }
    if state["status"] == "unavailable":
        return {
            **state,
            "summary": "Spec path cannot be inspected; choose a readable Markdown spec before composing a Loop.",
        }
    return state


def _web_alignment_workdir_state(workdir: Path | str) -> dict[str, object]:
    raw_workdir = str(workdir or "").strip()
    if raw_workdir and "\0" not in raw_workdir:
        try:
            raw_path = Path(raw_workdir).expanduser()
        except (RuntimeError, ValueError):
            raw_path = None
        if raw_path is not None and not raw_path.is_absolute():
            return {
                "status": "absolute_required",
                "workdir": "",
                "usable_for_agent_entries": False,
                "usable_for_agent_runtime": False,
                "usable_for_web_alignment": False,
                "summary": "Target project directory must be a server-side absolute path; choose or paste an absolute project directory before composing or running a Loop.",
                "error": "target project absolute path is required",
                "commands": {},
            }
    state = dict(adapter_workdir_state(workdir))
    state["usable_for_web_alignment"] = state["status"] == "ready"
    if state["status"] == "required":
        state["summary"] = "Target project directory is required; choose a project directory before composing or running a Loop."
        state["error"] = "workdir is required"
    elif state["status"] == "missing":
        state["summary"] = "Target project directory does not exist yet; create it before composing or running a Loop."
    elif state["status"] == "not_directory":
        state["summary"] = "Target project path exists but is not a directory; choose a project directory before composing or running a Loop."
    elif state["status"] == "unavailable":
        state["summary"] = "Target project directory cannot be inspected; choose a readable project directory before composing or running a Loop."
        state["error"] = "workdir could not be inspected"
    return state


def _web_alignment_error(summary: str, *, create_command: str) -> str:
    if create_command:
        return f"{summary} First run: {create_command}"
    return summary


def _web_loop_spec_error(summary: str, *, init_command: str) -> str:
    if init_command:
        return f"{summary} First run: {init_command}"
    return summary
