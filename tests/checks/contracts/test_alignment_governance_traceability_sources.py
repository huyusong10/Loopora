from __future__ import annotations

from pathlib import Path

from alignment_local_governance_traceability_support import (
    alignment_bundle,
    governance_session,
    has_governance_marker_issue,
)
from loopora.alignment_traceability_rules import alignment_bundle_agreement_traceability_issues
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.bundles import load_bundle_text


def test_alignment_traceability_uses_workdir_snapshot_for_local_governance(
    sample_workdir: Path,
) -> None:
    bundle = alignment_bundle(sample_workdir)
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir()
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir()
    session = governance_session(
        (
            "If project-local governance markers are present, Builder reads applicable rules, "
            "Inspector verifies related obligations, and GateKeeper blocks skipped governance."
        ),
        workdir=sample_workdir,
        key="local_governance",
    )

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert has_governance_marker_issue(issues)


def test_alignment_traceability_uses_parent_agents_snapshot_for_local_governance(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    workdir = project / "packages" / "app"
    workdir.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    bundle = alignment_bundle(workdir)
    session = governance_session(
        "No direct AGENTS.md file is visible in the selected workdir.",
        workdir=workdir,
        key="local_governance",
    )

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert has_governance_marker_issue(issues)


def test_alignment_traceability_checks_governance_markers_across_readiness_evidence(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(
        alignment_bundle_yaml(str(sample_workdir)).replace(
            "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
            "Workdir Snapshot detected AGENTS.md and tests/. Ship the focused starter experience.",
        )
    )
    session = governance_session(
        "AGENTS.md and tests/ are project-local governance markers that must shape runtime evidence.",
        key="evidence_preferences",
    )

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert has_governance_marker_issue(issues)
