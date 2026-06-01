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
def test_agent_native_output_contract_requires_step_view_output_schema(service_factory) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaConflictError, match="output_schema is required"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": {"action_policy": {"workspace": "read_only"}}},
        )

@pytest.mark.parametrize(
    ("missing_field", "message"),
    [
        ("judgment_contract", "judgment_contract is required"),
        ("required_coverage", "required_coverage is required"),
        ("action_policy", "action_policy is required"),
    ],
)
def test_agent_native_output_contract_requires_frozen_step_view_objects(
    service_factory,
    missing_field: str,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    step_view = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep the role tied to the reviewed Loop."},
        "required_coverage": {"status": "pending"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
        "known_evidence_ids": [],
    }
    step_view.pop(missing_field)

    with pytest.raises(LooporaConflictError, match=message):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
        )

def test_agent_native_output_contract_requires_known_evidence_id_closed_set(service_factory) -> None:
    service = service_factory(scenario="success")
    step_view = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep evidence refs inside the step view."},
        "required_coverage": {"status": "pending"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
    }

    with pytest.raises(LooporaConflictError, match="known_evidence_ids must be a list"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
        )

    step_view["known_evidence_ids"] = [123]
    with pytest.raises(LooporaConflictError, match="known_evidence_ids must contain strings"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
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
    step_view = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep permissions literal and inspectable."},
        "required_coverage": {"status": "pending"},
        "action_policy": action_policy,
        "known_evidence_ids": [],
    }

    with pytest.raises(LooporaConflictError, match=message):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
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

def test_agent_native_known_evidence_ids_empty_step_view_stays_closed(
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
    assert "ev_000_00_builder_step" in state["active_step"]["step_instruction_context"]["evidence"]["known_ids"]
    state["active_step"]["agent_step_view"]["known_evidence_ids"] = []
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    inspector_output = _agent_native_step_output(step)
    inspector_output["coverage_results"] = [
        {
            "target_id": "fake_done.risk_001",
            "status": "covered",
            "evidence_refs": ["ev_000_00_builder_step"],
            "note": "The ref exists in context but not in the step view closed set.",
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

def test_agent_native_active_step_view_refresh_persists_known_evidence_count(
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
    step_contract_path = Path(step["step_contract_absolute_path"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    step_contract_file = json.loads(step_contract_path.read_text(encoding="utf-8"))
    state["active_step"]["agent_step_view"].pop("known_evidence_count", None)
    state["active_step"]["agent_step_view"]["evidence_rules"] = [
        {
            "id": "coverage_results.target_id_must_be_known_coverage_target",
            "severity": "hard",
            "rule": "Every coverage_results.target_id must be copied exactly from judgment_contract.coverage_targets[].id.",
        }
    ]
    step_contract_file.pop("known_evidence_count", None)
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    step_contract_path.write_text(json.dumps(step_contract_file, ensure_ascii=False), encoding="utf-8")

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
    assert json.loads(step_contract_path.read_text(encoding="utf-8"))["known_evidence_count"] == 0
    refreshed_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert refreshed_state["active_step"]["agent_step_view"]["known_evidence_count"] == 0
