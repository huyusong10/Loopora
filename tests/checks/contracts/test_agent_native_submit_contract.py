from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepClaimRequest,
    AgentNativeStepSubmitRequest,
    LooporaConflictError,
    LooporaError,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    _drive_agent_native_until_archetype,
    alignment_bundle_yaml,
    json,
    pytest,
    read_jsonl,
)

def test_agent_native_submit_rejects_read_only_workspace_claims_and_schema_mismatches(
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
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    inspector_result = _drive_agent_native_until_archetype(
        service,
        started,
        adapter="codex",
        workdir=sample_workdir,
        archetype="inspector",
    )
    step = inspector_result["next_step"]
    raw_output_path = RunArtifactLayout(Path(inspector_result["run"]["runs_dir"])).step_output_raw_path(
        int(step["iter"]),
        int(step["step_order"]),
        str(step["step_id"]),
    )

    workspace_claim_output = _agent_native_step_output(step)
    workspace_claim_output["changed_files"] = ["README.md"]
    with pytest.raises(LooporaConflictError, match="read-only step cannot claim workspace artifact fields"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=workspace_claim_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    extra_field_output = _agent_native_step_output(step)
    extra_field_output["unexpected_workspace_story"] = "I also edited files."
    with pytest.raises(LooporaConflictError, match=r"unexpected_workspace_story is not allowed"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=extra_field_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    missing_required_output = _agent_native_step_output(step)
    missing_required_output.pop("coverage_results")
    with pytest.raises(LooporaConflictError, match=r"coverage_results is required"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=missing_required_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    wrong_type_output = _agent_native_step_output(step)
    wrong_type_output["execution_summary"]["total_checks"] = "one"
    with pytest.raises(LooporaConflictError, match=r"execution_summary\.total_checks expected integer"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=wrong_type_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    invalid_enum_output = _agent_native_step_output(step)
    invalid_enum_output["check_results"][0]["status"] = "ok"
    with pytest.raises(LooporaConflictError, match=r"check_results\[0\]\.status must be one of"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=invalid_enum_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    invalid_coverage_status_output = _agent_native_step_output(step)
    invalid_coverage_status_output["coverage_results"] = [
        {
            "target_id": "done_when.check_001",
            "status": "proven",
            "evidence_refs": [],
            "note": "Proven belongs in verdict buckets or notes, not coverage_results.status.",
        }
    ]
    with pytest.raises(LooporaConflictError, match=r"coverage_results\[0\]\.status must be one of"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=invalid_coverage_status_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    unknown_coverage_target_output = _agent_native_step_output(step)
    unknown_coverage_target_output["coverage_results"] = [
        {
            "target_id": "invented.target_999",
            "status": "covered",
            "evidence_refs": [],
            "note": "The host must not invent a target outside the frozen judgment contract.",
        }
    ]
    with pytest.raises(LooporaConflictError, match=r"coverage_results_unknown_target_id: invented\.target_999"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=unknown_coverage_target_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()
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
            "capsule": {
                "role_dispatch": {
                    "required": "true",
                    "target_agent": "loopora-builder",
                    "inline_allowed": False,
                    "accepted_dispatch_modes": ["host_subagent"],
                }
            }
        },
    }

    context["active"]["capsule"]["role_dispatch"] = {}
    with pytest.raises(LooporaConflictError, match="role_dispatch is required"):
        service._validate_agent_native_host_dispatch(context, None)

    context["active"]["capsule"]["role_dispatch"] = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="requires loopora_host_dispatch"):
        service._validate_agent_native_host_dispatch(context, None)

    context["active"]["capsule"]["role_dispatch"] = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="requires loopora_host_dispatch"):
        service._validate_agent_native_host_dispatch(context, {})

    context["active"]["capsule"]["role_dispatch"] = {
        "required": "true",
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    with pytest.raises(LooporaConflictError, match="required must be literal true"):
        service._validate_agent_native_host_dispatch(context, None)

    context["active"]["capsule"]["role_dispatch"] = {
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

    context["active"]["capsule"]["role_dispatch"] = {
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

    context["active"]["capsule"]["role_dispatch"] = {
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

    context["active"]["capsule"]["role_dispatch"] = {
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

def test_agent_native_output_contract_requires_capsule_output_schema(service_factory) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaConflictError, match="output_schema is required"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed capsule should fail closed."},
            active={"capsule": {"action_policy": {"workspace": "read_only"}}},
        )

@pytest.mark.parametrize(
    ("missing_field", "message"),
    [
        ("judgment_contract", "judgment_contract is required"),
        ("required_coverage", "required_coverage is required"),
        ("action_policy", "action_policy is required"),
    ],
)
def test_agent_native_output_contract_requires_frozen_capsule_objects(
    service_factory,
    missing_field: str,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    capsule = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep the role tied to the reviewed Loop."},
        "required_coverage": {"status": "pending"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
        "known_evidence_ids": [],
    }
    capsule.pop(missing_field)

    with pytest.raises(LooporaConflictError, match=message):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed capsule should fail closed."},
            active={"capsule": capsule},
        )

def test_agent_native_output_contract_requires_known_evidence_id_closed_set(service_factory) -> None:
    service = service_factory(scenario="success")
    capsule = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep evidence refs inside the capsule."},
        "required_coverage": {"status": "pending"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
    }

    with pytest.raises(LooporaConflictError, match="known_evidence_ids must be a list"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed capsule should fail closed."},
            active={"capsule": capsule},
        )

    capsule["known_evidence_ids"] = [123]
    with pytest.raises(LooporaConflictError, match="known_evidence_ids must contain strings"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed capsule should fail closed."},
            active={"capsule": capsule},
        )

@pytest.mark.parametrize(
    ("action_policy", "message"),
    [
        ({"workspace": "workspace-write", "can_block": True, "can_finish_run": False}, "action_policy.workspace"),
        ({"workspace": "read_only", "can_block": "true", "can_finish_run": False}, "action_policy.can_block"),
        ({"workspace": "read_only", "can_block": True, "can_finish_run": "false"}, "action_policy.can_finish_run"),
    ],
)
def test_agent_native_output_contract_rejects_malformed_action_policy(
    service_factory,
    action_policy: dict,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    capsule = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep permissions literal and inspectable."},
        "required_coverage": {"status": "pending"},
        "action_policy": action_policy,
        "known_evidence_ids": [],
    }

    with pytest.raises(LooporaConflictError, match=message):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed capsule should fail closed."},
            active={"capsule": capsule},
        )

def test_agent_native_gatekeeper_blocks_unknown_coverage_result_refs(
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
            message="Require coverage target evidence refs to stay inside the known evidence set.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="gatekeeper")
    step = result["next_step"]

    gatekeeper_output = _agent_native_step_output(step)
    gatekeeper_output["coverage_results"] = [
        {
            "target_id": "fake_done.risk_001",
            "status": "covered",
            "evidence_refs": ["invented_ev"],
            "note": "This target-level evidence ref is not from known_evidence_ids.",
        }
    ]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=gatekeeper_output,
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    normalized_gatekeeper_output = json.loads(
        layout.step_output_normalized_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).read_text(encoding="utf-8")
    )
    assert normalized_gatekeeper_output["passed"] is False
    assert normalized_gatekeeper_output["blocking_issues"] == ["gatekeeper_coverage_evidence_refs_unknown: invented_ev"]

def test_agent_native_gatekeeper_blocks_unknown_top_level_evidence_refs(
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
            message="Require coverage target evidence refs to stay inside the known evidence set.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="gatekeeper")
    step = result["next_step"]

    gatekeeper_output = _agent_native_step_output(step)
    gatekeeper_output["evidence_refs"] = ["invented_ev"]
    gatekeeper_output["coverage_results"] = []
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=gatekeeper_output,
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    normalized_gatekeeper_output = json.loads(
        layout.step_output_normalized_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).read_text(encoding="utf-8")
    )
    assert normalized_gatekeeper_output["passed"] is False
    assert normalized_gatekeeper_output["blocking_issues"] == ["gatekeeper_evidence_refs_unknown: invented_ev"]

def test_agent_native_rejects_non_gatekeeper_unknown_coverage_result_refs(
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
            message="Reject invented evidence refs before non-GateKeeper output enters the ledger.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="inspector")
    step = result["next_step"]

    inspector_output = _agent_native_step_output(step)
    inspector_output["coverage_results"] = [
        {
            "target_id": "fake_done.risk_001",
            "status": "covered",
            "evidence_refs": ["invented_ev"],
            "note": "The ref is not copied from known_evidence_ids.",
        }
    ]
    with pytest.raises(LooporaError, match="agent-native evidence_refs_unknown: invented_ev"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=inspector_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )

    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    assert not layout.step_output_raw_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).exists()
    ledger = read_jsonl(layout.evidence_ledger_path)
    assert not any(item.get("step_id") == step["step_id"] for item in ledger)

def test_agent_native_submitted_step_exposes_coverage_results(
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
            message=(
                "Ship the focused starter experience with explicit evidence classifications. "
                "Execution strategy: Inspector coverage_results must show exactly which target changed. "
                "Fake done risk: do not pass with only a handoff summary and no target evidence."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="inspector")
    step = result["next_step"]

    inspector_output = _agent_native_step_output(step)
    inspector_output["coverage_results"] = [
        {
            "target_id": "done_when.check_001",
            "status": "covered",
            "evidence_refs": ["ev_000_00_builder_step"],
            "note": "Inspector verified the Builder proof against the first Done When target.",
        }
    ]

    submitted = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=inspector_output,
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    assert submitted["submitted_step"]["coverage_results"] == [
        {
            "target_id": "done_when.check_001",
            "status": "covered",
            "evidence_refs": ["ev_000_00_builder_step"],
            "note": "Inspector verified the Builder proof against the first Done When target.",
        }
    ]

def test_agent_native_known_evidence_ids_empty_capsule_stays_closed(
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
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="inspector")
    step = result["next_step"]
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "ev_000_00_builder_step" in state["active_step"]["context_packet"]["evidence"]["known_ids"]
    state["active_step"]["capsule"]["known_evidence_ids"] = []
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    inspector_output = _agent_native_step_output(step)
    inspector_output["coverage_results"] = [
        {
            "target_id": "fake_done.risk_001",
            "status": "covered",
            "evidence_refs": ["ev_000_00_builder_step"],
            "note": "The ref exists in context but not in the capsule closed set.",
        }
    ]

    with pytest.raises(LooporaError, match="agent-native evidence_refs_unknown: ev_000_00_builder_step"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=inspector_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )

    assert not layout.step_output_raw_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).exists()
    ledger = read_jsonl(layout.evidence_ledger_path)
    assert not any(item.get("step_id") == step["step_id"] for item in ledger)

def test_agent_native_active_capsule_refresh_persists_known_evidence_count(
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
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = result["next_step"]
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    capsule_path = Path(step["capsule_absolute_path"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    capsule_file = json.loads(capsule_path.read_text(encoding="utf-8"))
    state["active_step"]["capsule"].pop("known_evidence_count", None)
    state["active_step"]["capsule"]["evidence_rules"] = [
        {
            "id": "coverage_results.target_id_must_be_known_coverage_target",
            "severity": "hard",
            "rule": "Every coverage_results.target_id must be copied exactly from judgment_contract.coverage_targets[].id.",
        }
    ]
    capsule_file.pop("known_evidence_count", None)
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    capsule_path.write_text(json.dumps(capsule_file, ensure_ascii=False), encoding="utf-8")

    refreshed = service.claim_agent_native_step(
        AgentNativeStepClaimRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=result["run"]["id"],
            entry_source="codex_project_skill",
        )
    )

    assert refreshed["next_step"]["known_evidence_count"] == 0
    refreshed_rules = {
        str(item.get("id")): str(item.get("rule"))
        for item in list(refreshed["next_step"].get("evidence_rules") or [])
        if isinstance(item, dict)
    }
    assert "loopora_result_contract.coverage_target_ids" in refreshed_rules["coverage_results.target_id_must_be_known_coverage_target"]
    assert json.loads(Path(refreshed["next_step"]["agent_step_view_absolute_path"]).read_text(encoding="utf-8"))["known_evidence_count"] == 0
    assert json.loads(capsule_path.read_text(encoding="utf-8"))["known_evidence_count"] == 0
    refreshed_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert refreshed_state["active_step"]["capsule"]["known_evidence_count"] == 0
