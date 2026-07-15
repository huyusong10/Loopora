from __future__ import annotations

from collections.abc import Mapping

from loopora.bundle_semantic_workflow import _alignment_workflow_role_keys
from loopora.bundle_semantic_workflow import (
    _lint_alignment_builder_guide_inputs,
    _lint_alignment_builder_review_inputs,
    _lint_alignment_guide_review_inputs,
    _lint_alignment_parallel_review_inputs,
    _lint_alignment_review_builder_inputs,
    _lint_alignment_workflow_intent,
)
from loopora.specs import compile_markdown_spec

import re


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



import yaml




from loopora.bundle_semantic_workflow import _parallel_review_role_text




from loopora.residual_risk_support import residual_risk_is_unmanaged



from loopora.bundle_semantic_workflow import (
    _alignment_workflow_role_archetype,
    _review_steps_since_latest_builder,
    _step_missing_evidence_query_archetypes,
)




def _lint_alignment_iteration_memory_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    issues.extend(_parallel_review_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    issues.extend(_guide_review_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    issues.extend(_builder_review_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    issues.extend(_builder_guide_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    return issues

def _parallel_review_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        role_id = str(step.get("role_id", "") or "")
        if not str(step.get("parallel_group", "") or "").strip():
            continue
        if workflow_role_archetype.get(role_id) not in {"inspector", "custom"}:
            continue
        if not _step_declares_iteration_memory(step):
            issues.append("parallel review step must declare inputs.iteration_memory so cross-iteration evidence flow is explicit: " + step_id)
        elif not _step_iteration_memory_includes_summary(step):
            issues.append("parallel review step must use inputs.iteration_memory=summary_only so previous GateKeeper verdict stays visible: " + step_id)
    return issues

def _guide_review_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
    issues: list[str] = []
    for index, step in enumerate(steps):
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) != "guide":
            continue
        review_steps = _review_steps_since_latest_builder(
            steps[:index],
            workflow_role_archetype=workflow_role_archetype,
            include_guides=False,
        )
        if review_steps and not _step_declares_iteration_memory(step):
            issues.append(
                "Guide step after review must declare inputs.iteration_memory so repair guidance can use prior iteration evidence explicitly: "
                + str(step.get("id", "") or "").strip()
            )
        elif review_steps and not _step_iteration_memory_includes_summary(step):
            issues.append(
                "Guide step after review must use inputs.iteration_memory=summary_only so previous GateKeeper blockers and residual risks stay visible: "
                + str(step.get("id", "") or "").strip()
            )
    return issues

def _builder_review_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
    review_steps_since_builder: list[str] = []
    guide_seen_since_builder = False
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        archetype = workflow_role_archetype.get(str(step.get("role_id", "") or ""))
        if archetype in {"inspector", "custom"}:
            review_steps_since_builder.append(step_id)
            continue
        if archetype == "guide":
            guide_seen_since_builder = True
            continue
        if archetype != "builder":
            continue
        if review_steps_since_builder and not guide_seen_since_builder and not _step_declares_iteration_memory(step):
            issues.append(
                "Builder step after review must declare inputs.iteration_memory so evidence-first repair does not rely on ambient context: " + step_id
            )
        elif review_steps_since_builder and not guide_seen_since_builder and not _step_iteration_memory_includes_summary(step):
            issues.append(
                "Builder step after review must use inputs.iteration_memory=summary_only so previous GateKeeper repair direction stays visible: "
                + step_id
            )
        review_steps_since_builder = []
        guide_seen_since_builder = False
    return issues

def _builder_guide_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
    guide_seen_since_builder = False
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        archetype = workflow_role_archetype.get(str(step.get("role_id", "") or ""))
        if archetype == "guide":
            guide_seen_since_builder = True
            continue
        if archetype != "builder":
            continue
        if guide_seen_since_builder and not _step_declares_iteration_memory(step):
            issues.append("Builder step after Guide must declare inputs.iteration_memory so repair pass does not rely on ambient context: " + step_id)
        elif guide_seen_since_builder and not _step_iteration_memory_includes_summary(step):
            issues.append("Builder step after Guide must use inputs.iteration_memory=summary_only so previous GateKeeper verdict stays visible: " + step_id)
        guide_seen_since_builder = False
    return issues

def _step_declares_iteration_memory(step: Mapping[str, Any]) -> bool:
    return bool(_step_iteration_memory(step))

def _step_iteration_memory_includes_summary(step: Mapping[str, Any]) -> bool:
    return _step_iteration_memory(step) == "summary_only"

def _step_iteration_memory(step: Mapping[str, Any]) -> str:
    inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
    return str(inputs.get("iteration_memory", "") if isinstance(inputs, Mapping) else "").strip()

def _lint_alignment_finishing_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    for step in workflow.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        step_id = str(step.get("id", "") or "").strip()
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []
        if not any(str(handoff or "").strip() for handoff in handoffs_from):
            issues.append("finishing GateKeeper step must name upstream handoffs in inputs.handoffs_from: " + step_id)
        if not (isinstance(inputs, Mapping) and inputs.get("evidence_query")):
            issues.append("finishing GateKeeper step must query upstream evidence in inputs.evidence_query: " + step_id)
    return issues

def _lint_alignment_review_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    for index, step in enumerate(steps):
        role_id = str(step.get("role_id", "") or "")
        if workflow_role_archetype.get(role_id) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        review_steps = _review_steps_since_latest_builder(
            steps[:index],
            workflow_role_archetype=workflow_role_archetype,
        )
        if not review_steps:
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        missing_handoffs = [step_id for step_id, _ in review_steps if step_id not in handoffs_from]
        if missing_handoffs:
            issues.append("finishing GateKeeper after review must include review handoffs in inputs.handoffs_from: " + ", ".join(missing_handoffs))
        missing_archetypes = _step_missing_evidence_query_archetypes(
            step,
            {archetype for _, archetype in review_steps},
        )
        if missing_archetypes:
            issues.append("finishing GateKeeper after review must query review evidence in inputs.evidence_query: " + ", ".join(missing_archetypes))
    return issues

def _lint_alignment_long_chain_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    for index, step in enumerate(steps):
        role_id = str(step.get("role_id", "") or "")
        if workflow_role_archetype.get(role_id) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        prior_steps = steps[:index]
        prior_builder_steps = [
            str(prior_step.get("id", "") or "").strip()
            for prior_step in prior_steps
            if workflow_role_archetype.get(str(prior_step.get("role_id", "") or "")) == "builder"
        ]
        if len(prior_builder_steps) < 2:
            continue
        prior_governance_handoffs = {
            str(prior_step.get("id", "") or "").strip()
            for prior_step in prior_steps
            if workflow_role_archetype.get(str(prior_step.get("role_id", "") or "")) in {"inspector", "custom", "guide"}
        }
        prior_governance_handoffs.update(prior_builder_steps[:-1])
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        if not handoffs_from.intersection(prior_governance_handoffs):
            issues.append(
                "long-chain GateKeeper must include an earlier phase, review, or Guide handoff in inputs.handoffs_from: "
                + str(step.get("id", "") or "").strip()
            )
    return issues

def _lint_alignment_parallel_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    parallel_review_steps = [
        (
            str(step.get("id", "") or "").strip(),
            workflow_role_archetype.get(str(step.get("role_id", "") or "")),
        )
        for step in steps
        if str(step.get("parallel_group", "") or "").strip() and workflow_role_archetype.get(str(step.get("role_id", "") or "")) in {"inspector", "custom"}
    ]
    parallel_review_step_ids = [
        str(step.get("id", "") or "").strip()
        for step in steps
        if str(step.get("parallel_group", "") or "").strip() and workflow_role_archetype.get(str(step.get("role_id", "") or "")) in {"inspector", "custom"}
    ]
    if not parallel_review_step_ids:
        return []
    issues: list[str] = []
    for step in steps:
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        missing = [step_id for step_id in parallel_review_step_ids if step_id not in handoffs_from]
        if missing:
            issues.append("GateKeeper step must include every parallel review handoff in inputs.handoffs_from: " + ", ".join(missing))
        expected_archetypes = {"builder", *(archetype for _, archetype in parallel_review_steps if archetype)}
        missing_archetypes = _step_missing_evidence_query_archetypes(step, expected_archetypes)
        if missing_archetypes:
            issues.append("GateKeeper step must query Builder and parallel review evidence in inputs.evidence_query: " + ", ".join(missing_archetypes))
    return issues

def _lint_alignment_gatekeeper_semantics(
    normalized: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
    used_role_keys: list[object],
) -> list[str]:
    if str(normalized["loop"].get("completion_mode", "") or "").strip().lower() != "gatekeeper":
        return []
    issues: list[str] = []
    archetypes = {role_by_key[str(role_key)]["archetype"] for role_key in used_role_keys if str(role_key) in role_by_key}
    if "gatekeeper" not in archetypes:
        issues.append("gatekeeper completion mode requires a GateKeeper role")
    return issues

def _lint_alignment_spec_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not _semantic_text_is_specific(compiled_spec.get("goal"), min_chars=72):
        issues.append("spec Task must describe the concrete user-facing task")
    issues.extend(_lint_alignment_spec_contract_sections(compiled_spec))
    return issues

def _lint_alignment_spec_contract_sections(compiled_spec: Mapping[str, Any]) -> list[str]:
    return [
        *_lint_alignment_done_when_semantics(compiled_spec),
        *_lint_alignment_success_and_fake_done_semantics(compiled_spec),
        *_lint_alignment_evidence_and_risk_semantics(compiled_spec),
    ]

def _lint_alignment_done_when_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not compiled_spec.get("checks"):
        issues.append("spec must include at least one Done When bullet")
    return issues

def _lint_alignment_success_and_fake_done_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not compiled_spec.get("success_surface"):
        issues.append("spec must include at least one Success Surface bullet")
    if not compiled_spec.get("fake_done_states"):
        issues.append("spec must include at least one Fake Done bullet")
    return issues

def _lint_alignment_evidence_and_risk_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not compiled_spec.get("evidence_preferences"):
        issues.append("spec must include at least one Evidence Preferences bullet")
    residual_risk = str(compiled_spec.get("residual_risk", "") or "").strip()
    if not residual_risk:
        issues.append("spec must include Residual Risk guidance")
    elif residual_risk_is_unmanaged(residual_risk):
        issues.append("spec Residual Risk guidance must name accepted risk handling or fail closed")
    return issues

def _lint_alignment_role_semantics(
    role_by_key: Mapping[str, Mapping[str, Any]],
    *,
    used_role_keys: list[object],
) -> list[str]:
    issues: list[str] = []
    for role_key in used_role_keys:
        role = role_by_key.get(str(role_key))
        if role is None:
            continue
        if _alignment_role_name_is_generic(role):
            issues.append(f"role_definition {role['key']} must use a task-specific role name")
        if not str(role.get("posture_notes", "") or "").strip():
            issues.append(f"role_definition {role['key']} must include task-scoped posture_notes")
    return issues

def _lint_alignment_duplicate_role_responsibilities(
    role_by_key: Mapping[str, Mapping[str, Any]],
    *,
    used_role_keys: list[object],
) -> list[str]:
    responsibilities: dict[tuple[str, str], list[str]] = {}
    for raw_key in dict.fromkeys(str(key) for key in used_role_keys):
        role = role_by_key.get(raw_key)
        if not role:
            continue
        archetype = str(role.get("archetype") or "").strip()
        role_text = _parallel_review_role_text(role)
        if not archetype or not role_text:
            continue
        responsibilities.setdefault((archetype, role_text), []).append(raw_key)
    return [
        "role_definitions must have distinct task evidence responsibilities: " + ", ".join(role_keys)
        for role_keys in responsibilities.values()
        if len(role_keys) > 1
    ]

def _alignment_role_name_is_generic(role: Mapping[str, Any]) -> bool:
    name = re.sub(r"\s+", " ", str(role.get("name", "") or "")).strip().lower()
    if name in {
        "builder",
        "generator",
        "inspector",
        "tester",
        "gatekeeper",
        "gate keeper",
        "verifier",
        "guide",
        "challenger",
        "custom",
    }:
        return True
    return bool(
        re.fullmatch(
            r"(?:builder|generator|inspector|tester|gatekeeper|gate keeper|verifier|guide|challenger|agent|role)[\s#_-]*\d+",
            name,
        )
    )

def lint_alignment_bundle_generation_text(raw_text: str) -> list[str]:
    """Return raw-text issues for Web compiler generated bundle candidates."""

    issues: list[str] = []
    stripped = str(raw_text or "").strip()
    if not stripped:
        return issues
    non_empty_lines = [line.strip() for line in str(raw_text or "").splitlines() if line.strip()]
    if non_empty_lines and re.match(r"^```(?:yaml|yml)?\s*$", non_empty_lines[0], re.IGNORECASE):
        issues.append("Web alignment generated bundle_yaml must be one raw YAML document, not markdown-fenced output")
    if non_empty_lines and not re.match(r"^version\s*:\s*1(?:\s*(?:#.*)?)?$", non_empty_lines[0]):
        issues.append("Web alignment generated bundle_yaml must start with version: 1")
    issues.extend(lint_alignment_bundle_generation_metadata(raw_text))
    return issues

def lint_alignment_bundle_generation_metadata(raw_text: str) -> list[str]:
    """Return raw-YAML metadata issues for Web compiler generated bundle candidates."""

    try:
        payload = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(payload, Mapping):
        return []
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return []
    metadata_keys = {str(key).strip() for key in metadata}
    if "source_bundle_id" not in metadata_keys and "revision" not in metadata_keys:
        return []
    return [
        "Web alignment generated bundles must omit metadata.source_bundle_id and metadata.revision; "
        "source context is temporary and final bundles are standalone candidates"
    ]

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
    if not re.search(r"gatekeeper|gate keeper|裁决|阻断|签字|收束", str(summary or ""), re.IGNORECASE):
        return ["collaboration_summary must explain GateKeeper or final judgment posture"]
    return []


def lint_alignment_bundle_semantics(bundle: Mapping[str, object]) -> list[str]:
    """Return high-signal semantic issues for Web-generated alignment bundles."""

    from loopora.bundle_normalization import normalize_bundle

    normalized = normalize_bundle(bundle)
    issues: list[str] = []
    issues.extend(_lint_alignment_standalone_metadata(normalized))
    issues.extend(_lint_alignment_collaboration_summary(normalized.get("collaboration_summary")))
    issues.extend(_lint_alignment_task_scoped_antipatterns(normalized))
    issues.extend(_lint_alignment_loop_fit_contradictions(normalized))
    issues.extend(_lint_alignment_completion_mode(normalized))
    issues.extend(_lint_alignment_evidence_bucket_projection(normalized))
    compiled_spec = compile_markdown_spec(str(normalized["spec"]["markdown"]))
    issues.extend(_lint_alignment_spec_semantics(compiled_spec))
    issues.extend(_lint_alignment_workflow_intent(normalized["workflow"]))
    role_by_key = {item["key"]: item for item in normalized["role_definitions"]}
    used_role_keys = _alignment_workflow_role_keys(normalized["workflow"])
    issues.extend(_lint_alignment_review_builder_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_parallel_review_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_builder_review_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_guide_review_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_builder_guide_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_finishing_gatekeeper_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_long_chain_gatekeeper_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_review_gatekeeper_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_parallel_gatekeeper_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_iteration_memory_inputs(normalized["workflow"], role_by_key=role_by_key))
    issues.extend(_lint_alignment_duplicate_role_responsibilities(role_by_key, used_role_keys=used_role_keys))
    issues.extend(_lint_alignment_role_semantics(role_by_key, used_role_keys=used_role_keys))
    issues.extend(_lint_alignment_gatekeeper_semantics(normalized, role_by_key=role_by_key, used_role_keys=used_role_keys))
    if len(used_role_keys) < 2:
        issues.append("alignment bundle workflow should use at least two roles")
    return issues
