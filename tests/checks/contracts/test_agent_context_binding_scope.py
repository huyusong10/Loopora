from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    LooporaConflictError,
    Path,
    agent_adapters,
    alignment_bundle_yaml,
    pytest,
)


def test_codex_agent_binding_is_scoped_by_host_context(service_factory, tmp_path: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Bind this READY bundle to one Codex thread.",
            bundle_file=bundle_file,
            context_id="thread-a",
        )
    )
    assert generated["host_context_id"] == "thread-a"
    assert generated["binding"]["host_context_id"] == "thread-a"

    with pytest.raises(LooporaConflictError, match="choose a recoverable context"):
        service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-b", execute_async=False)

    started = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-a", execute_async=False)
    thread_b_resolution = service.resolve_loopora_context(
        sample_workdir,
        intent="run",
        adapter="codex",
        context_id="thread-b",
    )

    assert started["started_new_run"] is True
    assert started["binding"]["context_source"] == "explicit"
    assert started["binding"]["host_context_id"] == "thread-a"
    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    assert thread_b_resolution["action"] == "choose_recoverable_context"
    assert thread_b_resolution["requires_user_choice"] is True
    assert thread_b_resolution["confidence"] == "single_recoverable"
    assert thread_b_resolution["choices"][0]["linked_run_id"] == started["run"]["id"]


def test_agent_context_binding_path_hashes_untrusted_context_id(sample_workdir: Path) -> None:
    binding_path = agent_adapters.agent_context_binding_path(
        "codex",
        sample_workdir,
        context_id="../thread-a\nwith/slashes",
    )

    assert binding_path.parent.name == "bindings"
    assert binding_path.name.endswith(".json")
    assert "/" not in binding_path.stem
    assert ".." not in binding_path.stem
    assert "thread-a" not in binding_path.name


def test_agent_loop_rejects_binding_to_different_workdir_session(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    other_workdir = tmp_path / "other-project"
    other_workdir.mkdir()
    bundle_file = tmp_path / "other-bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(other_workdir.resolve())), encoding="utf-8")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=other_workdir,
            message="Bind this READY bundle to the other project only.",
            bundle_file=bundle_file,
        )
    )
    agent_adapters.write_agent_binding(
        "codex",
        sample_workdir,
        {
            "alignment_session_id": generated["session"]["id"],
            "alignment_status": "ready",
            "bundle_path": generated["session"]["bundle_path"],
            "preview_path": f"/loops/new/bundle?alignment_session_id={generated['session']['id']}",
        },
    )

    with pytest.raises(LooporaConflictError, match="different workdir"):
        service.start_agent_loop("codex", workdir=sample_workdir, execute_async=False)
