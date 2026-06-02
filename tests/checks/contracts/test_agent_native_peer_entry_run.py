from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    Path,
    _drive_agent_native_run_to_success,
    alignment_bundle_yaml,
    pytest,
)


@pytest.mark.parametrize(
    "agent_case",
    [
        {
            "adapter": "claude",
            "entry_source": "claude_project_skill",
            "context_id": "claude-session-a",
            "context_source": "explicit",
        },
        {
            "adapter": "opencode",
            "entry_source": "opencode_project_command",
            "context_id": "",
            "context_source": "workdir",
        },
    ],
)
def test_peer_agent_gen_validates_ready_bundle_and_loop_starts_run(
    service_factory,
    monkeypatch,
    tmp_path: Path,
    sample_workdir: Path,
    agent_case: dict[str, str],
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-thread-must-not-bind-peer-agent")
    adapter = agent_case["adapter"]
    entry_source = agent_case["entry_source"]
    context_id = agent_case["context_id"]
    context_source = agent_case["context_source"]

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter=adapter,
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            context_id=context_id,
            entry_source=entry_source,
        )
    )

    assert generated["adapter"] == adapter
    assert generated["candidate_origin"] == "agent_entry"
    assert generated["candidate_entry_source"] == entry_source
    assert generated["host_context_id"] == context_id
    assert generated["ready"] is True
    assert generated["binding"]["context_source"] == context_source
    assert generated["binding"]["host_context_id"] == context_id
    assert generated["binding"]["candidate_origin"] == "agent_entry"
    assert generated["binding"]["candidate_adapter"] == adapter
    assert generated["binding"]["candidate_entry_source"] == entry_source
    assert generated["binding"]["entry_invocations"][-1]["entry_source"] == entry_source
    candidate_events = service.list_alignment_events(generated["session"]["id"], limit=20)
    assert any(
        event["event_type"] == "agent_candidate_received"
        and event["payload"]["candidate_origin"] == "agent_entry"
        and event["payload"]["adapter"] == adapter
        and event["payload"]["entry_source"] == entry_source
        and event["payload"]["host_context_id"] == context_id
        and event["payload"]["has_candidate_yaml"] is True
        for event in candidate_events
    )

    started = service.start_agent_loop(
        adapter,
        workdir=sample_workdir,
        context_id=context_id,
        entry_source=entry_source,
        execute_async=False,
    )

    assert started["adapter"] == adapter
    assert started["run"]["id"]
    assert started["started_new_run"] is True
    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    assert started["next_step"]["step_id"] == "builder_step"
    assert [item["action"] for item in started["binding"]["entry_invocations"][-2:]] == ["plan", "run"]
    assert {item["entry_source"] for item in started["binding"]["entry_invocations"][-2:]} == {entry_source}
    final = _drive_agent_native_run_to_success(
        service,
        adapter=adapter,
        started=started,
        workdir=sample_workdir,
        context_id=context_id,
    )
    assert final["complete"] is True
