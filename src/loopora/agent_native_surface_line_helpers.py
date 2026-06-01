from __future__ import annotations


def _native_surface_kv_line(
    title: str,
    source: dict,
    fields: tuple[tuple[str, str], ...],
) -> list[str]:
    rendered = []
    for label, key in fields:
        value = _native_surface_field_value(source.get(key))
        if value:
            rendered.append(f"{label}={value}")
    if not rendered:
        return []
    return [f"- {title}: " + "; ".join(rendered)]


def _native_surface_field_value(value: object) -> str:
    values = _compact_string_list(value)
    if values:
        return ", ".join(values[:5])
    return str(value or "").strip() if not isinstance(value, (list, tuple, set)) else ""


def _compact_string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _native_surface_reference_lines(surface: dict) -> list[str]:
    references = _compact_string_list(surface.get("reference_paths"))
    if not references:
        return []
    return ["- references: " + ", ".join(references[:4])]


def _native_surface_dispatch_detail_lines(surface: dict, dispatch: dict) -> list[str]:
    host_mechanism = str(dispatch.get("host_mechanism") or surface.get("host_mechanism") or "").strip()
    native_tools = [
        str(item).strip()
        for item in list(dispatch.get("accepted_native_tools") or surface.get("accepted_native_tools") or [])
        if str(item).strip()
    ]
    lines: list[str] = []
    if host_mechanism:
        lines.append(f"- host dispatch: {host_mechanism}")
    if native_tools:
        lines.append(f"- accepted native tools: {', '.join(native_tools)}")
    return lines


def _native_surface_target_agents(surface: dict) -> list[str]:
    targets = [str(item).strip() for item in list(surface.get("target_agents") or []) if str(item).strip()]
    if targets:
        return targets
    role_agents = surface.get("role_agents") if isinstance(surface.get("role_agents"), dict) else {}
    return [
        str(item.get("target_agent") or "").strip()
        for item in role_agents.values()
        if isinstance(item, dict) and str(item.get("target_agent") or "").strip()
    ]


def _native_surface_role_config_refs(role_agents: dict) -> list[str]:
    return [
        f"{str(item.get('target_agent') or '').strip()}={str(item.get('path') or '').strip()}"
        for item in role_agents.values()
        if isinstance(item, dict) and str(item.get("target_agent") or "").strip() and str(item.get("path") or "").strip()
    ]
