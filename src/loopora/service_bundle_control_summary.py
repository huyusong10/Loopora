from __future__ import annotations

from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.service_bundle_control_diagnostics import build_bundle_control_diagnostics
from loopora.service_bundle_control_flow import (
    build_bundle_control_summaries,
    build_bundle_diagnostic_step_contexts,
    build_bundle_gatekeeper_projection,
    build_bundle_role_lookup,
    build_bundle_strategy_flow_projection,
)
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
