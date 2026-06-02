from __future__ import annotations

from pathlib import Path

from step_instruction_context_test_support import build_step_context, builder_role


def test_step_instruction_context_normalizes_judgment_contract_field_types(tmp_path: Path) -> None:
    step_context = build_step_context(
        tmp_path,
        layout_name="run_prompt_contract_types",
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
        role=builder_role(),
        step={"id": "builder_step", "role_id": "builder"},
        step_order=0,
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
