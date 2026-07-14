from __future__ import annotations

from functools import lru_cache
import re
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.executor_alignment_task_projection import alignment_task_domain_projection

SPECIALIZED_WORKFLOW_DISPLAY_NAMES_ASSET_NAME = "specialized-workflow-display-names.json"


def _replace_specialized_workflow_shell_if_generic(
    bundle: dict,
    *,
    task: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    preset = str(workflow.get("preset") or "")
    if not preset or preset == "task-evidence-repair" or "repair" in preset:
        return
    text_surfaces = "\n".join(
        str(value or "")
        for value in (
            (bundle.get("metadata") or {}).get("name") if isinstance(bundle.get("metadata"), dict) else "",
            bundle.get("collaboration_summary"),
            (bundle.get("loop") or {}).get("name") if isinstance(bundle.get("loop"), dict) else "",
            (bundle.get("spec") or {}).get("markdown") if isinstance(bundle.get("spec"), dict) else "",
        )
    )
    if not any(token in text_surfaces for token in ("Task Evidence Repair Loop", "Repair Builder", "Guide 只把弱证据")):
        return

    language = "zh" if prefers_chinese else str(display_language or "").strip().lower()
    workflow_name = _specialized_workflow_display_name(preset, language=language)
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    metadata["name"] = workflow_name
    loop["name"] = workflow_name
    if language == "zh":
        metadata["description"] = "围绕专属 workflow 生成的证据治理 bundle。"
    elif language == "es":
        metadata["description"] = "Bundle de gobernanza para un workflow especializado."
    else:
        metadata["description"] = "Evidence-governance bundle for a specialized workflow."
    bundle["collaboration_summary"] = _specialized_workflow_collaboration_summary(
        task,
        preset=preset,
        language=language,
    )

    if not _specialized_workflow_spec_needs_shell_replacement(bundle):
        return

    projection = alignment_task_domain_projection(task, display_language="zh" if language == "zh" else language)
    role_lines, role_notes = _specialized_workflow_role_lines(bundle)
    gatekeeper_verifies = _specialized_workflow_gatekeeper_verifies(bundle)
    workflow_notes = _extract_specialized_workflow_notes(str((bundle.get("spec") or {}).get("markdown") or ""))
    if language == "zh":
        bundle["spec"]["markdown"] = f"""# Task
围绕这条用户任务锚点交付可证明的任务专属 evidence workflow：{task}

# Done When
- 任务特定证明焦点都有直接证据：{projection.success_focus}。
- workflow 中每个角色都产出自己的 handoff，并按步骤 fan-in 到 GateKeeper：
{role_lines}
- GateKeeper 查询这些 evidence buckets 后才允许 finish：{gatekeeper_verifies}。

# Guardrails
- 不继承通用 Repair/Guide 形状；专属 workflow 已经决定角色、handoff 和 evidence_query。
- 这些浅层状态不得通过：{projection.fake_done_focus}。
- 不声称已观察到技术栈、provider、runner 或现有实现，除非运行时在 workdir 中验证。
- 若 workdir 存在 AGENTS.md、design/README.md、design/ 或 tests/ 等本地治理入口，相关角色必须读取并验证适用义务。

# Success Surface
- 用户可以通过可运行行为、持久 artifact、日志、handoff 和证据桶审计这些任务证明面：{projection.success_focus}。
- 用户可以看到哪些声明是 Proven、Weak、Unproven、Blocking 或 Residual risk。

# Fake Done
- 这些浅层状态不得通过：{projection.fake_done_focus}。
- 缺少这些任务风险的证据时必须阻断：{projection.evidence_focus}。

# Evidence Preferences
- 优先收集这些任务声明的证据：{projection.evidence_focus}。
- Inspector 证据必须点名 Proven、Weak、Unproven、Blocking 和 Residual risk。
- GateKeeper verdict 必须引用上游 handoff、evidence refs 或 artifact，而不是只读最终总结。

# Execution Strategy
采用 workflow preset `{preset}`。每个 Builder / Inspector / Custom step 读取声明的 upstream handoff；GateKeeper 读取所有关键 handoff 和 evidence_query 后裁决。

# Judgment Tradeoffs
优先任务专属直接证据、负向样本、审计/对账、边界隔离和本地治理，而不是更快但证据薄弱的表面进度。

# Residual Risk
核心任务声明、负向证据、边界一致性、审计/对账和本地治理处理不足时必须 fail closed。只有已点名、可见、有人接手 follow-up 的非核心风险可以作为 Residual risk 保留。

# Role Notes
{role_notes}
{workflow_notes}
"""
        return
    if language == "es":
        bundle["spec"]["markdown"] = f"""# Task
Entregar un evidence workflow específico y probado para esta tarea: {task}

# Done When
- Focos de prueba: {projection.success_focus}.
- Roles y handoffs:
{role_lines}
- GateKeeper consulta estos evidence buckets antes de finish: {gatekeeper_verifies}.

# Guardrails
- No heredar una forma genérica de Repair/Guide; el workflow específico define roles, handoffs y evidence_query.
- Estados superficiales no pasan: {projection.fake_done_focus}.
- No afirmar stack, provider, runner o implementación existente sin verificación en workdir.

# Success Surface
- El usuario audita estas superficies con comportamiento ejecutable, artefactos, logs, handoffs y evidence buckets: {projection.success_focus}.
- Cada claim se clasifica como Proven, Weak, Unproven, Blocking o Residual risk.

# Fake Done
- Estados superficiales no pasan: {projection.fake_done_focus}.
- Falta de evidencia para estos riesgos bloquea: {projection.evidence_focus}.

# Evidence Preferences
- Preferir evidencia para: {projection.evidence_focus}.
- Inspector nombra Proven, Weak, Unproven, Blocking y Residual risk.
- GateKeeper cita handoffs, refs o artifacts.

# Execution Strategy
Usar workflow preset `{preset}`; cada step lee sus handoffs declarados y GateKeeper decide desde handoffs y evidence_query.

# Judgment Tradeoffs
Evidencia directa, negativos, auditoría/reconciliación, límites y governance pesan más que progreso superficial.

# Residual Risk
Faltas centrales fail closed; solo riesgos no centrales visibles y con owner/follow-up quedan como Residual risk.

# Role Notes
{role_notes}
{workflow_notes}
"""
        return

    bundle["spec"]["markdown"] = f"""# Task
Deliver a proven specialized workflow for this user task anchor: {task}

# Done When
- These domain proof focuses have direct evidence: {projection.success_focus}.
- Every workflow role produces its own handoff and fans in to GateKeeper through declared steps:
{role_lines}
- GateKeeper queries these evidence buckets before finish: {gatekeeper_verifies}.

# Guardrails
- Do not inherit a generic Repair/Guide shape; the specialized workflow owns roles, handoffs, and evidence_query.
- Shallow states that cannot pass: {projection.fake_done_focus}.
- Do not claim an observed stack, provider, runner, or existing implementation unless runtime workdir inspection proves it.
- When AGENTS.md, design/README.md, design/, or tests/ exist in the workdir, relevant roles must read and verify applicable local obligations.

# Success Surface
- The user can audit these domain proof surfaces through runnable behavior, durable artifacts, logs, handoffs, and evidence buckets: {projection.success_focus}.
- The user can see which claims are Proven, Weak, Unproven, Blocking, or Residual risk.

# Fake Done
- Shallow states that cannot pass: {projection.fake_done_focus}.
- Missing evidence for these task risks must block: {projection.evidence_focus}.

# Evidence Preferences
- Prefer evidence for these domain claims: {projection.evidence_focus}.
- Inspector evidence must name Proven, Weak, Unproven, Blocking, and Residual risk.
- GateKeeper verdict must cite upstream handoffs, evidence refs, or artifacts, not only a final summary.

# Execution Strategy
Use workflow preset `{preset}`. Each Builder / Inspector / Custom step reads declared upstream handoffs; GateKeeper reads all critical handoffs and evidence_query before judgment.

# Judgment Tradeoffs
Domain direct proof, negative samples, audit / reconciliation, boundary isolation, and local governance beat faster surface progress with weak evidence.

# Residual Risk
Core task claims, negative evidence, boundary consistency, audit / reconciliation, and local governance gaps fail closed. Only non-core risks that are named, visible, and owned by follow-up may remain as Residual risk.

# Role Notes
{role_notes}
{workflow_notes}
"""


def _specialized_workflow_collaboration_summary(task: str, *, preset: str, language: str) -> str:
    if language == "zh":
        return (
            f"这个任务需要多轮 Loopora governance，因为用户任务锚点（{task}）的风险必须通过专属 workflow 的 staged handoff、"
            "并行或阶段化 evidence inspection、evidence_query 和 GateKeeper fan-in 逐步证明；最终人工反馈太晚，不能作为唯一控制信号。"
            f"workflow 使用 {preset}，让任务专属成功面、假完成风险、证据桶和本地治理义务进入 runnable surfaces，而不是继承通用 Repair/Guide 外壳。"
        )
    if language == "es":
        return (
            f"Esta tarea necesita gobernanza multi-ronda de Loopora porque el ancla ({task}) debe probarse con handoffs, evidence inspection, evidence_query y GateKeeper fan-in del workflow especializado. "
            f"El preset `{preset}` proyecta éxito, falso terminado, evidencia y governance a superficies ejecutables sin heredar una carcasa genérica de Repair/Guide."
        )
    return (
        f"This task needs multi-round Loopora governance because the user's task anchor ({task}) must be proven through the specialized workflow's staged handoffs, evidence inspection, evidence_query, and GateKeeper fan-in; final feedback is too late to be the only control signal. "
        f"The workflow preset `{preset}` projects success surfaces, fake-done risks, evidence buckets, and local-governance duties into runnable surfaces instead of inheriting a generic Repair/Guide shell."
    )


def _specialized_workflow_spec_needs_shell_replacement(bundle: dict) -> bool:
    spec_text = str((bundle.get("spec") or {}).get("markdown") if isinstance(bundle.get("spec"), dict) else "")
    generic_spec_tokens = (
        "Task Evidence Repair Loop",
        "Repair Builder",
        "Guide 只把弱证据",
        "task-specific evidence workflow",
        "task-specific proof focuses",
        "These shallow states cannot pass",
        "Focos de prueba",
    )
    return any(token in spec_text for token in generic_spec_tokens)


def _specialized_workflow_display_name(preset: str, *, language: str) -> str:
    localized = _specialized_workflow_display_names_asset().get(str(preset or ""), {})
    if localized:
        return localized.get(language) or localized.get("en") or "Specialized Workflow Loop"
    words = str(preset or "").replace("_", "-").split("-")
    title = " ".join(word.upper() if word in {"api", "cdc", "sso", "rag"} else word.capitalize() for word in words if word)
    return f"{title or 'Specialized Workflow'} Loop"


@lru_cache
def _specialized_workflow_display_names_asset() -> dict[str, dict[str, str]]:
    asset = load_alignment_guidance_assets().specialized_workflow_display_names
    if not all(isinstance(preset, str) and isinstance(names, dict) for preset, names in asset.items()):
        raise ValueError(f"{SPECIALIZED_WORKFLOW_DISPLAY_NAMES_ASSET_NAME} must map presets to locale maps")
    return {preset: _specialized_workflow_locale_names(preset, names) for preset, names in asset.items()}


def _specialized_workflow_locale_names(preset: str, names: dict[str, Any]) -> dict[str, str]:
    required_locales = ("en", "zh", "es")
    if not all(isinstance(names.get(locale), str) and names[locale].strip() for locale in required_locales):
        raise ValueError(f"{SPECIALIZED_WORKFLOW_DISPLAY_NAMES_ASSET_NAME}.{preset} must include en/zh/es names")
    return {locale: str(names[locale]).strip() for locale in required_locales}


def _specialized_workflow_role_lines(bundle: dict) -> tuple[str, str]:
    role_definitions = bundle.get("role_definitions") if isinstance(bundle.get("role_definitions"), list) else []
    role_by_key = {str(role.get("key") or ""): role for role in role_definitions if isinstance(role, dict)}
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    workflow_roles = workflow.get("roles") if isinstance(workflow.get("roles"), list) else []
    role_key_by_id = {str(role.get("id") or ""): str(role.get("role_definition_key") or "") for role in workflow_roles if isinstance(role, dict)}
    lines: list[str] = []
    notes: list[str] = []
    for step in workflow.get("steps") or []:
        if not isinstance(step, dict):
            continue
        role_key = role_key_by_id.get(str(step.get("role_id") or ""))
        role = role_by_key.get(role_key, {})
        role_name = str(role.get("name") or step.get("role_id") or role_key or "Role")
        handoffs = ", ".join(str(item) for item in (step.get("inputs") or {}).get("handoffs_from", []) or [])
        parallel_group = str(step.get("parallel_group") or "")
        suffixes = []
        if handoffs:
            suffixes.append(f"reads {handoffs}")
        if parallel_group:
            suffixes.append(f"parallel_group {parallel_group}")
        suffix = f" ({'; '.join(suffixes)})" if suffixes else ""
        lines.append(f"- {step.get('id')}: {role_name}{suffix}.")
    for role in role_definitions:
        if not isinstance(role, dict):
            continue
        role_name = str(role.get("name") or role.get("key") or "Role")
        description = str(role.get("description") or role.get("posture_notes") or "Follow the task-specific workflow contract.")
        notes.append(f"## {role_name} Notes\n{description}")
    return "\n".join(lines) or "- Workflow steps must produce declared handoffs.", "\n\n".join(notes)


def _specialized_workflow_gatekeeper_verifies(bundle: dict) -> str:
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    steps = workflow.get("steps") if isinstance(workflow.get("steps"), list) else []
    if not steps:
        return "done_when, fake_done, evidence_buckets, residual_risk"
    gatekeeper_step = steps[-1] if isinstance(steps[-1], dict) else {}
    verifies = ((gatekeeper_step.get("inputs") or {}).get("evidence_query") or {}).get("verifies") or []
    return ", ".join(str(item) for item in verifies) or "done_when, fake_done, evidence_buckets, residual_risk"


def _extract_specialized_workflow_notes(markdown: str) -> str:
    matches = list(re.finditer(r"(?m)^# [^\n]*Workflow Notes\s*$", str(markdown or "")))
    if not matches:
        return ""
    return "\n" + str(markdown or "")[matches[-1].start() :].strip()
