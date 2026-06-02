from __future__ import annotations

from agent_adapter_test_support import _assert_cli_list, cli_agent_adapter_commands


KNOWN_EVIDENCE_COUNT = 10
KNOWN_EVIDENCE_OMITTED_COUNT = 2


def test_agent_cli_current_step_prints_zero_known_evidence_count(capsys) -> None:
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "iter": 0,
            "step_order": 0,
            "role": {"name": "Builder"},
            "role_dispatch": {"target_agent": "loopora-builder"},
            "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
            "required_coverage": {"status": "pending", "covered_check_count": 0, "missing_check_count": 2, "top_gaps": []},
            "known_evidence_ids": [],
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert "known_evidence_count: 0" in output
    assert "known_evidence_ids:" not in output


def test_agent_cli_current_step_prints_bounded_known_evidence_ids(capsys) -> None:
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "inspector_step",
            "iter": 1,
            "step_order": 2,
            "parallel_group": "reviewers",
            "role": {"name": "Inspector"},
            "role_dispatch": {"target_agent": "loopora-inspector"},
            "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
            "required_coverage": {
                "status": "partial",
                "covered_check_count": 1,
                "missing_check_count": 1,
                "top_gaps": [{"target_id": "gatekeeper.finish", "evidence_refs": ["ev_gatekeeper_blocker"]}],
            },
            "inputs": {"evidence_query": {"archetypes": ["builder"], "limit": 12}},
            "known_evidence_ids": [f"ev_{idx:03d}" for idx in range(KNOWN_EVIDENCE_COUNT)],
            "known_evidence_refs": [
                {
                    "id": "ev_006",
                    "step_id": "builder_step",
                    "role_name": "Builder",
                    "result": "completed",
                    "claim": "Builder produced a claim without direct proof.",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "no proof artifact",
                    "coverage_target_ids": [],
                    "artifact_refs": [
                        {"label": "proof-file:tests/browser-journey.json", "path": "tests/browser-journey.json"}
                    ],
                },
                {
                    "id": "ev_009",
                    "step_id": "inspector_step",
                    "role_name": "Inspector",
                    "result": "blocked",
                    "claim": "Inspector blocked the primary journey.",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "result is blocked",
                    "coverage_target_ids": ["done_when.check_001"],
                },
            ],
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert f"known_evidence_count: {KNOWN_EVIDENCE_COUNT}" in output
    assert "known_evidence_scope: filtered by evidence_query" in output
    assert "archetypes=builder" in output
    assert "parallel_group=reviewers" in output
    assert "coverage_gap_refs=included" in output
    assert "known_evidence_ids_omitted: 2 older" in output
    _assert_cli_list(output, "known_evidence_ids", "ev_002", "ev_009")
    assert "known_evidence_refs:" in output
    assert "- ev_006 result=completed support=non_supporting reason=no proof artifact" in output
    assert "claim: Builder produced a claim without direct proof." in output
    assert "artifacts: proof-file:tests/browser-journey.json: tests/browser-journey.json" in output
    assert "- ev_009 result=blocked support=non_supporting reason=result is blocked" in output
    assert "coverage_targets: done_when.check_001" in output
    assert "- ev_000" not in output
    assert "- ev_001" not in output


def test_agent_next_json_summary_bounds_known_evidence_ids_to_latest_window() -> None:
    summary = cli_agent_adapter_commands._agent_next_step_summary(
        {
            "step_id": "gatekeeper_step",
            "known_evidence_count": KNOWN_EVIDENCE_COUNT,
            "known_evidence_ids": [f"ev_{idx:03d}" for idx in range(KNOWN_EVIDENCE_COUNT)],
            "known_evidence_refs": [
                {
                    "id": "ev_009",
                    "step_id": "evidence_inspection_step",
                    "role_name": "Evidence Inspector",
                    "result": "completed",
                    "gatekeeper_support": "supporting",
                    "gatekeeper_support_reason": "review evidence verifies a passed check",
                }
            ],
        }
    )

    assert summary["known_evidence_count"] == KNOWN_EVIDENCE_COUNT
    assert summary["known_evidence_ids_omitted"] == KNOWN_EVIDENCE_OMITTED_COUNT
    assert summary["known_evidence_ids"] == [
        f"ev_{idx:03d}" for idx in range(KNOWN_EVIDENCE_OMITTED_COUNT, KNOWN_EVIDENCE_COUNT)
    ]
    assert summary["known_evidence_refs"][0]["id"] == "ev_009"
