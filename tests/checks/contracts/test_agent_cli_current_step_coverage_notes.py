from __future__ import annotations

from agent_adapter_test_support import cli_agent_adapter_commands


FIRST_BUILDER_EVIDENCE = "ev_000_00_builder_step"
PRIOR_GATEKEEPER_BLOCKER = "ev_000_03_gatekeeper_step"
NEW_BUILDER_EVIDENCE = "ev_001_00_builder_step"


def test_agent_cli_current_step_explains_unclassified_coverage_notes(capsys) -> None:
    cases = [
        (
            _current_step(
                required_coverage=_coverage("partial", missing_check_count=4, missing_target_count=14),
                known_evidence_count=1,
                known_evidence_ids=[FIRST_BUILDER_EVIDENCE],
            ),
            "known evidence is citable, but coverage remains unverified until a review role returns "
            "coverage_results with exact target IDs",
        ),
        (
            _current_step(
                iter=1,
                required_coverage=_coverage(
                    "blocked",
                    covered_check_count=1,
                    missing_check_count=3,
                    covered_target_count=3,
                    blocked_target_count=11,
                    missing_target_count=0,
                    top_gaps=[_blocked_gap("done_when.check_002", "Rollback proof is still classified from the previous GateKeeper verdict.")],
                ),
                known_evidence_count=5,
                known_evidence_ids=[FIRST_BUILDER_EVIDENCE, PRIOR_GATEKEEPER_BLOCKER, NEW_BUILDER_EVIDENCE],
                known_evidence_refs=[
                    _evidence_ref(PRIOR_GATEKEEPER_BLOCKER, "gatekeeper", "non_supporting", ["done_when.check_002"]),
                    _evidence_ref(NEW_BUILDER_EVIDENCE, "builder", "supporting"),
                ],
            ),
            "ev_001_00_builder_step is citable, but coverage still reflects earlier classifications until "
            "a review role returns coverage_results for that evidence",
        ),
    ]
    for next_step, expected_note in cases:
        _assert_coverage_note(capsys, next_step, expected_note)


def test_agent_cli_current_step_omits_unclassified_note_when_only_gatekeeper_finish_remains(capsys) -> None:
    next_step = _current_step(
        step_id="evidence_inspection_step",
        iter=1,
        step_order=2,
        role={"name": "Evidence Inspector"},
        required_coverage=_coverage(
            "blocked",
            covered_check_count=4,
            covered_target_count=13,
            blocked_target_count=1,
            top_gaps=[
                _blocked_gap(
                    "gatekeeper.finish",
                    "GateKeeper must finish from the next verdict.",
                    source_section="Workflow",
                )
            ],
        ),
        known_evidence_count=5,
        known_evidence_ids=[
            FIRST_BUILDER_EVIDENCE,
            NEW_BUILDER_EVIDENCE,
            "ev_001_01_contract_inspection_step",
        ],
        known_evidence_refs=[
            _evidence_ref(NEW_BUILDER_EVIDENCE, "builder", "supporting")
        ],
    )

    cli_agent_adapter_commands._print_agent_current_step(next_step)
    summary = cli_agent_adapter_commands._agent_next_step_summary(next_step)

    output = capsys.readouterr().out

    assert "coverage_classification_note:" not in output
    assert "coverage_classification_note" not in summary


def _current_step(**overrides: object) -> dict:
    next_step = {
        "step_id": "contract_inspection_step",
        "iter": 0,
        "step_order": 1,
        "role": {"name": "Contract Inspector"},
        "role_dispatch": {"target_agent": "loopora-inspector"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
        "required_coverage": _coverage("partial"),
        "submit_hint": {},
    }
    next_step.update(overrides)
    return next_step


def _coverage(status: str, **overrides: object) -> dict:
    coverage = {
        "status": status,
        "covered_check_count": 0,
        "missing_check_count": 0,
        "target_count": 14,
        "covered_target_count": 0,
        "weak_target_count": 0,
        "blocked_target_count": 0,
        "missing_target_count": 0,
        "top_gaps": [],
    }
    coverage.update(overrides)
    return coverage


def _blocked_gap(target_id: str, text: str, *, source_section: str = "Done When") -> dict:
    return {
        "target_id": target_id,
        "status": "blocked",
        "source_section": source_section,
        "text": text,
        "evidence_refs": [PRIOR_GATEKEEPER_BLOCKER],
    }


def _evidence_ref(evidence_id: str, archetype: str, support: str, target_ids: list[str] | None = None) -> dict:
    return {
        "id": evidence_id,
        "archetype": archetype,
        "gatekeeper_support": support,
        "coverage_target_ids": target_ids or [],
    }


def _assert_coverage_note(capsys, next_step: dict, expected_note: str) -> None:
    cli_agent_adapter_commands._print_agent_current_step(next_step)
    summary = cli_agent_adapter_commands._agent_next_step_summary(next_step)
    output = capsys.readouterr().out
    assert f"coverage_classification_note: {expected_note}" in output
    assert summary["coverage_classification_note"] == expected_note
