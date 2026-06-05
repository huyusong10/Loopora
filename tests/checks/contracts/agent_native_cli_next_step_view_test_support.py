from __future__ import annotations

from typing import Any

from agent_native_cli_test_support import (
    AgentNativeStepClaimRequest,
    CliRunner,
    Path,
    RunArtifactLayout,
    _assert_agent_next_json_summary,
    _assert_agent_next_plain_work_panel,
    _assert_cli_handoff_contract_paths,
    _assert_cli_list,
    _assert_cli_native_dispatch_contract,
    _mkdir,
    cli,
    json,
)

assert_agent_next_json_summary = _assert_agent_next_json_summary
assert_agent_next_plain_work_panel = _assert_agent_next_plain_work_panel
assert_cli_handoff_contract_paths = _assert_cli_handoff_contract_paths
assert_cli_list = _assert_cli_list
assert_cli_native_dispatch_contract = _assert_cli_native_dispatch_contract

RUN_ID = "run_next"
NEXT_STEP_ID = "inspector_step"
NEXT_STEP_DIR = f"iterations/iter_000/steps/01__{NEXT_STEP_ID}"


def invoke_agent_next_step_view(monkeypatch: Any, tmp_path: Path, *, json_output: bool = False, compact_json_output: bool = False):
    workdir = _mkdir(tmp_path / "project")
    layout = RunArtifactLayout(tmp_path / "runs" / "run_next")
    _write_next_step_run_contract(layout)
    _install_agent_next_step_view_service(monkeypatch, workdir=workdir, layout=layout)
    runner = CliRunner()
    args = [
        "agent",
        "codex",
        "next",
        "--workdir",
        str(workdir),
        "--run-id",
        RUN_ID,
        "--no-web",
    ]
    if json_output:
        args.append("--json")
    if compact_json_output:
        args.append("--compact-json")
    return runner.invoke(cli.app, args), layout


def assert_agent_contract_strategy_output(stdout: str, layout: RunArtifactLayout) -> None:
    assert f"run_contract_path: {layout.run_contract_path}" in stdout
    assert "judgment_contract_summary: Keep intermediate step views tied to frozen judgment." in stdout
    assert "check_mode: specified" in stdout
    assert "completion_mode: gatekeeper" in stdout
    assert "strategy_preset: quality_gate" in stdout
    assert "strategy_collaboration_intent: Inspector proof gaps must shape the release gate." in stdout
    assert "workflow_preset:" not in stdout
    assert "workflow_collaboration_intent:" not in stdout


def _write_next_step_run_contract(layout: RunArtifactLayout) -> None:
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep intermediate step views tied to frozen judgment.",
                "loop_fit_reasons": ["The next role needs the same proof bar as the first role."],
                "judgment_tradeoffs": ["Do not trade evidence coverage for fast handoff."],
                "execution_strategy": ["Claim the next proof gap before expanding scope."],
                "local_governance": ["Next role checks design and tests before submitting."],
                "role_postures": [
                    {
                        "role_name": "Inspector",
                        "archetype": "inspector",
                        "posture_notes": "Reject handoffs without evidence refs.",
                    }
                ],
                "completion_mode": "gatekeeper",
                "workflow": {
                    "preset": "quality_gate",
                    "collaboration_intent": "Inspector proof gaps must shape the release gate.",
                },
                "compiled_spec": {
                    "check_mode": "specified",
                    "checks": [{"id": "check_001"}],
                    "coverage_targets": [
                        {"id": "done_when.check_001", "required": True},
                        {"id": "gatekeeper.finish", "required": True},
                    ],
                },
                "success_surface": ["Support can trace the refund authorization path."],
                "fake_done_states": ["A handoff without evidence refs is fake done."],
                "evidence_preferences": ["Use command output and audit artifacts."],
                "residual_risk": "Only documented support handoff risk may remain.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _install_agent_next_step_view_service(monkeypatch: Any, *, workdir: Path, layout: RunArtifactLayout) -> None:
    class FakeService:
        def claim_agent_native_step(self, request: AgentNativeStepClaimRequest):
            assert request.adapter == "codex"
            assert request.workdir == workdir
            assert request.run_id == RUN_ID
            return _agent_next_step_view_payload(layout)

    monkeypatch.setattr(cli, "create_service", FakeService)


def _agent_next_step_view_payload(layout: RunArtifactLayout) -> dict:
    return {
        "run": {
            "id": RUN_ID,
            "status": "awaiting_agent",
            "run_status": "awaiting_agent",
            "runs_dir": str(layout.run_dir),
            "task_verdict": {
                "status": "failed",
                "summary": "Previous GateKeeper rejected the pass because evidence was non-supporting.",
            },
        },
        "run_path": f"/runs/{RUN_ID}",
        "next_step": {
            "step_id": NEXT_STEP_ID,
            "iter": 1,
            "step_order": 0,
            "role": {"name": "Inspector"},
            "role_dispatch": {
                "target_agent": "loopora-inspector",
                "target_agent_config_path": ".codex/agents/loopora-inspector.toml",
            },
            "native_todo": {
                "recommended": True,
                "not_evidence": True,
                "host_policy": (
                    "Create or update the host's official todo/progress list when available; "
                    "do not cite todo completion as Loopora evidence."
                ),
                "items": [
                    "Read top-level summary and the step contract.",
                    "Invoke loopora-inspector through the host-native role agent mechanism.",
                    "Fill the result template with schema-shaped output and preserve loopora_host_dispatch.",
                    "Submit the filled result and read top-level summary before continuing.",
                ],
            },
            "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
            "inputs": {"evidence_query": {"archetypes": ["builder"], "limit": 12}},
            "required_coverage": {
                "status": "weak",
                "covered_check_count": 1,
                "missing_check_count": 1,
                "top_gaps": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "weak",
                        "text": "Authorization proof is still weak.",
                    },
                ],
            },
            "coverage_target_ids": ["done_when.check_001", "gatekeeper.finish"],
            "coverage_targets": [
                {
                    "id": "done_when.check_001",
                    "kind": "done_when",
                    "required": True,
                    "text": "The primary user flow works end to end.",
                },
                {
                    "id": "gatekeeper.finish",
                    "kind": "gatekeeper",
                    "required": True,
                    "text": "GateKeeper must cite supporting upstream evidence refs.",
                },
            ],
            "known_evidence_count": 4,
            "known_evidence_ids": ["ev_builder", "ev_contract"],
            "known_evidence_refs": [
                {
                    "id": "ev_builder",
                    "step_id": "builder_step",
                    "role_name": "Builder",
                    "result": "completed",
                    "claim": "Builder supplied output but no proof artifact.",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "no proof artifact",
                    "coverage_target_ids": [],
                    "artifact_refs": [
                        {"label": "proof-file:tests/browser-journey.json", "path": "tests/browser-journey.json"}
                    ],
                },
                {
                    "id": "ev_contract",
                    "step_id": "contract_inspection_step",
                    "role_name": "Contract Inspector",
                    "result": "blocked",
                    "claim": "Inspector blocked the primary journey.",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "result is blocked",
                    "coverage_target_ids": ["done_when.check_001"],
                },
            ],
            "iteration_repair": {
                "active": True,
                "source_step_id": "gatekeeper_step",
                "source_role": "GateKeeper",
                "status": "blocked",
                "summary": "GateKeeper rejected the prior pass.",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                "recommended_next_action": "Produce direct project-owned proof before asking GateKeeper to pass again.",
                "evidence_refs": ["ev_gatekeeper_block"],
                "top_gaps": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "blocked",
                        "source_section": "Done When",
                        "reason": "Evidence reported this target as blocked.",
                        "text": "The primary user flow works end to end.",
                        "evidence_refs": ["ev_gatekeeper_block"],
                    }
                ],
            },
            "context_path": f"{NEXT_STEP_DIR}/step_instruction_context.json",
            "agent_step_view_path": f"{NEXT_STEP_DIR}/agent_step_view.json",
            "step_contract_path": f"{NEXT_STEP_DIR}/step_contract.json",
            "submit_hint": {
                "command": f"loopora agent codex submit --run-id {RUN_ID}",
                "result_file_contract": (
                    "Result file must contain one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; "
                    "replace null placeholders before submit."
                ),
                "result_template_path": f".loopora/agent_outbox/codex/{RUN_ID}__{NEXT_STEP_ID}.result.template.json",
                "result_outbox_dir": ".loopora/agent_outbox/codex",
            },
        },
        "complete": False,
    }
