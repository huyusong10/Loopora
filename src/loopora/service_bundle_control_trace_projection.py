from __future__ import annotations

from loopora.service_bundle_control_trace_preview import preview_list_items
from loopora.structured_booleans import structured_bool_is_true


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
