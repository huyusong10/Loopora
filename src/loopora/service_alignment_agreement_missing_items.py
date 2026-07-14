from __future__ import annotations


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
        "improvement_refactor_delta": (
            "task-scoped refactor delta",
            "任务范围内的重构 delta",
            "delta de refactor dentro del alcance",
        ),
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
