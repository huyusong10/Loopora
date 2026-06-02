from __future__ import annotations

from pathlib import Path

from loopora.context_flow import STEP_INSTRUCTION_CONTEXT_SCHEMA

from step_instruction_context_test_support import build_step_context


def test_step_instruction_context_preserves_judgment_contract_fields(tmp_path: Path) -> None:
    step_context = build_step_context(tmp_path, run_contract=_judgment_run_contract())

    assert step_context["contract"]["collaboration_summary"] == "Prefer evidence before closure."
    assert step_context["contract"]["loop_fit_reasons"] == ["Future iterations keep the proof target visible."]
    assert step_context["contract"]["judgment_tradeoffs"] == ["Evidence before polish."]
    assert step_context["contract"]["execution_strategy"] == [
        "Prove the smallest path first, then expand only after evidence is strong."
    ]
    assert step_context["contract"]["local_governance"] == [
        "GateKeeper treats skipped AGENTS.md responsibilities as Blocking."
    ]
    assert step_context["contract"]["role_postures"] == [
        {
            "role_id": "gatekeeper",
            "role_name": "GateKeeper",
            "archetype": "gatekeeper",
            "posture_notes": "Fail closed when evidence is weak.",
        }
    ]


def test_step_instruction_context_schema_requires_judgment_contract_fields() -> None:
    contract_schema = STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]

    for key in ("loop_fit_reasons", "judgment_tradeoffs", "execution_strategy", "local_governance", "role_postures"):
        assert key in contract_schema["required"]
        assert contract_schema["properties"][key]["type"] == "array"


def _judgment_run_contract() -> dict:
    return {
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
    }
