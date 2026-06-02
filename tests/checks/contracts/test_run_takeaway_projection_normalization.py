from __future__ import annotations

from loopora.run_takeaways import normalize_run_takeaway_projection_shape


NORMALIZED_BUNDLE_BYTES = 42
NORMALIZED_DIRECT_PROOF_CLAIM_COUNT = 2
NORMALIZED_MISSING_CHECK_COUNT = 2


def test_takeaway_projection_normalization_does_not_promote_boolean_counts() -> None:
    projection = normalize_run_takeaway_projection_shape(
        {"id": "run_projection_counts", "status": "succeeded", "run_status": "succeeded"},
        {
            "source_event_id": True,
            "evidence_count": True,
            "evidence_coverage": {
                "ledger_path": True,
                "coverage_path": True,
                "status": True,
                "evidence_count": True,
                "covered_check_count": "1",
                "missing_check_count": NORMALIZED_MISSING_CHECK_COUNT,
                "covered_check_ids": "check_001",
                "missing_check_ids": ["check_002", True],
                "risk_signals": [False, "manual review"],
            },
            "evidence_manifest": {
                "claim_count": True,
                "artifact_backed_claim_count": "1",
                "direct_proof_claim_count": NORMALIZED_DIRECT_PROOF_CLAIM_COUNT,
                "problem_count": True,
            },
            "judgment_contract": {
                "contract_path": True,
                "source_bundle": {
                    "id": "bundle_projection",
                    "name": "Projection Bundle",
                    "bundle_sha256": "abc123",
                    "bundle_bytes": NORMALIZED_BUNDLE_BYTES,
                    "bundle_yaml_path": "/tmp/loopora/bundle_projection.yml",
                },
                "collaboration_summary": True,
                "loop_fit_reasons": [False, "Future rounds keep proof alive."],
                "goal": "  Keep the frozen task visible.  ",
                "workflow_collaboration_intent": "legacy alias ignored by projection",
                "execution_strategy": [False, "Prove the focused path first."],
                "local_governance": [False, "GateKeeper treats skipped AGENTS.md evidence as Blocking."],
                "role_postures": [
                    {
                        "role_name": "Builder",
                        "archetype": "builder",
                        "posture_notes": "Keep the change narrow and verifiable.",
                    },
                    False,
                ],
                "judgment_tradeoffs": [False, "Prefer proof before polish."],
                "success_surface": ["Stable surface", True],
                "fake_done_states": [False, "Only the happy path"],
                "evidence_preferences": ["Proof artifact", 3],
                "residual_risk": "  Minor copy polish.  ",
            },
            "iteration_count": True,
            "role_conclusion_count": "1",
            "latest_display_iter": True,
        },
    )

    assert projection["source_event_id"] == 0
    assert projection["evidence_count"] == 0
    assert projection["evidence_coverage"]["ledger_path"] == ""
    assert projection["evidence_coverage"]["coverage_path"] == ""
    assert projection["evidence_coverage"]["status"] == "pending"
    assert projection["evidence_coverage"]["evidence_count"] == 0
    assert projection["evidence_coverage"]["covered_check_count"] == 0
    assert projection["evidence_coverage"]["missing_check_count"] == NORMALIZED_MISSING_CHECK_COUNT
    assert projection["evidence_coverage"]["covered_check_ids"] == []
    assert projection["evidence_coverage"]["missing_check_ids"] == ["check_002"]
    assert projection["evidence_coverage"]["risk_signals"] == ["manual review"]
    assert projection["evidence_manifest"]["claim_count"] == 0
    assert projection["evidence_manifest"]["artifact_backed_claim_count"] == 0
    assert projection["evidence_manifest"]["direct_proof_claim_count"] == NORMALIZED_DIRECT_PROOF_CLAIM_COUNT
    assert projection["evidence_manifest"]["problem_count"] == 0
    assert projection["judgment_contract"]["contract_path"] == ""
    assert projection["judgment_contract"]["source_bundle"]["id"] == "bundle_projection"
    assert projection["judgment_contract"]["source_bundle"]["bundle_sha256"] == "abc123"
    assert projection["judgment_contract"]["source_bundle"]["bundle_bytes"] == NORMALIZED_BUNDLE_BYTES
    assert projection["judgment_contract"]["source_bundle"]["bundle_yaml_path"] == "/tmp/loopora/bundle_projection.yml"
    assert projection["judgment_contract"]["collaboration_summary"] == ""
    assert projection["judgment_contract"]["loop_fit_reasons"] == ["Future rounds keep proof alive."]
    assert projection["judgment_contract"]["goal"] == "Keep the frozen task visible."
    assert projection["judgment_contract"]["check_mode"] == ""
    assert projection["judgment_contract"]["check_count"] == 0
    assert projection["judgment_contract"]["completion_mode"] == ""
    assert projection["judgment_contract"]["strategy_preset"] == ""
    assert projection["judgment_contract"]["strategy_collaboration_intent"] == ""
    assert "workflow_preset" not in projection["judgment_contract"]
    assert "workflow_collaboration_intent" not in projection["judgment_contract"]
    assert projection["judgment_contract"]["execution_strategy"] == ["Prove the focused path first."]
    assert projection["judgment_contract"]["local_governance"] == ["GateKeeper treats skipped AGENTS.md evidence as Blocking."]
    assert projection["judgment_contract"]["role_postures"] == ["Builder: Keep the change narrow and verifiable."]
    assert projection["judgment_contract"]["judgment_tradeoffs"] == ["Prefer proof before polish."]
    assert projection["judgment_contract"]["coverage_targets"] == []
    assert projection["judgment_contract"]["success_surface"] == ["Stable surface"]
    assert projection["judgment_contract"]["fake_done_states"] == ["Only the happy path"]
    assert projection["judgment_contract"]["evidence_preferences"] == ["Proof artifact"]
    assert projection["judgment_contract"]["residual_risk"] == "Minor copy polish."
    assert projection["iteration_count"] == 0
    assert projection["role_conclusion_count"] == 0
    assert projection["latest_display_iter"] is None


def test_takeaway_projection_normalizes_task_verdict_bucket_shapes() -> None:
    projection = normalize_run_takeaway_projection_shape(
        {"id": "run_projection_buckets", "status": "failed", "run_status": "failed"},
        {
            "task_verdict": {
                "status": "failed",
                "source": "gatekeeper",
                "summary": "Stored projection should keep stable bucket entries.",
                "buckets": {
                    "blocking": [True, "real blocker", {"label": "structured blocker"}],
                    "residual_risk": [False],
                },
            },
            "evidence_buckets": {
                "residual_risk": [False, "manual risk"],
                "unknown": ["not a stable bucket"],
            },
        },
    )

    assert projection["task_verdict"]["buckets"]["blocking"] == [
        {"label": "real blocker"},
        {"label": "structured blocker"},
    ]
    assert projection["task_verdict"]["buckets"]["residual_risk"] == []
    assert projection["evidence_buckets"] == {"residual_risk": [{"label": "manual risk"}]}
