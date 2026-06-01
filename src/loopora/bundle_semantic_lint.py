from __future__ import annotations

from collections.abc import Mapping

from loopora.bundle_semantic_bundle import (
    _lint_alignment_collaboration_summary,
    _lint_alignment_completion_mode,
    _lint_alignment_evidence_bucket_projection,
    _lint_alignment_loop_fit_contradictions,
    _lint_alignment_standalone_metadata,
    _lint_alignment_task_scoped_antipatterns,
)
from loopora.bundle_semantic_generation import (
    lint_alignment_bundle_generation_metadata as lint_alignment_bundle_generation_metadata,
    lint_alignment_bundle_generation_text as lint_alignment_bundle_generation_text,
)
from loopora.bundle_semantic_roles import (
    _lint_alignment_duplicate_role_responsibilities,
    _lint_alignment_role_semantics,
)
from loopora.bundle_semantic_spec import _lint_alignment_spec_semantics
from loopora.bundle_semantic_workflow_gatekeeper import (
    _lint_alignment_finishing_gatekeeper_inputs,
    _lint_alignment_gatekeeper_semantics,
    _lint_alignment_long_chain_gatekeeper_inputs,
    _lint_alignment_parallel_gatekeeper_inputs,
    _lint_alignment_review_gatekeeper_inputs,
)
from loopora.bundle_semantic_workflow_memory import _lint_alignment_iteration_memory_inputs
from loopora.bundle_semantic_workflow_support import _alignment_workflow_role_keys
from loopora.bundle_semantic_workflow import (
    _lint_alignment_builder_guide_inputs,
    _lint_alignment_builder_review_inputs,
    _lint_alignment_guide_review_inputs,
    _lint_alignment_parallel_review_inputs,
    _lint_alignment_review_builder_inputs,
    _lint_alignment_workflow_intent,
)
from loopora.specs import compile_markdown_spec


def lint_alignment_bundle_semantics(bundle: Mapping[str, object]) -> list[str]:
    """Return high-signal semantic issues for Web-generated alignment bundles."""

    from loopora.bundles import normalize_bundle

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
