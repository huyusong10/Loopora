from __future__ import annotations

import json
from pathlib import Path

from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot
from loopora.context_flow import (
    STEP_INSTRUCTION_CONTEXT_SCHEMA,
    StepInstructionContextRequest,
    build_step_instruction_context,
    render_evidence_section,
)
from loopora.executor import FakeCodexExecutor
from loopora.run_artifacts import RunArtifactLayout
from loopora.runner_step_context_inputs import manifest_prompt_context
from loopora.run_takeaways import build_judgment_contract, normalize_run_takeaway_projection_shape

from runner_helpers import (
    _assert_evidence_manifest,
    _create_loop,
    _read_jsonl,
    _step_outputs_by_archetype,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _assert_run_contract_freezes_spec_judgment_surfaces(run_contract: dict) -> None:
    compiled_spec = run_contract["compiled_spec"]
    assert run_contract["success_surface"] == compiled_spec["success_surface"]
    assert run_contract["fake_done_states"] == compiled_spec["fake_done_states"]
    assert run_contract["evidence_preferences"] == compiled_spec["evidence_preferences"]
    assert run_contract["residual_risk"] == compiled_spec["residual_risk"]
    assert run_contract["source_bundle"] == {}


def test_context_prompt_evidence_sections_have_dedicated_boundary() -> None:
    prompt_sections_source = (REPO_ROOT / "src" / "loopora" / "context_prompt_sections.py").read_text(
        encoding="utf-8"
    )
    evidence_sections_source = (REPO_ROOT / "src" / "loopora" / "context_prompt_evidence_sections.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.context_prompt_evidence_sections import" in prompt_sections_source
    assert "def render_evidence_section" in prompt_sections_source
    assert "return _render_evidence_section(evidence)" in prompt_sections_source
    assert "def render_artifact_refs" in prompt_sections_source
    assert "return _render_artifact_refs(refs)" in prompt_sections_source
    for marker in (
        "def _evidence_item_prompt_lines",
        "def _gatekeeper_support_prompt_value",
        "def _manifest_claims_by_id",
        "def _manifest_summary_prompt_line",
        "def _manifest_claim_prompt_lines",
        "def _prompt_bool",
        "def _artifact_ref_prompt_paths",
        "def _int_value",
    ):
        assert marker in evidence_sections_source
        assert marker not in prompt_sections_source
    for import_marker in (
        "from loopora.evidence_support import evidence_item_is_supporting_gatekeeper_ref",
        "from loopora.residual_risk_support import residual_risk_is_meaningful",
        "from loopora.structured_booleans import structured_bool_is_true",
        "from loopora.structured_numbers import structured_non_negative_int",
    ):
        assert import_marker in evidence_sections_source
        assert import_marker not in prompt_sections_source
    assert "context_prompt_evidence_sections.py" in design_source


def test_context_step_artifact_refs_have_dedicated_boundary() -> None:
    step_results_source = (REPO_ROOT / "src" / "loopora" / "context_step_results.py").read_text(encoding="utf-8")
    handoffs_source = (REPO_ROOT / "src" / "loopora" / "context_step_handoffs.py").read_text(encoding="utf-8")
    artifact_refs_source = (REPO_ROOT / "src" / "loopora" / "context_step_artifact_refs.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.context_step_handoffs import" in step_results_source
    assert "from loopora.context_step_artifact_refs import" in handoffs_source
    assert "def output_workspace_artifact_refs" in artifact_refs_source
    assert "def workspace_artifact_ref" in artifact_refs_source
    assert "def _output_workspace_artifact_refs" not in step_results_source
    assert "def _workspace_artifact_ref" not in step_results_source
    assert "context_step_artifact_refs.py" in design_source


def test_context_step_result_projections_have_dedicated_boundaries() -> None:
    step_results_source = (REPO_ROOT / "src" / "loopora" / "context_step_results.py").read_text(encoding="utf-8")
    handoffs_source = (REPO_ROOT / "src" / "loopora" / "context_step_handoffs.py").read_text(encoding="utf-8")
    evidence_source = (REPO_ROOT / "src" / "loopora" / "context_step_evidence_entries.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "class StepResultContext" in step_results_source
    assert "class StepEvidenceEntryRequest" in step_results_source
    assert "def build_step_handoff" in step_results_source and "return _build_step_handoff(result)" in step_results_source
    assert "def build_step_evidence_entry" in step_results_source and "return _build_step_evidence_entry(request)" in step_results_source
    assert "def build_step_handoff" in handoffs_source
    assert "def build_step_evidence_entry" in evidence_source
    assert "def evidence_entry_id" in evidence_source
    assert "def _evidence_verifies" in evidence_source
    assert "def _evidence_verifies" not in step_results_source
    assert "def _handoff_core" in handoffs_source
    assert "def _handoff_core" not in step_results_source
    assert "context_step_handoffs.py" in design_source
    assert "context_step_evidence_entries.py" in design_source


def test_successful_run_writes_expected_artifacts(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    step_outputs = _step_outputs_by_archetype(run_dir)
    assert run["status"] == "succeeded"
    assert (run_dir / "timeline" / "events.jsonl").exists()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "timeline" / "stagnation.json").exists()
    assert (run_dir / "stagnation.json").exists()
    assert (run_dir / "evidence" / "ledger.jsonl").exists()
    assert (run_dir / "evidence" / "coverage.json").exists()
    assert (run_dir / "evidence" / "manifest.json").exists()
    assert (run_dir / "evidence" / "task_verdict.json").exists()
    assert (run_dir / "contract" / "compiled_spec.json").exists()
    assert (run_dir / "contract" / "strategy_source.json").exists() and (run_dir / "contract" / "workflow.json").exists()
    assert (run_dir / "contract" / "run_contract.json").exists()
    assert (run_dir / "context" / "latest_state.json").exists()
    assert (run_dir / "context" / "latest_iteration_summary.json").exists()
    assert all((sample_workdir / ".loopora" / "loops" / loop["id"] / name).exists() for name in ("compiled_spec.json", "strategy_source.json"))
    frozen_strategy_source = json.loads((run_dir / "contract" / "strategy_source.json").read_text(encoding="utf-8"))
    run_contract = json.loads((run_dir / "contract" / "run_contract.json").read_text(encoding="utf-8"))
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    assert coverage["coverage_path"] == "evidence/coverage.json"
    assert coverage["ledger_path"] == "evidence/ledger.jsonl"
    assert coverage["status"] in {"covered", "weak"}
    assert coverage["targets"]
    _assert_evidence_manifest(run_dir)
    assert run["run_status"] == "succeeded"
    assert run["task_verdict"]["status"] == "passed"
    assert run["task_verdict"]["source"] == "gatekeeper"
    assert json.loads((run_dir / "evidence" / "task_verdict.json").read_text(encoding="utf-8")) == run["task_verdict"]
    _assert_run_contract_freezes_spec_judgment_surfaces(run_contract)
    assert run_contract["workflow"]["steps"] == [
        {
            "id": step["id"],
            "role_id": step["role_id"],
            "on_pass": step.get("on_pass", ""),
            "model": step.get("model", ""),
            "inherit_session": bool(step.get("inherit_session")),
            "extra_cli_args": step.get("extra_cli_args", ""),
            "parallel_group": step.get("parallel_group", ""),
            "inputs": step.get("inputs", {}),
            "action_policy": step.get("action_policy", {}),
        }
        for step in frozen_strategy_source["steps"]
    ]
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    builder_request = next(item for item in role_requests if item["role_archetype"] == "builder")
    inspector_request = next(item for item in role_requests if item["role_archetype"] == "inspector")
    gatekeeper_request = next(item for item in role_requests if item["role_archetype"] == "gatekeeper")
    assert builder_request["sandbox"] == "workspace-write"
    assert inspector_request["sandbox"] == "read-only"
    assert gatekeeper_request["sandbox"] == "read-only"
    assert "action_policy" in builder_request["extra_context_keys"]
    assert step_outputs["inspector"]
    assert step_outputs["gatekeeper"]
    assert any((item["step_dir"] / "prompt.md").exists() for item in step_outputs["inspector"])
    assert any((item["step_dir"] / "prompt.md").exists() for item in step_outputs["gatekeeper"])
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "All checks passed in this iteration." in summary
    assert "evidence/ledger.jsonl" in summary
    assert "timeline/iterations.jsonl" in summary


def test_builder_declared_workspace_artifacts_are_written_to_evidence_refs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class ChangedFileExecutor(FakeCodexExecutor):
        def _build_payload(self, request):
            payload = super()._build_payload(request)
            if request.role_archetype == "builder":
                proof_path = request.workdir / "tests" / "evidence" / "proof.json"
                proof_path.parent.mkdir(parents=True, exist_ok=True)
                proof_path.write_text('{"ok": true}\n', encoding="utf-8")
                (request.workdir / "progress.md").write_text("# Progress\n\nChanged.\n", encoding="utf-8")
                payload["changed_files"] = ["progress.md", "missing.md", "../outside.md"]
                payload["proof_files"] = ["tests/evidence/proof.json"]
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = lambda: ChangedFileExecutor(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Workspace Artifact Loop")

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    builder_entry = next(item for item in ledger if item["archetype"] == "builder")
    workspace_refs = [item for item in builder_entry["artifact_refs"] if item["kind"] == "workspace"]
    assert {item["workspace_path"] for item in workspace_refs} == {
        "progress.md",
        "tests/evidence/proof.json",
    }
    assert all(Path(item["absolute_path"]).is_absolute() for item in workspace_refs)
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    gatekeeper_request = next(item for item in role_requests if item["role_archetype"] == "gatekeeper")
    gatekeeper_prompt = (run_dir / gatekeeper_request["prompt_path"]).read_text(encoding="utf-8")
    assert "changed-file:progress.md" in gatekeeper_prompt
    assert "proof-file:tests/evidence/proof.json" in gatekeeper_prompt
    assert f"absolute: {(sample_workdir / 'tests' / 'evidence' / 'proof.json').resolve()}" in gatekeeper_prompt
    assert "Manifest: evidence/manifest.json" in gatekeeper_prompt
    assert "Proof strength:" in gatekeeper_prompt
    assert "proof_status=direct_proof" in gatekeeper_prompt
    assert "workspace_backed=true" in gatekeeper_prompt
    manifest = json.loads((run_dir / "evidence" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["direct_proof_claim_count"] >= 1
    builder_claim = next(item for item in manifest["claims"] if item["producer"]["archetype"] == "builder")
    assert builder_claim["verification_status"] == "direct_proof"
    assert builder_claim["workspace_backed"] is True
    assert builder_claim["reproducible"] is True
    proof_ref = next(item for item in builder_claim["artifact_refs"] if item["label"] == "proof-file:tests/evidence/proof.json")
    assert proof_ref["exists"] is True
    assert proof_ref["hash_status"] == "sha256"
    assert proof_ref["sha256"]


def test_manifest_prompt_context_does_not_promote_string_booleans(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt")
    layout.initialize()
    (layout.evidence_manifest_path).write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "id": "ev_string_bool",
                        "verification_status": "direct_proof",
                        "measured_evidence": "true",
                        "concrete_evidence_claim_count": True,
                        "artifact_count": 1,
                        "artifact_backed": "true",
                        "workspace_backed": "true",
                        "reproducible": "true",
                        "coverage_targets": [
                            {
                                "id": "done_when.check",
                                "kind": "done_when",
                                "label": "Done check",
                                "reported_status": "covered",
                                "coverage_status": "covered",
                                "required": "true",
                                "evidence_refs": ["ev_support"],
                            },
                            {
                                "id": "evidence_preference.pref_001",
                                "kind": "evidence_preference",
                                "label": "Evidence preference",
                                "reported_status": "weak",
                                "coverage_status": "weak",
                                "required": "true",
                                "evidence_refs": [],
                            },
                            "gatekeeper.finish",
                        ],
                    }
                ],
                "problems": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _summary, claims = manifest_prompt_context(layout, ["ev_string_bool"])

    assert claims[0]["measured_evidence"] is False
    assert claims[0]["concrete_evidence_claim_count"] == 0
    assert claims[0]["artifact_backed"] is False
    assert claims[0]["workspace_backed"] is False
    assert claims[0]["reproducible"] is False
    assert claims[0]["coverage_targets"][0] == {
        "id": "done_when.check",
        "kind": "done_when",
        "label": "Done check",
        "reported_status": "covered",
        "coverage_status": "covered",
        "required": True,
        "evidence_refs": ["ev_support"],
    }
    assert claims[0]["coverage_targets"][1]["required"] is False
    assert claims[0]["coverage_targets"][2]["id"] == "gatekeeper.finish"
    assert claims[0]["coverage_targets"][2]["required"] is True


def test_step_instruction_context_preserves_manifest_claim_target_trace(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt")
    layout.initialize()
    step_context = build_step_instruction_context(
        StepInstructionContextRequest(
            run_contract={
                "compiled_spec": {},
                "workflow": {"preset": "custom"},
                "completion_mode": "gatekeeper",
                "collaboration_summary": "Prefer evidence before closure.",
                "loop_fit_reasons": ["Future iterations keep the proof target visible."],
                "judgment_tradeoffs": ["Evidence before polish."],
                "execution_strategy": ["Prove the smallest path first, then expand only after evidence is strong."],
                "local_governance": ["GateKeeper treats skipped AGENTS.md responsibilities as Blocking."],
                "role_postures": [
                    {
                        "role_id": "gatekeeper",
                        "role_name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "posture_notes": "Fail closed when evidence is weak.",
                    }
                ],
            },
            layout=layout,
            iter_id=0,
            step={"id": "gatekeeper_step", "role_id": "gatekeeper"},
            step_order=1,
            role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
            execution_settings={},
            immediate_previous_step=None,
            completed_steps_this_iteration=[],
            previous_iteration_same_step=None,
            previous_iteration_same_role=None,
            previous_iteration_summary=None,
            previous_composite=None,
            stagnation_mode="none",
            evidence_items=[
                {
                    "id": "ev_target",
                    "role_name": "Inspector",
                    "archetype": "inspector",
                    "result": "passed",
                    "claim": "Inspector covered the target.",
                    "related_evidence_ids": [],
                    "coverage_results": [],
                    "artifact_refs": [],
                }
            ],
            evidence_known_ids=["ev_target"],
            evidence_manifest_summary={"claim_count": 1, "direct_proof_claim_count": 1},
            evidence_manifest_claims=[
                {
                    "id": "ev_target",
                    "verification_status": "direct_proof",
                    "measured_evidence": True,
                    "concrete_evidence_claim_count": 1,
                    "artifact_count": 1,
                    "artifact_backed": True,
                    "workspace_backed": True,
                    "reproducible": True,
                    "coverage_targets": [
                        {
                            "id": "done_when.check",
                            "kind": "done_when",
                            "label": "Done check",
                            "reported_status": "covered",
                            "coverage_status": "covered",
                            "required": "true",
                            "evidence_refs": ["ev_target"],
                        }
                    ],
                }
            ],
        )
    )

    assert step_context["contract"]["collaboration_summary"] == "Prefer evidence before closure."
    assert step_context["contract"]["loop_fit_reasons"] == ["Future iterations keep the proof target visible."]
    assert step_context["contract"]["judgment_tradeoffs"] == ["Evidence before polish."]
    assert step_context["contract"]["execution_strategy"] == ["Prove the smallest path first, then expand only after evidence is strong."]
    assert step_context["contract"]["local_governance"] == ["GateKeeper treats skipped AGENTS.md responsibilities as Blocking."]
    assert step_context["contract"]["role_postures"] == [
        {
            "role_id": "gatekeeper",
            "role_name": "GateKeeper",
            "archetype": "gatekeeper",
            "posture_notes": "Fail closed when evidence is weak.",
        }
    ]
    assert "loop_fit_reasons" in STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["required"]
    assert STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["properties"]["loop_fit_reasons"]["type"] == "array"
    assert "judgment_tradeoffs" in STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["required"]
    assert STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["properties"]["judgment_tradeoffs"]["type"] == "array"
    assert "execution_strategy" in STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["required"]
    assert STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["properties"]["execution_strategy"]["type"] == "array"
    assert "local_governance" in STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["required"]
    assert STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["properties"]["local_governance"]["type"] == "array"
    assert "role_postures" in STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["required"]
    assert STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]["properties"]["role_postures"]["type"] == "array"
    target_trace = step_context["evidence"]["manifest_claims"][0]["coverage_targets"][0]
    assert target_trace == {
        "id": "done_when.check",
        "kind": "done_when",
        "label": "Done check",
        "reported_status": "covered",
        "coverage_status": "covered",
        "required": True,
        "evidence_refs": ["ev_target"],
    }
    prompt_section = render_evidence_section(step_context["evidence"])
    assert '"id": "done_when.check"' in prompt_section
    assert '"required": true' in prompt_section


def test_step_instruction_context_derives_legacy_local_governance_before_prompting(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt_legacy_governance")
    layout.initialize()

    step_context = build_step_instruction_context(
        StepInstructionContextRequest(
            run_contract={
                "compiled_spec": {
                    "raw_sections": {
                        "Role Notes": (
                            "Builder reads AGENTS.md and design/README.md before editing.\n"
                            "Inspector verifies design/ and tests/ obligations against the result.\n"
                            "GateKeeper treats skipped AGENTS.md or tests/ validation as Weak, Unproven, or Blocking."
                        )
                    }
                },
                "workflow": {
                    "preset": "custom",
                    "collaboration_intent": "Route project-local governance proof through the handoffs before closure.",
                    "roles": [
                        {
                            "id": "gatekeeper",
                            "name": "GateKeeper",
                            "archetype": "gatekeeper",
                            "posture_notes": "Fail closed when local governance evidence is skipped.",
                        }
                    ],
                },
                "completion_mode": "gatekeeper",
                "collaboration_summary": "Future iterations keep inherited project rules visible.",
            },
            layout=layout,
            iter_id=0,
            step={"id": "gatekeeper_step", "role_id": "gatekeeper"},
            step_order=1,
            role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
            execution_settings={},
            immediate_previous_step=None,
            completed_steps_this_iteration=[],
            previous_iteration_same_step=None,
            previous_iteration_same_role=None,
            previous_iteration_summary=None,
            previous_composite=None,
            stagnation_mode="none",
        )
    )

    assert any("Builder reads AGENTS.md" in item for item in step_context["contract"]["local_governance"])
    assert any("Inspector verifies design/" in item for item in step_context["contract"]["local_governance"])
    assert any("GateKeeper treats skipped AGENTS.md" in item for item in step_context["contract"]["local_governance"])


def test_step_instruction_context_normalizes_judgment_contract_field_types(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt_contract_types")
    layout.initialize()

    step_context = build_step_instruction_context(
        StepInstructionContextRequest(
            run_contract={
                "compiled_spec": {
                    "goal": "Keep the step contract typed.",
                    "coverage_targets": [{"id": "done_when.typed"}, "not-a-target"],
                    "success_surface": ["Stable user-visible result.", True],
                    "fake_done_states": "happy path only",
                    "evidence_preferences": [False, "Direct command proof."],
                    "residual_risk": True,
                },
                "workflow": {"preset": "custom", "collaboration_intent": "Route proof before closure."},
                "completion_mode": "gatekeeper",
                "collaboration_summary": "Keep frozen judgment typed.",
                "loop_fit_reasons": ["Future rounds use the same contract.", False],
                "judgment_tradeoffs": "proof before polish",
                "execution_strategy": ["Prove the typed context first.", 3],
                "local_governance": [False, "GateKeeper blocks skipped local rules."],
                "role_postures": [
                    {
                        "role_id": "builder",
                        "role_name": "Builder",
                        "archetype": "builder",
                        "posture_notes": "Keep the implementation narrow.",
                    },
                    {"role_id": "inspector", "role_name": "Inspector", "archetype": "inspector"},
                    "not-a-posture",
                ],
                "success_surface": ["Top-level stable user-visible result.", False],
                "fake_done_states": ["Top-level happy-path-only proof is fake done.", 7],
                "evidence_preferences": ["Top-level direct command proof.", False],
                "residual_risk": "Top-level manual copy polish remains a visible follow-up.",
            },
            layout=layout,
            iter_id=0,
            step={"id": "builder_step", "role_id": "builder"},
            step_order=0,
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
            execution_settings={},
            immediate_previous_step=None,
            completed_steps_this_iteration=[],
            previous_iteration_same_step=None,
            previous_iteration_same_role=None,
            previous_iteration_summary=None,
            previous_composite=None,
            stagnation_mode="none",
        )
    )

    assert step_context["contract"]["coverage_targets"] == [{"id": "done_when.typed"}]
    assert step_context["contract"]["loop_fit_reasons"] == ["Future rounds use the same contract."]
    assert step_context["contract"]["judgment_tradeoffs"] == []
    assert step_context["contract"]["execution_strategy"] == ["Prove the typed context first."]
    assert step_context["contract"]["local_governance"] == ["GateKeeper blocks skipped local rules."]
    assert step_context["contract"]["role_postures"] == [
        {
            "role_id": "builder",
            "role_name": "Builder",
            "archetype": "builder",
            "posture_notes": "Keep the implementation narrow.",
        }
    ]
    assert step_context["contract"]["success_surface"] == ["Top-level stable user-visible result."]
    assert step_context["contract"]["fake_done_states"] == ["Top-level happy-path-only proof is fake done."]
    assert step_context["contract"]["evidence_preferences"] == ["Top-level direct command proof."]
    assert step_context["contract"]["residual_risk"] == "Top-level manual copy polish remains a visible follow-up."


def test_run_contract_tradeoffs_include_role_prompt_files(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt_tradeoffs")
    layout.initialize()

    contract = build_run_contract_snapshot(
        RunContractSnapshotRequest(
            run={
                "id": "run_tradeoff",
                "loop_id": "loop_tradeoff",
                "workdir": str(tmp_path),
                "completion_mode": "gatekeeper",
                "max_iters": 4,
                "max_role_retries": 1,
                "delta_threshold": 0.005,
                "trigger_window": 2,
                "regression_window": 2,
                "iteration_interval_seconds": 0,
                "executor_kind": "codex",
                "executor_mode": "preset",
                "model": "gpt-5.4",
                "reasoning_effort": "medium",
            },
            compiled_spec={"checks": [], "raw_sections": {}},
            strategy_source={
                "preset": "custom",
                "collaboration_intent": "First route evidence before GateKeeper closure, then expand only after proof is strong.",
                "roles": [
                    {
                        "id": "gatekeeper",
                        "name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "prompt_ref": "gatekeeper.md",
                        "posture_notes": "Reject weak proof even when the happy path looks polished.",
                    }
                ],
                "steps": [],
            },
            prompt_files={
                "builder.md": "Builder reads AGENTS.md before changing work.",
                "inspector.md": "Inspector verifies AGENTS.md and tests/ obligations.",
                "gatekeeper.md": (
                    "Strict blocking beats pragmatic progress when evidence is weak. "
                    "GateKeeper treats skipped AGENTS.md or tests/ validation as Blocking."
                ),
            },
            workspace_baseline={"file_count": 0},
            layout=layout,
            collaboration_summary="Future iterations stay anchored to the contract as new evidence appears.",
        )
    )

    assert any("Strict blocking beats pragmatic progress" in item for item in contract["judgment_tradeoffs"])
    assert any("First route evidence before GateKeeper closure" in item for item in contract["execution_strategy"])
    assert any("Builder reads AGENTS.md" in item for item in contract["local_governance"])
    assert any("Inspector verifies AGENTS.md" in item for item in contract["local_governance"])
    assert any("GateKeeper treats skipped AGENTS.md" in item for item in contract["local_governance"])
    assert contract["role_postures"] == [
        {
            "role_id": "gatekeeper",
            "role_name": "GateKeeper",
            "archetype": "gatekeeper",
            "posture_notes": "Reject weak proof even when the happy path looks polished.",
        }
    ]
    assert contract["loop_fit_reasons"] == ["Future iterations stay anchored to the contract as new evidence appears."]


def test_run_contract_role_postures_can_fall_back_to_role_prompt_body(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt_role_posture")
    layout.initialize()

    contract = build_run_contract_snapshot(
        RunContractSnapshotRequest(
            run={
                "id": "run_prompt_posture",
                "loop_id": "loop_prompt_posture",
                "workdir": str(tmp_path),
                "completion_mode": "gatekeeper",
                "max_iters": 4,
                "max_role_retries": 1,
                "delta_threshold": 0.005,
                "trigger_window": 2,
                "regression_window": 2,
                "iteration_interval_seconds": 0,
                "executor_kind": "codex",
                "executor_mode": "preset",
                "model": "gpt-5.4",
                "reasoning_effort": "medium",
            },
            compiled_spec={"checks": [], "raw_sections": {}},
            strategy_source={
                "preset": "custom",
                "collaboration_intent": "Keep role-specific evidence visible.",
                "roles": [
                    {
                        "id": "contract_inspector",
                        "name": "Contract Inspector",
                        "archetype": "inspector",
                        "prompt_ref": "inspector.md",
                    }
                ],
                "steps": [],
            },
            prompt_files={
                "inspector.md": (
                    "---\nversion: 1\narchetype: inspector\n---\n\n"
                    "Inspect the Builder handoff against fake-done risk before GateKeeper closes."
                ),
            },
            workspace_baseline={"file_count": 0},
            layout=layout,
        )
    )

    assert contract["role_postures"] == [
        {
            "role_id": "contract_inspector",
            "role_name": "Contract Inspector",
            "archetype": "inspector",
            "posture_notes": "Inspect the Builder handoff against fake-done risk before GateKeeper closes.",
        }
    ]


def test_run_contract_does_not_freeze_summary_only_local_governance(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt_summary_only_governance")
    layout.initialize()

    contract = build_run_contract_snapshot(
        RunContractSnapshotRequest(
            run={
                "id": "run_summary_governance",
                "loop_id": "loop_summary_governance",
                "workdir": str(tmp_path),
                "completion_mode": "gatekeeper",
                "max_iters": 4,
                "max_role_retries": 1,
                "delta_threshold": 0.005,
                "trigger_window": 2,
                "regression_window": 2,
                "iteration_interval_seconds": 0,
                "executor_kind": "codex",
                "executor_mode": "preset",
                "model": "gpt-5.4",
                "reasoning_effort": "medium",
            },
            compiled_spec={"checks": [], "raw_sections": {}},
            strategy_source={
                "preset": "custom",
                "collaboration_intent": "Use the handoff and evidence flow before GateKeeper closure.",
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                    {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                ],
                "steps": [],
            },
            prompt_files={},
            workspace_baseline={"file_count": 0},
            layout=layout,
            collaboration_summary=(
                "Future iterations stay anchored to the contract. Builder reads AGENTS.md, Inspector verifies "
                "design/ and tests/, and GateKeeper treats skipped AGENTS.md responsibilities as Blocking."
            ),
        )
    )

    assert contract["local_governance"] == []


def test_judgment_contract_preserves_empty_runtime_local_governance(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt_empty_governance_takeaway")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "contract_path": "contract/run_contract.json",
                "completion_mode": "gatekeeper",
                "compiled_spec": {
                    "check_mode": "specified",
                    "checks": [{"id": "check_001"}],
                    "coverage_targets": [{"id": "done_when.check_001", "required": True}],
                    "raw_sections": {},
                },
                "workflow": {"preset": "custom", "collaboration_intent": "Keep evidence moving."},
                "collaboration_summary": (
                    "Builder reads AGENTS.md, Inspector verifies design/ and tests/, and GateKeeper treats "
                    "skipped AGENTS.md responsibilities as Blocking."
                ),
                "local_governance": [],
                "role_postures": [
                    {
                        "role_id": "builder",
                        "role_name": "Builder",
                        "archetype": "builder",
                        "posture_notes": "Treat project-local rules as part of the task evidence.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    judgment_contract = build_judgment_contract({"runs_dir": str(layout.run_dir)})

    assert judgment_contract["local_governance"] == []
    assert judgment_contract["contract_path"] == "contract/run_contract.json"
    assert judgment_contract["check_mode"] == "specified"
    assert judgment_contract["check_count"] == 1
    assert judgment_contract["completion_mode"] == "gatekeeper"
    assert judgment_contract["strategy_preset"] == "custom" and "workflow_preset" not in judgment_contract
    assert judgment_contract["coverage_targets"] == [{"id": "done_when.check_001", "required": True}]
    assert judgment_contract["role_postures"] == [
        "Builder: Treat project-local rules as part of the task evidence."
    ]


def test_takeaway_judgment_contract_preserves_inherited_run_id_after_normalization() -> None:
    projection = normalize_run_takeaway_projection_shape(
        {"id": "run_next", "status": "awaiting_agent"},
        {
            "judgment_contract": {
                "goal": "Continue from the prior evidence gap.",
                "inherited_from_run_id": "run_previous",
            },
        },
    )

    assert projection["judgment_contract"]["inherited_from_run_id"] == "run_previous"
