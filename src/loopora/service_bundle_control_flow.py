from __future__ import annotations

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
