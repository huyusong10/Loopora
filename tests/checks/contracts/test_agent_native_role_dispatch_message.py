from __future__ import annotations

from pathlib import Path

from loopora.agent_native_next_step_summary import agent_next_step_summary


def test_role_dispatch_message_prefers_workdir_relative_paths(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    context_path = workdir / ".loopora" / "runs" / "run_1" / "iterations" / "iter_000" / "steps" / "00__builder_step" / "step_instruction_context.json"
    step_contract_path = context_path.with_name("step_contract.json")
    result_template = workdir / ".loopora" / "agent_outbox" / "claude" / "run_1__builder_step.result.template.json"
    next_step = {
        "adapter": "claude",
        "step_id": "builder_step",
        "role": {"name": "Builder"},
        "role_dispatch": {"target_agent": "loopora-builder"},
        "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
        "coverage_target_ids": ["done_when.check_001", "gatekeeper.finish"],
        "context_absolute_path": str(context_path),
        "step_contract_absolute_path": str(step_contract_path),
        "submit_hint": {
            "result_template_absolute_path": str(result_template),
        },
    }

    summary = agent_next_step_summary(next_step, adapter="claude", workdir=str(workdir), compact=True)

    message = summary["role_dispatch_message"]
    assert f"context_path={context_path.relative_to(workdir)}" in message
    assert f"step_contract_path={step_contract_path.relative_to(workdir)}" in message
    assert f"result_template={result_template.relative_to(workdir)}" in message
    assert str(workdir) not in message
    assert "Open local paths" in message
    assert "Use this exact string as the whole Agent/Task prompt" in message
    assert "prepend `You are running as`" in message
    assert "append `Do the following`" in message
    assert "direct .loopora/agent_artifacts" in message
    assert "no /tmp staging" in message
    assert "wc/count-only probes" in message


def test_role_dispatch_message_keeps_core_paths_before_later_anchors(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    run_id = "run_20260604211846_3548c237"
    context_path = (
        workdir
        / ".loopora"
        / "runs"
        / run_id
        / "iterations"
        / "iter_000"
        / "steps"
        / "03__gatekeeper_step"
        / "step_instruction_context.json"
    )
    step_contract_path = context_path.with_name("step_contract.json")
    result_template = (
        workdir
        / ".loopora"
        / "agent_outbox"
        / "claude"
        / f"{run_id}__iter000__step03__gatekeeper_step.result.template.json"
    )
    coverage_target_ids = [
        "done_when.check_001",
        "done_when.check_002",
        "success_surface.surface_001",
        "fake_done.risk_001",
        "fake_done.risk_002",
        "evidence_preference.pref_001",
        "evidence_preference.pref_002",
        "gatekeeper.finish",
    ]
    next_step = {
        "adapter": "claude",
        "step_id": "gatekeeper_step",
        "role": {"name": "Conservative GateKeeper"},
        "role_dispatch": {"target_agent": "loopora-gatekeeper"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": True},
        "known_evidence_ids": [
            "ev_000_00_builder_step",
            "ev_000_01_contract_inspection_step",
            "ev_000_02_evidence_inspection_step",
        ],
        "coverage_target_ids": coverage_target_ids,
        "context_absolute_path": str(context_path),
        "step_contract_absolute_path": str(step_contract_path),
        "required_coverage": {
            "status": "partial",
            "covered_check_count": 2,
            "missing_check_count": 0,
            "target_count": 8,
            "covered_target_count": 6,
            "weak_target_count": 1,
            "missing_target_count": 1,
        },
        "submit_hint": {
            "result_template_absolute_path": str(result_template),
        },
    }

    summary = agent_next_step_summary(next_step, adapter="claude", workdir=str(workdir), compact=True)

    message = summary["role_dispatch_message"]
    context_anchor = f"context_path={context_path.relative_to(workdir)}"
    step_contract_anchor = f"step_contract_path={step_contract_path.relative_to(workdir)}"
    result_template_anchor = f"result_template={result_template.relative_to(workdir)}"
    assert len(message) <= 1000
    assert context_anchor in message
    assert step_contract_anchor in message
    assert result_template_anchor in message
    assert ".result.templat…" not in message
    assert "known_evidence_ids=ev_000_00_builder_step" in message
    assert "coverage_target_ids=done_when.check_001" in message
    assert "(+" in message
    assert "omitted" in message
    assert "GateKeeper evidence reuse rule" in message
    assert "do not rerun same successful command" in message
    assert "proof detours" in message
    assert str(workdir) not in message
    assert message.index(context_anchor) < message.index("action_policy=read_only, can_block, can_finish_run")
    assert message.index(result_template_anchor) < message.index("coverage_target_ids=")
