from __future__ import annotations

from loopora.agent_adapters import agent_loop_json_command
from loopora.cli_agent_runtime_support import agent_plan_cli_command as _agent_plan_cli_command
from loopora.service_alignment_agent_entry_review import agent_entry_review_language


def _latest_alignment_question(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    for item in reversed(transcript):
        if isinstance(item, dict) and str(item.get("role") or "").strip() == "assistant":
            return str(item.get("content") or "").strip()
    return ""


def _agent_repair_cli_command(result: dict, *, plan_file: str) -> str:
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    adapter = str(result.get("adapter") or binding.get("adapter") or binding.get("candidate_adapter") or "").strip()
    workdir = str(result.get("workdir") or binding.get("workdir") or "").strip()
    message = _agent_task_message_from_session(result)
    if not adapter or not workdir or not message:
        return ""
    context_id = str(binding.get("host_context_id") or result.get("host_context_id") or "").strip()
    entry_source = str(result.get("candidate_entry_source") or binding.get("candidate_entry_source") or binding.get("entry_source") or "").strip()
    command = _agent_plan_cli_command(
        adapter=adapter,
        workdir=workdir,
        message=message,
        context_id=context_id,
        entry_source=entry_source,
        bundle_file=plan_file,
    )
    return f"{command} --json --compact-json"


def _agent_review_message_cli_command(result: dict, *, reply: str) -> str:
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    adapter = str(result.get("adapter") or binding.get("adapter") or binding.get("candidate_adapter") or "").strip()
    workdir = str(result.get("workdir") or binding.get("workdir") or "").strip()
    message = _agent_review_command_message(reply)
    if not adapter or not workdir or not message:
        return ""
    context_id = str(binding.get("host_context_id") or result.get("host_context_id") or "").strip()
    entry_source = str(result.get("candidate_entry_source") or binding.get("candidate_entry_source") or binding.get("entry_source") or "").strip()
    command = _agent_plan_cli_command(
        adapter=adapter,
        workdir=workdir,
        message=message,
        context_id=context_id,
        entry_source=entry_source,
    )
    return f"{command} --json --compact-json"


def _agent_review_command_message(reply: str) -> str:
    return " ".join(str(reply or "").split()).strip()


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


def _agent_web_review_language(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    return agent_entry_review_language(session)


def _agent_gen_error_summary(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    return str(result.get("context_binding_error") or result.get("error") or session.get("error_message") or validation.get("error") or "").strip()
