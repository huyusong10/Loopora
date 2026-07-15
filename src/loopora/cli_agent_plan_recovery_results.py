from __future__ import annotations

import shlex

from loopora.agent_adapters import agent_loop_json_command
from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _validation_repair_hints
from loopora.cli_agent_runtime_support import agent_plan_cli_command as _agent_plan_cli_command
from loopora.cli_summary_helpers import clip_inline as _clip_inline
from loopora.service_alignment_agent_entry_review import agent_entry_review_language
from loopora.system_prompt_assets import load_system_prompt_asset


def _agent_native_recovery_asset(asset_ref: str) -> str:
    return load_system_prompt_asset(f"agent_native/{asset_ref}").strip()


def _agent_native_recovery_asset_lines(asset_ref: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in _agent_native_recovery_asset(asset_ref).splitlines() if line.strip())


REPAIR_CLI_COMMAND_POLICY = _agent_native_recovery_asset("repair-cli-command-policy.md")
REPAIR_REFERENCE = _agent_native_recovery_asset("repair-reference.md")
REPAIR_FORBIDDEN_ACTIONS = _agent_native_recovery_asset_lines("repair-forbidden-actions.md")
REPAIR_NEXT_ACTION = _agent_native_recovery_asset("repair-next-action.md")
REPAIR_NEXT_REPAIR_STEP = _agent_native_recovery_asset("repair-next-repair-step.md")
ALIGNMENT_QUESTION_SUBAGENT_POLICY = _agent_native_recovery_asset("alignment-question-subagent-policy.md")
ALIGNMENT_QUESTION_NEXT_MESSAGE_POLICY = _agent_native_recovery_asset("alignment-question-next-message-policy.md")
ALIGNMENT_QUESTION_NEXT_STEP = _agent_native_recovery_asset("alignment-question-next-step.md")
READY_RUN_NEXT_STEP = _agent_native_recovery_asset("ready-run-next-step.md")


def _attach_agent_gen_recovery_fields(result: dict) -> None:
    if result.get("ready"):
        return
    if str(result.get("status") or "").strip() == "skipped":
        result["loop_recovery"] = "alignment_skipped"
        result["requires_web_alignment"] = False
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
            result["repair_cli_command_policy"] = REPAIR_CLI_COMMAND_POLICY
        result["repair_reference"] = REPAIR_REFERENCE
        result["next_repair_step"] = REPAIR_NEXT_REPAIR_STEP
        action = _agent_plan_repair_action(result)
        if action:
            result["agent_work_panel"] = {
                "state": "repair_candidate_plan_file",
                "task_proven": False,
                "task_outcome": "not_ready_repair_candidate_plan_file",
                "next_action": action["next_action"],
                "evidence_focus": "validation_error and repair_focus from the rejected candidate plan",
                "todo_items": [
                    "edit the candidate plan file",
                    "rerun repair_cli_command exactly with compact JSON",
                    "start /loopora-run only after preview readiness",
                ],
            }
            result["repair_action"] = action
        return
    if result.get("continued_alignment_session") and result.get("requires_web_alignment"):
        result["loop_recovery"] = "continue_alignment_dialogue"
        result["ask_user"] = _latest_alignment_question(result)
        result["question_action"] = {
            "target": "main_agent_session",
            "must_wait_for_user_reply": True,
            "subagent_policy": ALIGNMENT_QUESTION_SUBAGENT_POLICY,
            "next_message_policy": ALIGNMENT_QUESTION_NEXT_MESSAGE_POLICY,
        }
        result["next_alignment_step"] = ALIGNMENT_QUESTION_NEXT_STEP
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
        result["review_reply_message"] = reply
        result["review_reply_preview"] = _clip_inline(reply, 260)
        command = _agent_review_message_cli_command(result, reply=reply)
        if command:
            result["message_cli_command"] = command
            result["next_plan_cli_command"] = command
    if result.get("loopora_fit_contradiction"):
        result["next_review_step"] = _agent_web_review_next_step(result, not_fit=True)
        return
    result["next_review_step"] = _agent_web_review_next_step(result, not_fit=False)
    result["after_review_ready"] = _agent_after_review_ready_message(result)
    result["run_blocked_until_web_review"] = "yes"
    result["after_review_cli_command_status"] = "blocked_until_web_review_complete"
    result["after_review_slash_command"] = _agent_entry_return_slash_command()
    command = _agent_entry_return_run_command(result)
    if command:
        result["after_web_review_cli_command"] = command
        result["after_review_cli_command"] = command
    result["after_review_command"] = command


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
    return f"{command} --json --compact-json"


def _agent_review_message_cli_command(result: dict, *, reply: str) -> str:
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    adapter = str(result.get("adapter") or binding.get("adapter") or binding.get("candidate_adapter") or "").strip()
    workdir = str(result.get("workdir") or binding.get("workdir") or "").strip()
    message = _agent_review_command_message(reply)
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
    )
    return f"{command} --json --compact-json"


def _agent_review_command_message(reply: str) -> str:
    return " ".join(str(reply or "").split()).strip()


def _agent_plan_repair_action(result: dict) -> dict[str, object]:
    plan_file = str(result.get("plan_file_to_repair") or "").strip()
    next_command = str(result.get("repair_cli_command") or result.get("repair_slash_command") or "").strip()
    action: dict[str, object] = {
        "state": "repair_candidate_plan_file",
        "next_action": REPAIR_NEXT_ACTION,
        "allowed_inputs": [
            "validation_error",
            "repair_focus",
            "repair_task_message",
            "managed Candidate Bundle Skeleton",
            "the candidate plan file itself",
        ],
        "forbidden_actions": list(REPAIR_FORBIDDEN_ACTIONS),
        "stop_before": "/loopora-run until the repaired preview returns ready=true",
    }
    if plan_file:
        action["file_to_edit"] = plan_file
    if next_command:
        action["command_after_edit"] = next_command
    return action


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
    result["ready_next_step"] = READY_RUN_NEXT_STEP
    result["ready_slash_command"] = _agent_entry_return_slash_command()
    command = _agent_entry_return_run_command(result)
    if command:
        result["ready_cli_command"] = command
        result["ready_run_command"] = command


def _agent_web_review_task_anchor_fields(result: dict) -> dict[str, str]:
    message = _agent_task_message_from_session(result)
    if not message:
        return {}
    language = _agent_web_review_language(result)
    if language == "es":
        if result.get("loopora_fit_contradiction"):
            status = (
                "ancla de tarea preservada desde /loopora-plan; hay que redefinir el encaje con Loopora antes "
                "de convertirla en un Loop ejecutable"
            )
        else:
            status = (
                "ancla de tarea preservada desde /loopora-plan; ningún plan candidato la ha proyectado todavía "
                "en un Loop ejecutable"
            )
        return {
            "task_anchor_status": status,
            "task_anchor_preview": _clip_inline(message, 260),
            "review_scope": "review_focus enumera las superficies de Loop que se compilan desde el ancla de tarea, no datos faltantes del chat",
        }
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
    language = _agent_web_review_language(result)
    if language == "es":
        if result.get("loopora_fit_contradiction"):
            return "no ejecutable; hay que redefinir si Loopora encaja"
        return "no ejecutable; no se envió ningún archivo de plan candidato"
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
    language = _agent_web_review_language(result)
    if language == "es":
        focus = [
            "Encaje con Loopora: explica qué aportan las rondas futuras más allá de una pasada de Agent",
            "Superficie de éxito: nombra el resultado visible para el usuario que debe probarse",
            "Riesgos de falso terminado: nombra estados superficiales que deben bloquear el cierre",
            "Expectativas de evidencia: nombra las pruebas, logs, rutas de navegador, auditorías o artefactos confiables",
            "Estrategia de ejecución y tradeoffs: di qué probar, reparar, acotar, expandir o diferir primero",
            "Riesgo residual y gobernanza local: nombra qué puede quedar, quién lo asume y qué reglas del proyecto deben leerse o bloquear",
        ]
        if result.get("loopora_fit_contradiction"):
            focus[0] = (
                "Encaje con Loopora: define evidencia posterior, handoffs o valor de decisión de GateKeeper antes "
                "de crear un Loop ejecutable"
            )
        return focus
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


def _agent_web_review_next_step(result: dict, *, not_fit: bool) -> str:
    language = _agent_web_review_language(result)
    if language == "es":
        if not_fit:
            return (
                "responde con review_reply_preview para omitir la generación del Loop, o explica qué evidencia nueva, "
                "handoffs o valor de GateKeeper aportan las rondas futuras antes de pedir un Loop ejecutable"
            )
        return "abre la URL de preview, completa la checklist de Web review y usa /loopora-run solo cuando la vista previa esté lista"
    if not_fit:
        return (
            "reply with review_reply_preview to skip Loop generation, or explain why later rounds add new evidence, "
            "handoffs, or GateKeeper value before asking for a runnable Loop"
        )
    return "open the preview URL, complete the Web review checklist, then use /loopora-run only after the preview is ready"


def _agent_after_review_ready_message(result: dict) -> str:
    if _agent_web_review_language(result) == "es":
        return "vuelve a esta sesión de Agent y ejecuta /loopora-run; no inicies la ejecución desde Agent Runner en Web"
    return READY_RUN_NEXT_STEP


def _agent_web_review_language(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    return agent_entry_review_language(session)


def _agent_gen_error_summary(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    return str(session.get("error_message") or validation.get("error") or "").strip()
