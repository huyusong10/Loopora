from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    alignment_bundle_yaml,
    yaml,
)


def test_agent_bundle_candidate_rejects_explicit_execution_strategy_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing refund path in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Ship the billing refund path. Execution strategy: first repair the root cause before "
                "expanding dashboards or polishing UI."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "execution strategy" in generated["session"]["error_message"]
    assert "repair/root-cause" in generated["session"]["error_message"]


def test_agent_bundle_candidate_rejects_labeled_single_execution_strategy_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing refund path in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the billing refund path. Execution strategy: first repair the root cause.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "execution strategy" in generated["session"]["error_message"]
    assert "repair/root-cause" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_explicit_execution_strategy_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing refund path in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nExecution Strategy: first repair the root cause, then consider dashboard expansion or UI polish."
    )
    bundle["workflow"]["collaboration_intent"] += (
        " Builder should repair the root cause before any dashboard expansion or UI polish."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Ship the billing refund path. Execution strategy: first repair the root cause before "
                "expanding dashboards or polishing UI."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
