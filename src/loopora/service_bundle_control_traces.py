from __future__ import annotations

from loopora.service_bundle_control_trace_mining import preview_list_items

from loopora.utils import structured_bool_is_true

def coverage_trace(coverage: dict) -> list[str]:
    traces = [str(coverage.get("summary") or "").strip()]
    for target in list(coverage.get("targets") or [])[:3]:
        if not isinstance(target, dict):
            continue
        target_id = str(target.get("id") or "").strip()
        if not target_id:
            continue
        suffix = "required" if target.get("required") is True else "advisory"
        traces.append(f"{target_id} ({suffix})")
    return [trace for trace in traces if trace]

def append_trace_item(
    items: list[dict],
    *,
    key: str,
    label: str,
    surfaces: list[str],
    evidence: list[str],
) -> None:
    cleaned_evidence = [str(item).strip() for item in evidence if str(item).strip()]
    items.append(
        {
            "key": key,
            "label": label,
            "surfaces": surfaces,
            "evidence": cleaned_evidence[:4],
            "mapped": bool(cleaned_evidence),
        }
    )

def strategy_flow_trace(strategy_source: dict, strategy_flow_projection: dict) -> list[str]:
    traces = preview_list_items(str(strategy_source.get("collaboration_intent") or ""), limit=2)
    summary = str(strategy_flow_projection.get("summary") or "").strip()
    if summary:
        traces.append(summary)
    return traces[:4]

def gatekeeper_trace(gatekeeper: dict) -> list[str]:
    if not structured_bool_is_true(gatekeeper.get("enabled")):
        return []
    roles = ", ".join(str(item) for item in gatekeeper.get("roles") or [] if str(item).strip())
    finish_steps = ", ".join(str(item) for item in gatekeeper.get("finish_steps") or [] if str(item).strip())
    trace = "GateKeeper"
    if roles:
        trace = f"{trace}: {roles}"
    if finish_steps:
        trace = f"{trace}; finish steps: {finish_steps}"
    return [trace]

def control_trace(controls: list[dict]) -> list[str]:
    traces: list[str] = []
    for control in controls:
        control_id = str(control.get("id") or "").strip()
        signal = str(control.get("signal") or "").strip()
        role_name = str(control.get("role_name") or control.get("role_id") or "").strip()
        traces.append(f"{control_id or 'control'}: {signal or 'signal'} -> {role_name or 'role'}")
    return traces[:4]

_append_trace_item = append_trace_item
_control_trace = control_trace
_coverage_trace = coverage_trace
_gatekeeper_trace = gatekeeper_trace

"""Traceability assembly for bundle control summaries."""

from loopora.service_bundle_control_trace_mining import (
    build_execution_strategy_trace,
    build_judgment_tradeoff_trace,
    build_local_governance_trace,
    build_loop_fit_trace,
    build_residual_risk_policy_trace,
    build_runtime_local_governance_trace,
    local_governance_markers_present,
    strategy_source_payload,
)
from loopora.service_bundle_control_trace_mining import (
    build_role_posture_trace,
    role_posture_preview,
)


__all__ = [
    "build_bundle_traceability_projection",
    "build_execution_strategy_trace",
    "build_judgment_tradeoff_trace",
    "build_local_governance_trace",
    "build_loop_fit_trace",
    "build_residual_risk_policy_trace",
    "build_role_posture_trace",
    "build_runtime_local_governance_trace",
    "preview_list_items",
    "role_posture_preview",
    "strategy_source_payload",
]


def build_bundle_traceability_projection(context: dict) -> dict:
    bundle = dict(context.get("bundle") or {})
    raw_sections = dict(context.get("raw_sections") or {})
    roles = list(context.get("roles") or [])
    strategy_source = dict(context.get("strategy_source") or context.get("workflow") or {})
    strategy_flow_projection = dict(context.get("strategy_flow_projection") or context.get("workflow_projection") or {})
    gatekeeper = dict(context.get("gatekeeper") or {})
    controls = list(context.get("controls") or [])
    coverage = dict(context.get("coverage") or {})
    collaboration_summary = str(bundle.get("collaboration_summary") or "").strip()
    judgment_tradeoffs = list(
        context.get("judgment_tradeoffs")
        or build_judgment_tradeoff_trace(
            collaboration_summary=collaboration_summary,
            raw_sections=raw_sections,
            roles=roles,
            strategy_source=strategy_source,
        )
    )
    execution_strategy = list(
        context.get("execution_strategy")
        or build_execution_strategy_trace(
            collaboration_summary=collaboration_summary,
            raw_sections=raw_sections,
            roles=roles,
            strategy_source=strategy_source,
        )
    )
    residual_risk_policy = list(context.get("residual_risk_policy") or build_residual_risk_policy_trace(raw_sections))
    local_governance = list(
        context.get("local_governance")
        or build_local_governance_trace(
            collaboration_summary=collaboration_summary,
            raw_sections=raw_sections,
            roles=roles,
            strategy_source=strategy_source,
        )
    )
    role_postures = list(context.get("role_postures") or build_role_posture_trace(roles))
    runtime_local_governance = build_runtime_local_governance_trace(
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
    )
    loop_fit_reasons = list(context.get("loop_fit_reasons") or build_loop_fit_trace(collaboration_summary))
    items: list[dict] = []

    _append_trace_item(
        items,
        key="loop_fit",
        label="Loopora fit",
        surfaces=["collaboration_summary"],
        evidence=loop_fit_reasons,
    )
    _append_trace_item(
        items,
        key="collaboration_story",
        label="Collaboration story",
        surfaces=["collaboration_summary"],
        evidence=preview_list_items(collaboration_summary, limit=2),
    )
    _append_trace_item(
        items,
        key="task_scope",
        label="Task scope",
        surfaces=["spec.markdown#Task"],
        evidence=preview_list_items(str(raw_sections.get("Task") or ""), limit=2),
    )
    _append_trace_item(
        items,
        key="success_surface",
        label="Success surface",
        surfaces=["spec.markdown#Success Surface"],
        evidence=preview_list_items(str(raw_sections.get("Success Surface") or ""), limit=3),
    )
    _append_trace_item(
        items,
        key="fake_done_risks",
        label="Fake done risks",
        surfaces=["spec.markdown#Fake Done"],
        evidence=preview_list_items(str(raw_sections.get("Fake Done") or ""), limit=3),
    )
    _append_trace_item(
        items,
        key="evidence_preferences",
        label="Evidence preferences",
        surfaces=["spec.markdown#Evidence Preferences"],
        evidence=preview_list_items(str(raw_sections.get("Evidence Preferences") or ""), limit=3),
    )
    if coverage.get("target_count"):
        _append_trace_item(
            items,
            key="coverage_targets",
            label="Coverage targets",
            surfaces=[
                "spec.markdown#Done When",
                "spec.markdown#Success Surface",
                "spec.markdown#Fake Done",
                "spec.markdown#Evidence Preferences",
            ],
            evidence=_coverage_trace(coverage),
        )
    _append_trace_item(
        items,
        key="execution_strategy",
        label="Execution strategy",
        surfaces=[
            "collaboration_summary",
            "spec.markdown",
            "role_definitions[].posture_notes",
            "workflow.collaboration_intent",
            "workflow.steps[].inputs",
        ],
        evidence=execution_strategy,
    )
    _append_trace_item(
        items,
        key="residual_risk_policy",
        label="Residual risk policy",
        surfaces=["spec.markdown#Residual Risk"],
        evidence=residual_risk_policy,
    )
    if local_governance or local_governance_markers_present(
        bundle=bundle,
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
    ):
        _append_trace_item(
            items,
            key="local_governance",
            label="Local governance",
            surfaces=[
                "spec.markdown#Role Notes",
                "role_definitions[].prompt_markdown",
                "role_definitions[].posture_notes",
                "workflow.collaboration_intent",
                "workflow.steps[].inputs",
            ],
            evidence=runtime_local_governance,
        )
    _append_trace_item(
        items,
        key="judgment_tradeoffs",
        label="Judgment tradeoffs",
        surfaces=[
            "collaboration_summary",
            "spec.markdown",
            "role_definitions[].posture_notes",
            "workflow.collaboration_intent",
        ],
        evidence=judgment_tradeoffs,
    )
    _append_trace_item(
        items,
        key="role_posture",
        label="Role posture",
        surfaces=["role_definitions[].prompt_markdown", "role_definitions[].posture_notes"],
        evidence=role_postures,
    )
    _append_trace_item(
        items,
        key="workflow_judgment",
        label="Run flow",
        surfaces=["workflow.collaboration_intent", "workflow.steps[].inputs"],
        evidence=_strategy_flow_trace(strategy_source, strategy_flow_projection),
    )
    _append_trace_item(
        items,
        key="gatekeeper_closure",
        label="GateKeeper closure",
        surfaces=["workflow.steps[].on_pass", "workflow.steps[].inputs.evidence_query"],
        evidence=_gatekeeper_trace(gatekeeper),
    )
    if controls:
        _append_trace_item(
            items,
            key="runtime_controls",
            label="Runtime controls",
            surfaces=["workflow.controls[]"],
            evidence=_control_trace(controls),
        )

    mapped_items = [item for item in items if item["mapped"]]
    return {
        "items": items,
        "mapped_count": len(mapped_items),
        "required_count": len(items),
        "missing": [item["key"] for item in items if not item["mapped"]],
        "surfaces": sorted({surface for item in mapped_items for surface in item["surfaces"]}),
    }


def _strategy_flow_trace(strategy_source: dict, strategy_flow_projection: dict) -> list[str]:
    return strategy_flow_trace(strategy_source, strategy_flow_projection)
