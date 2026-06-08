from __future__ import annotations

import json
import re

from loopora.alignment_readiness_governance import alignment_governance_marker_responsibilities_present
from loopora.specs import SpecError, compile_markdown_spec


def alignment_bundle_visible_text(bundle: dict) -> str:
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    parts = [
        str(metadata.get("name", "") or ""),
        str(metadata.get("description", "") or ""),
        str(bundle.get("collaboration_summary", "") or ""),
        str(loop.get("name", "") or ""),
        str(spec.get("markdown", "") or ""),
        str(workflow.get("collaboration_intent", "") or ""),
    ]
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        parts.extend(
            [
                str(role.get("name", "") or ""),
                str(role.get("description", "") or ""),
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
            ]
        )
    return "\n".join(parts)


def alignment_session_user_task_text(session: dict) -> str:
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    user_messages = [
        str(entry.get("content") or "").strip()
        for entry in transcript
        if isinstance(entry, dict) and entry.get("role") == "user" and str(entry.get("content") or "").strip()
    ]
    return "\n".join(user_messages[:4])


def normalize_alignment_traceability_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def alignment_traceability_term_is_present(term: str, *, normalized_bundle_text: str) -> bool:
    value = str(term or "").strip().lower()
    if not value:
        return False
    if "/" in value or "." in value:
        return value in normalized_bundle_text
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(value)}(?![a-z0-9])", normalized_bundle_text))


def alignment_governance_marker_responsibility_issues(evidence: dict, *, normalized_runtime_text: str) -> list[str]:
    agreement_evidence_text = normalize_alignment_traceability_text(" ".join(str(value or "") for value in evidence.values()))
    governance_markers = ("agents.md", "design/readme.md", "design/", "tests/")
    if not any(marker in agreement_evidence_text for marker in governance_markers):
        return []
    if alignment_governance_marker_responsibilities_present(normalized_runtime_text):
        return []
    return [
        "alignment bundle must convert project-local governance markers into Builder reading, "
        "Inspector or Custom verification, and GateKeeper gating responsibilities"
    ]


def alignment_bundle_agreement_projection_text(bundle: dict) -> str:
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    parts = [
        str(bundle.get("collaboration_summary", "") or ""),
        str(spec.get("markdown", "") or ""),
        str(workflow.get("collaboration_intent", "") or ""),
    ]
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        parts.extend(
            [
                str(role.get("description", "") or ""),
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
            ]
        )
    if isinstance(workflow, dict):
        parts.append(json.dumps(_alignment_workflow_traceability_projection(workflow), ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def alignment_bundle_runnable_projection_text(bundle: dict) -> str:
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    parts = [
        str(spec.get("markdown", "") or ""),
        str(workflow.get("collaboration_intent", "") or ""),
    ]
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        parts.extend(
            [
                str(role.get("description", "") or ""),
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
            ]
        )
    if isinstance(workflow, dict):
        parts.append(json.dumps(_alignment_workflow_traceability_projection(workflow), ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def alignment_bundle_runtime_responsibility_projection_text(bundle: dict) -> str:
    spec_role_notes = alignment_bundle_spec_role_notes_projection_text(bundle)
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    parts: list[str] = [spec_role_notes]
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        parts.extend(
            [
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
                str(role.get("description", "") or ""),
            ]
        )
    if isinstance(workflow, dict):
        parts.append(str(workflow.get("collaboration_intent", "") or ""))
        parts.append(json.dumps(_alignment_workflow_traceability_projection(workflow), ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def alignment_bundle_spec_role_notes_projection_text(bundle: dict) -> str:
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    markdown = str(spec.get("markdown", "") or "")
    if not markdown.strip():
        return ""
    try:
        compiled_spec = compile_markdown_spec(markdown)
    except SpecError:
        return ""
    raw_sections = compiled_spec.get("raw_sections") if isinstance(compiled_spec, dict) else {}
    return str(raw_sections.get("Role Notes") or "") if isinstance(raw_sections, dict) else ""


def _alignment_workflow_traceability_projection(workflow: dict) -> dict:
    return {
        "steps": [
            {
                "inputs": step.get("inputs") if isinstance(step.get("inputs"), dict) else {},
                "action_policy": step.get("action_policy") if isinstance(step.get("action_policy"), dict) else {},
                "control": step.get("control") if isinstance(step.get("control"), dict) else {},
            }
            for step in list(workflow.get("steps") or [])
            if isinstance(step, dict)
        ],
        "controls": list(workflow.get("controls") or []) if isinstance(workflow.get("controls"), list) else [],
    }
