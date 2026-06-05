from __future__ import annotations

ARTIFACT_REF_KEYS = ("kind", "label", "relative_path", "workspace_path", "absolute_path")


def agent_native_context_artifact_refs(step_instruction_context: object) -> list[dict[str, str]]:
    step_context = step_instruction_context if isinstance(step_instruction_context, dict) else {}
    artifacts = step_context.get("artifacts") if isinstance(step_context.get("artifacts"), list) else []
    refs: list[dict[str, str]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        ref = {key: str(item.get(key) or "").strip() for key in ARTIFACT_REF_KEYS}
        if ref["label"] and (ref["relative_path"] or ref["workspace_path"] or ref["absolute_path"]):
            refs.append(ref)
    return refs
