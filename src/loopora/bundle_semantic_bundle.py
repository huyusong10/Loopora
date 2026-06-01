from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from loopora.alignment_semantics import (
    text_mentions_loop_fit_contradiction,
    text_mentions_multiround_loopora_governance,
)
from loopora.bundle_semantic_text import (
    _semantic_text_is_specific,
    _semantic_text_mentions_evidence,
    _semantic_text_mentions_evidence_bucket_projection,
    _semantic_text_mentions_named_loopora_antipattern,
    _semantic_text_mentions_personality_memory_antipattern,
)


def _lint_alignment_standalone_metadata(normalized: Mapping[str, Any]) -> list[str]:
    metadata = normalized.get("metadata") if isinstance(normalized.get("metadata"), Mapping) else {}
    if not str(metadata.get("source_bundle_id", "") or "").strip():
        return []
    return ["Web alignment bundles must not encode metadata.source_bundle_id; source context is temporary and final bundles are standalone candidates"]


def _lint_alignment_evidence_bucket_projection(normalized: Mapping[str, Any]) -> list[str]:
    if _semantic_text_mentions_evidence_bucket_projection(_alignment_bundle_runtime_governance_text(normalized)):
        return []
    return ["alignment bundle must project task verdict evidence into Proven, Weak, Unproven, Blocking, and Residual risk buckets"]


def _lint_alignment_completion_mode(normalized: Mapping[str, Any]) -> list[str]:
    completion_mode = str(normalized["loop"].get("completion_mode", "") or "").strip().lower()
    if completion_mode == "gatekeeper":
        return []
    return ["Web alignment bundles must use gatekeeper completion_mode so task verdict is evidence-based, not only run lifecycle completion"]


def _lint_alignment_task_scoped_antipatterns(normalized: Mapping[str, Any]) -> list[str]:
    text = _alignment_bundle_governance_text(normalized)
    issues: list[str] = []
    if _semantic_text_mentions_named_loopora_antipattern(text):
        issues.append("alignment bundle must not present prompt pack, role zoo, loop script, benchmark grinder, or chat wrapper as Loopora governance")
    if _semantic_text_mentions_personality_memory_antipattern(text):
        issues.append("alignment bundle must stay task-scoped, not personality memory or global preferences")
    return issues


def _lint_alignment_loop_fit_contradictions(normalized: Mapping[str, Any]) -> list[str]:
    if not text_mentions_loop_fit_contradiction(_alignment_bundle_governance_text(normalized)):
        return []
    return [
        "alignment bundle must not claim a single pass, direct chat / direct answer, one-off task handling, "
        "no-new-evidence round, or benchmark/test-harness-only path is sufficient while compiling a Loop"
    ]


def _alignment_bundle_governance_text(normalized: Mapping[str, Any]) -> str:
    metadata = normalized.get("metadata") if isinstance(normalized.get("metadata"), Mapping) else {}
    loop = normalized.get("loop") if isinstance(normalized.get("loop"), Mapping) else {}
    workflow = normalized.get("workflow") if isinstance(normalized.get("workflow"), Mapping) else {}
    spec = normalized.get("spec") if isinstance(normalized.get("spec"), Mapping) else {}
    parts = [
        str(metadata.get("name", "") or "") if isinstance(metadata, Mapping) else "",
        str(metadata.get("description", "") or "") if isinstance(metadata, Mapping) else "",
        str(normalized.get("collaboration_summary", "") or ""),
        str(loop.get("name", "") or "") if isinstance(loop, Mapping) else "",
        str(spec.get("markdown", "") or "") if isinstance(spec, Mapping) else "",
        str(workflow.get("collaboration_intent", "") or "") if isinstance(workflow, Mapping) else "",
    ]
    for role in normalized.get("role_definitions", []):
        if not isinstance(role, Mapping):
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


def _alignment_bundle_runtime_governance_text(normalized: Mapping[str, Any]) -> str:
    workflow = normalized.get("workflow") if isinstance(normalized.get("workflow"), Mapping) else {}
    spec = normalized.get("spec") if isinstance(normalized.get("spec"), Mapping) else {}
    parts = [
        str(normalized.get("collaboration_summary", "") or ""),
        str(spec.get("markdown", "") or "") if isinstance(spec, Mapping) else "",
        str(workflow.get("collaboration_intent", "") or "") if isinstance(workflow, Mapping) else "",
    ]
    for role in normalized.get("role_definitions", []):
        if not isinstance(role, Mapping):
            continue
        parts.extend(
            [
                str(role.get("description", "") or ""),
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
            ]
        )
    return "\n".join(parts)


def _lint_alignment_collaboration_summary(summary: object) -> list[str]:
    if not _semantic_text_is_specific(summary, min_chars=72):
        return ["collaboration_summary must explain the governance story"]
    if not text_mentions_multiround_loopora_governance(summary):
        return ["collaboration_summary must explain why this task needs multi-round Loopora governance"]
    if not _semantic_text_mentions_evidence(summary):
        return ["collaboration_summary must mention evidence, proof, verification, handoff, or blockers"]
    if not re.search(r"gatekeeper|gate keeper|裁决|阻断|签字|收束", str(summary or ""), re.I):
        return ["collaboration_summary must explain GateKeeper or final judgment posture"]
    return []
