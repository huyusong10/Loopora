from __future__ import annotations

from pathlib import Path

import yaml

from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_agent_native import AgentNativeStepSubmitRequest
from agent_adapter_test_common import (
    _assert_recovery_choice_has_copyable_commands,
    _assert_non_runnable_recovery_choice_routes_to_plan,
    _assert_recovery_choice_has_status_hint,
)


def _assert_terminal_recovery_choice(choice: dict, *, expected: dict) -> None:
    assert choice["action"] == expected["action"]
    assert choice["choice_status"] == expected["status"]
    assert expected["hint_text"] in choice["choice_hint_en"]
    assert choice["linked_run_id"] == expected["previous_run_id"]
    assert choice["linked_run_status"] == "succeeded"
    assert choice["task_verdict_status"] == expected["verdict"]
    assert expected["summary_text"] in choice["task_verdict_summary"]
    assert choice["label_en"].startswith(expected["label_prefix"])

def _assert_ambiguous_agent_recovery_choices(
    ambiguous: dict,
    *,
    generated_a: dict,
    generated_b: dict,
    started_a: dict,
) -> dict:
    assert ambiguous["action"] == "choose_recoverable_context"
    assert ambiguous["confidence"] == "ambiguous"
    assert ambiguous["requires_user_choice"] is True
    assert ambiguous["choice_count"] == len(ambiguous["choices"])
    assert ambiguous["runnable_choice_count"] >= 1
    assert "runnable context" in ambiguous["selection_hint"]
    choices_by_session = {choice["alignment_session_id"]: choice for choice in ambiguous["choices"]}
    assert choices_by_session[generated_a["session"]["id"]]["action"] == "resume_active_run"
    assert choices_by_session[generated_a["session"]["id"]]["linked_run_id"] == started_a["run"]["id"]
    _assert_recovery_choice_has_status_hint(choices_by_session[generated_a["session"]["id"]], expected_status="active_run")
    assert choices_by_session[generated_b["session"]["id"]]["linked_run_id"] == ""
    if choices_by_session[generated_b["session"]["id"]]["choice_status"] in {"not_ready", "needs_repair"}:
        _assert_non_runnable_recovery_choice_routes_to_plan(
            choices_by_session[generated_b["session"]["id"]],
            expected_status=choices_by_session[generated_b["session"]["id"]]["choice_status"],
        )
    else:
        _assert_recovery_choice_has_copyable_commands(choices_by_session[generated_b["session"]["id"]])
        assert choices_by_session[generated_b["session"]["id"]]["choice_status"] == "ready_preview"
    assert choices_by_session[generated_b["session"]["id"]]["choice_hint_en"]
    return choices_by_session

def _alignment_bundle_yaml_with_gatekeeper_control(
    workdir: Path,
    *,
    after: str = "0s",
    signal: str = "gatekeeper_rejected",
    control_id: str = "gatekeeper_repair",
    trigger_window: int | None = None,
) -> str:
    payload = yaml.safe_load(alignment_bundle_yaml(str(workdir.resolve())))
    if trigger_window is not None:
        payload["loop"]["trigger_window"] = trigger_window
    payload["role_definitions"].append(
        {
            "key": "repair-guide",
            "name": "Repair Guide",
            "description": "Turns a rejected verdict into a narrow repair direction.",
            "archetype": "guide",
            "prompt_ref": "guide.md",
            "prompt_markdown": (
                "---\n"
                "version: 1\n"
                "archetype: guide\n"
                "---\n\n"
                "Read the rejected GateKeeper verdict and provide one narrow repair direction without changing the workspace."
            ),
            "posture_notes": "Prefer the smallest evidence-producing repair over broad re-planning.",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_cli": "",
            "command_args_text": "",
            "model": "",
            "reasoning_effort": "",
        }
    )
    payload["workflow"]["roles"].append({"id": "repair_guide", "role_definition_key": "repair-guide"})
    payload["workflow"]["controls"] = [
        {
            "id": control_id,
            "when": {"signal": signal, "after": after},
            "call": {"role_id": "repair_guide"},
            "mode": "repair_guidance",
            "max_fires_per_run": 1,
        }
    ]
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

def _alignment_bundle_yaml_with_peer_visible_parallel_review_inputs(workdir: Path) -> str:
    payload = yaml.safe_load(alignment_bundle_yaml(str(workdir.resolve())))
    for step in payload["workflow"]["steps"]:
        if step.get("id") in {"contract_inspection_step", "evidence_inspection_step"}:
            step["parallel_group"] = "inspection_pack"
            step["inputs"] = {
                "handoffs_from": ["builder_step", "contract_inspection_step"],
                "evidence_query": {"archetypes": ["builder", "inspector"], "limit": 12},
                "iteration_memory": "summary_only",
            }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

def _agent_native_step_output(step: dict) -> dict:
    step_id = str(step["step_id"])
    role = step.get("role") if isinstance(step.get("role"), dict) else {}
    archetype = str(role.get("archetype") or "")
    if archetype == "guide":
        return {
            "created_at_iter": int(step.get("iter") or 0),
            "mode": "repair_guidance",
            "consumed": False,
            "analysis": {
                "stagnation_pattern": "gatekeeper_rejected",
                "recommended_shift": "Add direct evidence for the rejected Done When target.",
                "risk_note": "GateKeeper rejected the current evidence set.",
            },
            "seed_question": "Which missing proof can Builder produce next?",
            "meta_note": "Agent-native workflow control fired.",
        }
    if archetype == "inspector" or "inspection" in step_id:
        return {
            "execution_summary": {"total_checks": 1, "passed": 1, "failed": 0, "errored": 0, "total_duration_ms": 1},
            "check_results": [
                {
                    "id": "agent_native_path",
                    "title": "Agent-native path",
                    "status": "passed",
                    "notes": "The host Agent submitted structured inspection evidence through Loopora Core.",
                }
            ],
            "dynamic_checks": [],
            "tester_observations": "The Agent-native adapter path produced structured inspection evidence.",
            "coverage_results": [],
        }
    if archetype == "gatekeeper" or "gatekeeper" in step_id:
        evidence_refs = [
            str(item)
            for item in list(step.get("known_evidence_ids") or [])
            if str(item).strip() and "gatekeeper" not in str(item)
        ]
        return {
            "passed": True,
            "decision_summary": "Agent-native adapter path passed with inspector evidence.",
            "feedback_to_builder": "",
            "feedback_to_generator": "",
            "blocking_issues": [],
            "metrics": [{"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True}],
            "metric_scores": {
                "check_pass_rate": {"value": 1.0, "threshold": 1.0, "passed": True},
                "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
            },
            "hard_constraint_violations": [],
            "failed_check_ids": [],
            "priority_failures": [],
            "composite_score": 1.0,
            "evidence_refs": evidence_refs[-4:],
            "evidence_claims": ["The inspector evidence confirms the host Agent submitted a structured result."],
            "residual_risks": [],
            "coverage_results": [],
        }
    return {
        "attempted": "Prepared the workspace under the Loopora Agent-native capsule.",
        "abandoned": "",
        "assumption": "The unit test simulates host-native role execution without launching a nested Agent CLI.",
        "summary": "Builder produced a structured handoff for downstream inspection.",
        "changed_files": [],
        "proof_files": [],
        "proof_artifacts": [],
        "artifact_paths": [],
    }

def _agent_native_rejected_gatekeeper_output(step: dict) -> dict:
    output = _agent_native_step_output(step)
    output.update(
        {
            "passed": False,
            "decision_summary": "The task still lacks required evidence.",
            "feedback_to_builder": "Produce direct proof for the primary user flow.",
            "feedback_to_generator": "Produce direct proof for the primary user flow.",
            "blocking_issues": ["missing_primary_flow_evidence"],
            "composite_score": 0.42,
            "metrics": [{"name": "quality_score", "value": 0.42, "threshold": 0.9, "passed": False}],
            "evidence_claims": [],
        }
    )
    return output

def _drive_agent_native_until_archetype(service, result: dict, *, adapter: str, workdir: Path, archetype: str) -> dict:
    while True:
        step = result["next_step"]
        if step["role"]["archetype"] == archetype:
            return result
        result = service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter=adapter,
                workdir=workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=_agent_native_host_dispatch(adapter, step),
                entry_source=f"{adapter}_project_skill" if adapter != "opencode" else "opencode_project_command",
            )
        )

def _agent_native_host_dispatch(adapter: str, step: dict) -> dict:
    role_dispatch = step.get("role_dispatch") if isinstance(step.get("role_dispatch"), dict) else {}
    target_agent = str(role_dispatch.get("target_agent") or "")
    return {
        "schema_version": 1,
        "adapter": adapter,
        "run_id": str(step["run_id"]),
        "iter": int(step.get("iter") or 0),
        "step_id": str(step["step_id"]),
        "step_order": int(step.get("step_order") or 0),
        "target_agent": target_agent,
        "actual_agent": target_agent,
        "dispatch_mode": "host_subagent",
        "inline": False,
        "attestation": "The test simulates host-native role agent dispatch without launching a nested Agent CLI.",
    }

def _drive_agent_native_run_to_success(service, *, adapter: str, started: dict, workdir: Path, context_id: str = "") -> dict:
    result = started
    seen_steps = []
    while not result.get("complete"):
        step = result.get("next_step")
        assert isinstance(step, dict)
        step_id = str(step["step_id"])
        role = step.get("role") if isinstance(step.get("role"), dict) else {}
        role_dispatch = step.get("role_dispatch") if isinstance(step.get("role_dispatch"), dict) else {}
        assert role_dispatch.get("required") is True
        assert role_dispatch.get("inline_allowed") is False
        assert role_dispatch.get("target_agent")
        assert role_dispatch.get("host_mechanism")
        assert role_dispatch.get("accepted_native_tools")
        assert role_dispatch.get("target_agent_config_path")
        assert role_dispatch.get("target_agent_config_absolute_path")
        if role.get("archetype") == "gatekeeper":
            evidence_rule_ids = {
                str(item.get("id"))
                for item in list(step.get("evidence_rules") or [])
                if isinstance(item, dict)
            }
            assert "evidence_refs.must_be_exact_known_ids" in evidence_rule_ids
            assert "gatekeeper.pass_requires_supporting_upstream_evidence" in evidence_rule_ids
            assert "gatekeeper.finish_coverage_is_core_derived" in evidence_rule_ids
            assert step.get("evidence_ref_contract", {}).get("unknown_ids_are_blocking") is True
        seen_steps.append(step_id)
        result = service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                run_id=str(step["run_id"]),
                step_id=step_id,
                output=_agent_native_step_output(step),
                host_dispatch=_agent_native_host_dispatch(adapter, step),
                entry_source=f"{adapter}_project_skill" if adapter != "opencode" else "opencode_project_command",
            )
        )
    assert seen_steps[0] == "builder_step"
    assert any("gatekeeper" in item for item in seen_steps)
    assert result["run"]["status"] == "succeeded"
    assert result["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    return result
