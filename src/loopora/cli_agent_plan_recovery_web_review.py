from __future__ import annotations

from loopora.cli_agent_plan_recovery_assets import NEXT_PLAN_CLI_COMMAND_POLICY, READY_RUN_NEXT_STEP
from loopora.cli_agent_plan_recovery_common import (
    _agent_entry_return_run_command,
    _agent_entry_return_slash_command,
    _agent_entry_review,
    _agent_review_message_cli_command,
    _agent_task_message_from_session,
    _agent_web_review_language,
    _recommended_review_option,
)
from loopora.cli_summary_helpers import clip_inline as _clip_inline


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
            result["next_plan_cli_command_policy"] = NEXT_PLAN_CLI_COMMAND_POLICY
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


def _agent_web_review_task_anchor_fields(result: dict) -> dict[str, str]:
    message = _agent_task_message_from_session(result)
    if not message:
        return {}
    language = _agent_web_review_language(result)
    if language == "es":
        if result.get("loopora_fit_contradiction"):
            status = "ancla de tarea preservada desde /loopora-plan; hay que redefinir el encaje con Loopora antes de convertirla en un Loop ejecutable"
        else:
            status = "ancla de tarea preservada desde /loopora-plan; ningún plan candidato la ha proyectado todavía en un Loop ejecutable"
        return {
            "task_anchor_status": status,
            "task_anchor_preview": _clip_inline(message, 260),
            "review_scope": "review_focus enumera las superficies de Loop que se compilan desde el ancla de tarea, no datos faltantes del chat",
        }
    if result.get("loopora_fit_contradiction"):
        status = "task anchor preserved from /loopora-plan; Loopora fit must be redefined before it can become a runnable Loop"
    else:
        status = "task anchor preserved from /loopora-plan; no candidate plan has projected it into a runnable Loop yet"
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
            focus[0] = "Encaje con Loopora: define evidencia posterior, handoffs o valor de decisión de GateKeeper antes de crear un Loop ejecutable"
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
        return "vuelve a esta sesión de Agent y ejecuta /loopora-run; no inicies esta ejecución same-Agent desde Web"
    return READY_RUN_NEXT_STEP
