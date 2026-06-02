from __future__ import annotations

from pathlib import Path

from run_contract_snapshot_test_support import build_contract_snapshot


def test_run_contract_tradeoffs_include_role_prompt_files(tmp_path: Path) -> None:
    contract = build_contract_snapshot(
        tmp_path,
        "run_prompt_tradeoffs",
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
        collaboration_summary="Future iterations stay anchored to the contract as new evidence appears.",
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
    contract = build_contract_snapshot(
        tmp_path,
        "run_prompt_role_posture",
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
    )

    assert contract["role_postures"] == [
        {
            "role_id": "contract_inspector",
            "role_name": "Contract Inspector",
            "archetype": "inspector",
            "posture_notes": "Inspect the Builder handoff against fake-done risk before GateKeeper closes.",
        }
    ]
