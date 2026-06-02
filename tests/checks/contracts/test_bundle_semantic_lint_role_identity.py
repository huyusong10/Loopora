from __future__ import annotations

from pathlib import Path

from loopora.bundles import lint_alignment_bundle_semantics
from bundle_semantic_lint_workflow_support import load_default_alignment_bundle


def test_alignment_semantic_lint_rejects_generic_role_names(sample_workdir: Path) -> None:
    bundle = load_default_alignment_bundle(sample_workdir)
    assert not any("task-specific role name" in issue for issue in lint_alignment_bundle_semantics(bundle))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["name"] = "Inspector 1"
    role_by_key["evidence-inspector"]["name"] = "Inspector 2"
    issues = lint_alignment_bundle_semantics(bundle)

    assert "role_definition contract-inspector must use a task-specific role name" in issues
    assert "role_definition evidence-inspector must use a task-specific role name" in issues
