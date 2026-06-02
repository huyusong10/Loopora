from __future__ import annotations

from pathlib import Path

from loopora.context_flow import render_evidence_section

from step_instruction_context_test_support import build_step_context


def test_step_instruction_context_preserves_manifest_claim_target_trace(tmp_path: Path) -> None:
    step_context = build_step_context(
        tmp_path,
        run_contract={"compiled_spec": {}, "workflow": {"preset": "custom"}, "completion_mode": "gatekeeper"},
        evidence_items=[
            {
                "id": "ev_target",
                "role_name": "Inspector",
                "archetype": "inspector",
                "result": "passed",
                "claim": "Inspector covered the target.",
                "related_evidence_ids": [],
                "coverage_results": [],
                "artifact_refs": [],
            }
        ],
        evidence_known_ids=["ev_target"],
        evidence_manifest_summary={"claim_count": 1, "direct_proof_claim_count": 1},
        evidence_manifest_claims=[
            {
                "id": "ev_target",
                "verification_status": "direct_proof",
                "measured_evidence": True,
                "concrete_evidence_claim_count": 1,
                "artifact_count": 1,
                "artifact_backed": True,
                "workspace_backed": True,
                "reproducible": True,
                "coverage_targets": [
                    {
                        "id": "done_when.check",
                        "kind": "done_when",
                        "label": "Done check",
                        "reported_status": "covered",
                        "coverage_status": "covered",
                        "required": "true",
                        "evidence_refs": ["ev_target"],
                    }
                ],
            }
        ],
    )

    target_trace = step_context["evidence"]["manifest_claims"][0]["coverage_targets"][0]
    assert target_trace == {
        "id": "done_when.check",
        "kind": "done_when",
        "label": "Done check",
        "reported_status": "covered",
        "coverage_status": "covered",
        "required": True,
        "evidence_refs": ["ev_target"],
    }
    prompt_section = render_evidence_section(step_context["evidence"])
    assert '"id": "done_when.check"' in prompt_section
    assert '"required": true' in prompt_section
