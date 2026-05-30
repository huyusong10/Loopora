from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from loopora.service_agent_native import AgentNativeStepSubmitRequest
from loopora.service_types import LooporaConflictError
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_common import (
    _assert_loopora_agent_command,
    _assert_loopora_cli_command,
    _assert_cli_handoff_contract_paths,
    _assert_cli_list,
)
from agent_adapter_test_surface import (
    _assert_codex_native_surface_summary,
)


def _assert_agent_run_summary_for_started_run(started: dict) -> None:
    summary = started["agent_run_summary"]
    assert summary["run_id"] == started["run"]["id"]
    assert summary["run_status"] == "awaiting_agent"
    assert summary["started_new_run"] is True
    assert summary["complete"] is False
    assert summary["next_step_id"] == "builder_step"
    assert summary["next_target_agent"] == "loopora-builder"
    _assert_codex_native_surface_summary(summary)

def _assert_agent_run_summary_continuation(
    summary: dict,
    *,
    previous_run_id: str,
    previous_task_verdict_status: str,
    missing_required_check_count: int | None = None,
) -> dict:
    continuation = summary["continuation"]
    assert continuation["active"] is True
    assert continuation["previous_run_id"] == previous_run_id
    assert continuation["previous_task_verdict_status"] == previous_task_verdict_status
    if missing_required_check_count is None:
        assert continuation["missing_required_check_count"] > 0
    else:
        assert continuation["missing_required_check_count"] == missing_required_check_count
    return continuation

def _assert_agent_native_observation_current_step(current_step: dict) -> None:
    assert current_step["step_id"] == "builder_step"
    assert current_step["role"]["name"] == "Focused Builder"
    assert current_step["target_agent"] == "loopora-builder"
    assert current_step["target_agent_config_path"] == ".codex/agents/loopora-builder.toml"
    assert current_step["target_agent_config_absolute_path"].endswith(".codex/agents/loopora-builder.toml")
    assert current_step["target_agent_config_exists"] is False
    assert current_step["role_dispatch"]["target_agent_config_path"] == ".codex/agents/loopora-builder.toml"
    assert current_step["role_dispatch"]["target_agent_config_exists"] is False
    assert current_step["action_policy"]["workspace"] == "workspace_write"
    assert current_step["required_coverage"]["missing_check_count"] == 2
    assert current_step["required_coverage"]["top_gaps"][0]["target_id"] == "done_when.check_001"
    assert current_step["context_path"].endswith("step_instruction_context.json")
    assert current_step["step_contract_path"].endswith("step_contract.json")
    assert "capsule_path" not in current_step
    assert "capsule_absolute_path" not in current_step
    assert current_step["submit_hint"]["result_template_path"].endswith(".result.template.json")
    assert current_step["submit_hint"]["result_file_path"].endswith(".result.json")
    assert current_step["submit_hint"]["result_outbox_dir"].endswith(".loopora/agent_outbox/codex")
    assert current_step["submit_hint"]["result_outbox_absolute_dir"].endswith(".loopora/agent_outbox/codex")
    assert current_step["submit_hint"]["result_file_absolute_path"].endswith(".result.json")
    assert current_step["submit_hint"]["result_file_contract"] == (
        "Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; "
        "replace null placeholders before submit."
    )
    assert isinstance(current_step["known_evidence_count"], int)
    _assert_submit_hint_command_requests_json(current_step["submit_hint"]["command"])
    assert "prompt" not in current_step
    assert "output_schema" not in current_step

def _assert_agent_native_observation_artifacts(service, current_step: dict, started: dict, sample_workdir: Path) -> None:
    step_contract_path = Path(current_step["step_contract_absolute_path"])
    agent_step_view_path = Path(started["next_step"]["agent_step_view_absolute_path"])
    template_path = Path(current_step["submit_hint"]["result_template_absolute_path"])
    assert step_contract_path.exists()
    assert agent_step_view_path.exists()
    assert template_path.exists()
    step_contract = json.loads(step_contract_path.read_text(encoding="utf-8"))
    agent_step_view = json.loads(agent_step_view_path.read_text(encoding="utf-8"))
    assert agent_step_view == step_contract
    _assert_agent_native_observation_step_view(step_contract)
    template = json.loads(template_path.read_text(encoding="utf-8"))
    _assert_agent_native_observation_template(template, step_contract, started)
    with pytest.raises(
        LooporaConflictError,
        match=r"agent-native result does not match output_schema: \$\.attempted expected string, got null",
    ):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                context_id="thread-handoff",
                run_id=started["run"]["id"],
                step_id="builder_step",
                output=template["result"],
                host_dispatch=template["loopora_host_dispatch"],
                entry_source="codex_project_skill",
            )
        )
    assert not Path(step_contract["result_output_path"]).is_absolute()
    assert not (Path(started["run"]["runs_dir"]) / step_contract["result_output_path"]).exists()
    assert f"--workdir {sample_workdir.resolve()}" in step_contract["submit_hint"]["command"]

    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    role_requests = read_jsonl(layout.role_requests_path)
    assert role_requests
    assert role_requests[-1]["step_id"] == "builder_step"
    assert role_requests[-1]["context_path"].endswith("step_instruction_context.json")
    claimed = [event for event in read_jsonl(layout.legacy_events_path) if event["event_type"] == "agent_native_step_claimed"][-1]
    assert claimed["payload"]["target_agent"] == "loopora-builder"
    assert claimed["payload"]["step_contract_path"].endswith("step_contract.json")
    assert "capsule_path" not in claimed["payload"]
    assert claimed["payload"]["result_template_path"].endswith(".result.template.json")

def _assert_agent_native_observation_step_view(step_view: dict) -> None:
    assert step_view["step_id"] == "builder_step"
    assert step_view["entry_source"] == "codex_project_skill"
    assert step_view["role_dispatch"]["target_agent"] == "loopora-builder"
    assert step_view["role_dispatch"]["host_mechanism"] == "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    assert step_view["role_dispatch"]["accepted_native_tools"] == ["spawn_agent"]
    assert step_view["known_evidence_count"] == 0
    assert step_view["known_evidence_ids"] == []
    assert step_view["role_dispatch"]["target_agent_config_absolute_path"].endswith(".codex/agents/loopora-builder.toml")
    assert step_view["role_dispatch"]["target_agent_config_exists"] is False
    _assert_step_view_submit_hint_uses_safe_filled_result_path(step_view["submit_hint"], step_stem="iter000__step00__builder_step")
    assert "prompt" in step_view
    assert "output_schema" in step_view

def _assert_agent_native_observation_template(template: dict, step_view: dict, started: dict) -> None:
    _assert_result_template_dispatch(template, run_id=started["run"]["id"])
    assert template["loopora_result_contract"]["ignored_on_submit"] is True
    assert template["loopora_result_contract"]["result_must_match_output_schema"] is True
    assert template["loopora_result_contract"]["result_is_schema_shaped_scaffold"] is True
    assert template["loopora_result_contract"]["result_scaffold_uses_null_placeholders"] is True
    assert template["loopora_result_contract"]["replace_null_placeholders_before_submit"] is True
    assert template["loopora_result_contract"]["step_id"] == "builder_step"
    assert template["loopora_result_contract"]["role"]["name"] == "Focused Builder"
    assert template["loopora_result_contract"]["action_policy"]["workspace"] == "workspace_write"
    assert template["loopora_result_contract"]["required_coverage"]["missing_check_count"] == 2
    assert template["loopora_result_contract"]["required_coverage"]["top_gaps"][0]["target_id"] == "done_when.check_001"
    assert template["loopora_result_contract"]["result_file_to_write"] == step_view["submit_hint"]["result_file_absolute_path"]
    assert template["loopora_result_contract"]["submit_command"] == step_view["submit_hint"]["command"]
    assert template["loopora_result_contract"]["result_template_path"] == step_view["submit_hint"]["result_template_absolute_path"]
    assert template["loopora_result_contract"]["role_dispatch"]["target_agent"] == "loopora-builder"
    assert template["loopora_result_contract"]["role_dispatch"]["host_mechanism"] == "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    assert template["loopora_result_contract"]["role_dispatch"]["accepted_native_tools"] == ["spawn_agent"]
    assert template["loopora_result_contract"]["role_dispatch"]["inline_allowed"] is False
    _assert_result_template_contract_targets(template)
    assert "known_evidence_ids" in template["loopora_result_contract"]
    assert template["loopora_result_contract"]["evidence_ref_contract"]["must_copy_exact_ids"] is True
    assert template["loopora_result_contract"]["output_schema"]["required"] == step_view["output_schema"]["required"]
    abandoned_schema = template["loopora_result_contract"]["output_schema"]["properties"]["abandoned"]
    assert "deliberate scope limits" in abandoned_schema["description"]
    assert "prompt" not in template["loopora_result_contract"]
    assert template["result"] == {
        "attempted": None,
        "abandoned": None,
        "assumption": None,
        "summary": None,
        "changed_files": [None],
        "proof_files": [None],
        "proof_artifacts": [None],
        "artifact_paths": [None],
    }

def _assert_step_view_submit_hint_uses_safe_filled_result_path(submit_hint: dict, *, step_stem: str = "") -> None:
    assert submit_hint["result_file_path"].endswith(".result.json")
    assert submit_hint["result_file_absolute_path"].endswith(".result.json")
    if step_stem:
        assert step_stem in Path(submit_hint["result_template_path"]).name
        assert step_stem in Path(submit_hint["result_file_path"]).name
    _assert_submit_hint_command_requests_json(submit_hint["command"])

def _assert_result_template_dispatch(template: dict, *, run_id: str) -> None:
    dispatch = template["loopora_host_dispatch"]
    assert dispatch["run_id"] == run_id
    assert dispatch["iter"] == 0
    assert dispatch["step_id"] == "builder_step"
    assert dispatch["step_order"] == 0
    assert dispatch["actual_agent"] == "loopora-builder"
    assert dispatch["inline"] is False

def _assert_result_template_contract_targets(template: dict) -> None:
    result_contract = template["loopora_result_contract"]
    assert "judgment_contract" not in result_contract
    assert result_contract["coverage_target_ids"][0] == "done_when.check_001"
    assert result_contract["coverage_targets"][0] == {
        "id": "done_when.check_001",
        "kind": "done_when",
        "required": True,
        "text": "The primary user flow works end to end.",
    }

def _assert_submit_hint_command_requests_json(command: str) -> None:
    _assert_loopora_agent_command(command, "submit")
    assert ".result.json" in command
    assert "<result-json>" not in command

def _write_agent_native_cli_contract(layout: RunArtifactLayout) -> None:
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "source_bundle": {
                    "id": "bundle_agent",
                    "name": "Agent Native Refund Bundle",
                    "revision": 2,
                    "source_bundle_id": "",
                    "imported_from_path": "/tmp/loopora/bundle.yml",
                },
                "collaboration_summary": "Prefer frozen judgment over lifecycle optimism.",
                "loop_fit_reasons": ["Future Agent rounds keep the same proof bar active."],
                "judgment_tradeoffs": ["Evidence beats fast closure."],
                "execution_strategy": ["Prove the refund path first, then expand after audit evidence is strong."],
                "local_governance": ["GateKeeper treats skipped AGENTS.md checks as Blocking."],
                "role_postures": [{"role_name": "GateKeeper", "archetype": "gatekeeper", "posture_notes": "Fail closed when evidence is weak."}],
                "completion_mode": "gatekeeper",
                "workflow": {
                    "preset": "quality_gate",
                    "collaboration_intent": "Linear review must feed GateKeeper before closure.",
                },
                "compiled_spec": {
                    "check_mode": "specified",
                    "checks": [{"id": "check_001"}, {"id": "check_002"}],
                    "coverage_targets": [
                        {"id": "done_when.check_001", "required": True},
                        {"id": "gatekeeper.finish", "required": True},
                    ],
                    "success_surface": ["Support admin can approve a refund."],
                    "fake_done_states": ["CSV export without permission audit is fake done."],
                    "evidence_preferences": ["Require browser journey and audit log command evidence."],
                    "residual_risk": "No residual risk is acceptable.",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

def _assert_agent_native_cli_output(
    stdout: str,
    layout: RunArtifactLayout,
    *,
    adapter: str = "codex",
    loopora_home: Path | str | None = None,
) -> None:
    assert "run_start: started_new_agent_runner_run" in stdout
    assert f"run_contract_path: {layout.run_contract_path}" in stdout
    assert "source_plan: Agent Native Refund Bundle (bundle_agent, rev 2)" in stdout
    assert "source_plan_path: /tmp/loopora/bundle.yml" in stdout
    assert 'source_plan: {"id":' not in stdout
    assert "judgment_contract_summary: Prefer frozen judgment over lifecycle optimism." in stdout
    assert "check_mode: specified" in stdout
    assert "completion_mode: gatekeeper" in stdout
    assert "strategy_preset: quality_gate" in stdout
    assert "strategy_collaboration_intent: Linear review must feed GateKeeper before closure." in stdout
    assert "workflow_preset:" not in stdout
    assert "workflow_collaboration_intent:" not in stdout
    assert "check_count: 2" in stdout
    _assert_cli_list(stdout, "coverage_targets", "done_when.check_001 (required)", "gatekeeper.finish (required)")
    _assert_cli_list(stdout, "loop_fit_reasons", "Future Agent rounds keep the same proof bar active.")
    _assert_cli_list(stdout, "judgment_tradeoffs", "Evidence beats fast closure.")
    _assert_cli_list(
        stdout,
        "execution_strategy",
        "Prove the refund path first, then expand after audit evidence is strong.",
    )
    _assert_cli_list(stdout, "local_governance", "GateKeeper treats skipped AGENTS.md checks as Blocking.")
    _assert_cli_list(stdout, "role_postures", "GateKeeper: Fail closed when evidence is weak.")
    _assert_cli_list(stdout, "success_surface", "Support admin can approve a refund.")
    _assert_cli_list(stdout, "fake_done_states", "CSV export without permission audit is fake done.")
    _assert_cli_list(stdout, "evidence_preferences", "Require browser journey and audit log command evidence.")
    assert "residual_risk: No residual risk is acceptable." in stdout
    assert "run_url: /runs/run_agent" in stdout
    assert "next_step_id: builder_step" in stdout
    assert "next_target_agent: loopora-builder" in stdout
    assert "next_target_agent_config:" in stdout
    assert ".codex/agents/loopora-builder.toml" in stdout
    assert "next_target_agent_config_exists: false" in stdout
    _assert_cli_dispatch_unavailable(stdout, adapter=adapter, loopora_home=loopora_home)
    assert "continuation_previous_run: run_previous" in stdout
    assert "continuation_task_verdict: insufficient_evidence" in stdout
    assert "continuation_required_coverage: 1 covered / 2 missing" in stdout
    assert "continuation_next_focus:" in stdout
    assert "- done_when.check_001: Support admin path still lacks direct proof." in stdout
    assert "next_action_policy: workspace_write" in stdout
    assert "required_coverage: pending; required checks 0 covered / 2 missing" in stdout
    assert "top_coverage_gaps:" in stdout
    assert "- done_when.check_001: Support admin can approve a refund." in stdout
    assert "next_context_path:" in stdout
    assert "step_instruction_context.json" in stdout
    assert "known_evidence_count: 3" in stdout
    assert "known_evidence_ids:" not in stdout
    assert "result_template_contract: Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit." in stdout
    assert "result_template_fill: open the template, replace null placeholders in result, keep loopora_host_dispatch, then submit the filled copy" in stdout
    _assert_cli_handoff_contract_paths(
        stdout,
        step_contract_fragment="step_contract.json",
        template_fragment="run_agent__builder_step.result.template.json",
        outbox_fragment=".loopora/agent_outbox/codex",
    )
    assert "submit_hint: loopora agent codex submit --run-id run_agent --step-id builder_step" in stdout

def _assert_agent_run_json_summary_reports_missing_dispatch(
    payload: dict,
    *,
    adapter: str,
    workdir: Path,
    loopora_home: Path | str | None = None,
) -> None:
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_run", summary_key="agent_run_summary")
    assert summary["next_target_agent"] == "loopora-builder"
    assert summary["next_target_agent_config"].endswith(".codex/agents/loopora-builder.toml")
    assert summary["next_target_agent_config_exists"] is False
    assert "dispatch_next" not in summary
    assert summary["next_context_path"].endswith("step_instruction_context.json")
    assert summary["next_step_contract_path"].endswith("step_contract.json")
    assert summary["next_result_template"].endswith("run_agent__builder_step.result.template.json")
    assert summary["next_submit_command"] == "loopora agent codex submit --run-id run_agent --step-id builder_step"
    next_step_summary = summary["next_step"]
    assert next_step_summary["step_id"] == "builder_step"
    assert next_step_summary["target_agent"] == "loopora-builder"
    assert "dispatch_next" not in next_step_summary
    assert next_step_summary["context_path"].endswith("step_instruction_context.json")
    assert next_step_summary["step_contract_path"].endswith("step_contract.json")
    assert next_step_summary["result_template"].endswith("run_agent__builder_step.result.template.json")
    assert next_step_summary["result_template_contract"].startswith("Write one wrapper JSON object")
    assert "replace null placeholders" in next_step_summary["result_template_fill"]
    assert next_step_summary["result_outbox_dir"].endswith(".loopora/agent_outbox/codex")
    assert next_step_summary["submit_command"] == "loopora agent codex submit --run-id run_agent --step-id builder_step"
    assert next_step_summary["top_coverage_gaps"][0]["target_id"] == "done_when.check_001"
    assert next_step_summary["top_coverage_gaps"][0]["text"] == "Support admin can approve a refund."
    assert next_step_summary["dispatch_unavailable"]["reason"] == "target_agent_config_missing"
    _assert_loopora_cli_command(
        next_step_summary["dispatch_unavailable"]["check_command"],
        f"loopora agent {adapter} check --workdir {workdir}",
        loopora_home=loopora_home,
    )
    _assert_loopora_cli_command(
        next_step_summary["dispatch_unavailable"]["repair_command"],
        f"loopora init {adapter} --workdir {workdir}",
        loopora_home=loopora_home,
    )
    assert summary["dispatch_unavailable"]["reason"] == "target_agent_config_missing"
    assert summary["dispatch_unavailable"]["target_agent"] == "loopora-builder"
    _assert_loopora_cli_command(
        summary["dispatch_unavailable"]["check_command"],
        f"loopora agent {adapter} check --workdir {workdir}",
        loopora_home=loopora_home,
    )
    _assert_loopora_cli_command(
        summary["dispatch_unavailable"]["repair_command"],
        f"loopora init {adapter} --workdir {workdir}",
        loopora_home=loopora_home,
    )
    assert "do not submit inline role work" in summary["dispatch_unavailable"]["next"]

def _assert_cli_dispatch_unavailable(
    stdout: str,
    *,
    adapter: str,
    loopora_home: Path | str | None = None,
) -> None:
    assert "dispatch_unavailable: loopora-builder config is missing;" in stdout
    if loopora_home is not None:
        assert f"LOOPORA_HOME={shlex.quote(str(loopora_home))} " in stdout
    assert f'loopora agent {adapter} check --workdir "$PWD"' in stdout
    assert f'loopora init {adapter} --workdir "$PWD"' in stdout
    assert "dispatch_next: invoke loopora-builder" not in stdout
