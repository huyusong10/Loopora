from __future__ import annotations

from loopora.agent_native_step_view_context import agent_native_step_view_judgment_contract
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepClaimRequest,
    Path,
    RunArtifactLayout,
    alignment_bundle_yaml,
    json,
)

SNAPSHOT_CONTRACT_FIELDS = ("loop_fit_reasons", "execution_strategy", "local_governance", "role_postures")
STEP_CONTEXT_CONTRACT_FIELDS = (
    "collaboration_summary",
    "loop_fit_reasons",
    "judgment_tradeoffs",
    "execution_strategy",
    "local_governance",
    "coverage_targets",
    "success_surface",
    "fake_done_states",
    "evidence_preferences",
    "residual_risk",
    "completion_mode",
)
REFRESH_FALLBACK_FIELDS = (
    "judgment_tradeoffs",
    "execution_strategy",
    "local_governance",
    "success_surface",
    "fake_done_states",
    "evidence_preferences",
    "residual_risk",
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
    for field in SNAPSHOT_CONTRACT_FIELDS:
        assert snapshot_contract[field] == started["judgment_contract"][field]
    assert step_judgment_contract["collaboration_summary"].startswith(
        started["judgment_contract"]["collaboration_summary"].removesuffix("…")
    )
    assert step_judgment_contract["contract_path"] == context_contract["path"]
    for field in STEP_CONTEXT_CONTRACT_FIELDS:
        assert step_judgment_contract[field] == context_contract[field]
    assert step_judgment_contract["role_postures"]
    assert context_contract["role_postures"]
    assert any("Keep implementation narrow" in item for item in step_judgment_contract["role_postures"])
    assert any(item["posture_notes"].startswith("Keep implementation narrow") for item in context_contract["role_postures"])

    state_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["agent_step_view"].pop("judgment_contract", None)
    for field in REFRESH_FALLBACK_FIELDS:
        state["active_step"]["step_instruction_context"]["contract"][field] = "" if field == "residual_risk" else []
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    claimed = service.claim_agent_native_step(
        AgentNativeStepClaimRequest(adapter="codex", workdir=sample_workdir, run_id=started["run"]["id"])
    )
    assert claimed["next_step"]["judgment_contract"]["contract_path"] == claimed["judgment_contract"]["contract_path"]
    for field in REFRESH_FALLBACK_FIELDS:
        assert claimed["next_step"]["judgment_contract"][field] == started["judgment_contract"][field]
    assert claimed["next_step"]["judgment_contract"]["coverage_targets"] == context_contract["coverage_targets"]
    persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted_state["active_step"]["agent_step_view"]["judgment_contract"] == claimed["next_step"]["judgment_contract"]


def test_agent_native_step_view_judgment_contract_falls_back_when_context_is_trimmed(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "runs" / "run_step_view_fallback")
    layout.initialize()
    frozen_contract = {
        "collaboration_summary": "Keep frozen judgment stronger than stale context.",
        "loop_fit_reasons": ["Later role handoffs need the same proof bar."],
        "judgment_tradeoffs": ["Evidence beats fast closure."],
        "execution_strategy": ["Prove inherited governance before polishing."],
        "local_governance": ["GateKeeper treats skipped AGENTS.md checks as Blocking."],
        "success_surface": ["Admin can complete the audited action."],
        "fake_done_states": ["Summary-only evidence is fake done."],
        "evidence_preferences": ["Require command output and audit artifacts."],
        "residual_risk": "No unmanaged residual risk is acceptable.",
    }
    layout.run_contract_path.write_text(json.dumps(frozen_contract, ensure_ascii=False), encoding="utf-8")

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

    for field in REFRESH_FALLBACK_FIELDS:
        assert contract[field] == frozen_contract[field]
