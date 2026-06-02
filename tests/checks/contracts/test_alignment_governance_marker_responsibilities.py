from __future__ import annotations

from pathlib import Path

from alignment_local_governance_traceability_support import (
    alignment_bundle,
    governance_session,
    has_governance_marker_issue,
)
from loopora.alignment_traceability_rules import alignment_bundle_agreement_traceability_issues


def test_alignment_traceability_rejects_disconnected_governance_marker_responsibilities(
    sample_workdir: Path,
) -> None:
    bundle = alignment_bundle(sample_workdir)
    bundle["spec"]["markdown"] += (
        "\nWorkdir Snapshot detected AGENTS.md, design/README.md, design/, and tests/.\n"
        + ("Neutral context keeps the marker list separate from generic role responsibilities. " * 10)
    )
    bundle["collaboration_summary"] += (
        "\nBuilder reads task notes. Inspector checks the result. GateKeeper blocks weak proof."
    )
    session = governance_session()

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert has_governance_marker_issue(issues)


def test_alignment_traceability_accepts_marker_specific_role_responsibilities(
    sample_workdir: Path,
) -> None:
    bundle = alignment_bundle(sample_workdir)
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n\nBuilder reads AGENTS.md, design/README.md, design/, and tests/ before editing."
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\n\nInspector verifies AGENTS.md, design/README.md, design/, and tests/ obligations against the result."
    )
    role_by_key["gatekeeper"]["prompt_markdown"] += (
        "\n\nGateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ evidence as Weak, Unproven, or Blocking."
    )
    session = governance_session()

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert not has_governance_marker_issue(issues)


def test_alignment_traceability_accepts_role_notes_governance_responsibilities(
    sample_workdir: Path,
) -> None:
    bundle = alignment_bundle(sample_workdir)
    spec_without_role_notes = bundle["spec"]["markdown"].split("\n# Role Notes\n", 1)[0]
    bundle["spec"]["markdown"] = (
        spec_without_role_notes
        + "\n\n# Role Notes\n\n"
        + "## Builder Notes\n\nBuilder reads AGENTS.md, design/README.md, design/, and tests/ before editing.\n\n"
        + "## Inspector Notes\n\nInspector verifies AGENTS.md, design/README.md, design/, and tests/ obligations against the result.\n\n"
        + "## GateKeeper Notes\n\nGateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ evidence as Weak, Unproven, or Blocking.\n"
    )
    session = governance_session()

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert not has_governance_marker_issue(issues)


def test_alignment_traceability_rejects_summary_only_governance_responsibilities(
    sample_workdir: Path,
) -> None:
    bundle = alignment_bundle(sample_workdir)
    bundle["collaboration_summary"] += (
        "\nBuilder reads AGENTS.md, design/README.md, design/, and tests/ before editing. "
        "Inspector verifies AGENTS.md, design/README.md, design/, and tests/ obligations against the result. "
        "GateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ evidence as Weak, Unproven, or Blocking."
    )
    session = governance_session()

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert has_governance_marker_issue(issues)
