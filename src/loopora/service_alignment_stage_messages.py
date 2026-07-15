from __future__ import annotations

from dataclasses import dataclass

from loopora.service_alignment_clarifying_questions import alignment_clarifying_question_issues
from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.service_alignment_decision_options import (
    alignment_needs_user_input,
    default_alignment_decision_options,
    not_fit_alignment_decision_options,
)
from loopora.service_alignment_language import alignment_assistant_message_language_issue


@dataclass(frozen=True)
class AlignmentOutputMessagePlan:
    assistant_message: str
    bundle_yaml: str
    missing_items: list[str] | None
    has_bundle_for_options: bool
    event_type: str = ""
    event_payload: dict | None = None
    force_needs_user_input: bool = False
    use_default_decision_options: bool = False


@dataclass(frozen=True)
class AlignmentAgreementBlockCandidate:
    issues: list[str]
    event_type: str
    fallback_message: str


@dataclass(frozen=True)
class AlignmentAgreementBlockPlan:
    event_type: str
    event_payload: dict
    output_updates: dict


@dataclass(frozen=True)
class AlignmentClarifyingStagePlan:
    update_fields: dict
    output_updates: dict
    event_type: str = ""
    event_payload: dict | None = None


def alignment_agreement_block_plan(
    candidates: list[AlignmentAgreementBlockCandidate],
    *,
    prefers_chinese: bool,
    display_language: str = "",
    not_fit_source_text: str = "",
) -> AlignmentAgreementBlockPlan | None:
    for candidate in candidates:
        missing = list(candidate.issues)
        if not missing:
            continue
        use_not_fit = alignment_block_should_offer_skip_loop(missing, not_fit_source_text)
        return AlignmentAgreementBlockPlan(
            event_type=candidate.event_type,
            event_payload={"alignment_stage": "clarifying", "missing": missing},
            output_updates={
                "alignment_phase": "clarifying",
                "agreement_summary": "",
                "bundle_yaml": "",
                "needs_user_input": True,
                "alignment_missing_items": missing,
                "assistant_message": (
                    alignment_not_fit_block_message(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                    )
                    if use_not_fit
                    else alignment_block_message(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                        event_type=candidate.event_type,
                        missing=missing,
                        fallback_zh=candidate.fallback_message,
                    )
                ),
                "decision_options": (
                    not_fit_alignment_decision_options(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                    )
                    if use_not_fit
                    else default_alignment_decision_options(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                    )
                ),
            },
        )
    return None


def alignment_block_should_offer_skip_loop(missing: list[str], source_text: str) -> bool:
    return "loop_fit" in set(missing) and text_mentions_loop_fit_contradiction(source_text)


def alignment_not_fit_block_message(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return (
            "这看起来更像一次性任务、直接回答或已有检查足够裁决的工作，不适合先编排成 Loop。"
            "除非后续轮次会产生一次 Agent 执行没有的新证据、handoff 或 GateKeeper 判断，否则建议先不生成 Loop。"
        )
    if str(display_language or "").strip().lower() == "es":
        return (
            "Esto parece una tarea puntual, respuesta directa, o trabajo ya cubierto por checks existentes; "
            "no conviene componerlo como Loop todavía. Salvo que rondas posteriores produzcan evidencia, handoffs "
            "o juicio de GateKeeper que una sola pasada no produciría, recomiendo omitir el Loop."
        )
    return (
        "This looks like one-off work, a direct answer, or work already decided by existing checks, "
        "so it is not suitable to compose as a Loop yet. Unless later rounds would create new evidence, "
        "handoffs, or GateKeeper judgment that one Agent pass would not, skip Loop generation for now."
    )


def alignment_output_message_plan(  # noqa: PLR0913 - output planning keeps stage, missing-item, and language gates explicit.
    output: dict,
    *,
    stage_error: str,
    stage_missing_items: list[str] | None = None,
    missing_items: list[str] | None,
    prefers_chinese: bool,
    display_language: str = "",
) -> AlignmentOutputMessagePlan:
    assistant_message = str(output.get("assistant_message", "") or "").strip()
    bundle_yaml = str(output.get("bundle_yaml", "") or "").strip()
    if stage_error:
        event_payload = {"status": "waiting_user", "error": stage_error}
        if stage_missing_items:
            event_payload["missing"] = list(stage_missing_items)
        return AlignmentOutputMessagePlan(
            assistant_message=stage_error,
            bundle_yaml="",
            missing_items=None,
            has_bundle_for_options=False,
            event_type="alignment_stage_blocked",
            event_payload=event_payload,
            force_needs_user_input=True,
            use_default_decision_options=True,
        )
    if assistant_message and alignment_assistant_message_language_issue(
        assistant_message,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    ):
        return AlignmentOutputMessagePlan(
            assistant_message=alignment_fallback_assistant_message(
                has_bundle=bool(bundle_yaml),
                needs_user_input=alignment_needs_user_input(output),
                display_language=display_language,
            ),
            bundle_yaml=bundle_yaml,
            missing_items=missing_items,
            has_bundle_for_options=bool(bundle_yaml),
            event_type="alignment_language_mismatch",
            event_payload={"missing": ["assistant_message"], "surface": "assistant_message"},
            use_default_decision_options=True,
        )
    return AlignmentOutputMessagePlan(
        assistant_message=assistant_message,
        bundle_yaml=bundle_yaml,
        missing_items=missing_items,
        has_bundle_for_options=bool(bundle_yaml),
    )


def alignment_block_message(
    *,
    prefers_chinese: bool,
    display_language: str = "",
    event_type: str,
    missing: list[str],
    fallback_zh: str,
) -> str:
    labels = ", ".join(
        alignment_missing_item_label(
            item,
            prefers_chinese=prefers_chinese,
            display_language=display_language,
        )
        for item in missing
    )
    followup = alignment_missing_items_followup_question(
        missing,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    if prefers_chinese:
        return _alignment_block_message_with_followup(
            fallback_zh.format(missing=labels),
            followup=followup,
            event_type=event_type,
            prefers_chinese=True,
            display_language=display_language,
        )
    message = alignment_block_message_base(
        event_type=event_type,
        labels=labels,
        fallback=fallback_zh,
        display_language=display_language,
    )
    return _alignment_block_message_with_followup(
        message,
        followup=followup,
        event_type=event_type,
        prefers_chinese=False,
        display_language=display_language,
    )


def alignment_block_message_base(*, event_type: str, labels: str, fallback: str, display_language: str = "") -> str:
    if str(display_language or "").strip().lower() == "es":
        return alignment_block_message_base_es(event_type=event_type, labels=labels)
    return alignment_block_message_base_en(event_type=event_type, labels=labels, fallback=fallback)


def alignment_block_message_base_en(*, event_type: str, labels: str, fallback: str) -> str:
    if event_type == "alignment_checklist_incomplete":
        return (
            "I can't prepare the confirmation agreement yet; these readiness checks are incomplete: "
            f"{labels}."
        )
    if event_type == "alignment_evidence_incomplete":
        return (
            "I can't prepare the confirmation agreement yet; this readiness evidence is not specific enough: "
            f"{labels}."
        )
    if event_type == "alignment_improvement_incomplete":
        return (
            "I can't prepare the improvement agreement yet; these source-based improvement judgments "
            f"are not specific enough: {labels}."
        )
    if event_type == "alignment_language_mismatch":
        return (
            "I can't prepare the confirmation agreement yet; these user-facing agreement fields need "
            f"the user's language: {labels}. Please rewrite those judgments."
        )
    return fallback.format(missing=labels)


def alignment_block_message_base_es(*, event_type: str, labels: str) -> str:
    if event_type == "alignment_checklist_incomplete":
        return f"Todavía no puedo preparar el acuerdo de confirmación; estas revisiones de preparación están incompletas: {labels}."
    if event_type == "alignment_evidence_incomplete":
        return f"Todavía no puedo preparar el acuerdo de confirmación; esta evidencia de preparación no es suficientemente específica: {labels}."
    if event_type == "alignment_improvement_incomplete":
        return f"Todavía no puedo preparar el acuerdo de mejora; estos juicios basados en la fuente no son suficientemente específicos: {labels}."
    if event_type == "alignment_language_mismatch":
        return f"Todavía no puedo preparar el acuerdo de confirmación; estos campos visibles necesitan el idioma del usuario: {labels}. Reescribe esos juicios."
    return f"Todavía no puedo preparar el acuerdo de confirmación; faltan estos juicios: {labels}."


def _alignment_block_message_with_followup(
    message: str,
    *,
    followup: str,
    event_type: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    if not followup or event_type == "alignment_language_mismatch":
        return message
    if prefers_chinese:
        suffix = f"下一步请回答：{followup}"
    elif str(display_language or "").strip().lower() == "es":
        suffix = f"Responde: {followup}"
    else:
        suffix = f"Please answer: {followup}"
    return f"{message} {suffix}"


def alignment_missing_items_followup_question(
    missing: list[str],
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    for item in missing:
        question = alignment_missing_item_followup_question(
            item,
            prefers_chinese=prefers_chinese,
            display_language=display_language,
        )
        if question:
            return question
    if str(display_language or "").strip().lower() == "es":
        return "¿Qué juicio debería cambiar la división de roles, la puerta de evidencia o la condición de cierre del Loop?"
    return (
        "这次哪一个判断会真正改变 Loop 的角色分工、证据门槛或收尾条件？"
        if prefers_chinese
        else "Which judgment should change the Loop's role split, evidence gate, or closure condition?"
    )


def alignment_missing_item_followup_question(item: str, *, prefers_chinese: bool, display_language: str = "") -> str:
    normalized = str(item or "").strip()
    questions = {
        "workdir_facts": (
            "Which project facts are already observed, and which must the Loop verify at runtime?",
            "哪些项目事实已经观察到，哪些必须让 Loop 在运行时验证？",
            "¿Qué hechos del proyecto ya están observados y cuáles debe verificar el Loop en ejecución?",
        ),
        "task_scoped_judgment": (
            "What concrete user task or workflow should this Loop govern?",
            "这次 Loop 应该治理哪一个具体用户任务或工作流？",
            "¿Qué tarea o flujo concreto del usuario debe gobernar este Loop?",
        ),
        "loop_fit": (
            "What new evidence or handoff will later rounds produce that one Agent pass would not?",
            "后续轮次会产生什么一次 Agent 执行不会产生的新证据或交接？",
            "¿Qué evidencia o handoff nuevo producirán rondas posteriores que una sola pasada del Agent no produciría?",
        ),
        "task_scope": (
            "What exact user-facing slice is in scope, and what should stay out of scope?",
            "这次范围内的具体用户可见切片是什么，哪些内容应明确不做？",
            "¿Qué corte visible para el usuario está dentro de alcance y qué queda fuera?",
        ),
        "success_surface": (
            "When this is done, what specific user-visible outcome or audit result must be proven?",
            "完成时，必须证明哪个具体的用户可见结果或可审计结果？",
            "Cuando esto esté terminado, ¿qué resultado visible o auditable debe quedar probado?",
        ),
        "fake_done_risks": (
            "What would look complete but must still block closure without stronger evidence?",
            "哪种看起来完成的状态在缺少更强证据时必须阻断？",
            "¿Qué parecería terminado pero debe bloquear el cierre sin evidencia más fuerte?",
        ),
        "evidence_preferences": (
            "What evidence should GateKeeper trust most: tests, command output, browser paths, logs, or artifacts?",
            "GateKeeper 最该信任哪类证据：测试、命令输出、浏览器路径、日志还是产物？",
            "¿Qué evidencia debería confiar más GateKeeper: pruebas, salida de comandos, rutas de navegador, logs o artefactos?",
        ),
        "execution_strategy": (
            "What should the first run prove, repair, narrow, expand, or defer?",
            "第一轮应该先证明、修复、收窄、扩展或暂缓什么？",
            "¿Qué debe probar, reparar, acotar, ampliar o diferir la primera ejecución?",
        ),
        "residual_risk_policy": (
            "Which risks may remain as visible follow-up, and which must fail closed?",
            "哪些风险可以作为可见 follow-up 保留，哪些必须 fail closed？",
            "¿Qué riesgos pueden quedar como follow-up visible y cuáles deben fallar cerrados?",
        ),
        "judgment_tradeoffs": (
            "What tradeoff should dominate when speed, scope, polish, and evidence conflict?",
            "速度、范围、打磨和证据冲突时，哪个取舍应该优先？",
            "¿Qué tradeoff debe dominar cuando velocidad, alcance, pulido y evidencia entran en conflicto?",
        ),
        "local_governance": (
            "Which project rules, design docs, or tests must the roles read or verify?",
            "哪些项目规则、design 或 tests 必须由角色读取或验证？",
            "¿Qué reglas del proyecto, documentos de diseño o pruebas deben leer o verificar los roles?",
        ),
        "role_posture": (
            "What should Builder, Inspector, Guide, or GateKeeper each be responsible for?",
            "Builder、Inspector、Guide 或 GateKeeper 各自应该负责什么？",
            "¿De qué debe responsabilizarse Builder, Inspector, Guide o GateKeeper?",
        ),
        "readiness_evidence": (
            "What concrete evidence should prove the working agreement is ready to compile?",
            "什么具体证据能证明工作协议已经足够生成 Loop？",
            "¿Qué evidencia concreta debe probar que el acuerdo de trabajo está listo para compilarse?",
        ),
        "evidence_buckets": (
            "How should GateKeeper classify proof as Proven, Weak, Unproven, Blocking, or Residual risk?",
            "GateKeeper 应该如何把证据分成已证明、弱证据、未证明、阻断或残余风险？",
            "¿Cómo debe clasificar GateKeeper la prueba como Proven, Weak, Unproven, Blocking o Residual risk?",
        ),
        "agreement_summary": (
            "What one-sentence working agreement should this Loop preserve?",
            "这次 Loop 应保留的一句话工作协议是什么？",
            "¿Qué acuerdo de trabajo en una frase debe preservar este Loop?",
        ),
        "improvement_delta": (
            "What feedback-driven change should revise the source spec, roles, workflow, evidence, or GateKeeper?",
            "这次反馈驱动的变化要改来源方案的哪个 spec、角色、workflow、证据或 GateKeeper 面？",
            "¿Qué cambio impulsado por feedback debe revisar el spec, roles, workflow, evidencia o GateKeeper de origen?",
        ),
        "improvement_surface": (
            "Which bundle surface should carry this improvement: spec, roles, workflow, evidence, or GateKeeper?",
            "这次改进应该落到哪个 bundle 面：spec、角色、workflow、证据还是 GateKeeper？",
            "¿Qué superficie del bundle debe llevar esta mejora: spec, roles, workflow, evidencia o GateKeeper?",
        ),
        "improvement_refactor_delta": (
            "What task-scoped refactor proof should change the Loop, such as complexity not merely moving, behavior not regressing, or evidence becoming reproducible?",
            "这次任务范围内的重构要证明什么，才值得改变 Loop？例如复杂度没有只是换地方、用户行为没有回归、证据路径可复验。",
            "¿Qué prueba de refactor dentro del alcance debe cambiar el Loop, como que la complejidad no solo se mueva, el comportamiento no retroceda o la evidencia sea reproducible?",
        ),
        "improvement_completion_mode_delta": (
            "How should the revision convert the source completion mode into evidence-backed GateKeeper task verdicts?",
            "这次修订要如何把来源完成模式转换成由证据支持的 GateKeeper 任务裁决？",
            "¿Cómo debe convertir la revisión el modo de finalización de origen en veredictos de tarea de GateKeeper basados en evidencia?",
        ),
    }
    if normalized not in questions:
        return ""
    english, chinese, spanish = questions[normalized]
    if str(display_language or "").strip().lower() == "es":
        return spanish
    return chinese if prefers_chinese else english


def alignment_missing_item_label(item: str, *, prefers_chinese: bool, display_language: str = "") -> str:
    normalized = str(item or "").strip()
    labels = {
        "workdir_facts": ("run directory/project facts", "运行目录/项目事实", "hechos del proyecto/directorio"),
        "task_scoped_judgment": ("task-scoped judgment", "任务范围内的判断", "juicio dentro del alcance"),
        "loop_fit": ("Loopora fit", "是否适合 Loopora", "encaje con Loopora"),
        "task_scope": ("task scope", "任务范围", "alcance de la tarea"),
        "success_surface": ("success surface", "成功面", "superficie de éxito"),
        "fake_done_risks": ("fake-done risks", "假完成风险", "riesgos de falso terminado"),
        "evidence_preferences": ("evidence expectations", "证据预期", "expectativas de evidencia"),
        "execution_strategy": ("execution strategy", "执行策略", "estrategia de ejecución"),
        "residual_risk_policy": ("residual-risk policy", "残余风险策略", "política de riesgo residual"),
        "judgment_tradeoffs": ("judgment tradeoffs", "判断取舍", "tradeoffs de juicio"),
        "local_governance": ("local governance", "本地治理责任", "gobernanza local"),
        "role_posture": ("role posture", "角色姿态", "postura de roles"),
        "readiness_evidence": ("readiness evidence", "对齐证据", "evidencia de preparación"),
        "evidence_buckets": ("evidence classification", "证据分级", "clasificación de evidencia"),
        "agreement_summary": ("agreement summary", "工作协议摘要", "resumen del acuerdo"),
        "improvement_delta": ("improvement delta", "改进变化", "delta de mejora"),
        "improvement_surface": ("improvement surface", "改进治理面", "superficie de mejora"),
        "improvement_refactor_delta": ("task-scoped refactor delta", "任务范围内的重构 delta", "delta de refactor dentro del alcance"),
        "improvement_completion_mode_delta": (
            "improvement completion mode delta",
            "改进完成模式变化",
            "delta del modo de finalización",
        ),
    }
    fallback = normalized.replace("_", " ")
    english, chinese, spanish = labels.get(normalized, (fallback, fallback, fallback))
    if str(display_language or "").strip().lower() == "es":
        return spanish
    return chinese if prefers_chinese else english


def alignment_fallback_assistant_message(
    *,
    has_bundle: bool,
    needs_user_input: bool,
    display_language: str = "",
) -> str:
    if str(display_language or "").strip().lower() == "es":
        if has_bundle:
            return "Preparé un bundle de Loopora importable."
        if needs_user_input:
            return "Necesito seguir alineando en tu idioma; confirma primero qué riesgo importa más: falso terminado sin evidencia o avanzar demasiado lento."
        return "Necesito seguir alineando en tu idioma antes de continuar."
    if has_bundle:
        return "已整理成一个可导入的 Loopora bundle。"
    if needs_user_input:
        return "我需要继续用中文对齐；请先确认一个会改变 Loop 形状的点：这次更怕结果看起来完成但证据不足，还是推进太慢？"
    return "我需要继续用中文对齐后再继续。"


def alignment_clarifying_reframe_message(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return (
            "我先给一个推荐判断：默认应该优先阻断“看起来完成但证据不足”的结果，"
            "这样后续运行不会靠漂亮叙事过关。你可以直接选推荐，也可以改成更偏速度的方向。"
        )
    if str(display_language or "").strip().lower() == "es":
        return (
            "Mi recomendación inicial es bloquear resultados que parecen terminados pero no tienen evidencia, "
            "para que la ejecución no pase por una historia pulida. Puedes elegir esa recomendación o priorizar velocidad."
        )
    return (
        "My recommended default is to block results that look done but lack evidence, so the run cannot "
        "pass on a polished story alone. You can choose that recommendation or switch toward speed."
    )


def alignment_clarifying_stage_plan(
    output: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> AlignmentClarifyingStagePlan:
    question_issues = alignment_clarifying_question_issues(output)
    if not question_issues:
        return AlignmentClarifyingStagePlan(update_fields={"alignment_stage": "clarifying"}, output_updates={})
    return AlignmentClarifyingStagePlan(
        update_fields={"alignment_stage": "clarifying"},
        output_updates={
            "assistant_message": alignment_clarifying_reframe_message(
                prefers_chinese=prefers_chinese,
                display_language=display_language,
            ),
            "decision_options": default_alignment_decision_options(
                prefers_chinese=prefers_chinese,
                display_language=display_language,
            ),
            "needs_user_input": True,
            "bundle_yaml": "",
        },
        event_type="alignment_question_reframed",
        event_payload={"alignment_stage": "clarifying", "issues": question_issues},
    )
