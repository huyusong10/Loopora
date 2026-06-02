from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_bundle_control_summary import build_bundle_control_summary


SUMMARY_ONLY_LOCAL_GOVERNANCE = (
    "\nBuilder reads AGENTS.md and design/README.md before editing. "
    "Inspector verifies AGENTS.md and tests/ obligations against the result. "
    "GateKeeper treats skipped AGENTS.md or tests/ evidence as Weak, Unproven, or Blocking."
)


def test_bundle_control_summary_projects_local_governance_responsibilities(sample_workdir: Path) -> None:
    bundle = _add_project_local_governance_responsibilities(_alignment_bundle(sample_workdir))

    summary = build_bundle_control_summary(bundle)
    local_item = _traceability_item(summary, "local_governance")

    _assert_local_governance_chain(summary["local_governance"])
    assert "collaboration_summary" not in local_item["surfaces"]
    assert "spec.markdown#Role Notes" in local_item["surfaces"]
    assert local_item["mapped"] is True
    assert "local_governance" not in summary["traceability"]["missing"]


def test_bundle_control_summary_keeps_local_governance_chain_when_builder_repeats(sample_workdir: Path) -> None:
    bundle = _add_project_local_governance_responsibilities(_alignment_bundle(sample_workdir))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    for index in range(6):
        role_by_key["builder"]["prompt_markdown"] += (
            f"\n\nBuilder reads AGENTS.md and design/README.md before editing phase {index}."
        )

    summary = build_bundle_control_summary(bundle)
    local_item = _traceability_item(summary, "local_governance")

    _assert_local_governance_chain(local_item["evidence"])
    assert local_item["mapped"] is True


def test_bundle_control_summary_does_not_map_marker_lists_as_local_governance(sample_workdir: Path) -> None:
    bundle = _alignment_bundle(sample_workdir)
    bundle["collaboration_summary"] += " AGENTS.md, design/README.md, design/, and tests/ are visible markers."

    _assert_missing_local_governance(bundle)


def test_bundle_control_summary_requires_complete_local_governance_chain(sample_workdir: Path) -> None:
    bundle = _alignment_bundle(sample_workdir)
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n\nBuilder reads AGENTS.md and design/README.md before changing code."
    )

    _assert_missing_local_governance(bundle)


def test_bundle_control_summary_does_not_map_summary_only_local_governance_chain(sample_workdir: Path) -> None:
    bundle = _add_summary_only_local_governance(_alignment_bundle(sample_workdir))

    _assert_missing_local_governance(bundle)


def test_bundle_governance_summary_projects_local_governance(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    bundle = _add_project_local_governance_responsibilities(_alignment_bundle(sample_workdir))

    governance = service._bundle_governance_summary(bundle)

    assert any("Read AGENTS.md" in item for item in governance["local_governance"])


def test_bundle_governance_summary_omits_summary_only_local_governance(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    bundle = _add_summary_only_local_governance(_alignment_bundle(sample_workdir))

    governance = service._bundle_governance_summary(bundle)

    assert governance["local_governance"] == []


def test_bundle_governance_summary_omits_unmanaged_residual_risk(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    bundle = _alignment_bundle(sample_workdir)
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )

    governance = service._bundle_governance_summary(bundle)

    assert governance["residual_risk_policy"] == []


def _alignment_bundle(sample_workdir: Path) -> dict:
    return load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))


def _add_project_local_governance_responsibilities(bundle: dict) -> dict:
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n\nRead AGENTS.md, design/README.md, design/, and tests/ before changing code, "
        "and follow those project-local governance contracts in the Builder handoff."
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\n\nInspector must verify AGENTS.md, design/README.md, design/, and tests/ were followed, "
        "and must mark skipped local governance as weak or missing evidence."
    )
    role_by_key["gatekeeper"]["prompt_markdown"] += (
        "\n\nGateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ responsibilities "
        "as Weak, Unproven, or Blocking before accepting the run."
    )
    return bundle


def _add_summary_only_local_governance(bundle: dict) -> dict:
    bundle["collaboration_summary"] += SUMMARY_ONLY_LOCAL_GOVERNANCE
    return bundle


def _assert_local_governance_chain(items: list[str]) -> None:
    assert any("Read AGENTS.md" in item or "Builder reads AGENTS.md" in item for item in items)
    for term in ("Inspector must verify AGENTS.md", "GateKeeper treats skipped AGENTS.md"):
        assert any(term in item for item in items)


def _assert_missing_local_governance(bundle: dict) -> None:
    summary = build_bundle_control_summary(bundle)
    local_item = _traceability_item(summary, "local_governance")

    assert summary["local_governance"] == []
    assert local_item["mapped"] is False
    assert "local_governance" in summary["traceability"]["missing"]


def _traceability_item(summary: dict, key: str) -> dict:
    return next(item for item in summary["traceability"]["items"] if item["key"] == key)
