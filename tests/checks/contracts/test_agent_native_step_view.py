from __future__ import annotations

from loopora.agent_native_step_view_context import agent_native_step_view_judgment_contract
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
    _alignment_bundle_yaml_with_peer_visible_parallel_review_inputs,
    alignment_bundle_yaml,
    append_jsonl,
    json,
    pytest,
    read_jsonl,
)


def _assert_agent_native_official_tool_contract(started: dict) -> None:
    native_todo = started["agent_run_summary"]["native_todo"]
    assert native_todo["recommended"] is True
    assert native_todo["not_evidence"] is True
    assert "official todo" in native_todo["host_policy"]
    assert started["next_step"]["native_todo"]["not_evidence"] is True
    assert started["next_step"]["role_dispatch"]["host_mechanism"] == "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    assert "spawn_agent" in started["next_step"]["role_dispatch"]["accepted_native_tools"]
    assert started["next_step"]["role_dispatch"]["native_trace_contract"]["field"] == "native_trace"


def test_agent_native_step_view_projects_full_judgment_contract(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir(exist_ok=True)
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
    _assert_agent_native_official_tool_contract(started)
    step_judgment_contract = started["next_step"]["judgment_contract"]
    context_contract = json.loads(Path(started["next_step"]["context_absolute_path"]).read_text(encoding="utf-8"))["contract"]
    snapshot_contract = service.run_observation_snapshot(started["run"]["id"])["key_takeaways"]["judgment_contract"]

    assert step_judgment_contract["contract_path"] == started["judgment_contract"]["contract_path"]
    assert snapshot_contract["contract_path"] == started["judgment_contract"]["contract_path"]
    assert snapshot_contract["loop_fit_reasons"] == started["judgment_contract"]["loop_fit_reasons"]
    assert snapshot_contract["execution_strategy"] == started["judgment_contract"]["execution_strategy"]
    assert snapshot_contract["local_governance"] == started["judgment_contract"]["local_governance"]
    assert snapshot_contract["role_postures"] == started["judgment_contract"]["role_postures"]
    assert step_judgment_contract["collaboration_summary"].startswith(
        started["judgment_contract"]["collaboration_summary"].removesuffix("…")
    )
    assert step_judgment_contract["contract_path"] == context_contract["path"]
    assert step_judgment_contract["collaboration_summary"] == context_contract["collaboration_summary"]
    assert step_judgment_contract["loop_fit_reasons"] == context_contract["loop_fit_reasons"]
    assert step_judgment_contract["judgment_tradeoffs"] == context_contract["judgment_tradeoffs"]
    assert step_judgment_contract["execution_strategy"] == context_contract["execution_strategy"]
    assert step_judgment_contract["local_governance"] == context_contract["local_governance"]
    assert step_judgment_contract["role_postures"]
    assert context_contract["role_postures"]
    assert any("Keep implementation narrow" in item for item in step_judgment_contract["role_postures"])
    assert any(item["posture_notes"].startswith("Keep implementation narrow") for item in context_contract["role_postures"])
    assert step_judgment_contract["coverage_targets"] == context_contract["coverage_targets"]
    assert step_judgment_contract["success_surface"] == context_contract["success_surface"]
    assert step_judgment_contract["fake_done_states"] == context_contract["fake_done_states"]
    assert step_judgment_contract["evidence_preferences"] == context_contract["evidence_preferences"]
    assert step_judgment_contract["residual_risk"] == context_contract["residual_risk"]
    assert step_judgment_contract["completion_mode"] == context_contract["completion_mode"]

    state_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["agent_step_view"].pop("judgment_contract", None)
    for field, replacement in {
        "judgment_tradeoffs": [],
        "execution_strategy": [],
        "local_governance": [],
        "success_surface": [],
        "fake_done_states": [],
        "evidence_preferences": [],
        "residual_risk": "",
    }.items():
        state["active_step"]["step_instruction_context"]["contract"][field] = replacement
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    claimed = service.claim_agent_native_step(
        AgentNativeStepClaimRequest(adapter="codex", workdir=sample_workdir, run_id=started["run"]["id"])
    )
    assert claimed["next_step"]["judgment_contract"]["contract_path"] == claimed["judgment_contract"]["contract_path"]
    for field in (
        "judgment_tradeoffs",
        "execution_strategy",
        "local_governance",
        "success_surface",
        "fake_done_states",
        "evidence_preferences",
        "residual_risk",
    ):
        assert claimed["next_step"]["judgment_contract"][field] == started["judgment_contract"][field]
    assert claimed["next_step"]["judgment_contract"]["coverage_targets"] == context_contract["coverage_targets"]
    persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted_state["active_step"]["agent_step_view"]["judgment_contract"] == claimed["next_step"]["judgment_contract"]

def test_agent_native_required_coverage_refs_stay_known_when_evidence_query_filters_items(
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
            message="Keep blocked coverage evidence citable by the next Agent Runner role.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    contract_step = result["next_step"]
    builder_evidence_id = contract_step["known_evidence_ids"][0]
    blocking_output = {
        "execution_summary": {"total_checks": 1, "passed": 0, "failed": 1, "errored": 0, "total_duration_ms": 1},
        "check_results": [
            {
                "id": "check_001",
                "title": "Primary contract proof",
                "status": "failed",
                "notes": "The Builder evidence does not prove the first required target.",
            }
        ],
        "dynamic_checks": [],
        "tester_observations": "Contract Inspector blocks the first required target using the Builder evidence.",
        "coverage_results": [
            {
                "target_id": "done_when.check_001",
                "status": "blocked",
                "evidence_refs": [builder_evidence_id],
                "note": "Builder evidence is insufficient for the first required target.",
            }
        ],
    }

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(contract_step["run_id"]),
            step_id=str(contract_step["step_id"]),
            output=blocking_output,
            host_dispatch=_agent_native_host_dispatch("codex", contract_step),
            entry_source="codex_project_skill",
        )
    )

    evidence_step = result["next_step"]
    blocking_evidence_id = "ev_000_01_contract_inspection_step"
    assert evidence_step["step_id"] == "evidence_inspection_step"
    assert evidence_step["required_coverage"]["top_gaps"][0]["evidence_refs"] == [blocking_evidence_id]
    assert blocking_evidence_id in evidence_step["known_evidence_ids"]
    known_evidence_refs = {item["id"]: item for item in evidence_step["known_evidence_refs"]}
    assert known_evidence_refs[builder_evidence_id]["claim"]
    assert known_evidence_refs[blocking_evidence_id]["claim"] == "Contract Inspector blocks the first required target using the Builder evidence."
    assert known_evidence_refs[blocking_evidence_id]["coverage_target_ids"] == ["done_when.check_001"]
    assert known_evidence_refs[blocking_evidence_id]["gatekeeper_support"] == "non_supporting"
    assert known_evidence_refs[blocking_evidence_id]["gatekeeper_support_reason"] == "result is blocked"
    assert evidence_step["required_coverage"]["target_count"] >= evidence_step["required_coverage"]["covered_check_count"]
    assert "blocked_target_count" in evidence_step["required_coverage"]

    step_instruction_context = json.loads(Path(evidence_step["context_absolute_path"]).read_text(encoding="utf-8"))
    assert step_instruction_context["iteration"]["target_count"] == evidence_step["required_coverage"]["target_count"]
    assert blocking_evidence_id in step_instruction_context["evidence"]["known_ids"]
    assert any(item["id"] == blocking_evidence_id for item in step_instruction_context["evidence"]["items"])

    template = json.loads(Path(evidence_step["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    assert blocking_evidence_id in template["loopora_result_contract"]["known_evidence_ids"]
    template_refs = {item["id"]: item for item in template["loopora_result_contract"]["known_evidence_refs"]}
    assert template_refs[blocking_evidence_id]["role_name"] == "Contract Inspector"
    assert template_refs[blocking_evidence_id]["coverage_target_ids"] == ["done_when.check_001"]
    assert template_refs[blocking_evidence_id]["gatekeeper_support"] == "non_supporting"

def test_agent_native_known_evidence_refs_classify_gatekeeper_support(
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
            message="Show which evidence refs can support GateKeeper.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    proof_path = sample_workdir / "proof" / "primary-flow.txt"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text("PASS: primary flow proof is project-owned.\n", encoding="utf-8")
    builder_output = _agent_native_step_output(builder_step)
    builder_output["changed_files"] = ["proof/primary-flow.txt"]
    builder_output["proof_files"] = ["proof/primary-flow.txt"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=builder_output,
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )

    contract_step = result["next_step"]
    builder_evidence_id = contract_step["known_evidence_ids"][0]
    step_refs = {item["id"]: item for item in contract_step["known_evidence_refs"]}
    assert step_refs[builder_evidence_id]["gatekeeper_support"] == "supporting"
    assert "proof-file" in step_refs[builder_evidence_id]["gatekeeper_support_reason"]
    assert step_refs[builder_evidence_id]["artifact_refs"] == [
        {"path": "proof/primary-flow.txt", "label": "proof-file:proof/primary-flow.txt"}
    ]

    template = json.loads(Path(contract_step["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    template_refs = {item["id"]: item for item in template["loopora_result_contract"]["known_evidence_refs"]}
    assert template_refs[builder_evidence_id]["gatekeeper_support"] == "supporting"
    assert "proof-file" in template_refs[builder_evidence_id]["gatekeeper_support_reason"]
    assert template_refs[builder_evidence_id]["artifact_refs"] == [
        {"path": "proof/primary-flow.txt", "label": "proof-file:proof/primary-flow.txt"}
    ]

def test_agent_native_duplicate_submit_cannot_append_second_evidence_entry(
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
            message="Keep agent-native step submission single-accept.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    stale_claimed_state = json.loads(state_path.read_text(encoding="utf-8"))

    first_result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    assert first_result["submitted_step"]["evidence_refs"] == ["ev_000_00_builder_step"]

    state_path.write_text(json.dumps(stale_claimed_state, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(LooporaConflictError, match="already submitted"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(builder_step["run_id"]),
                step_id=str(builder_step["step_id"]),
                output=_agent_native_step_output(builder_step),
                host_dispatch=_agent_native_host_dispatch("codex", builder_step),
                entry_source="codex_project_skill",
            )
        )

    evidence_ids = [str(item.get("id") or "") for item in read_jsonl(layout.evidence_ledger_path)]
    assert evidence_ids.count("ev_000_00_builder_step") == 1

def test_agent_native_known_evidence_ids_dedupe_duplicate_ledger_entries(
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
    builder_step = started["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    builder_evidence = next(item for item in read_jsonl(layout.evidence_ledger_path) if item.get("id") == "ev_000_00_builder_step")
    append_jsonl(layout.evidence_ledger_path, builder_evidence)

    inspector_step = result["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(inspector_step["run_id"]),
            step_id=str(inspector_step["step_id"]),
            output=_agent_native_step_output(inspector_step),
            host_dispatch=_agent_native_host_dispatch("codex", inspector_step),
            entry_source="codex_project_skill",
        )
    )

    known_ids = result["next_step"]["known_evidence_ids"]
    assert known_ids == list(dict.fromkeys(known_ids))
    step_instruction_context = json.loads(Path(result["next_step"]["context_absolute_path"]).read_text(encoding="utf-8"))
    assert step_instruction_context["evidence"]["known_ids"] == list(dict.fromkeys(step_instruction_context["evidence"]["known_ids"]))
    template = json.loads(Path(result["next_step"]["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    template_known_ids = template["loopora_result_contract"]["known_evidence_ids"]
    assert template_known_ids == list(dict.fromkeys(template_known_ids))

def test_agent_native_step_view_judgment_contract_falls_back_when_context_is_trimmed(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "runs" / "run_step_view_fallback")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep frozen judgment stronger than stale context.",
                "loop_fit_reasons": ["Later role handoffs need the same proof bar."],
                "judgment_tradeoffs": ["Evidence beats fast closure."],
                "execution_strategy": ["Prove inherited governance before polishing."],
                "local_governance": ["GateKeeper treats skipped AGENTS.md checks as Blocking."],
                "success_surface": ["Admin can complete the audited action."],
                "fake_done_states": ["Summary-only evidence is fake done."],
                "evidence_preferences": ["Require command output and audit artifacts."],
                "residual_risk": "No unmanaged residual risk is acceptable.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    contract = agent_native_step_view_judgment_contract(
        {"runs_dir": str(layout.run_dir)},
        {
            "contract": {
                "path": "contract/run_contract.json",
                "judgment_tradeoffs": [],
                "execution_strategy": [],
                "local_governance": [],
                "success_surface": [],
                "fake_done_states": [],
                "evidence_preferences": [],
                "residual_risk": "",
            }
        },
    )

    assert contract["judgment_tradeoffs"] == ["Evidence beats fast closure."]
    assert contract["execution_strategy"] == ["Prove inherited governance before polishing."]
    assert contract["local_governance"] == ["GateKeeper treats skipped AGENTS.md checks as Blocking."]
    assert contract["success_surface"] == ["Admin can complete the audited action."]
    assert contract["fake_done_states"] == ["Summary-only evidence is fake done."]
    assert contract["evidence_preferences"] == ["Require command output and audit artifacts."]
    assert contract["residual_risk"] == "No unmanaged residual risk is acceptable."

def test_agent_native_claim_rejects_corrupted_active_step_view(
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
            message="Do not turn corrupted active step views into partial execution contracts.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    state_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["agent_step_view"] = "not-a-step-view-object"
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LooporaError, match="active step contract is invalid"):
        service.claim_agent_native_step(
            AgentNativeStepClaimRequest(adapter="codex", workdir=sample_workdir, run_id=started["run"]["id"])
        )

def test_agent_native_parallel_group_peer_context_uses_group_start_snapshot(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(_alignment_bundle_yaml_with_peer_visible_parallel_review_inputs(sample_workdir), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Keep agent-native parallel reviewers isolated from peer outputs.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = result["next_step"]
    assert builder_step["action_policy"] == {
        "workspace": "workspace_write",
        "can_block": False,
        "can_finish_run": False,
    }
    assert builder_step["role"]["prompt_ref"].endswith("builder.md")
    assert "Keep implementation narrow" in builder_step["role"]["posture_notes"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )

    first_peer_step = result["next_step"]
    assert first_peer_step["step_id"] == "contract_inspection_step"
    assert first_peer_step["action_policy"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": False,
    }
    assert first_peer_step["role"]["prompt_ref"].endswith("inspector.md")
    assert "contract-level proof" in first_peer_step["role"]["posture_notes"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(first_peer_step["run_id"]),
            step_id=str(first_peer_step["step_id"]),
            output=_agent_native_step_output(first_peer_step),
            host_dispatch=_agent_native_host_dispatch("codex", first_peer_step),
            entry_source="codex_project_skill",
        )
    )

    second_peer_step = result["next_step"]
    assert second_peer_step["step_id"] == "evidence_inspection_step"
    second_peer_context = json.loads(Path(second_peer_step["context_absolute_path"]).read_text(encoding="utf-8"))
    second_peer_handoff_steps = [item["source"]["step_id"] for item in second_peer_context["upstream"]["completed_steps_this_iteration"]]

    assert second_peer_handoff_steps == ["builder_step"]
    assert second_peer_context["evidence"]["known_ids"] == ["ev_000_00_builder_step"]
    assert second_peer_step["inputs"]["evidence_query"] == {"archetypes": ["builder", "inspector"], "limit": 12}
    assert second_peer_step["parallel_group"] == "inspection_pack"
    assert second_peer_step["known_evidence_ids"] == ["ev_000_00_builder_step"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(second_peer_step["run_id"]),
            step_id=str(second_peer_step["step_id"]),
            output=_agent_native_step_output(second_peer_step),
            host_dispatch=_agent_native_host_dispatch("codex", second_peer_step),
            entry_source="codex_project_skill",
        )
    )

    gatekeeper_step = result["next_step"]
    assert gatekeeper_step["step_id"] == "gatekeeper_step"
    assert gatekeeper_step["action_policy"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": True,
    }
    assert gatekeeper_step["role"]["prompt_ref"].endswith("gatekeeper.md")
    assert "Close only when" in gatekeeper_step["role"]["posture_notes"]
    gatekeeper_context = json.loads(Path(gatekeeper_step["context_absolute_path"]).read_text(encoding="utf-8"))
    gatekeeper_handoff_steps = [item["source"]["step_id"] for item in gatekeeper_context["upstream"]["completed_steps_this_iteration"]]

    assert gatekeeper_handoff_steps == ["contract_inspection_step", "evidence_inspection_step"]
    assert {
        "ev_000_01_contract_inspection_step",
        "ev_000_02_evidence_inspection_step",
    }.issubset(set(gatekeeper_context["evidence"]["known_ids"]))
    events = service.stream_events(str(gatekeeper_step["run_id"]), limit=200)
    assert any(
        event["event_type"] == "parallel_group_started"
        and event["payload"]["parallel_group"] == "inspection_pack"
        and event["payload"]["step_ids"] == ["contract_inspection_step", "evidence_inspection_step"]
        for event in events
    )
    assert any(
        event["event_type"] == "parallel_group_finished"
        and event["payload"]["parallel_group"] == "inspection_pack"
        and event["payload"]["step_ids"] == ["contract_inspection_step", "evidence_inspection_step"]
        for event in events
    )
