from __future__ import annotations

import re

from loopora.alignment_traceability_terms import agent_candidate_traceability_terms
from loopora.executor_alignment_agreement_responses import (
    alignment_agreement_response,
    alignment_chinese_agreement_response,
)


def alignment_english_task_anchored_agreement_response(task_text: str) -> dict:
    payload = alignment_agreement_response()
    task = task_text or "the user-confirmed task"
    anchors = _task_anchor_terms_text(task_text)
    payload["assistant_message"] = (
        "Please confirm this task-specific working agreement; I will preserve the task anchor across spec, roles, "
        "workflow handoffs, repair guidance, and the final GateKeeper evidence verdict."
    )
    payload["agreement_summary"] = (
        f"Govern this task anchor through an evidence-first repair Loop: {task}. "
        "A narrow Builder proves the smallest real loop, Inspector tries to disprove the task-specific claims, "
        "Guide turns weak proof into repair, Repair Builder closes named gaps, and GateKeeper fails closed when proof is weak."
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            f"The task anchor ({task}) fits Loopora because important risk is not settled by one Agent pass or one demo. "
            "Later rounds must create Builder handoffs, negative evidence, audit or reconciliation artifacts when relevant, "
            "Guide repair direction, and a GateKeeper verdict that can be reused as an auditable contract."
        ),
        "task_scope": (
            f"Scope stays on the concrete user task: {task}. The Loop should prove the smallest task-specific closed path "
            "and avoid broad platform rewrite, generic starter work, or unrelated polish."
        ),
        "success_surface": _task_success_surface_evidence(task, anchors=anchors, prefers_chinese=False),
        "fake_done_risks": _task_fake_done_risk_evidence(task, prefers_chinese=False),
        "evidence_preferences": (
            "Prefer project-owned checks, command output, provider fixture or API proof when relevant, audit logs, "
            "reconciliation artifacts, provider failure / timeout / retry / fallback evidence when relevant, "
            "role handoffs, and explicit Proven / Weak / Unproven / Blocking / Residual risk buckets."
        ),
        "execution_strategy": (
            "Build the smallest real task loop first; inspect negative paths, boundary consistency, audit or reconciliation "
            "claims, and fake-done risk; route weak proof through Guide; repair named gaps only; then GateKeeper judges from all handoffs."
        ),
        "residual_risk_policy": (
            "Core task claims, negative evidence, boundary consistency, audit or reconciliation proof, and local-governance gaps fail closed. "
            "Only out-of-scope risks that are visible, named, and owned by follow-up may remain as Residual risk."
        ),
        "judgment_tradeoffs": (
            "Prefer a narrow proven loop over broader or prettier work with weak proof. Speed loses to task-anchor traceability, "
            "negative evidence, auditability, boundary isolation, and GateKeeper blocking."
        ),
        "local_governance": (
            "If project-local governance markers are present, Builder reads the applicable rules before editing, Inspector verifies "
            "the related design or test obligations, and GateKeeper treats skipped local governance as Weak, Unproven, or Blocking."
        ),
        "role_posture": (
            "Builder constructs the task slice, Inspector tries to disprove task-specific claims, Guide narrows repair from Weak / "
            "Unproven / Blocking evidence, Repair Builder fixes named gaps, and GateKeeper closes only from direct proof."
        ),
        "workflow_shape": (
            "Use Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper. Inspector reads Builder handoff and Builder evidence; "
            "Guide reads Inspector findings; Repair Builder reads Guide and inspection handoffs; GateKeeper reads every upstream handoff "
            "and queries Builder, Inspector, and Guide evidence before finishing."
        ),
        "workdir_facts": (
            "Observed workdir facts are limited to the target path and snapshot. Stack, test runner, and existing implementation details "
            "must be verified during the run before the Loop claims them."
        ),
        "open_questions": "Waiting for explicit user confirmation of the working agreement.",
    }
    return payload


def alignment_chinese_task_anchored_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_agreement_response()
    task = task_text or "用户确认的任务"
    anchors = _task_anchor_terms_text(task_text)
    payload["assistant_message"] = "请确认这份任务专属工作协议；确认后我会把任务锚点贯穿到 spec、roles、workflow、修复 handoff 和 GateKeeper 证据裁决里。"
    payload["agreement_summary"] = (
        f"围绕这条任务锚点编排证据优先的修复 Loop：{task}。"
        "先由 Builder 证明最小真实闭环，再由 Inspector 反证任务声明，Guide 把弱证据收窄成修复，"
        "Repair Builder 补被点名缺口，GateKeeper 在证据薄弱时 fail closed。"
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            f"任务锚点（{task}）适合 Loopora，因为关键风险不能靠一次 Agent pass 或一次 demo 裁决。"
            "后续轮次需要产生 Builder handoff、负向证据、相关审计或对账 artifact、Guide 修复方向，以及可复用、可审计的 GateKeeper verdict。"
        ),
        "task_scope": (f"范围固定在这条具体用户任务：{task}。Loop 只证明最小任务闭环，不扩展成宽泛平台改造、泛化 starter work 或无关 polish。"),
        "success_surface": _task_success_surface_evidence(task, anchors=anchors, prefers_chinese=True),
        "fake_done_risks": _task_fake_done_risk_evidence(task, prefers_chinese=True),
        "evidence_preferences": (
            "优先项目内检查、命令输出、相关 provider fixture 或 API 证据、审计日志、对账 artifact、角色 handoff，"
            "涉及 provider failure 时还要有 timeout、retry/backoff 或 fallback 证据，并明确区分 Proven、Weak、Unproven、Blocking 和 Residual risk。"
        ),
        "execution_strategy": (
            "先构建最小真实任务闭环；再检查负向路径、边界一致性、审计或对账声明和假完成风险；"
            "弱证据进入 Guide；Repair Builder 只补被点名缺口；最后 GateKeeper 从所有 handoff 裁决。"
        ),
        "residual_risk_policy": (
            "核心任务声明、负向证据、边界一致性、审计或对账证据、本地治理处理不足时必须 fail closed。"
            "只有超出本轮范围且已点名、可见、有人接手 follow-up 的风险可作为 Residual risk 保留。"
        ),
        "judgment_tradeoffs": (
            "优先小而可证明的闭环，而不是更宽或更漂亮但证据薄弱的实现。速度不能覆盖任务锚点 traceability、负向证据、审计性、边界隔离或 GateKeeper 阻断。"
        ),
        "local_governance": (
            "若存在项目本地治理入口，Builder 先读取适用规则，Inspector 验证相关 design 或 test 义务，GateKeeper 将跳过本地治理视为 Weak、Unproven 或 Blocking。"
        ),
        "role_posture": (
            "Builder 构建任务切片，Inspector 反证任务声明，Guide 根据 Weak / Unproven / Blocking 证据收窄修复，"
            "Repair Builder 修复被点名缺口，GateKeeper 只按直接证据收束。"
        ),
        "workflow_shape": (
            "采用 Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper。Inspector 读取 Builder handoff 和证据；"
            "Guide 读取 Inspector 发现；Repair Builder 读取 Guide 与检查 handoff；GateKeeper 读取全部上游 handoff 并查询 Builder、Inspector、Guide 证据后才能 finish。"
        ),
        "workdir_facts": ("已观察事实只限目标路径和 Workdir Snapshot；技术栈、测试 runner 和既有实现位置必须在运行中验证后才能声称。"),
        "open_questions": "等待用户明确确认这份工作协议。",
    }
    return payload


def alignment_spanish_task_anchored_agreement_response(task_text: str) -> dict:
    payload = alignment_agreement_response()
    task = task_text or "la tarea confirmada por el usuario"
    anchors = _task_anchor_terms_text(task_text)
    payload["assistant_message"] = (
        "Confirma este acuerdo de trabajo específico de la tarea; después preservaré el ancla de tarea en spec, roles, "
        "workflow, handoffs de reparación y veredicto de evidencia de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta ancla de tarea con un Loop de reparación guiado por evidencia: {task}. "
        "Builder prueba el cierre real mínimo, Inspector intenta refutar las afirmaciones específicas, Guide convierte "
        "evidencia débil en reparación, Repair Builder cierra brechas nombradas y GateKeeper falla cerrado cuando la evidencia es débil."
    )
    payload["readiness_evidence"] = {
        "loop_fit": (
            f"La ancla de tarea ({task}) encaja con Loopora porque el riesgo importante no se resuelve con una sola pasada del Agent "
            "ni una demo. Rondas posteriores deben crear handoffs de Builder, evidencia negativa, auditoría o reconciliación cuando aplique, "
            "dirección de reparación de Guide y un veredicto auditable de GateKeeper."
        ),
        "task_scope": (
            f"El alcance queda limitado a la tarea concreta del usuario: {task}. El Loop debe probar el camino mínimo específico "
            "y evitar una reescritura amplia, trabajo inicial genérico o pulido sin evidencia."
        ),
        "success_surface": _task_success_surface_evidence(task, anchors=anchors, prefers_chinese=False, display_language="es"),
        "fake_done_risks": _task_fake_done_risk_evidence(task, prefers_chinese=False, display_language="es"),
        "evidence_preferences": (
            "Preferir pruebas del proyecto, salida de comandos, evidencia de fixture o API del provider cuando aplique, logs de auditoría, "
            "artefactos de reconciliación, evidencia de timeout/retry/fallback si hay fallo de provider, handoffs de roles y buckets Proven, Weak, Unproven, Blocking y Residual risk."
        ),
        "execution_strategy": (
            "Construir primero el cierre real mínimo de la tarea; inspeccionar rutas negativas, consistencia de límites, auditoría o reconciliación "
            "y riesgos de falso terminado; enviar evidencia débil a Guide; reparar solo brechas nombradas; luego GateKeeper juzga desde todos los handoffs."
        ),
        "residual_risk_policy": (
            "Afirmaciones centrales, evidencia negativa, consistencia de límites, auditoría o reconciliación y gobernanza local deben fallar cerrados si no están probados. "
            "Solo riesgos fuera de alcance que sean visibles, nombrados y con follow-up dueño pueden quedar como Residual risk."
        ),
        "judgment_tradeoffs": (
            "Preferir un cierre pequeño y probado sobre trabajo más amplio o pulido con evidencia débil. La velocidad pierde frente a trazabilidad, evidencia negativa, auditoría, aislamiento de límites y bloqueo de GateKeeper."
        ),
        "local_governance": (
            "Si hay marcadores de gobernanza local del proyecto, Builder lee las reglas aplicables antes de editar, Inspector verifica obligaciones de diseño o pruebas, "
            "y GateKeeper trata gobernanza omitida como Weak, Unproven o Blocking."
        ),
        "role_posture": (
            "Builder construye el corte de tarea, Inspector refuta afirmaciones específicas, Guide acota reparación desde evidencia Weak, Unproven o Blocking, "
            "Repair Builder corrige brechas nombradas y GateKeeper cierra solo con evidencia directa."
        ),
        "workflow_shape": (
            "El flujo de ejecución usa Builder -> Inspector -> Guide -> Repair Builder -> GateKeeper como secuencia de decisión. "
            "Inspector lee handoff y evidencia de auditoría de Builder; Guide lee hallazgos de Inspector; Repair Builder lee handoffs de Guide e Inspector; "
            "GateKeeper consulta toda la evidencia antes de cerrar."
        ),
        "workdir_facts": (
            "Los hechos del proyecto observados se limitan al path objetivo y snapshot; stack, runner de pruebas e implementación existente deben verificarse durante la ejecución antes de reclamarlos como evidencia."
        ),
        "open_questions": "Esperando confirmación explícita del usuario sobre el acuerdo de trabajo.",
    }
    return payload


def _agreement_task_clause(task_text: str) -> str:
    return str(task_text or "").strip().rstrip("。.!?？")


def _task_anchor_terms_text(task_text: str) -> str:
    terms = agent_candidate_traceability_terms(task_text)
    if terms:
        return ", ".join(terms[:8])
    return "the confirmed task scope"


def _task_success_surface_evidence(
    task_text: str,
    *,
    anchors: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    explicit = _task_sentence_matching(
        task_text,
        (
            r"\b(?:success|done|complete|completion|must prove|must show|prove|verified|audit(?:able)?)\b",
            r"完成时|成功|完成标准|必须证明|需要证明|证明|可审计|可追踪|用户能|用户可以",
        ),
        reject_patterns=(
            r"\b(?:fake[- ]?done|not enough|not complete|doesn't count|happy[- ]?path|screenshot|mock[- ]?only)\b",
            r"不算完成|假完成|截图|只有|只靠|happy path|mock-only",
        ),
    )
    if explicit:
        if str(display_language or "").strip().lower() == "es":
            return (
                f"La superficie de éxito sigue el juicio de cierre del usuario: {explicit}. GateKeeper también necesita comportamiento ejecutable, "
                "artefactos duraderos, handoffs y buckets de evidencia que prueben ese juicio."
            )
        return (
            f"成功面采用用户给出的完成判断：{explicit}。GateKeeper 还要看到可运行行为、持久 artifact、handoff 和证据桶能证明这条判断。"
            if prefers_chinese
            else f"Success surface follows the user's completion judgment: {explicit}. GateKeeper also needs runnable behavior, durable artifacts, handoffs, and evidence buckets that prove this judgment."
        )
    if str(display_language or "").strip().lower() == "es":
        return (
            "El éxito significa que el usuario puede auditar cómo se satisface la ancla de tarea con comportamiento ejecutable, "
            f"artefactos duraderos, handoffs y buckets de evidencia ligados a estas anclas: {anchors}."
        )
    if prefers_chinese:
        return f"成功意味着用户能从可运行行为、持久 artifact、handoff 和证据桶里审计任务锚点如何成立；需要保留这些锚点：{anchors}。"
    return (
        "Success means the user can inspect how the task anchor is satisfied through runnable behavior, "
        f"durable artifacts, handoffs, and evidence buckets tied to these anchors: {anchors}."
    )


def _task_fake_done_risk_evidence(
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    explicit = _task_sentence_matching(
        task_text,
        (
            r"\b(?:fake[- ]?done|not enough|not complete|doesn't count|happy[- ]?path|screenshot|mock[- ]?only|block)\b",
            r"不算完成|假完成|截图|只有|只靠|happy path|mock-only|必须阻断|要阻断",
        ),
    )
    if str(display_language or "").strip().lower() == "es":
        base = (
            "Rechazar evidencia solo happy path, solo mock, capturas o cambios de estado sin casos negativos, "
            "handoffs genéricos, falta de timeout/retry/fallback cuando importa el fallo de provider, y cualquier bundle que pierda el ancla de tarea."
        )
        return f"Riesgo de falso terminado nombrado por el usuario: {explicit}. {base}" if explicit else base
    if prefers_chinese:
        base = (
            "拒绝只有 happy path、mock-only、没有负向样本的截图或状态变化、泛泛 handoff；"
            "涉及 provider failure 时缺少 timeout、retry/backoff 或 fallback 证据也必须阻断；不得把任务锚点降级成泛化首版框架。"
        )
    else:
        base = (
            "Reject happy-path-only proof, mock-only proof, screenshots or status changes without negative cases, "
            "generic handoffs, missing timeout / retry / fallback proof when provider failure matters, "
            "and any bundle that drops the task anchor into starter-experience framing."
        )
    if not explicit:
        return base
    return f"用户点名的假完成风险：{explicit}。{base}" if prefers_chinese else f"User-named fake-done risk: {explicit}. {base}"


def _task_sentence_matching(
    task_text: str,
    patterns: tuple[str, ...],
    *,
    reject_patterns: tuple[str, ...] = (),
) -> str:
    for sentence in _task_sentences(task_text):
        if reject_patterns and any(re.search(pattern, sentence, re.IGNORECASE) for pattern in reject_patterns):
            continue
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in patterns):
            return sentence
    return ""


def _task_sentences(task_text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(task_text or "")).strip()
    if not normalized:
        return []
    sentences = [item.strip(" \t\r\n,，.。;；:：") for item in re.split(r"[。.!?！？；;]\s*", normalized)]
    return [sentence for sentence in sentences if sentence]
