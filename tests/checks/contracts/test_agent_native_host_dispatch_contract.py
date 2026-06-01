from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    LooporaConflictError,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    alignment_bundle_yaml,
    json,
    pytest,
)


def test_agent_native_submit_requires_matching_host_dispatch_proof(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Require native role dispatch proof.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = started["next_step"]
    raw_output_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).step_output_raw_path(
        int(step["iter"]),
        int(step["step_order"]),
        str(step["step_id"]),
    )

    with pytest.raises(LooporaConflictError, match="loopora_host_dispatch"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    for field in ("adapter", "run_id", "iter", "step_id", "step_order"):
        incomplete_dispatch = _agent_native_host_dispatch("codex", step)
        incomplete_dispatch.pop(field)
        with pytest.raises(LooporaConflictError, match=rf"{field} is required"):
            service.submit_agent_native_step(
                AgentNativeStepSubmitRequest(
                    adapter="codex",
                    workdir=sample_workdir,
                    run_id=str(step["run_id"]),
                    step_id=str(step["step_id"]),
                    output=_agent_native_step_output(step),
                    host_dispatch=incomplete_dispatch,
                    entry_source="codex_project_skill",
                )
            )
        assert not raw_output_path.exists()

    stale_dispatch = _agent_native_host_dispatch("codex", step)
    stale_dispatch["iter"] = int(step["iter"]) + 1
    with pytest.raises(LooporaConflictError, match="iter does not match the claimed agent-native step"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=stale_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    stale_dispatch = _agent_native_host_dispatch("codex", step)
    stale_dispatch["step_order"] = int(step["step_order"]) + 1
    with pytest.raises(LooporaConflictError, match="step_order does not match the claimed agent-native step"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=stale_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    bad_dispatch = _agent_native_host_dispatch("codex", step)
    bad_dispatch["actual_agent"] = "loopora-gatekeeper"
    with pytest.raises(LooporaConflictError, match="expected loopora-builder"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=bad_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()


def test_agent_native_submit_preserves_optional_official_native_trace(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_yaml = alignment_bundle_yaml(str(sample_workdir.resolve())).replace(
        "Future iterations stay anchored to this contract",
        "Preserve native subagent trace proof when the host exposes it. Future iterations stay anchored to this contract",
    )
    bundle_file.write_text(bundle_yaml, encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Preserve native subagent trace proof when the host exposes it.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = started["next_step"]
    dispatch = _agent_native_host_dispatch("codex", step)
    dispatch["native_tool_name"] = "spawn_agent"
    dispatch["native_trace_ref"] = "codex-tool-call-123"
    dispatch["native_trace"] = {
        "available": True,
        "tool_name": "spawn_agent",
        "tool_call_id": "toolu_codex_123",
        "subagent_run_id": "subagent-run-1",
        "event_ref": "events.jsonl#12",
    }

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=_agent_native_step_output(step),
            host_dispatch=dispatch,
            entry_source="codex_project_skill",
        )
    )

    native_trace = result["submitted_step"]["host_dispatch"]["native_trace"]
    assert native_trace["available"] is True
    assert native_trace["tool_name"] == "spawn_agent"
    assert native_trace["official_tool_match"] is True
    assert native_trace["trace_ref"] == "codex-tool-call-123"
    assert native_trace["tool_call_id"] == "toolu_codex_123"
    state_path = RunArtifactLayout(Path(result["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["host_dispatches"][-1]["native_trace"]["subagent_run_id"] == "subagent-run-1"


def test_agent_native_host_dispatch_requires_literal_role_dispatch_booleans(service_factory) -> None:
    service = service_factory(scenario="success")
    context = {
        "adapter": "codex",
        "run": {"id": "run_agent"},
        "step_id": "builder_step",
        "role": {"archetype": "builder"},
        "active": {
            "agent_step_view": {
                "role_dispatch": {
                    "required": "true",
                    "target_agent": "loopora-builder",
                    "inline_allowed": False,
                    "accepted_dispatch_modes": ["host_subagent"],
                }
            }
        },
    }

    context["active"]["agent_step_view"]["role_dispatch"] = {}
    with pytest.raises(LooporaConflictError, match="role_dispatch is required"):
        service._validate_agent_native_host_dispatch(context, None)

    context["active"]["agent_step_view"]["role_dispatch"] = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="requires loopora_host_dispatch"):
        service._validate_agent_native_host_dispatch(context, None)

    context["active"]["agent_step_view"]["role_dispatch"] = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="requires loopora_host_dispatch"):
        service._validate_agent_native_host_dispatch(context, {})

    context["active"]["agent_step_view"]["role_dispatch"] = {
        "required": "true",
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="required must be literal true"):
        service._validate_agent_native_host_dispatch(context, None)

    context["active"]["agent_step_view"]["role_dispatch"] = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": "false",
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="inline_allowed must be a literal boolean"):
        service._validate_agent_native_host_dispatch(
            context,
            {
                "schema_version": 1,
                "adapter": "codex",
                "run_id": "run_agent",
                "step_id": "builder_step",
                "target_agent": "loopora-builder",
                "actual_agent": "loopora-builder",
                "dispatch_mode": "host_subagent",
                "inline": False,
            },
        )

    context["active"]["agent_step_view"]["role_dispatch"] = {
        "required": True,
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="target_agent is required"):
        service._validate_agent_native_host_dispatch(
            context,
            {
                "schema_version": 1,
                "adapter": "codex",
                "run_id": "run_agent",
                "step_id": "builder_step",
                "target_agent": "loopora-builder",
                "actual_agent": "loopora-builder",
                "dispatch_mode": "host_subagent",
                "inline": False,
            },
        )

    context["active"]["agent_step_view"]["role_dispatch"] = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": [],
    }
    with pytest.raises(LooporaConflictError, match="accepted_dispatch_modes"):
        service._validate_agent_native_host_dispatch(
            context,
            {
                "schema_version": 1,
                "adapter": "codex",
                "run_id": "run_agent",
                "step_id": "builder_step",
                "target_agent": "loopora-builder",
                "actual_agent": "loopora-builder",
                "dispatch_mode": "host_subagent",
                "inline": False,
            },
        )

    context["active"]["agent_step_view"]["role_dispatch"] = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    missing_inline_dispatch = {
        "schema_version": 1,
        "adapter": "codex",
        "run_id": "run_agent",
        "step_id": "builder_step",
        "target_agent": "loopora-builder",
        "actual_agent": "loopora-builder",
        "dispatch_mode": "host_subagent",
    }
    with pytest.raises(LooporaConflictError, match="inline must be a literal boolean"):
        service._validate_agent_native_host_dispatch(context, missing_inline_dispatch)

    string_inline_dispatch = {**missing_inline_dispatch, "inline": "false"}
    with pytest.raises(LooporaConflictError, match="inline must be a literal boolean"):
        service._validate_agent_native_host_dispatch(context, string_inline_dispatch)

    with pytest.raises(LooporaConflictError, match="cannot claim inline"):
        service._validate_agent_native_host_dispatch(
            context,
            {
                "schema_version": 1,
                "adapter": "codex",
                "run_id": "run_agent",
                "step_id": "builder_step",
                "target_agent": "loopora-builder",
                "actual_agent": "loopora-builder",
                "dispatch_mode": "host_subagent",
                "inline": True,
            },
        )

    with pytest.raises(LooporaConflictError, match="schema_version must be an integer"):
        service._validate_agent_native_host_dispatch(
            context,
            {
                "schema_version": "latest",
                "adapter": "codex",
                "run_id": "run_agent",
                "step_id": "builder_step",
                "target_agent": "loopora-builder",
                "actual_agent": "loopora-builder",
                "dispatch_mode": "host_subagent",
                "inline": False,
            },
        )

    for schema_version in (True, 1.5, "1"):
        dispatch = {
            "schema_version": schema_version,
            "adapter": "codex",
            "run_id": "run_agent",
            "step_id": "builder_step",
            "target_agent": "loopora-builder",
            "actual_agent": "loopora-builder",
            "dispatch_mode": "host_subagent",
            "inline": False,
        }
        with pytest.raises(LooporaConflictError, match="schema_version must be an integer"):
            service._validate_agent_native_host_dispatch(context, dispatch)
