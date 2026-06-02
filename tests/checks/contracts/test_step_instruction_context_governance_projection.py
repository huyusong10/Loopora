from __future__ import annotations

from pathlib import Path

from step_instruction_context_test_support import build_step_context


def test_step_instruction_context_derives_legacy_local_governance_before_prompting(tmp_path: Path) -> None:
    step_context = build_step_context(
        tmp_path,
        layout_name="run_prompt_legacy_governance",
        run_contract={
            "compiled_spec": {
                "raw_sections": {
                    "Role Notes": (
                        "Builder reads AGENTS.md and design/README.md before editing.\n"
                        "Inspector verifies design/ and tests/ obligations against the result.\n"
                        "GateKeeper treats skipped AGENTS.md or tests/ validation as Weak, Unproven, or Blocking."
                    )
                }
            },
            "workflow": {
                "preset": "custom",
                "collaboration_intent": "Route project-local governance proof through the handoffs before closure.",
                "roles": [
                    {
                        "id": "gatekeeper",
                        "name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "posture_notes": "Fail closed when local governance evidence is skipped.",
                    }
                ],
            },
            "completion_mode": "gatekeeper",
            "collaboration_summary": "Future iterations keep inherited project rules visible.",
        },
    )

    assert any("Builder reads AGENTS.md" in item for item in step_context["contract"]["local_governance"])
    assert any("Inspector verifies design/" in item for item in step_context["contract"]["local_governance"])
    assert any("GateKeeper treats skipped AGENTS.md" in item for item in step_context["contract"]["local_governance"])
