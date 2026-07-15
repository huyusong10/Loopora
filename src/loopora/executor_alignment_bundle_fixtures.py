from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from loopora.alignment_guidance import alignment_guidance_dir
from loopora.bundle_io import bundle_to_yaml, load_bundle_text


def alignment_bundle_governance_sentence(workdir: str, *, locale: str) -> str:
    markers = _governance_markers_for_workdir(workdir)
    if not markers:
        return ""
    marker_text = ", ".join(markers)
    if locale == "zh":
        return (
            f" 项目本地治理入口（{marker_text}）也是运行责任：Builder 读取适用规则，"
            "Inspector / Custom 验证相关 design 或 test 契约，GateKeeper 将跳过本地治理或缺少预期验证视为 Weak、Unproven 或 Blocking。"
        )
    return (
        f" Project-local governance markers ({marker_text}) are runtime responsibilities: "
        "Builder reads the applicable rules, Inspector / Custom verifies related design or test contracts, "
        "and GateKeeper treats skipped local governance or missing expected validation as Weak, Unproven, or Blocking."
    )

def alignment_bundle_governance_role_snippet(workdir: str, *, role: str, locale: str) -> str:
    markers = _governance_markers_for_workdir(workdir)
    if not markers:
        return ""
    marker_text = ", ".join(markers)
    if locale == "zh":
        snippets = {
            "builder": f"\n      Builder 读取适用的项目本地治理入口（{marker_text}），再修改工作并在 handoff 中说明治理证据。",
            "inspector": f"\n      Inspector 验证 Builder 是否遵守 {marker_text} 中相关规则、design 或 test 契约；跳过本地治理应作为弱证据或缺失证明。",
            "gatekeeper": f"\n      GateKeeper 将跳过 {marker_text} 中相关本地治理责任或缺少预期验证视为 Weak、Unproven 或 Blocking。",
        }
    else:
        snippets = {
            "builder": f"\n      Builder reads applicable project-local governance markers ({marker_text}) before changing work and names the governance evidence in the handoff.",
            "inspector": f"\n      Inspector verifies whether Builder followed the relevant {marker_text} rules, design, or test contracts; skipped local governance is weak or missing evidence.",
            "gatekeeper": f"\n      GateKeeper treats skipped {marker_text} local-governance responsibilities or missing expected validation as Weak, Unproven, or Blocking.",
        }
    return snippets.get(role, "")

def _governance_markers_for_workdir(workdir: str) -> list[str]:
    root = Path(str(workdir or "")).expanduser()
    markers: list[str] = []
    if (root / "AGENTS.md").is_file():
        markers.append("AGENTS.md")
    design_dir = root / "design"
    if (design_dir / "README.md").is_file():
        markers.append("design/README.md")
    if design_dir.is_dir():
        markers.append("design/")
    if (root / "tests").is_dir():
        markers.append("tests/")
    return markers

_local_governance_role_snippet = alignment_bundle_governance_role_snippet
_local_governance_bundle_sentence = alignment_bundle_governance_sentence

@dataclass(frozen=True)
class AlignmentTaskDomainProjection:
    success_focus: str
    fake_done_focus: str
    evidence_focus: str
    evidence_verifies: list[str]

def alignment_task_domain_projection(
    task_text: str,
    *,
    display_language: str = "",
) -> AlignmentTaskDomainProjection:
    del task_text
    language = "zh" if str(display_language or "").strip().lower().startswith("zh") else "en"
    values = _GENERIC_PROJECTION[language]
    return AlignmentTaskDomainProjection(
        success_focus=values["success_focus"],
        fake_done_focus=values["fake_done_focus"],
        evidence_focus=values["evidence_focus"],
        evidence_verifies=list(_GENERIC_VERIFIES),
    )

_GENERIC_VERIFIES = ["task_anchor", "success_criteria", "negative_paths", "evidence", "residual_risk"]

_GENERIC_PROJECTION = {
    "en": {
        "success_focus": "the user-confirmed success criteria and observable task outcome",
        "fake_done_focus": "happy-path, mock-only, prose-only, or uncited completion claims",
        "evidence_focus": "direct behavior, negative paths, durable artifacts, and reproducible checks",
    },
    "zh": {
        "success_focus": "用户确认的成功标准与可观察任务结果",
        "fake_done_focus": "只覆盖 happy path、mock、文案或没有引用证据的完成声明",
        "evidence_focus": "直接行为、负向路径、持久 artifact 与可复验检查",
    },
}

def alignment_bundle_yaml(workdir: str) -> str:
    replacements = {
        "workdir": workdir,
        "local_governance_sentence": alignment_bundle_governance_sentence(workdir, locale="en"),
        "builder_governance": alignment_bundle_governance_role_snippet(workdir, role="builder", locale="en"),
        "inspector_governance": alignment_bundle_governance_role_snippet(workdir, role="inspector", locale="en"),
        "gatekeeper_governance": alignment_bundle_governance_role_snippet(workdir, role="gatekeeper", locale="en"),
    }
    return _render_base_bundle_template(replacements)

def _render_base_bundle_template(replacements: dict[str, str]) -> str:
    rendered = _base_bundle_template()
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("unresolved base bundle template placeholder")
    return rendered

def _base_bundle_template() -> str:
    return (alignment_guidance_dir() / "base-bundle.yml").read_text(encoding="utf-8")


def alignment_chinese_bundle_yaml(workdir: str) -> str:
    bundle = load_bundle_text(alignment_bundle_yaml(workdir))
    bundle["metadata"]["name"] = "对齐 Starter Bundle"
    bundle["metadata"]["description"] = "由 Web alignment flow 生成的通用证据治理 bundle。"
    bundle["loop"]["name"] = "对齐 Starter Bundle"
    bundle["collaboration_summary"] = (
        "把工作协议投影成任务契约、Builder/Inspector handoff 和 GateKeeper 裁决。"
        "每轮必须留下可复验的中间证据；主流程、负向路径或必需证据未证明时 fail closed。"
    )
    bundle["spec"]["markdown"] = _task_spec_markdown("用户确认的任务", language="zh")
    role_names = {
        "builder": "聚焦 Builder",
        "contract-inspector": "契约 Inspector",
        "evidence-inspector": "证据 Inspector",
        "gatekeeper": "审慎 GateKeeper",
    }
    for role in bundle.get("role_definitions", []):
        key = str(role.get("key") or "")
        if key in role_names:
            role["name"] = role_names[key]
    return bundle_to_yaml(bundle)


def alignment_chinese_bundle_yaml_with_english_visible_names(workdir: str) -> str:
    bundle = load_bundle_text(alignment_chinese_bundle_yaml(workdir))
    bundle["metadata"]["name"] = "Aligned Starter Bundle"
    bundle["metadata"]["description"] = "Bundle generated by the Web alignment flow."
    bundle["loop"]["name"] = "Aligned Starter Bundle"
    role_names = {
        "builder": "Focused Builder",
        "contract-inspector": "Contract Inspector",
        "evidence-inspector": "Evidence Inspector",
        "gatekeeper": "Conservative GateKeeper",
    }
    for role in bundle.get("role_definitions", []):
        key = str(role.get("key") or "")
        if key in role_names:
            role["name"] = role_names[key]
    return bundle_to_yaml(bundle)


def alignment_improvement_bundle_yaml(workdir: str) -> str:
    bundle = load_bundle_text(alignment_bundle_yaml(workdir))
    bundle["metadata"]["name"] = "Aligned Improvement Bundle"
    bundle["metadata"]["description"] = "Feedback-driven revision of a reviewed Loop contract."
    bundle["loop"]["name"] = "Aligned Improvement Bundle"
    bundle["collaboration_summary"] = (
        "Preserve stable task intent and workdir while tightening only the evidence, role posture, workflow, "
        "or closure judgment that feedback proves weak."
    )
    bundle["spec"]["markdown"] += (
        "\n\n# Improvement Boundary\n\nPreserve stable source intent; change only feedback-proven gaps and verify before/after behavior."
    )
    return bundle_to_yaml(bundle)


def alignment_chinese_improvement_bundle_yaml(workdir: str) -> str:
    bundle = load_bundle_text(alignment_chinese_bundle_yaml(workdir))
    bundle["metadata"]["name"] = "对齐改进 Bundle"
    bundle["metadata"]["description"] = "基于反馈修订经评审的 Loop 契约。"
    bundle["loop"]["name"] = "对齐改进 Bundle"
    bundle["collaboration_summary"] = "保留稳定任务意图和 workdir，只加强反馈证明薄弱的证据、角色、workflow 或收束裁决。"
    bundle["spec"]["markdown"] += "\n\n# Improvement Boundary\n\n保留稳定来源意图；只改反馈证明的缺口，并验证 before/after 行为。"
    return bundle_to_yaml(bundle)


def alignment_chinese_refactor_improvement_bundle_yaml(workdir: str) -> str:
    bundle = load_bundle_text(
        alignment_task_anchored_repair_bundle_yaml(
            workdir,
            "在用户确认边界内降低复杂度，并用 before/after 行为和复杂度证据证明没有回归或转移复杂度",
            prefers_chinese=True,
        )
    )
    bundle["metadata"]["name"] = "重构改进 Bundle"
    bundle["metadata"]["description"] = "任务范围内、证据驱动的重构改进候选。"
    bundle["loop"]["name"] = "重构改进 Bundle"
    return bundle_to_yaml(bundle)


def alignment_refund_repair_bundle_yaml(workdir: str) -> str:
    return alignment_task_anchored_repair_bundle_yaml(
        workdir,
        "deliver a safe refund flow with authorization, failure, audit, and duplicate-prevention evidence",
        prefers_chinese=False,
    )


def alignment_chinese_refund_repair_bundle_yaml(workdir: str) -> str:
    return alignment_task_anchored_repair_bundle_yaml(
        workdir,
        "交付有授权、失败处理、审计和重复退款防护证据的安全退款流程",
        prefers_chinese=True,
    )


def alignment_task_anchored_repair_bundle_yaml(
    workdir: str,
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    task = str(task_text or "").strip() or ("用户确认的任务" if prefers_chinese else "the user-confirmed task")
    normalized_language = str(display_language or "").strip().lower()
    language = "zh" if prefers_chinese or normalized_language == "zh" or _text_has_cjk(task) else "es" if normalized_language == "es" else "en"
    base = alignment_chinese_bundle_yaml(workdir) if language == "zh" else alignment_bundle_yaml(workdir)
    bundle = load_bundle_text(base)
    name = {"zh": "任务证据 Loop", "es": "Loop de evidencia de tarea", "en": "Task Evidence Loop"}[language]
    bundle["metadata"]["name"] = name
    bundle["metadata"]["description"] = {
        "zh": "保留用户任务锚点的通用证据治理 bundle。",
        "es": "Bundle genérico de evidencia que conserva la tarea confirmada.",
        "en": "Generic evidence-governed bundle with the confirmed task anchor preserved.",
    }[language]
    bundle["loop"]["name"] = name
    bundle["loop"]["workdir"] = workdir
    bundle["collaboration_summary"] = {
        "zh": f"围绕用户确认的任务“{task}”构建最小真实闭环，先由 Builder 交付，再由两个 Inspector 反证，最后由 GateKeeper 依据直接证据保守裁决。",
        "es": f"Construir el cierre mínimo para «{task}», desafiarlo con dos Inspectors y dejar que GateKeeper decida desde evidencia directa.",
        "en": f"Build the smallest real loop for '{task}', challenge it through two Inspector views, then let GateKeeper judge from direct evidence.",
    }[language]
    bundle["spec"]["markdown"] = _task_spec_markdown(task, language=language)
    workflow = bundle.get("workflow")
    if isinstance(workflow, dict):
        workflow["collaboration_intent"] = {
            "zh": f"任务锚点：{task}。Builder 交付最小闭环；契约与证据 Inspector 反证；GateKeeper 对未证明声明 fail closed。",
            "es": f"Tarea: {task}. Builder entrega; dos Inspectors desafían; GateKeeper bloquea afirmaciones no probadas.",
            "en": f"Task anchor: {task}. Builder delivers; contract and evidence Inspectors challenge; GateKeeper fails closed on unproven claims.",
        }[language]
    return bundle_to_yaml(bundle)


def _task_spec_markdown(task: str, *, language: str) -> str:
    projection = alignment_task_domain_projection(task, display_language=language)
    if language == "zh":
        return f"""# Task

交付用户确认任务的最小可证明闭环：{task}

# Done When

- 用户确认的成功标准和可观察结果都有直接证据：{projection.success_focus}。
- Builder handoff 说明改动、证据、未证明项和 blocker；Inspector 独立复验。

# Guardrails

- 不推断用户未确认的业务域、技术栈或更宽范围；遵守 workdir 中适用的本地治理。

# Success Surface

- 用户可以从行为、artifact、命令结果和 handoff 审计任务结果。

# Fake Done

- 不接受这些浅层完成声明：{projection.fake_done_focus}。

# Evidence Preferences

- 优先：{projection.evidence_focus}。

# Execution Strategy

Builder 先完成最小真实闭环；契约 Inspector 与证据 Inspector 反证；GateKeeper 依据 handoff 和 evidence_query 裁决。

# Judgment Tradeoffs

优先小而可证明的闭环，不用更宽、更快或更漂亮但证据薄弱的实现换取通过。

# Residual Risk

核心声明或必需证据未证明时 fail closed；仅允许已点名、可见且有 owner 的范围外风险。

# Role Notes

## Builder Notes

改动目标并留下改动、证据、未证明项和 blocker。

## Inspector Notes

独立复验证据并质疑 happy path、mock-only 和范围漂移声明。

## GateKeeper Notes

核心声明未证明或必需证据缺失时阻断收束。"""
    if language == "es":
        return f"""# Task

Entregar el cierre mínimo y probado para la tarea confirmada: {task}

# Done When

- Los criterios confirmados y el resultado observable tienen evidencia directa: {projection.success_focus}.
- El handoff de Builder nombra cambios, prueba, afirmaciones no probadas y blockers; Inspectors verifican de forma independiente.

# Guardrails

- No inferir dominio, stack o alcance no confirmado; respetar la gobernanza local aplicable.

# Success Surface

- El usuario puede auditar comportamiento, artefactos, resultados y handoffs.

# Fake Done

- No aceptar: {projection.fake_done_focus}.

# Evidence Preferences

- Preferir: {projection.evidence_focus}.

# Execution Strategy

Builder entrega el cierre mínimo; dos Inspectors desafían; GateKeeper juzga desde evidencia directa.

# Judgment Tradeoffs

Preferir un cierre pequeño y probado sobre trabajo amplio con evidencia débil.

# Residual Risk

Falta de prueba central bloquea; solo riesgos visibles, nombrados y con dueño pueden quedar.

# Role Notes

## Builder Notes

Cambiar el objetivo y dejar cambios, evidencia, afirmaciones no probadas y blockers.

## Inspector Notes

Verificar evidencia de forma independiente y cuestionar happy path, mocks y deriva de alcance.

## GateKeeper Notes

Bloquear el cierre cuando falta prueba central o evidencia requerida."""
    return f"""# Task

Deliver the smallest proven loop for the confirmed user task: {task}

# Done When

- Confirmed success criteria and the observable result have direct evidence: {projection.success_focus}.
- Builder handoff names changes, evidence, unproven claims, and blockers; Inspectors verify independently.

# Guardrails

- Do not infer an unconfirmed business domain, stack, or broader scope; follow applicable workdir governance.

# Success Surface

- The user can audit behavior, artifacts, command results, and handoffs.

# Fake Done

- Do not accept: {projection.fake_done_focus}.

# Evidence Preferences

- Prefer: {projection.evidence_focus}.

# Execution Strategy

Builder delivers the smallest real loop; contract and evidence Inspectors challenge it; GateKeeper judges from handoffs and evidence queries.

# Judgment Tradeoffs

Prefer a narrow proven loop over broader, faster, or more polished work with weak evidence.

# Residual Risk

Missing core proof fails closed; only named, visible, owned out-of-scope risks may remain.

# Role Notes

## Builder Notes

Change the target and leave changed surfaces, evidence, unproven claims, and blockers.

## Inspector Notes

Independently verify evidence and challenge happy-path, mock-only, and scope-drift claims.

## GateKeeper Notes

Block closure when core claims or required evidence remain unproven."""


def _text_has_cjk(value: object) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def alignment_bundle_yaml_with_unsupported_observed_workdir_claim(workdir: str) -> str:
    return alignment_bundle_yaml(workdir).replace(
        "Ship the focused starter experience for the target user in the target workdir",
        "Observed Workdir Snapshot shows a React frontend app with npm build scripts. Ship the focused starter experience for the target user",
        1,
    )


def alignment_bundle_yaml_with_governance_markers_listed_as_facts(workdir: str) -> str:
    yaml_text = alignment_bundle_yaml(workdir).replace(_local_governance_bundle_sentence(workdir, locale="en"), "")
    for role in ("builder", "inspector", "gatekeeper"):
        yaml_text = yaml_text.replace(_local_governance_role_snippet(workdir, role=role, locale="en"), "")
    return yaml_text.replace(
        "Ship the focused starter experience for the target user in the target workdir",
        "Workdir Snapshot detected AGENTS.md, design/README.md, design/, and tests/. Ship the focused starter experience for the target user",
        1,
    )


def alignment_bundle_yaml_with_lineage_metadata(workdir: str) -> str:
    return alignment_bundle_yaml(workdir).replace(
        '  description: "Bundle generated by the Web alignment flow."\n',
        '  description: "Bundle generated by the Web alignment flow."\n  source_bundle_id: "source_bundle_old"\n  revision: 2\n',
        1,
    )


def alignment_bundle_yaml_without_semantics(workdir: str) -> str:
    yaml_text = alignment_bundle_yaml(workdir)
    yaml_text = re.sub(r"\n    # Success Surface\n\n    - .+?\n(?=\n    # Fake Done)", "\n", yaml_text, flags=re.DOTALL)
    return re.sub(
        r"\n    # Evidence Preferences\n\n    - .+?\n(?=\n    # Role Notes)",
        "\n",
        yaml_text,
        flags=re.DOTALL,
    )
