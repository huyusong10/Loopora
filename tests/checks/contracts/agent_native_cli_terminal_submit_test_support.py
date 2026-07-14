from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    Path,
    RunArtifactLayout,
    _assert_agent_native_handoff_surface_plain,
    _assert_cli_list,
    _assert_codex_native_surface_summary,
    assert_agent_v3_envelope,
    cli,
    json,
)

assert_cli_list = _assert_cli_list
assert_agent_native_handoff_surface_plain = _assert_agent_native_handoff_surface_plain
assert_codex_native_surface_summary = _assert_codex_native_surface_summary

TERMINAL_RUN_ID = "run_terminal"
TERMINAL_STEP_ID = "gatekeeper_step"
TERMINAL_TARGET_AGENT = "loopora-gatekeeper"
TERMINAL_EVIDENCE_REF = f"ev_000_03_{TERMINAL_STEP_ID}"
TERMINAL_TASK_VERDICT_STATUS = "insufficient_evidence"


def terminal_plain_submit_fixture(tmp_path: Path) -> dict:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / TERMINAL_RUN_ID)
    layout.initialize()
    _write_terminal_submit_run_contract(layout)
    return {
        "workdir": workdir,
        "layout": layout,
        "result_file": write_terminal_submit_result_file(tmp_path),
    }


def terminal_json_submit_fixture(tmp_path: Path) -> dict:
    workdir = tmp_path / "project"
    workdir.mkdir()
    return {
        "workdir": workdir,
        "result_file": write_terminal_submit_result_file(tmp_path),
    }


def write_terminal_submit_result_file(tmp_path: Path) -> Path:
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": TERMINAL_RUN_ID,
                    "step_id": TERMINAL_STEP_ID,
                    "target_agent": TERMINAL_TARGET_AGENT,
                    "actual_agent": TERMINAL_TARGET_AGENT,
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"passed": True},
            }
        ),
        encoding="utf-8",
    )
    return result_file


def invoke_terminal_submit(workdir: Path, result_file: Path, *, json_output: bool = False):
    args = [
        "agent",
        "codex",
        "submit",
        "--workdir",
        str(workdir),
        "--run-id",
        TERMINAL_RUN_ID,
        "--step-id",
        TERMINAL_STEP_ID,
        "--result-file",
        str(result_file),
        "--entry-source",
        "codex_project_skill",
        "--no-web",
    ]
    if json_output:
        args.append("--json")
    return CliRunner().invoke(cli.app, args)


def install_terminal_plain_submit_service(monkeypatch, layout: RunArtifactLayout) -> None:
    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": TERMINAL_RUN_ID,
                    "status": "succeeded",
                    "run_status": "succeeded",
                    "runs_dir": str(layout.run_dir),
                    "task_verdict": {
                        "status": TERMINAL_TASK_VERDICT_STATUS,
                        "source": "gatekeeper",
                        "summary": "Required coverage still lacks direct evidence.",
                    },
                },
                "run_path": f"/runs/{TERMINAL_RUN_ID}",
                "next_step": None,
                "complete": True,
                "submitted_step": {
                    "step_id": TERMINAL_STEP_ID,
                    "status": "blocked",
                    "summary": "GateKeeper submitted terminal evidence with an insufficient-evidence verdict.",
                    "evidence_refs": [TERMINAL_EVIDENCE_REF],
                    "blocking_items": ["gatekeeper_pass_has_unmanaged_residual_risk"],
                    "recommended_next_action": "Move the residual risk to a blocking issue or name the owner and follow-up.",
                    "handoff_absolute_path": str(
                        layout.run_dir / "iterations" / "iter_000" / "steps" / f"03__{TERMINAL_STEP_ID}" / "handoff.json"
                    ),
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)


def install_terminal_json_submit_service(monkeypatch, workdir: Path) -> None:
    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": TERMINAL_RUN_ID,
                    "status": "succeeded",
                    "run_status": "succeeded",
                    "task_verdict": {
                        "status": TERMINAL_TASK_VERDICT_STATUS,
                        "source": "gatekeeper",
                        "summary": "Required coverage still lacks direct evidence.",
                    },
                },
                "run_path": f"/runs/{TERMINAL_RUN_ID}",
                "next_step": None,
                "complete": True,
                "submitted_step": {
                    "step_id": TERMINAL_STEP_ID,
                    "status": "passed",
                    "summary": "GateKeeper submitted a passing role decision while Core kept the task verdict insufficient.",
                    "evidence_refs": [TERMINAL_EVIDENCE_REF],
                    "blocking_items": ["missing_direct_terminal_proof"],
                    "recommended_next_action": "Continue evidence in a new run before passing.",
                    "handoff_absolute_path": str(workdir / ".loopora" / "runs" / TERMINAL_RUN_ID / "handoff.json"),
                },
                "task_next_action": {
                    "kind": "continue_evidence",
                    "reason": "run_lifecycle_complete_task_not_proven",
                    "task_verdict_status": TERMINAL_TASK_VERDICT_STATUS,
                    "next_loop_command": "/loopora-run",
                    "guidance": "Run lifecycle is complete, but the task is not proven.",
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)


def terminal_submit_summary(stdout: str) -> dict:
    payload = json.loads(stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit", summary_key="agent_submit_summary", status="complete"
    )
    return summary


def _write_terminal_submit_run_contract(layout: RunArtifactLayout) -> None:
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep the evidence standard frozen through terminal submit.",
                "loop_fit_reasons": ["Later role outputs can drift without the frozen contract."],
                "judgment_tradeoffs": ["Direct proof beats narrative confidence."],
                "execution_strategy": ["Collect audit evidence before terminal closure."],
                "local_governance": ["Inspector verifies tests/ evidence before terminal closure."],
                "role_postures": [
                    {
                        "role_name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "posture_notes": "Separate run success from task proof.",
                    }
                ],
                "success_surface": ["Checkout instrumentation records the buyer action."],
                "fake_done_states": ["A story without audit evidence is fake done."],
                "evidence_preferences": ["Audit log command output is required."],
                "residual_risk": "Manual billing export remains a Support-owned follow-up.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
