from __future__ import annotations

from pathlib import Path

from loopora.context_value_helpers import string_list as _string_list
from loopora.run_artifacts import RunArtifactLayout


def output_workspace_artifact_refs(layout: RunArtifactLayout, output: dict) -> list[dict[str, str]]:
    fields = (
        ("proof_files", "proof-file"),
        ("proof_artifacts", "proof-artifact"),
        ("artifact_paths", "artifact"),
        ("generated_files", "generated-file"),
        ("changed_files", "changed-file"),
    )
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    for field_name, label_prefix in fields:
        for value in _string_list(output.get(field_name)):
            ref = workspace_artifact_ref(layout, value, label_prefix=label_prefix)
            if not ref or ref["absolute_path"] in seen:
                continue
            refs.append(ref)
            seen.add(ref["absolute_path"])
    return refs[:20]


def workspace_artifact_ref(layout: RunArtifactLayout, value: str, *, label_prefix: str) -> dict[str, str] | None:
    cleaned = str(value or "").strip()
    if not cleaned or "\x00" in cleaned:
        return None
    candidate = Path(cleaned)
    workdir = layout.workdir_path.resolve()
    try:
        resolved = candidate.resolve() if candidate.is_absolute() else (workdir / candidate).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    try:
        workspace_path = resolved.relative_to(workdir).as_posix()
    except ValueError:
        return None
    try:
        if not resolved.exists():
            return None
    except OSError:
        return None
    return {
        "kind": "workspace",
        "label": f"{label_prefix}:{workspace_path}",
        "relative_path": workspace_path,
        "workspace_path": workspace_path,
        "absolute_path": str(resolved),
    }
