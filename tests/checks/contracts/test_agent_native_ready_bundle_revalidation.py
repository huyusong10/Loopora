from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    LooporaError,
    Path,
    _ready_candidate_digest,
    alignment_bundle_yaml,
    pytest,
    yaml,
)


def test_agent_loop_revalidates_ready_bundle_file_before_start(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship a ready bundle, but fail closed if the artifact changes after validation.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    ready_path = Path(generated["session"]["bundle_path"])
    ready_bundle = yaml.safe_load(ready_path.read_text(encoding="utf-8"))
    ready_bundle["spec"]["markdown"] = ready_bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps or residual risks only when they are explicitly named, visible, tracked, and owned as a follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )
    assert "Some risk is fine." in ready_bundle["spec"]["markdown"]
    ready_path.write_text(yaml.safe_dump(ready_bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(LooporaError, match="Residual Risk guidance"):
        service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    session = service.get_alignment_session(generated["session"]["id"])
    assert session["status"] == "ready"
    assert session["validation"]["ok"] is False
    assert any(
        event["event_type"] == "alignment_import_failed"
        and "Residual Risk guidance" in event["payload"].get("error", "")
        for event in service.list_alignment_events(session["id"])
    )


def test_agent_loop_refreshes_ready_hash_after_valid_bundle_file_change(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    original_ready_sha = generated["binding"]["ready_candidate_sha256"]
    ready_path = Path(generated["session"]["bundle_path"])
    ready_bundle = yaml.safe_load(ready_path.read_text(encoding="utf-8"))
    ready_bundle["metadata"]["description"] = "Run from a valid canonical edit made after the first preview."
    ready_path.write_text(yaml.safe_dump(ready_bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")
    expected_ready_sha, expected_ready_bytes = _ready_candidate_digest(ready_path.read_text(encoding="utf-8"))
    assert expected_ready_sha != original_ready_sha

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["binding"]["ready_candidate_sha256"] == expected_ready_sha
    assert started["binding"]["ready_candidate_bytes"] == expected_ready_bytes
    assert started["session"]["validation"]["bundle_sha256"] == expected_ready_sha
    assert started["session"]["validation"]["bundle_bytes"] == expected_ready_bytes
