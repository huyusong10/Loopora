from __future__ import annotations

import shlex

from loopora.agent_adapters import agent_loop_json_command
from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _validation_repair_hints
from loopora.cli_agent_runtime_support import agent_plan_cli_command as _agent_plan_cli_command
from loopora.cli_summary_helpers import clip_inline as _clip_inline


def _attach_agent_gen_recovery_fields(result: dict) -> None:
    if result.get("ready"):
        return
    if result.get("requires_candidate_repair"):
        result["loop_recovery"] = "repair_candidate_plan_file"
        error = _agent_gen_error_summary(result)
        result["validation_error"] = error
        result["repair_focus"] = _validation_repair_hints(error)
        repair_task_message = _agent_task_message_from_session(result)
        if repair_task_message:
            result["repair_task_message"] = repair_task_message
        session = result.get("session") if isinstance(result.get("session"), dict) else {}
        binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
        plan_file = str(binding.get("source_path") or session.get("bundle_path") or "").strip()
        result["plan_file_to_repair"] = plan_file
        result["preview_plan_copy"] = str(session.get("bundle_path") or "").strip()
        result["next_plan_command"] = "/loopora-plan"
        if plan_file:
            result["repair_slash_command"] = f"/loopora-plan {shlex.quote(plan_file)}"
        repair_cli_command = _agent_repair_cli_command(result, plan_file=plan_file)
        if repair_cli_command:
            result["repair_cli_command"] = repair_cli_command
        result["next_repair_step"] = (
            "repair the candidate plan file so it preserves repair_task_message and repair_focus in spec, roles, "
            "workflow, and evidence rules; rerun repair_cli_command or repair_slash_command, then use /loopora-run "
            "only after the preview is ready"
        )
        return
    if result.get("requires_web_alignment"):
        _attach_agent_web_review_recovery_fields(result)


def _attach_agent_web_review_recovery_fields(result: dict) -> None:
    result["loop_recovery"] = "finish_web_review"
    result["review_status"] = _agent_web_review_status(result)
    result["review_focus"] = _agent_web_review_focus(result)
    result.update(_agent_web_review_task_anchor_fields(result))
    review = _agent_entry_review(result)
    recommended = _recommended_review_option(review)
    label = str(recommended.get("label") or recommended.get("id") or "").strip()
    if label:
        result["review_recommended_action"] = label
    reply = str(recommended.get("user_reply") or review.get("suggested_reply") or "").strip()
    if reply:
        result["review_reply_preview"] = _clip_inline(reply, 260)
    result["next_review_step"] = "open the preview URL, complete the Web review checklist, then use /loopora-run only after the preview is ready"
    result["after_review_ready"] = "return to this Agent session and run /loopora-run; do not start the Agent Runner run from Web"
    result["after_review_slash_command"] = _agent_entry_return_slash_command()
    command = _agent_entry_return_run_command(result)
    if command:
        result["after_review_cli_command"] = command
        result["after_review_command"] = command


def _agent_repair_cli_command(result: dict, *, plan_file: str) -> str:
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    adapter = str(result.get("adapter") or binding.get("adapter") or binding.get("candidate_adapter") or "").strip()
    workdir = str(result.get("workdir") or binding.get("workdir") or "").strip()
    message = _agent_task_message_from_session(result)
    if not adapter or not workdir or not message:
        return ""
    context_id = str(binding.get("host_context_id") or result.get("host_context_id") or "").strip()
    entry_source = str(
        result.get("candidate_entry_source") or binding.get("candidate_entry_source") or binding.get("entry_source") or ""
    ).strip()
    command = _agent_plan_cli_command(
        adapter=adapter,
        workdir=workdir,
        message=message,
        context_id=context_id,
        entry_source=entry_source,
        bundle_file=plan_file,
    )
    return f"{command} --json"


def _agent_task_message_from_session(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    for item in reversed(transcript):
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "").strip() != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content:
            return content
    return ""


def _attach_agent_ready_run_handoff_fields(result: dict) -> None:
    if not result.get("ready"):
        return
    result["review_before_loop"] = "confirm the preview carries these judgments before running /loopora-run"
    result["ready_next_step"] = "return to this Agent session and run /loopora-run; do not start the Agent Runner run from Web"
    result["ready_slash_command"] = _agent_entry_return_slash_command()
    command = _agent_entry_return_run_command(result)
    if command:
        result["ready_cli_command"] = command
        result["ready_run_command"] = command


def _agent_web_review_task_anchor_fields(result: dict) -> dict[str, str]:
    message = _agent_task_message_from_session(result)
    if not message:
        return {}
    if result.get("loopora_fit_contradiction"):
        status = (
            "task anchor preserved from /loopora-plan; Loopora fit must be redefined before it can become a runnable Loop"
        )
    else:
        status = (
            "task anchor preserved from /loopora-plan; no candidate plan has projected it into a runnable Loop yet"
        )
    return {
        "task_anchor_status": status,
        "task_anchor_preview": _clip_inline(message, 260),
        "review_scope": "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input",
    }


def _agent_web_review_status(result: dict) -> str:
    if result.get("loopora_fit_contradiction"):
        return "not runnable; Loopora fit needs to be redefined"
    return "not runnable; no candidate plan file was submitted"


def _agent_entry_return_slash_command() -> str:
    return "/loopora-run"


def _agent_entry_return_run_command(result: dict) -> str:
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    adapter = str(result.get("adapter") or binding.get("adapter") or binding.get("candidate_adapter") or "").strip()
    workdir = str(result.get("workdir") or binding.get("workdir") or "").strip()
    context_id = str(binding.get("host_context_id") or "").strip()
    entry_source = str(binding.get("candidate_entry_source") or binding.get("entry_source") or "").strip()
    if adapter and workdir:
        return agent_loop_json_command(adapter, workdir, entry_source=entry_source, context_id=context_id)
    return str(_agent_entry_launch(result).get("loop_command") or "").strip()


def _agent_entry_review(result: dict) -> dict:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    return session.get("agent_entry_review") if isinstance(session.get("agent_entry_review"), dict) else {}


def _agent_entry_launch(result: dict) -> dict:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    return session.get("agent_entry_launch") if isinstance(session.get("agent_entry_launch"), dict) else {}


def _recommended_review_option(review: dict) -> dict:
    options = [item for item in list(review.get("decision_options") or []) if isinstance(item, dict)]
    recommended = next((item for item in options if item.get("recommended") is True), None)
    return recommended or (options[0] if options else {})


def _agent_web_review_focus(result: dict) -> list[str]:
    focus = [
        "Loopora fit: explain what future rounds add beyond one Agent pass",
        "Success surface: name the user-visible outcome that must be proven",
        "Fake-done risks: name shallow states that must block closure",
        "Evidence expectations: name the checks, logs, browser paths, audits, or artifacts to trust",
        "Execution strategy and tradeoffs: say what to prove, repair, narrow, expand, or defer first",
        "Residual risk and local governance: name what may remain, who owns it, and which project rules must be read or gated",
    ]
    if result.get("loopora_fit_contradiction"):
        focus[0] = "Loopora fit: define later evidence, handoffs, or GateKeeper value before creating a runnable Loop"
    return focus


def _agent_gen_error_summary(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    return str(session.get("error_message") or validation.get("error") or "").strip()
