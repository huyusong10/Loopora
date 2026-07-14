from __future__ import annotations


def default_alignment_decision_options(*, prefers_chinese: bool, display_language: str = "") -> list[dict]:
    if prefers_chinese:
        return [
            {
                "id": "evidence_first",
                "label": "优先阻断假完成（推荐）",
                "description": "少做一点也可以，但必须证明核心路径真的成立。",
                "recommended": True,
                "user_reply": "采用推荐：优先阻断看起来完成但证据不足的结果，少而真实也可以。",
            },
            {
                "id": "speed_first",
                "label": "优先快速推进",
                "description": "先交一个更务实的首版，允许部分残余风险保持可见。",
                "recommended": False,
                "user_reply": "我选择优先快速推进，可以接受部分残余风险保持可见。",
            },
            {
                "id": "add_judgment",
                "label": "我补充判断",
                "description": "我想说明另一种更重要的完成标准或风险。",
                "recommended": False,
                "user_reply": "我想补充另一种判断：",
            },
        ]
    if str(display_language or "").strip().lower() == "es":
        return [
            {
                "id": "evidence_first",
                "label": "Bloquear falso terminado (recomendado)",
                "description": "Un resultado menor es aceptable, pero el camino central debe quedar probado.",
                "recommended": True,
                "user_reply": "Uso la recomendación: bloquear resultados que parecen terminados pero no tienen evidencia, aunque la primera versión sea menor.",
            },
            {
                "id": "speed_first",
                "label": "Avanzar más rápido",
                "description": "Entregar una primera versión pragmática y mantener visibles los riesgos residuales.",
                "recommended": False,
                "user_reply": "Elijo avanzar más rápido y acepto riesgos residuales visibles.",
            },
            {
                "id": "add_judgment",
                "label": "Agregaré juicio",
                "description": "Quiero nombrar otro estándar de cierre o riesgo importante.",
                "recommended": False,
                "user_reply": "Quiero agregar otro juicio:",
            },
        ]
    return [
        {
            "id": "evidence_first",
            "label": "Block fake done (Recommended)",
            "description": "A smaller result is acceptable, but the core path must be proven.",
            "recommended": True,
            "user_reply": "Use the recommendation: block results that look done but lack evidence, even if the first version is smaller.",
        },
        {
            "id": "speed_first",
            "label": "Move faster",
            "description": "Ship a more pragmatic first pass and keep residual risks visible.",
            "recommended": False,
            "user_reply": "I choose speed first and can accept visible residual risks.",
        },
        {
            "id": "add_judgment",
            "label": "I'll add judgment",
            "description": "I want to name a different completion standard or risk.",
            "recommended": False,
            "user_reply": "I want to add another judgment:",
        },
    ]


def agreement_confirmation_decision_options(*, prefers_chinese: bool, display_language: str = "") -> list[dict]:
    if prefers_chinese:
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
    if str(display_language or "").strip().lower() == "es":
        return [
            {
                "id": "confirm_agreement",
                "label": "Usar esta dirección (recomendado)",
                "description": "Generar el Loop desde este acuerdo de trabajo.",
                "recommended": True,
                "user_reply": "Confirmo; usa esta dirección.",
            },
            {
                "id": "adjust_agreement",
                "label": "Quiero cambios",
                "description": "Revisar un juicio antes de generar el plan.",
                "recommended": False,
                "user_reply": "Quiero ajustar este acuerdo de trabajo:",
            },
        ]
    return [
        {
            "id": "confirm_agreement",
            "label": "Use this direction (Recommended)",
            "description": "Generate the Loop plan from this working agreement.",
            "recommended": True,
            "user_reply": "Confirm; use this direction.",
        },
        {
            "id": "adjust_agreement",
            "label": "I want changes",
            "description": "Revise one judgment before generating the plan.",
            "recommended": False,
            "user_reply": "I want to adjust this working agreement:",
        },
    ]


def not_fit_alignment_decision_options(*, prefers_chinese: bool, display_language: str = "") -> list[dict]:
    if prefers_chinese:
        return [
            {
                "id": "skip_loop",
                "label": "先不生成 Loop（推荐）",
                "description": "这更像一次性任务，不需要额外编排。",
                "recommended": True,
                "user_reply": "同意，先不生成 Loop 方案。",
            },
            {
                "id": "still_compile",
                "label": "仍然编排",
                "description": "我会说明需要继承的反复判断或新证据。",
                "recommended": False,
                "user_reply": "仍然需要编排，因为这套判断需要被后续运行继承：",
            },
        ]
    if str(display_language or "").strip().lower() == "es":
        return [
            {
                "id": "skip_loop",
                "label": "Omitir Loop por ahora (recomendado)",
                "description": "Esto parece una tarea puntual que no necesita gobernanza adicional.",
                "recommended": True,
                "user_reply": "De acuerdo, no generes un Loop por ahora.",
            },
            {
                "id": "still_compile",
                "label": "Aun así componerlo",
                "description": "Explicaré el juicio repetido o la nueva evidencia que debe heredar la ejecución.",
                "recommended": False,
                "user_reply": "Aun así necesito un Loop porque este juicio debe heredarse en la ejecución:",
            },
        ]
    return [
        {
            "id": "skip_loop",
            "label": "Skip Loop for now (Recommended)",
            "description": "This looks like a one-off task that does not need governance.",
            "recommended": True,
            "user_reply": "Agreed, do not generate a Loop plan for now.",
        },
        {
            "id": "still_compile",
            "label": "Still compose it",
            "description": "I will explain the repeated judgment or new evidence this run must inherit.",
            "recommended": False,
            "user_reply": "I still need a Loop because this judgment should be inherited by the run:",
        },
    ]
