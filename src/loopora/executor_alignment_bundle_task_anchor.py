from __future__ import annotations

import re

from loopora.bundle_io import bundle_to_yaml, load_bundle_text
from loopora.executor_alignment_bundle_refund_variants import alignment_chinese_refund_repair_bundle_yaml, alignment_refund_repair_bundle_yaml
from loopora.executor_alignment_bundle_specialized_shell import _replace_specialized_workflow_shell_if_generic
from loopora.executor_alignment_bundle_task_predicates import _is_prompt_asset_ownership_task
from loopora.executor_alignment_bundle_task_roles import _replace_task_anchored_roles
from loopora.executor_alignment_bundle_task_routing import _append_selected_workflow_spec_notes
from loopora.executor_alignment_bundle_task_workflow_dispatch import _replace_task_anchored_workflow
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def alignment_task_anchored_repair_bundle_yaml(
    workdir: str,
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    normalized_language = str(display_language or "").strip().lower()
    use_chinese = prefers_chinese or normalized_language == "zh" or _text_has_cjk(task_text)
    generation_display_language = "zh" if use_chinese else display_language
    bundle = load_bundle_text(alignment_chinese_refund_repair_bundle_yaml(workdir) if use_chinese else alignment_refund_repair_bundle_yaml(workdir))
    _apply_task_anchored_repair_bundle(
        bundle,
        workdir=workdir,
        task_text=task_text,
        prefers_chinese=use_chinese,
        display_language=generation_display_language,
    )
    return bundle_to_yaml(bundle)


def _text_has_cjk(value: object) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def _apply_task_anchored_repair_bundle(
    bundle: dict,
    *,
    workdir: str,
    task_text: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    if str(display_language or "").strip().lower() == "es":
        fallback = "la tarea confirmada por el usuario"
    else:
        fallback = "用户确认的任务" if prefers_chinese else "the user-confirmed task"
    task = _bundle_safe_task_anchor(str(task_text or "").strip() or fallback)
    if prefers_chinese:
        _apply_chinese_task_anchored_repair_bundle(bundle, workdir=workdir, task=task)
        return
    if str(display_language or "").strip().lower() == "es":
        _apply_spanish_task_anchored_repair_bundle(bundle, workdir=workdir, task=task)
        return
    _apply_english_task_anchored_repair_bundle(bundle, workdir=workdir, task=task)


def _bundle_safe_task_anchor(task: str) -> str:
    text = str(task or "")
    if not _is_prompt_asset_ownership_task(text):
        return text
    replacements = (
        (r"\bdesign/contracts\.md\b", "the applicable project-local prompt ownership design boundary"),
        (r"\bexisting\s+prompt\s+ownership\s+tests?\b", "applicable prompt ownership tests if present"),
        (r"\bsystem_prompt_assets\.py\b", "the system prompt asset loader"),
        (r"\bAgent\s+Native\s+adapter\s+templates\b", "Agent Native adapter template surfaces"),
        (r"\balignment\s+guidance\b", "alignment compiler guidance assets"),
        (r"\bStrategy\s+Source\s+prompt\s+asset\s+boundaries\b", "Strategy Source prompt asset boundaries"),
        (r"\bPython\s+code\b", "implementation code"),
        (r"\bPython\b", "implementation modules"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _apply_chinese_task_anchored_repair_bundle(bundle: dict, *, workdir: str, task: str) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh")
    bundle["metadata"]["name"] = "任务证据修复 Loop"
    bundle["metadata"]["description"] = "由交互式 Web alignment 生成，并保留用户任务锚点的证据治理 bundle。"
    bundle["loop"]["name"] = "任务证据修复 Loop"
    bundle["loop"]["workdir"] = workdir
    bundle["collaboration_summary"] = (
        f"这个任务需要多轮 Loopora governance，因为用户任务锚点（{task}）不能靠一次 Agent pass、direct chat、"
        "one-off handling 或只跑测试裁决；后续轮次会产生新的证据、handoff、修复方向、阻断判断和 GateKeeper verdict。"
        "最终反馈太慢，不能作为唯一控制信号；关键风险会在重复执行、负向样本、跨系统对账、审计证据和修复 handoff 中逐轮暴露。"
        "spec 固定任务范围、完成标准、假完成和证据偏好；roles 区分构建、检查、Guide 修复和 "
        "GateKeeper 裁决；workflow 先构建最小可证明切片，再由 Inspector 暴露弱证据，Guide 把 Weak / Unproven / "
        "Blocking 项收窄成修复，Repair Builder 只补实现或证据缺口，GateKeeper 依据 Proven、Weak、Unproven、"
        "Blocking 和 Residual risk 关闭或阻断。"
    )
    bundle["spec"]["markdown"] = f"""# Task
围绕这条用户任务锚点交付可证明的实现切片：{task}

# Done When
- 任务特定证明焦点都有直接证据：{projection.success_focus}。
- Builder 留下实现 handoff，说明改动面、证据命令或 artifact、未证明项和阻断项。
- Inspector 验证假完成风险、负向路径、跨边界一致性和证据桶，而不是只接受 happy path。
- Guide 将 Weak、Unproven 或 Blocking 发现转成最小修复方向。
- GateKeeper 只有在核心任务声明进入 Proven，且残余风险可见、点名并有 owner 或 follow-up 时才允许收束。

# Guardrails
- 不扩展成宽泛平台改造，先证明任务锚点中的最小闭环。
- 不把截图、mock-only、happy path、单一状态更新或口头总结当成完成。
- 不声称已观察到技术栈、测试 runner 或现有实现，除非运行时在 workdir 中验证。
- 若 workdir 存在 AGENTS.md、design/README.md、design/ 或 tests/ 等项目本地治理入口，Builder 必须读取适用规则，Inspector 必须验证相关 design 或 test 义务，GateKeeper 必须把跳过本地治理视为 Weak、Unproven 或 Blocking。

# Success Surface
- 用户可以通过可运行行为、持久 artifact、日志、handoff 和证据桶审计这些任务证明面：{projection.success_focus}。
- 用户可以看到哪些声明是 Proven、Weak、Unproven、Blocking 或 Residual risk。

# Fake Done
- 这些浅层状态不得通过：{projection.fake_done_focus}。
- 缺少这些任务风险的证据时必须阻断：{projection.evidence_focus}。
- 涉及 provider failure、webhook、队列、外部 API 或异步恢复时，缺少 timeout、retry/backoff、fallback 或失败恢复证据时不得通过。

# Evidence Preferences
- 优先收集这些任务声明的证据：{projection.evidence_focus}。
- 继续使用项目内测试、命令输出、provider fixture/API 证据、审计日志、对账 artifact 和角色 handoff。
- 涉及外部 provider 或异步边界时，优先收集 timeout、retry/backoff、fallback、失败恢复和 provider failure 证据。
- Inspector 证据必须点名 Proven、Weak、Unproven、Blocking 和 Residual risk。
- GateKeeper verdict 必须引用上游 evidence refs 或 artifact，而不是只读最终总结。

# Execution Strategy
先实现任务锚点里的最小真实闭环；随后让 Inspector 检查 {projection.evidence_focus} 和假完成风险；Guide 只把弱证据转成下一轮最小修复；Repair Builder 读取 Guide handoff 后补实现或证据；GateKeeper 最后从完整 handoff 和 evidence_query 裁决。

# Judgment Tradeoffs
优先小而可证明的核心闭环，而不是更宽、更漂亮但证据薄弱的实现。速度不能覆盖负向样本、审计、对账、边界隔离或 GateKeeper 阻断。

# Residual Risk
核心任务声明、负向证据、边界一致性、审计/对账和本地治理处理不足时必须 fail closed。只有超出本轮最小闭环且已点名、可见、有人接手 follow-up 的风险可以作为 Residual risk 保留。

# Role Notes
## 任务 Builder Notes
构建任务锚点中的最小真实闭环，留下改动面、证据、未证明项和阻断项；若存在 AGENTS.md、design/README.md、design/ 或 tests/，先读取适用本地规则。

## 任务 Inspector Notes
只读检查 Builder handoff 和 evidence refs，重点反证 happy path、mock-only、边界漂移和审计/对账缺口，并验证相关 design/test 义务是否被满足。

## 修复 Guide Notes
把 Weak、Unproven 或 Blocking 发现转成最小修复方向，不鼓励扩展范围。

## 修复 Builder Notes
读取 Guide 与 Inspector handoff 后，只修复被点名的实现或证据缺口。

## 严格 GateKeeper Notes
从 Builder、Inspector、Guide 和 Repair Builder handoff 以及 evidence_query 裁决；核心声明未 Proven 或本地治理被跳过时阻断。"""
    _replace_task_anchored_roles(bundle, prefers_chinese=True, task=task)
    _replace_task_anchored_workflow(bundle, prefers_chinese=True, task=task)
    _append_selected_workflow_spec_notes(bundle, prefers_chinese=True, task=task, display_language="zh")
    _replace_specialized_workflow_shell_if_generic(
        bundle,
        task=task,
        prefers_chinese=True,
        display_language="zh",
    )


def _apply_english_task_anchored_repair_bundle(bundle: dict, *, workdir: str, task: str) -> None:
    projection = alignment_task_domain_projection(task)
    bundle["metadata"]["name"] = "Task Evidence Repair Loop"
    bundle["metadata"]["description"] = "Evidence-governed bundle generated from interactive Web alignment with the task anchor preserved."
    bundle["loop"]["name"] = "Task Evidence Repair Loop"
    bundle["loop"]["workdir"] = workdir
    bundle["collaboration_summary"] = (
        f"This task needs multi-round Loopora governance because the user's task anchor ({task}) cannot be judged by one Agent pass, "
        "direct chat, one-off handling, or a test-only path. Later rounds create new evidence, handoffs, repair direction, "
        "blocking judgment, and GateKeeper verdict context; final feedback is too late to be the only control signal. "
        "The important risks appear through negative samples, cross-boundary consistency, "
        "audit artifacts, reconciliation evidence, and repair handoffs. Later rounds create Builder handoffs, Inspector "
        "evidence, Guide repair direction, Repair Builder proof, and a GateKeeper verdict that separates Proven, Weak, "
        "Unproven, Blocking, and Residual risk."
    )
    bundle["spec"]["markdown"] = f"""# Task
Deliver a proven implementation slice for this user task anchor: {task}

# Done When
- These domain proof focuses have direct evidence: {projection.success_focus}.
- Builder leaves a handoff naming changed surfaces, commands or artifacts, unproven claims, and blockers.
- Inspector verifies fake-done risks, negative paths, cross-boundary consistency, and evidence buckets.
- Guide converts Weak, Unproven, or Blocking findings into the smallest repair direction.
- GateKeeper closes only when core task claims are Proven and any Residual risk is visible, named, and owned.

# Guardrails
- Do not expand into a broad platform rewrite before the task anchor's minimal loop is proven.
- Do not accept screenshot-only, mock-only, happy-path-only, status-only, or prose-only proof.
- Do not claim an observed stack, test runner, or existing implementation unless runtime workdir inspection proves it.
- When AGENTS.md, design/README.md, design/, or tests/ exist in the workdir, Builder must read applicable local rules, Inspector must verify related design or test obligations, and GateKeeper must treat skipped local governance as Weak, Unproven, or Blocking.

# Success Surface
- The user can audit these domain proof surfaces through runnable behavior, durable artifacts, logs, handoffs, and evidence buckets: {projection.success_focus}.
- The user can see which claims are Proven, Weak, Unproven, Blocking, or Residual risk.

# Fake Done
- Shallow states that cannot pass: {projection.fake_done_focus}.
- Missing evidence for these task risks must block: {projection.evidence_focus}.
- When the task touches provider failure, webhooks, queues, external APIs, or async recovery, missing timeout, retry/backoff, fallback, or failure-recovery proof must block.

# Evidence Preferences
- Prefer evidence for these domain claims: {projection.evidence_focus}.
- Continue using project-owned tests, command output, provider fixture or API evidence, audit logs, reconciliation artifacts, and role handoffs.
- For external provider or async boundaries, prefer timeout, retry/backoff, fallback, failure-recovery, and provider failure evidence.
- Inspector evidence must name Proven, Weak, Unproven, Blocking, and Residual risk.
- GateKeeper verdict must cite upstream evidence refs or artifacts, not only a final summary.

# Execution Strategy
Build the smallest real loop from the task anchor first; then inspect {projection.evidence_focus} and fake-done risk; route weak evidence through Guide; let Repair Builder fix only named gaps; then let GateKeeper judge from all handoffs and evidence queries.

# Judgment Tradeoffs
Prefer a narrow proven loop over broader or more polished work with weak evidence. Speed cannot hide negative samples, audit, reconciliation, boundary isolation, or GateKeeper blockers.

# Residual Risk
Core task claims, negative evidence, boundary consistency, audit / reconciliation, and local governance gaps fail closed. Only out-of-scope risks that are named, visible, and owned by follow-up may remain as Residual risk.

# Role Notes
## Task Builder Notes
Build the minimal real task loop and leave changed surfaces, evidence, unproven claims, and blockers. If AGENTS.md, design/README.md, design/, or tests/ exist, read applicable local rules before editing.

## Task Inspector Notes
Read Builder handoff and evidence refs; try to disprove happy-path, mock-only, boundary drift, and audit / reconciliation claims, and verify related design or test obligations.

## Repair Guide Notes
Convert Weak, Unproven, or Blocking findings into the smallest repair direction.

## Repair Builder Notes
Read Guide and Inspector handoffs, then repair only the named implementation or evidence gaps.

## Strict GateKeeper Notes
Judge from Builder, Inspector, Guide, Repair Builder handoffs, and evidence_query; block when core claims are not Proven or local governance was skipped."""
    _replace_task_anchored_roles(bundle, prefers_chinese=False, task=task)
    _replace_task_anchored_workflow(bundle, prefers_chinese=False, task=task)
    _append_selected_workflow_spec_notes(bundle, prefers_chinese=False, task=task, display_language="")
    _replace_specialized_workflow_shell_if_generic(
        bundle,
        task=task,
        prefers_chinese=False,
        display_language="",
    )


def _apply_spanish_task_anchored_repair_bundle(bundle: dict, *, workdir: str, task: str) -> None:
    projection = alignment_task_domain_projection(task)
    bundle["metadata"]["name"] = "Loop de reparación de evidencia"
    bundle["metadata"]["description"] = "Bundle de gobernanza generado desde alignment interactivo, preservando el ancla de tarea y la evidencia de auditoría."
    bundle["loop"]["name"] = "Loop de reparación de evidencia"
    bundle["loop"]["workdir"] = workdir
    bundle["collaboration_summary"] = (
        f"Esta tarea necesita gobernanza multi-ronda de Loopora porque el ancla de tarea del usuario ({task}) no puede juzgarse con una sola pasada del Agent, "
        "chat directo, manejo puntual o solo una prueba aislada. Las rondas posteriores producen evidencia nueva, handoffs, dirección de reparación, "
        "juicio de bloqueo y veredicto auditable de GateKeeper; el feedback final llega demasiado tarde para ser la única señal de control. "
        "Los riesgos importantes aparecen en muestras negativas, consistencia de límites, artefactos de auditoría, reconciliación y handoffs de reparación. "
        "El spec fija alcance, éxito, falso terminado y preferencias de evidencia; los roles separan construcción, inspección, Guide de reparación y juicio de GateKeeper; "
        "el workflow construye el corte mínimo, expone evidencia débil, repara brechas nombradas y separa Proven, Weak, Unproven, Blocking y Residual risk."
    )
    bundle["spec"]["markdown"] = f"""# Task
Entregar un corte de implementación probado para esta ancla de tarea del usuario: {task}

# Done When
- Estos focos de prueba específicos de la tarea tienen evidencia directa: {projection.success_focus}.
- Builder deja un handoff con superficies cambiadas, comandos o artefactos, afirmaciones no probadas y blockers.
- Inspector verifica riesgos de falso terminado, rutas negativas, consistencia de límites y buckets de evidencia.
- Guide convierte hallazgos Weak, Unproven o Blocking en la dirección de reparación más pequeña.
- GateKeeper cierra solo cuando las afirmaciones centrales están Proven y cualquier Residual risk es visible, nombrado y con dueño.

# Guardrails
- No ampliar a una reescritura amplia antes de probar el cierre mínimo del ancla de tarea.
- No aceptar capturas, mock-only, happy path, estado visual o resumen narrativo como evidencia suficiente.
- No reclamar stack, runner de pruebas o implementación existente sin verificación en el workdir durante la ejecución.
- Si existen AGENTS.md, design/README.md, design/ o tests/, Builder lee reglas locales aplicables, Inspector verifica obligaciones de diseño o pruebas y GateKeeper trata omisiones como Weak, Unproven o Blocking.

# Success Surface
- El usuario puede auditar estas superficies de prueba mediante comportamiento ejecutable, artefactos duraderos, logs, handoffs y buckets de evidencia: {projection.success_focus}.
- El usuario puede ver qué afirmaciones son Proven, Weak, Unproven, Blocking o Residual risk.

# Fake Done
- Estos estados superficiales no pueden pasar: {projection.fake_done_focus}.
- Debe bloquear la falta de evidencia para estos riesgos de tarea: {projection.evidence_focus}.
- Si hay provider, webhook, cola, API externa o recuperación async, debe bloquear la falta de timeout, retry/backoff, fallback o prueba de recuperación.

# Evidence Preferences
- Preferir evidencia para estas afirmaciones específicas de la tarea: {projection.evidence_focus}.
- Seguir usando pruebas del proyecto, salida de comandos, evidencia de fixture/API del provider, logs de auditoría, artefactos de reconciliación y handoffs de roles.
- Para límites externos o async, preferir evidencia de timeout, retry/backoff, fallback, recuperación y fallo de provider.
- La evidencia de Inspector debe nombrar Proven, Weak, Unproven, Blocking y Residual risk.
- El veredicto de GateKeeper debe citar evidence refs o artefactos upstream, no solo un resumen final.

# Execution Strategy
Construir primero el cierre real mínimo del ancla de tarea; después inspeccionar {projection.evidence_focus} y falso terminado; enviar evidencia débil a Guide; Repair Builder corrige solo brechas nombradas; GateKeeper juzga desde todos los handoffs y evidence_query.

# Judgment Tradeoffs
Preferir un cierre estrecho y probado sobre trabajo más amplio o pulido con evidencia débil. La velocidad no puede ocultar muestras negativas, auditoría, reconciliación, aislamiento de límites o blockers de GateKeeper.

# Residual Risk
Afirmaciones centrales, evidencia negativa, consistencia de límites, auditoría/reconciliación y gobernanza local fallan cerradas si no están probadas. Solo riesgos fuera de alcance, visibles, nombrados y con dueño de follow-up pueden quedar como Residual risk.

# Role Notes
## Builder de ejecución Notes
Construye el cierre real mínimo y deja superficies cambiadas, evidencia, afirmaciones no probadas y blockers. Si existen AGENTS.md, design/README.md, design/ o tests/, lee reglas locales aplicables antes de editar.

## Inspector de evidencia Notes
Lee handoff y evidence refs de Builder; intenta refutar happy path, mock-only, deriva de límites, auditoría y reconciliación, y verifica obligaciones de diseño o pruebas.

## Guide de reparación Notes
Convierte hallazgos Weak, Unproven o Blocking en la dirección de reparación más pequeña.

## Builder de reparación Notes
Lee handoffs de Guide e Inspector, luego repara solo brechas de implementación o evidencia nombradas.

## GateKeeper de decisión Notes
Juzga desde handoffs de Builder, Inspector, Guide, Repair Builder y evidence_query; bloquea cuando las afirmaciones centrales no están Proven o se omitió gobernanza local."""
    _replace_task_anchored_roles(bundle, prefers_chinese=False, task=task, display_language="es")
    _replace_task_anchored_workflow(bundle, prefers_chinese=False, display_language="es", task=task)
    _append_selected_workflow_spec_notes(bundle, prefers_chinese=False, task=task, display_language="es")
    _replace_specialized_workflow_shell_if_generic(
        bundle,
        task=task,
        prefers_chinese=False,
        display_language="es",
    )
