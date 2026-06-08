from __future__ import annotations

from loopora.agent_adapters import agent_loop_json_command
from loopora.service_alignment_agreement_stage import alignment_agreement_text_snippet
from loopora.service_alignment_language import alignment_prefers_chinese, alignment_prefers_spanish
from loopora.structured_numbers import structured_non_negative_int


def agent_entry_candidate_payload(candidate_event: dict) -> dict:
    return candidate_event.get("payload") if isinstance(candidate_event.get("payload"), dict) else {}


def agent_entry_candidate_adapter(session: dict, payload: dict) -> str:
    return str(payload.get("adapter") or session.get("executor_kind") or "").strip()


def agent_entry_review_language(session: dict) -> str:
    if alignment_prefers_chinese(session):
        return "zh"
    if alignment_prefers_spanish(session):
        return "es"
    return "en"


def agent_entry_review_suggested_reply(session: dict, *, review_mode: str, task_message: str) -> str:
    task_anchor = alignment_agreement_text_snippet(task_message, limit=520)
    language = agent_entry_review_language(session)
    if language == "zh":
        if review_mode == "not_fit":
            return (
                "请先按这次 /loopora-plan 的任务锚点重新判断是否适合 Loopora："
                f"{task_anchor}\n"
                "如果仍要继续，请明确后续轮次会新增哪些证据、handoff 或 GateKeeper 裁决价值；"
                "如果不适合，请不要生成可运行 Loop。"
            )
        return (
            "请基于这次 /loopora-plan 的任务锚点继续 Web review："
            f"{task_anchor}\n"
            "推荐采用证据优先路径：先确认 Loopora fit，再把完成标准、伪完成风险、证据预期、"
            "执行策略、判断取舍、残余风险和本地治理责任整理成可确认的工作协议；"
            "确认后再生成可审查的 Loop 预览。"
        )
    if language == "es":
        if review_mode == "not_fit":
            return (
                "Primero vuelve a comprobar si este ancla de tarea de /loopora-plan encaja con Loopora: "
                f"{task_anchor}\n"
                "Si debemos continuar, explica qué evidencia posterior, handoffs o juicio de GateKeeper aportarán valor; "
                "si no encaja, no generes un Loop ejecutable."
            )
        return (
            "Continuar Web review desde este ancla de tarea de /loopora-plan: "
            f"{task_anchor}\n"
            "Usa el camino de evidencia primero: confirma primero el encaje con Loopora y luego convierte los criterios "
            "de éxito, riesgos de falso terminado, expectativas de evidencia, estrategia de ejecución, tradeoffs de "
            "juicio, política de riesgo residual y gobernanza local en un acuerdo de trabajo confirmable antes de "
            "generar una vista previa revisable del Loop."
        )
    if review_mode == "not_fit":
        return (
            "First re-check whether this /loopora-plan task anchor fits Loopora: "
            f"{task_anchor}\n"
            "If we should continue, explain what later evidence, handoffs, or GateKeeper judgment would add; "
            "if it does not fit, do not generate a runnable Loop."
        )
    return (
        "Continue Web review from this /loopora-plan task anchor: "
        f"{task_anchor}\n"
        "Use the evidence-first path: first confirm Loopora fit, then turn the success criteria, fake-done risks, "
        "evidence expectations, execution strategy, judgment tradeoffs, residual-risk policy, and local governance "
        "into a confirmable working agreement before generating a reviewable Loop preview."
    )


def agent_entry_review_decision_options(session: dict, *, review_mode: str, task_message: str) -> list[dict]:
    suggested_reply = agent_entry_review_suggested_reply(session, review_mode=review_mode, task_message=task_message)
    task_anchor = alignment_agreement_text_snippet(task_message, limit=420)
    language = agent_entry_review_language(session)
    if language == "zh":
        if review_mode == "not_fit":
            return [
                {
                    "id": "skip_loop",
                    "label": "先不生成 Loop（推荐）",
                    "description": "任务锚点更像一次性任务或已有硬检查足够，先避免把它包装成长期 Loop。",
                    "recommended": True,
                    "user_reply": f"同意，先不生成 Loop 方案。本次任务锚点：{task_anchor}",
                },
                {
                    "id": "reframe_as_loop",
                    "label": "重定义成长期 Loop",
                    "description": "我会说明后续证据、handoff 或 GateKeeper 裁决为什么值得保留。",
                    "recommended": False,
                    "user_reply": suggested_reply,
                },
            ]
        return [
            {
                "id": "continue_web_review_evidence_first",
                "label": "按证据优先继续 Web review（推荐）",
                "description": "把宿主 Agent 的任务锚点转成可确认工作协议，再生成 Loop 预览。",
                "recommended": True,
                "user_reply": suggested_reply,
            },
            {
                "id": "recheck_loop_fit",
                "label": "先重新判断是否需要 Loop",
                "description": "如果这其实是一轮任务或已有检查足够，先阻止编排。",
                "recommended": False,
                "user_reply": (
                    "请先重新判断这个任务是否适合 Loopora，而不是直接生成 Loop。"
                    f"任务锚点：{task_anchor}"
                ),
            },
        ]
    if language == "es":
        if review_mode == "not_fit":
            return [
                {
                    "id": "skip_loop",
                    "label": "Omitir Loop por ahora (recomendado)",
                    "description": "El ancla parece una tarea puntual o ya cubierta por comprobaciones duras; evita empaquetarla como Loop de larga duración.",
                    "recommended": True,
                    "user_reply": f"De acuerdo; no generes un plan Loop por ahora. Ancla de tarea: {task_anchor}",
                },
                {
                    "id": "reframe_as_loop",
                    "label": "Reformular como Loop",
                    "description": "Explicaré por qué la evidencia posterior, los handoffs o el juicio de GateKeeper deben conservarse.",
                    "recommended": False,
                    "user_reply": suggested_reply,
                },
            ]
        return [
            {
                "id": "continue_web_review_evidence_first",
                "label": "Continuar revisión con evidencia primero (recomendado)",
                "description": "Convierte el ancla del Agent anfitrión en un acuerdo de trabajo confirmable y luego genera la vista previa del Loop.",
                "recommended": True,
                "user_reply": suggested_reply,
            },
            {
                "id": "recheck_loop_fit",
                "label": "Revisar primero el encaje con Loopora",
                "description": "Si basta una sola pasada o las comprobaciones duras ya deciden, bloquea la composición primero.",
                "recommended": False,
                "user_reply": (
                    "Primero revisa si esta tarea realmente encaja con Loopora antes de generar un Loop. "
                    f"Ancla de tarea: {task_anchor}"
                ),
            },
        ]
    if review_mode == "not_fit":
        return [
            {
                "id": "skip_loop",
                "label": "Skip Loop (Recommended)",
                "description": "The task anchor looks one-off or already covered by hard checks, so do not package it as a long-running Loop.",
                "recommended": True,
                "user_reply": f"Agreed; do not generate a Loop plan yet. Task anchor: {task_anchor}",
            },
            {
                "id": "reframe_as_loop",
                "label": "Reframe as a Loop",
                "description": "I will explain why later evidence, handoffs, or GateKeeper judgment should survive.",
                "recommended": False,
                "user_reply": suggested_reply,
            },
        ]
    return [
        {
            "id": "continue_web_review_evidence_first",
            "label": "Continue evidence-first review (Recommended)",
            "description": "Turn the host Agent task anchor into a confirmable working agreement, then generate the Loop preview.",
            "recommended": True,
            "user_reply": suggested_reply,
        },
        {
            "id": "recheck_loop_fit",
            "label": "Re-check Loop fit",
            "description": "If this is only one pass or hard checks already decide it, block composition first.",
            "recommended": False,
            "user_reply": (
                "Please re-check whether this task actually fits Loopora before generating a Loop. "
                f"Task anchor: {task_anchor}"
            ),
        },
    ]


def agent_entry_review_projection(
    session: dict,
    *,
    candidate_event: dict,
    task_message: str,
    missing_judgment_item_ids: list[str],
) -> dict:
    if not candidate_event:
        return {}
    payload = agent_entry_candidate_payload(candidate_event)
    requires_web_alignment = payload.get("requires_web_alignment") is True
    requires_candidate_repair = payload.get("requires_candidate_repair") is True
    loopora_fit_contradiction = payload.get("loopora_fit_contradiction") is True
    review_mode = "not_fit" if loopora_fit_contradiction else "missing_candidate_plan"
    status = str(session.get("status") or "")
    stage = str(session.get("alignment_stage") or "")
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    agreement_started = bool(str(agreement.get("summary") or "").strip()) or stage in {
        "agreement_ready",
        "confirmed",
        "compiling",
        "ready_review",
    }
    if not requires_web_alignment or status in {"ready", "imported", "running_loop"} or agreement_started:
        return {}
    suggested_reply = agent_entry_review_suggested_reply(
        session,
        review_mode=review_mode,
        task_message=task_message,
    )
    return {
        "schema_version": 1,
        "source": "agent_entry",
        "review_mode": review_mode,
        "not_runnable": status != "ready",
        "requires_web_alignment": requires_web_alignment,
        "requires_candidate_repair": requires_candidate_repair,
        "has_candidate_yaml": payload.get("has_candidate_yaml") is True,
        "loopora_fit_contradiction": loopora_fit_contradiction,
        "adapter": str(payload.get("adapter") or session.get("executor_kind") or ""),
        "entry_source": str(payload.get("entry_source") or ""),
        "source_path": str(payload.get("source_path") or ""),
        "candidate_sha256": str(payload.get("candidate_sha256") or ""),
        "candidate_bytes": structured_non_negative_int(payload.get("candidate_bytes"), default=0),
        "ready_candidate_sha256": str(payload.get("ready_candidate_sha256") or ""),
        "ready_candidate_bytes": structured_non_negative_int(payload.get("ready_candidate_bytes"), default=0),
        "task_message": task_message,
        "missing_judgment_item_ids": list(missing_judgment_item_ids),
        "suggested_reply": suggested_reply,
        "decision_options": agent_entry_review_decision_options(
            session,
            review_mode=review_mode,
            task_message=task_message,
        ),
    }


def agent_entry_launch_projection(session: dict, *, candidate_event: dict, ready_event: dict | None = None) -> dict:
    if not candidate_event:
        return {}
    payload = agent_entry_candidate_payload(candidate_event)
    adapter = str(payload.get("adapter") or session.get("executor_kind") or "").strip()
    if not adapter:
        return {}
    entry_source = str(payload.get("entry_source") or "").strip()
    host_context_id = str(payload.get("host_context_id") or "").strip()
    workdir = str(session.get("workdir") or "").strip()
    ready_payload = ready_event.get("payload") if isinstance((ready_event or {}).get("payload"), dict) else {}
    ready_sha = str(ready_payload.get("ready_candidate_sha256") or payload.get("ready_candidate_sha256") or "").strip()
    ready_bytes = structured_non_negative_int(
        ready_payload.get("ready_candidate_bytes", payload.get("ready_candidate_bytes")),
        default=0,
    )
    return {
        "schema_version": 1,
        "source": "agent_entry",
        "adapter": adapter,
        "entry_source": entry_source,
        "host_context_id": host_context_id,
        "slash_command": "/loopora-run",
        "loop_command": agent_loop_json_command(
            adapter,
            workdir,
            entry_source=entry_source,
            context_id=host_context_id,
        ),
        "workdir": workdir,
        "candidate_sha256": str(payload.get("candidate_sha256") or ""),
        "candidate_bytes": structured_non_negative_int(payload.get("candidate_bytes"), default=0),
        "ready_candidate_sha256": ready_sha,
        "ready_candidate_bytes": ready_bytes,
    }
