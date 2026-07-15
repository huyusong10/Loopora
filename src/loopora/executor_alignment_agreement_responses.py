from __future__ import annotations

from loopora.executor_alignment_readiness_responses import (
    alignment_chinese_improvement_readiness_evidence,
    alignment_chinese_readiness_evidence,
    alignment_improvement_readiness_evidence,
    alignment_readiness_evidence,
)


def _session_ref() -> dict:
    return {
        "session_id": "",
        "thread_id": "",
        "conversation_id": "",
        "provider": "fake",
        "raw_json": "",
    }


def _decision_options(*, chinese: bool) -> list[dict]:
    if chinese:
        return [
            {
                "id": "confirm_agreement",
                "label": "采用这个方向（推荐）",
                "description": "按这份工作协议生成 Loop 方案。",
                "recommended": True,
                "user_reply": "确认，采用这个方向。",
            },
            {
                "id": "adjust_agreement",
                "label": "我想调整",
                "description": "先修改其中一个判断，再生成方案。",
                "recommended": False,
                "user_reply": "我想调整这份工作协议：",
            },
        ]
    return [
        {
            "id": "confirm_agreement",
            "label": "Use this direction (recommended)",
            "description": "Compile the Loop from this working agreement.",
            "recommended": True,
            "user_reply": "Confirm this working agreement.",
        },
        {
            "id": "adjust_agreement",
            "label": "Adjust it",
            "description": "Revise one judgment before compilation.",
            "recommended": False,
            "user_reply": "I want to adjust this working agreement:",
        },
    ]


def _agreement_payload(
    *,
    assistant_message: str,
    summary: str,
    readiness_evidence: dict,
    chinese: bool,
) -> dict:
    return {
        "status": "question",
        "assistant_message": assistant_message,
        "needs_user_input": True,
        "decision_options": _decision_options(chinese=chinese),
        "bundle_yaml": "",
        "session_ref": _session_ref(),
        "alignment_phase": "agreement",
        "agreement_summary": summary,
        "readiness_checklist": {
            "loop_fit": True,
            "task_scope": True,
            "success_surface": True,
            "fake_done_risks": True,
            "evidence_preferences": True,
            "execution_strategy": True,
            "residual_risk_policy": True,
            "judgment_tradeoffs": True,
            "local_governance": True,
            "role_posture": True,
            "workflow_shape": True,
            "explicit_confirmation": False,
        },
        "readiness_evidence": readiness_evidence,
    }


def alignment_agreement_response() -> dict:
    return _agreement_payload(
        assistant_message=(
            "Please confirm this working agreement. I will compile a focused Builder, evidence Inspector, "
            "repair handoff, and conservative GateKeeper into the Loop."
        ),
        summary="Use a focused Builder, evidence Inspector, repair handoff, and strict GateKeeper.",
        readiness_evidence=alignment_readiness_evidence(
            open_questions="Waiting for explicit user confirmation of the working agreement."
        ),
        chinese=False,
    )


def alignment_chinese_agreement_response() -> dict:
    return _agreement_payload(
        assistant_message="请确认这份工作协议；我会把聚焦实现、证据检查、修复交接和保守裁决编译进 Loop。",
        summary="使用聚焦 Builder、证据 Inspector、修复交接和严格 GateKeeper 推进任务。",
        readiness_evidence=alignment_chinese_readiness_evidence(open_questions="等待用户明确确认这份工作协议。"),
        chinese=True,
    )


def alignment_improvement_agreement_response() -> dict:
    payload = alignment_agreement_response()
    payload["assistant_message"] = (
        "Please confirm this improvement agreement; I will preserve stable task intent and revise only the "
        "feedback-driven governance surfaces."
    )
    payload["agreement_summary"] = (
        "Preserve stable task intent and workdir while strengthening evidence, role posture, and closure judgment."
    )
    payload["readiness_evidence"] = alignment_improvement_readiness_evidence(
        open_questions="Waiting for explicit user confirmation of the improvement agreement."
    )
    return payload


def alignment_chinese_improvement_agreement_response() -> dict:
    payload = alignment_chinese_agreement_response()
    payload["assistant_message"] = "请确认这份改进协议；我会保留稳定任务意图，只修订反馈指向的治理面。"
    payload["agreement_summary"] = "保留稳定任务意图和 workdir，并基于反馈加强证据、角色姿态和收束裁决。"
    payload["readiness_evidence"] = alignment_chinese_improvement_readiness_evidence(
        open_questions="等待用户明确确认这份改进协议。"
    )
    return payload


def alignment_chinese_refactor_improvement_agreement_response(feedback_text: str) -> dict:
    payload = alignment_chinese_improvement_agreement_response()
    feedback = str(feedback_text or "用户要求在任务边界内做更深的重构。")
    payload["assistant_message"] = "请确认这份重构改进协议；确认后我会把重构边界、回归证据和阻断条件编译进 Loop。"
    payload["agreement_summary"] = "保留任务目标与 workdir，只接受有基线、回归证据和可审计 handoff 的重构。"
    payload["readiness_evidence"].update(
        {
            "task_scope": f"重构只覆盖用户反馈点名的任务边界，不扩展成开放式平台重写。用户反馈：{feedback}",
            "success_surface": "重构后的行为、复杂度变化、回归结果和证据路径都可以被独立复验。",
            "fake_done_risks": "拒绝只移动复杂度、只增加抽象、只更新文案或缺少 before/after 回归证据的结果。",
            "evidence_preferences": "优先使用基线、聚焦检查、回归结果、复杂度报告、artifact 和角色 handoff。",
            "execution_strategy": "先锁定基线和边界，再实施最小完整重构；Inspector 反证回归与复杂度转移，GateKeeper 最后裁决。",
            "residual_risk_policy": "行为回归、证据不可复验、复杂度转移或跳过本地治理必须阻断。",
            "judgment_tradeoffs": "优先可证明的结构简化，不用更宽的改动或更多角色伪装成深度。",
            "role_posture": "Builder 简化实现，Inspector 验证行为与复杂度，Guide 收窄修复，GateKeeper 对未证明结果 fail closed。",
            "workflow_shape": "Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper，每轮产生可引用证据。",
        }
    )
    return payload


def alignment_task_anchored_agreement_response(
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> dict:
    task = str(task_text or "").strip() or ("用户确认的任务" if prefers_chinese else "the user-confirmed task")
    language = str(display_language or "").strip().lower()
    if prefers_chinese or language == "zh":
        return alignment_chinese_task_anchored_agreement_response(task)
    if language == "es":
        return alignment_spanish_task_anchored_agreement_response(task)
    return alignment_english_task_anchored_agreement_response(task)


def _task_readiness_evidence(task: str, *, language: str) -> dict:
    if language == "zh":
        return {
            "loop_fit": f"任务“{task}”需要多轮实现、反证、修复和裁决；最终反馈太晚，不能作为唯一控制信号。",
            "task_scope": f"范围以用户任务锚点为准：{task}。不得用关键词推断未确认的业务域或技术栈。",
            "success_surface": "核心声明必须映射到用户可观察行为、持久 artifact、命令结果或可引用 handoff。",
            "fake_done_risks": "拒绝 happy-path-only、mock-only、截图、状态更新、文案总结或仅增加证据数量的完成声明。",
            "evidence_preferences": "优先使用项目检查、负向路径、运行结果、artifact、日志和带稳定引用的角色 handoff。",
            "execution_strategy": "Builder 交付最小真实闭环，Inspector 反证，Guide 收窄修复，Repair Builder 补缺口，GateKeeper 裁决。",
            "residual_risk_policy": "核心声明、阻断缺口或必需证据未证明时 fail closed；仅允许已点名、可见且有 owner 的范围外风险。",
            "judgment_tradeoffs": "优先小而可证明的闭环，不用更宽、更快或更漂亮但证据薄弱的实现换取通过。",
            "local_governance": "若 workdir 存在适用的 AGENTS、design、schema 或 tests，执行前读取，裁决时验证。",
            "role_posture": "Builder 改动目标，Inspector 质疑声明，Guide 收窄修复，GateKeeper 独立判断是否收束。",
            "workflow_shape": "使用线性、可解释的 Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper 工作流。",
            "workdir_facts": "只把运行时实际观察到的路径、工具和治理入口当作 workdir 事实。",
            "open_questions": "等待用户明确确认这份工作协议。",
        }
    if language == "es":
        return {
            "loop_fit": f"La tarea «{task}» necesita varias rondas de implementación, refutación, reparación y juicio.",
            "task_scope": f"El alcance permanece anclado en la tarea confirmada: {task}.",
            "success_surface": "Las afirmaciones centrales requieren comportamiento observable, artefactos duraderos o resultados reproducibles.",
            "fake_done_risks": "No pasan capturas, mocks, happy path, cambios de estado o resúmenes sin prueba directa.",
            "evidence_preferences": "Se prefieren checks del proyecto, rutas negativas, resultados, artefactos, logs y handoffs con referencias estables.",
            "execution_strategy": "Builder entrega el cierre mínimo; Inspector refuta; Guide limita la reparación; GateKeeper juzga.",
            "residual_risk_policy": "Falta de evidencia requerida o blockers impide el cierre; solo riesgos visibles y con dueño pueden quedar.",
            "judgment_tradeoffs": "Se prefiere un cierre pequeño y probado sobre trabajo amplio con evidencia débil.",
            "local_governance": "Se leen y verifican las reglas, diseños, schemas y pruebas aplicables del workdir.",
            "role_posture": "Builder cambia el objetivo, Inspector cuestiona, Guide limita la reparación y GateKeeper decide.",
            "workflow_shape": "Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper, con handoffs explícitos.",
            "workdir_facts": "Solo rutas, herramientas y reglas observadas durante la ejecución cuentan como hechos.",
            "open_questions": "Esperando confirmación explícita del acuerdo de trabajo.",
        }
    return {
        "loop_fit": f"The task '{task}' needs repeated implementation, challenge, repair, and judgment; final feedback is too late to be the only control signal.",
        "task_scope": f"Scope stays anchored to the confirmed user task: {task}. Keywords do not imply an unreviewed business domain or stack.",
        "success_surface": "Core claims map to user-observable behavior, durable artifacts, command results, or referenceable handoffs.",
        "fake_done_risks": "Reject happy-path-only, mock-only, screenshot, status, prose, or evidence-count-only completion claims.",
        "evidence_preferences": "Prefer project checks, negative paths, runtime results, artifacts, logs, and role handoffs with stable references.",
        "execution_strategy": "Builder delivers the smallest real loop; Inspector challenges it; Guide narrows repair; Repair Builder fills named gaps; GateKeeper judges.",
        "residual_risk_policy": "Missing required proof or blocking gaps fail closed; only named, visible, owned out-of-scope risks may remain.",
        "judgment_tradeoffs": "Prefer a narrow proven loop over broader, faster, or more polished work with weak evidence.",
        "local_governance": "Read applicable workdir AGENTS, design, schema, and tests before execution and verify them at judgment time.",
        "role_posture": "Builder changes the target, Inspector challenges claims, Guide narrows repair, and GateKeeper independently judges closure.",
        "workflow_shape": "Use an explainable Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper sequence with explicit handoffs.",
        "workdir_facts": "Only paths, tools, and governance entries observed at runtime count as workdir facts.",
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }


def alignment_english_task_anchored_agreement_response(task_text: str) -> dict:
    task = str(task_text or "").strip() or "the user-confirmed task"
    return _agreement_payload(
        assistant_message="Please confirm this task-anchored working agreement; confirmation compiles it into a runnable Loop.",
        summary=f"Govern the confirmed task through evidence and independent closure judgment: {task}",
        readiness_evidence=_task_readiness_evidence(task, language="en"),
        chinese=False,
    )


def alignment_chinese_task_anchored_agreement_response(task_text: str) -> dict:
    task = str(task_text or "").strip() or "用户确认的任务"
    return _agreement_payload(
        assistant_message="请确认这份任务锚定工作协议；确认后我会把它编译成可运行 Loop。",
        summary=f"通过证据与独立收束裁决治理用户确认的任务：{task}",
        readiness_evidence=_task_readiness_evidence(task, language="zh"),
        chinese=True,
    )


def alignment_spanish_task_anchored_agreement_response(task_text: str) -> dict:
    task = str(task_text or "").strip() or "la tarea confirmada por el usuario"
    return _agreement_payload(
        assistant_message="Confirma este acuerdo anclado en la tarea; después se compilará en un Loop ejecutable.",
        summary=f"Gobernar la tarea confirmada mediante evidencia y juicio independiente: {task}",
        readiness_evidence=_task_readiness_evidence(task, language="es"),
        chinese=False,
    )


def alignment_refund_agreement_response() -> dict:
    return alignment_english_task_anchored_agreement_response(
        "deliver a safe refund flow with authorization, failure, audit, and duplicate-prevention evidence"
    )


def alignment_chinese_refund_agreement_response() -> dict:
    return alignment_chinese_task_anchored_agreement_response("交付有授权、失败处理、审计和重复退款防护证据的安全退款流程")
