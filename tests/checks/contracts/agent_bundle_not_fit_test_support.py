from agent_bundle_candidates_test_support import AgentBundleCandidateRequest, Path, alignment_bundle_yaml


def create_not_fit_agent_bundle_candidate(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    *,
    message: str,
    prepare_project_evidence: bool = False,
) -> tuple[object, dict]:
    service = service_factory(scenario="success")
    if prepare_project_evidence:
        (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
        (sample_workdir / "design").mkdir(exist_ok=True)
        (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
        (sample_workdir / "tests").mkdir(exist_ok=True)

    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=message,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    return service, generated


def assert_loopora_not_fit_failure(
    generated: dict,
    *,
    requires_candidate_repair: bool | None = None,
    loopora_fit_contradiction: bool = False,
) -> None:
    assert generated["ready"] is False
    assert generated["status"] == "failed"
    if requires_candidate_repair is not None:
        assert generated["requires_candidate_repair"] is requires_candidate_repair
    if loopora_fit_contradiction:
        assert generated["loopora_fit_contradiction"] is True
        assert generated["binding"]["loopora_fit_contradiction"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]


__all__ = [
    "assert_loopora_not_fit_failure",
    "create_not_fit_agent_bundle_candidate",
]
