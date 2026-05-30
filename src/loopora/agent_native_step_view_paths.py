from __future__ import annotations


def agent_native_step_view_path_text(
    step_view: dict,
    *,
    absolute: bool = False,
    legacy_fallback: bool = False,
) -> str:
    keys = (
        ("agent_step_view_absolute_path", "agent_step_view_path")
        if absolute
        else ("agent_step_view_path", "agent_step_view_absolute_path")
    )
    if legacy_fallback:
        keys = (*keys, *_legacy_capsule_path_keys(absolute=absolute))
    return _first_path_text(step_view, *keys)


def agent_native_step_contract_path_text(
    step_view: dict,
    *,
    absolute: bool = False,
    legacy_fallback: bool = True,
) -> str:
    keys = (
        ("step_contract_absolute_path", "step_contract_path")
        if absolute
        else ("step_contract_path", "step_contract_absolute_path")
    )
    if legacy_fallback:
        keys = (*keys, *_legacy_capsule_path_keys(absolute=absolute))
    return _first_path_text(step_view, *keys)


def agent_native_legacy_capsule_path_text(step_view: dict, *, absolute: bool = False) -> str:
    return _first_path_text(step_view, *_legacy_capsule_path_keys(absolute=absolute))


def agent_native_step_view_artifact_path_texts(step_view: dict) -> list[str]:
    candidates = [
        _first_path_text(step_view, "agent_step_view_absolute_path", "agent_step_view_path"),
        _first_path_text(step_view, "step_contract_absolute_path", "step_contract_path"),
        _first_path_text(step_view, "capsule_absolute_path", "capsule_path"),
    ]
    return list(dict.fromkeys(path for path in candidates if path))


def _first_path_text(step_view: dict, *keys: str) -> str:
    if not isinstance(step_view, dict):
        return ""
    for key in keys:
        text = str(step_view.get(key) or "").strip()
        if text:
            return text
    return ""


def _legacy_capsule_path_keys(*, absolute: bool) -> tuple[str, str]:
    return ("capsule_absolute_path", "capsule_path") if absolute else ("capsule_path", "capsule_absolute_path")
