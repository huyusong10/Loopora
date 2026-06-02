from __future__ import annotations

from web_timeline_projection_test_support import formatted_timeline_event


def test_timeline_run_result_accepted_projects_judgment_contract_detail() -> None:
    accepted_with_judgment = formatted_timeline_event(
        "run_result_accepted",
        {
            "status": "succeeded",
            "task_verdict_status": "passed",
            "run_contract_path": "contract/run_contract.json",
            "judgment_contract_summary": "Prefer proof before closure.",
            "loop_fit_reasons": ["Future rounds keep proof alive."],
            "execution_strategy": ["Prove the contract before polish."],
            "local_governance": ["GateKeeper treats skipped AGENTS.md obligations as Blocking."],
            "role_postures": ["GateKeeper: Fail closed when evidence is weak."],
            "judgment_tradeoffs": ["Proof beats polish."],
            "success_surface": ["Support admin can approve a refund."],
            "fake_done_states": ["CSV export without permission audit is fake done."],
            "evidence_preferences": ["Use browser journey and audit log evidence."],
            "residual_risk": "No residual risk is acceptable.",
        },
    )

    assert accepted_with_judgment["detail"] == (
        "status=succeeded, task_verdict_status=passed, judgment=Prefer proof before closure., "
        "loop_fit=Future rounds keep proof alive., strategy=Prove the contract before polish., "
        "local_governance=GateKeeper treats skipped AGENTS.md obligations as Blocking., "
        "role_posture=GateKeeper: Fail closed when evidence is weak., "
        "tradeoff=Proof beats polish., success=Support admin can approve a refund., "
        "fake_done=CSV export without permission audit is fake done., "
        "evidence=Use browser journey and audit log evidence., residual_risk=No residual risk is acceptable."
    )
