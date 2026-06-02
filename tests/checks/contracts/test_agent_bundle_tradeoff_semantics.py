from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    alignment_bundle_yaml,
    yaml,
)


def test_agent_bundle_candidate_rejects_explicit_tradeoff_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] = bundle["collaboration_summary"].replace(
        "Prefer a smaller proven flow over polished but unproven breadth, and let GateKeeper reject speed or surface completeness when evidence is weak. ",
        "",
    )
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace("Accept minor polish gaps", "Accept minor follow-up gaps")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Prioritize proof over speed: block polished-looking fake completion until evidence proves "
                "the primary flow."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "judgment tradeoffs" in generated["session"]["error_message"]
    assert "speed/polish" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_explicit_tradeoff_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] += (
        "\n\nTradeoff: prioritize proof over speed; UI polish must wait until primary-flow evidence is Proven."
    )
    bundle["workflow"]["collaboration_intent"] += (
        " GateKeeper should block polished-looking fake completion when proof is weak."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Reject speed-first or polish-first closure unless direct evidence proves the primary flow."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Prioritize proof over speed: block polished-looking fake completion until evidence proves "
                "the primary flow."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"


def test_agent_bundle_candidate_rejects_pragmatic_progress_tradeoff_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prefer strict blocking over pragmatic progress when evidence is weak.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "judgment tradeoffs" in generated["session"]["error_message"]
    assert "pragmatic/progress" in generated["session"]["error_message"]


def test_agent_bundle_candidate_accepts_pragmatic_progress_tradeoff_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] += "\n\nTradeoff: strict blocking beats pragmatic progress when evidence is weak."
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prefer strict blocking over pragmatic progress when evidence is weak.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
