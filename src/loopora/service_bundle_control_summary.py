from __future__ import annotations

from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.service_bundle_control_traces import (
    build_bundle_traceability_projection as _traceability_projection,
    build_execution_strategy_trace,
    build_judgment_tradeoff_trace,
    build_local_governance_trace,
    build_loop_fit_trace,
    build_residual_risk_policy_trace as _residual_risk_policy_trace,
    build_role_posture_trace as _role_posture_trace,
    build_runtime_local_governance_trace,
    preview_list_items,
    role_posture_preview,
    strategy_source_payload as _strategy_source_payload,
)
from loopora.specs import SpecError, compile_markdown_spec

from loopora.residual_risk_support import residual_risk_is_unmanaged

from loopora.service_bundle_control_input_diagnostics import (
    append_bundle_control_diagnostic as _append_diagnostic,
)

from loopora.service_bundle_control_input_diagnostics import append_strategy_input_diagnostics

"""Strategy Source flow/control projections for bundle control summaries."""

def build_bundle_role_lookup(*, roles: list[dict], workflow_roles: list[dict]) -> dict:
    role_definition_by_key = {str(role.get("key") or ""): role for role in roles if isinstance(role, dict)}
    workflow_role_by_id = {
        str(role.get("id") or ""): role
        for role in workflow_roles
        if isinstance(role, dict) and str(role.get("id") or "").strip()
    }
    return {
        "role_definition_by_key": role_definition_by_key,
        "workflow_role_by_id": workflow_role_by_id,
    }

def role_for_bundle_step(step: dict, role_lookup: dict) -> dict:
    workflow_role = role_lookup["workflow_role_by_id"].get(str(step.get("role_id") or ""), {})
    return role_lookup["role_definition_by_key"].get(str(workflow_role.get("role_definition_key") or ""), {})

def bundle_step_label(step: dict, role_lookup: dict) -> str:
    role = role_for_bundle_step(step, role_lookup)
    return str(role.get("name") or step.get("role_id") or step.get("id") or "").strip()

def build_bundle_strategy_flow_projection(steps: list[dict], role_lookup: dict) -> dict:
    return {
        "step_count": len(steps),
        "parallel_groups": bundle_parallel_groups(steps),
        "summary": " -> ".join(item for item in grouped_bundle_step_labels(steps, role_lookup) if item),
    }

def bundle_parallel_groups(steps: list[dict]) -> list[str]:
    return sorted(
        {
            str(step.get("parallel_group") or "").strip()
            for step in steps
            if str(step.get("parallel_group") or "").strip()
        }
    )

def grouped_bundle_step_labels(steps: list[dict], role_lookup: dict) -> list[str]:
    grouped_steps: list[str] = []
    index = 0
    while index < len(steps):
        step = steps[index]
        group = str(step.get("parallel_group") or "").strip()
        if group:
            grouped = []
            while index < len(steps) and str(steps[index].get("parallel_group") or "").strip() == group:
                grouped.append(bundle_step_label(steps[index], role_lookup))
                index += 1
            grouped_steps.append("[" + " + ".join(item for item in grouped if item) + "]")
            continue
        grouped_steps.append(bundle_step_label(step, role_lookup))
        index += 1
    return grouped_steps

def build_bundle_gatekeeper_projection(steps: list[dict], role_lookup: dict) -> dict:
    gatekeeper_steps = [
        step
        for step in steps
        if str(role_for_bundle_step(step, role_lookup).get("archetype") or "").strip().lower() == "gatekeeper"
    ]
    gatekeeper_enabled = bool(gatekeeper_steps)
    return {
        "enabled": gatekeeper_enabled,
        "roles": bundle_gatekeeper_role_names(gatekeeper_steps, role_lookup),
        "finish_steps": [
            str(step.get("id") or "").strip()
            for step in gatekeeper_steps
            if str(step.get("on_pass") or "").strip() == "finish_run"
        ],
        "requires_evidence_refs": gatekeeper_enabled,
    }

def bundle_gatekeeper_role_names(gatekeeper_steps: list[dict], role_lookup: dict) -> list[str]:
    gatekeeper_roles = []
    for step in gatekeeper_steps:
        role_name = bundle_step_label(step, role_lookup)
        if role_name and role_name not in gatekeeper_roles:
            gatekeeper_roles.append(role_name)
    return gatekeeper_roles

def build_bundle_control_summaries(strategy_source: dict, role_lookup: dict) -> list[dict]:
    control_summaries = []
    for control in list(strategy_source.get("controls") or []):
        if not isinstance(control, dict):
            continue
        role_id = str((control.get("call") or {}).get("role_id") or "").strip()
        strategy_role = role_lookup["workflow_role_by_id"].get(role_id, {})
        role_definition = role_lookup["role_definition_by_key"].get(str(strategy_role.get("role_definition_key") or ""), {})
        control_summaries.append(
            {
                "id": str(control.get("id") or "").strip(),
                "signal": str((control.get("when") or {}).get("signal") or "").strip(),
                "after": str((control.get("when") or {}).get("after") or "").strip(),
                "role_id": role_id,
                "role_name": str(role_definition.get("name") or role_id).strip(),
                "role_archetype": str(role_definition.get("archetype") or "").strip(),
                "mode": str(control.get("mode") or "").strip(),
                "max_fires_per_run": bundle_control_max_fires_per_run(control.get("max_fires_per_run")),
            }
        )
    return control_summaries

def bundle_control_max_fires_per_run(value: object) -> int | str:
    if value is None or value == "":
        return 1
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()

def build_bundle_diagnostic_step_contexts(steps: list[dict], role_lookup: dict) -> list[dict]:
    return [
        {
            "step": step,
            "step_id": str(step.get("id") or "").strip(),
            "archetype": str(role_for_bundle_step(step, role_lookup).get("archetype") or "").strip().lower(),
            "inputs": step.get("inputs") if isinstance(step.get("inputs"), dict) else {},
            "on_pass": str(step.get("on_pass") or "").strip(),
        }
        for step in steps
    ]

def build_bundle_control_diagnostics(
    *,
    bundle: dict,
    raw_sections: dict,
    step_contexts: list[dict],
    traceability: dict,
) -> list[dict]:
    diagnostics: list[dict] = []
    _append_traceability_diagnostics(diagnostics, traceability)
    _append_residual_risk_policy_diagnostics(diagnostics, raw_sections)
    _append_completion_mode_diagnostics(diagnostics, bundle)
    append_strategy_input_diagnostics(diagnostics, step_contexts)
    return diagnostics

def _append_traceability_diagnostics(diagnostics: list[dict], traceability: dict) -> None:
    missing = [str(item).strip() for item in list(traceability.get("missing") or []) if str(item).strip()]
    if not missing:
        return
    _append_diagnostic(
        diagnostics,
        {
            "code": "traceability_missing",
            "severity": "warning",
            "title_en": "Judgment projection is incomplete",
            "title_zh": "判断投影不完整",
            "message_en": "Some confirmed judgment areas do not map to a runnable bundle surface.",
            "message_zh": "部分已确认判断没有映射到可运行的方案表面。",
            "surfaces": ["collaboration_summary", "spec.markdown", "role_definitions[]", "workflow"],
            "details": {"missing": missing},
        },
    )

def _append_residual_risk_policy_diagnostics(diagnostics: list[dict], raw_sections: dict) -> None:
    residual_risk = str(raw_sections.get("Residual Risk") or "").strip()
    if not residual_risk or not residual_risk_is_unmanaged(residual_risk):
        return
    _append_diagnostic(
        diagnostics,
        {
            "code": "residual_risk_unmanaged",
            "severity": "warning",
            "title_en": "Residual risk policy is not actionable",
            "title_zh": "残余风险策略不可执行",
            "message_en": "Residual risk must name what may remain and who owns, tracks, follows up, accepts, or blocks it.",
            "message_zh": "残余风险必须说明哪些风险可以留下，以及由谁负责、如何跟踪、后续处理、接受或阻断。",
            "surfaces": ["spec.markdown#Residual Risk"],
        },
    )

def _append_completion_mode_diagnostics(diagnostics: list[dict], bundle: dict) -> None:
    completion_mode = str((bundle.get("loop") or {}).get("completion_mode") or "").strip().lower()
    if completion_mode == "gatekeeper":
        return
    _append_diagnostic(
        diagnostics,
        {
            "code": "completion_not_gatekeeper",
            "severity": "info",
            "title_en": "Run closes without evidence-backed GateKeeper mode",
            "title_zh": "运行不是由证据守门模式收束",
            "message_en": "Expert bundles may use this, but the task verdict will lean more on runtime lifecycle than GateKeeper evidence closure.",
            "message_zh": "专家方案可以这样运行，但 Loop 裁决会更依赖运行生命周期，而不是 GateKeeper 的证据收口。",
            "surfaces": ["loop.completion_mode"],
        },
    )


__all__ = [
    "_strategy_source_payload",
    "_traceability_projection",
    "build_bundle_control_summary",
    "build_execution_strategy_trace",
    "build_judgment_tradeoff_trace",
    "build_local_governance_trace",
    "build_loop_fit_trace",
    "build_runtime_local_governance_trace",
    "preview_list_items",
    "role_posture_preview",
]


def build_bundle_control_summary(bundle: dict) -> dict:
    compiled_spec = _compile_bundle_spec(bundle)
    raw_sections = _raw_sections(compiled_spec)
    coverage = _coverage_projection(compiled_spec)
    roles = list(bundle.get("role_definitions") or [])
    strategy_source = dict(bundle.get("workflow") or {})
    steps = list(strategy_source.get("steps") or [])
    role_lookup = build_bundle_role_lookup(roles=roles, workflow_roles=list(strategy_source.get("roles") or []))
    strategy_flow_projection = build_bundle_strategy_flow_projection(steps, role_lookup)
    gatekeeper = build_bundle_gatekeeper_projection(steps, role_lookup)
    controls = build_bundle_control_summaries(strategy_source, role_lookup)
    collaboration_summary = str(bundle.get("collaboration_summary") or "").strip()
    loop_fit_reasons = build_loop_fit_trace(collaboration_summary)
    judgment_tradeoffs = build_judgment_tradeoff_trace(
        collaboration_summary=bundle.get("collaboration_summary"),
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
    )
    execution_strategy = build_execution_strategy_trace(
        collaboration_summary=bundle.get("collaboration_summary"),
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
    )
    residual_risk_policy = _residual_risk_policy_trace(raw_sections)
    role_postures = _role_posture_trace(roles)
    task_scope = preview_list_items(str(raw_sections.get("Task") or ""), limit=2)
    success_surface = preview_list_items(str(raw_sections.get("Success Surface") or ""), limit=3)
    fake_done_risks = preview_list_items(str(raw_sections.get("Fake Done") or ""), limit=3)
    evidence_preferences = preview_list_items(str(raw_sections.get("Evidence Preferences") or ""), limit=3)
    local_governance_signals = build_local_governance_trace(
        collaboration_summary=bundle.get("collaboration_summary"),
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
    )
    local_governance = build_runtime_local_governance_trace(
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
    )
    traceability = _traceability_projection(
        {
            "bundle": bundle,
            "raw_sections": raw_sections,
            "roles": roles,
            "strategy_source": strategy_source,
            "strategy_flow_projection": strategy_flow_projection,
            "gatekeeper": gatekeeper,
            "controls": controls,
            "loop_fit_reasons": loop_fit_reasons,
            "judgment_tradeoffs": judgment_tradeoffs,
            "execution_strategy": execution_strategy,
            "residual_risk_policy": residual_risk_policy,
            "local_governance": local_governance_signals,
            "role_postures": role_postures,
            "coverage": coverage,
        }
    )
    diagnostics = build_bundle_control_diagnostics(
        bundle=bundle,
        raw_sections=raw_sections,
        step_contexts=build_bundle_diagnostic_step_contexts(steps, role_lookup),
        traceability=traceability,
    )

    return {
        "risks": preview_list_items(
            str(raw_sections.get("Fake Done") or "") + "\n" + str(raw_sections.get("Residual Risk") or ""),
            limit=4,
        ),
        "evidence": _evidence_titles(compiled_spec),
        "coverage": coverage,
        "task_scope": task_scope,
        "success_surface": success_surface,
        "fake_done_risks": fake_done_risks,
        "evidence_preferences": evidence_preferences,
        "loop_fit_reasons": loop_fit_reasons,
        "residual_risk_policy": residual_risk_policy,
        "execution_strategy": execution_strategy,
        "local_governance": local_governance,
        "role_postures": role_postures,
        "judgment_tradeoffs": judgment_tradeoffs,
        "workflow": strategy_flow_projection,
        "gatekeeper": gatekeeper,
        "traceability": traceability,
        "diagnostics": diagnostics,
        "controls": controls,
    }


def _compile_bundle_spec(bundle: dict) -> dict:
    try:
        compiled_spec = compile_markdown_spec(str(bundle.get("spec", {}).get("markdown") or ""))
    except SpecError:
        return {"raw_sections": {}}
    if not isinstance(compiled_spec, dict):
        return {"raw_sections": {}}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    completion_mode = str(loop.get("completion_mode") or "gatekeeper").strip() or "gatekeeper"
    return with_coverage_targets(compiled_spec, completion_mode=completion_mode)


def _raw_sections(compiled_spec: dict) -> dict:
    raw_sections = compiled_spec.get("raw_sections")
    return raw_sections if isinstance(raw_sections, dict) else {}


def _evidence_titles(compiled_spec: dict) -> list[str]:
    return [
        str(check.get("title") or "").strip()
        for check in list(compiled_spec.get("checks") or [])[:4]
        if isinstance(check, dict) and str(check.get("title") or "").strip()
    ]


def _coverage_projection(compiled_spec: dict) -> dict:
    checks = [check for check in list(compiled_spec.get("checks") or []) if isinstance(check, dict)]
    targets = [target for target in list(compiled_spec.get("coverage_targets") or []) if isinstance(target, dict)]
    target_rows = [
        {
            "id": str(target.get("id") or "").strip(),
            "kind": str(target.get("kind") or "").strip(),
            "source_section": str(target.get("source_section") or "").strip(),
            "required": target.get("required") is True,
        }
        for target in targets
        if str(target.get("id") or "").strip()
    ]
    check_count = len(checks)
    target_count = len(target_rows)
    required_target_count = sum(1 for target in target_rows if target["required"])
    return {
        "check_mode": str(compiled_spec.get("check_mode") or "").strip(),
        "check_count": check_count,
        "target_count": target_count,
        "required_target_count": required_target_count,
        "targets": target_rows[:12],
        "summary": _coverage_summary_text_en(check_count, target_count, required_target_count),
        "summary_en": _coverage_summary_text_en(check_count, target_count, required_target_count),
        "summary_zh": _coverage_summary_text_zh(check_count, target_count, required_target_count),
    }


def _coverage_summary_text_en(check_count: int, target_count: int, required_target_count: int) -> str:
    if check_count and target_count:
        return f"{check_count} checks / {target_count} coverage targets ({required_target_count} required)"
    if check_count:
        return f"{check_count} checks"
    if target_count:
        return f"{target_count} coverage targets ({required_target_count} required)"
    return ""


def _coverage_summary_text_zh(check_count: int, target_count: int, required_target_count: int) -> str:
    if check_count and target_count:
        return f"{check_count} 项检查 / {target_count} 个覆盖目标（{required_target_count} 必需）"
    if check_count:
        return f"{check_count} 项检查"
    if target_count:
        return f"{target_count} 个覆盖目标（{required_target_count} 必需）"
    return ""
