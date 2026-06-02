from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    alignment_bundle_yaml,
    yaml,
)

GOVERNANCE_MARKERS = "AGENTS.md, design/README.md, design/, and tests/"
GOVERNANCE_ERROR_FRAGMENT = "project-local governance markers"
GOVERNANCE_MESSAGE = f"Build the focused starter experience while following {GOVERNANCE_MARKERS} as runtime governance inputs."
STARTER_MESSAGE = (
    "Build the focused starter experience in the target workdir with small, maintainable changes "
    "that preserve the primary user flow."
)


def test_agent_bundle_candidate_rejects_governance_markers_without_runtime_responsibilities(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += f" {GOVERNANCE_MARKERS} are project-local governance markers."
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=GOVERNANCE_MESSAGE,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert GOVERNANCE_ERROR_FRAGMENT in generated["session"]["error_message"]
    assert "Builder reading" in generated["session"]["error_message"]


def test_agent_bundle_candidate_uses_workdir_snapshot_for_governance_markers(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir(exist_ok=True)

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=STARTER_MESSAGE,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert GOVERNANCE_ERROR_FRAGMENT in generated["session"]["error_message"]


def test_agent_bundle_candidate_uses_parent_agents_file_as_governance_marker(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    project = tmp_path / "project"
    workdir = project / "packages" / "app"
    workdir.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=workdir,
            message=STARTER_MESSAGE,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert GOVERNANCE_ERROR_FRAGMENT in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_governance_markers_as_role_responsibilities(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        f"\n\nRead {GOVERNANCE_MARKERS} before changing code, "
        "and follow those project-local governance contracts in the Builder handoff."
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        f"\n\nInspector must verify {GOVERNANCE_MARKERS} were followed, "
        "and must mark skipped local governance as weak or missing evidence."
    )
    role_by_key["gatekeeper"]["prompt_markdown"] += (
        f"\n\nGateKeeper treats skipped {GOVERNANCE_MARKERS} responsibilities "
        "as Weak, Unproven, or Blocking before accepting the run."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=GOVERNANCE_MESSAGE,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
