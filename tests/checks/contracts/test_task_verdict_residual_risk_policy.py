from __future__ import annotations

from pathlib import Path

from loopora.task_verdicts import build_task_verdict

from task_verdict_test_support import write_task_verdict_coverage as _write_coverage


def test_task_verdict_does_not_pass_with_unmanaged_residual_risk(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_unmanaged_residual_risk"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {"id": "done_when.check_001", "label": "Required proof", "status": "covered", "required": True},
                {"id": "gatekeeper.finish", "label": "GateKeeper finish", "status": "covered", "required": True},
            ],
            "risk_signals": [],
            "latest_gatekeeper": {
                "id": "ev_gatekeeper",
                "result": "passed",
                "residual_risk": "Some residual risk remains.",
            },
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "GateKeeper accepted a vague risk.",
                "residual_risks": ["Some residual risk remains."],
            },
        },
        run_dir=run_dir,
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["summary"] == "GateKeeper reported residual risk without a named owner, follow-up, or acceptance path."
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": "Some residual risk remains.",
            "reason": "Residual risk was reported without enough management detail to accept it.",
            "managed": False,
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []


def test_task_verdict_treats_vague_chinese_residual_risk_acceptance_as_unmanaged(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_vague_chinese_residual_risk"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {"id": "done_when.check_001", "label": "Required proof", "status": "covered", "required": True},
                {"id": "gatekeeper.finish", "label": "GateKeeper finish", "status": "covered", "required": True},
            ],
            "risk_signals": [],
            "latest_gatekeeper": {
                "id": "ev_gatekeeper",
                "result": "passed",
                "residual_risk": "有些风险可以接受。",
            },
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "GateKeeper accepted a vague risk.",
                "residual_risks": ["有些风险可以接受。"],
            },
        },
        run_dir=run_dir,
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["summary"] == "GateKeeper reported residual risk without a named owner, follow-up, or acceptance path."
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": "有些风险可以接受。",
            "reason": "Residual risk was reported without enough management detail to accept it.",
            "managed": False,
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []


def test_task_verdict_does_not_treat_manual_or_visible_words_as_residual_risk_management(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_manual_visible_residual_risk"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {"id": "done_when.check_001", "label": "Required proof", "status": "covered", "required": True},
                {"id": "gatekeeper.finish", "label": "GateKeeper finish", "status": "covered", "required": True},
            ],
            "risk_signals": [],
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "GateKeeper named a manual but ownerless risk.",
                "residual_risks": ["Ownerless manual billing export remains visible."],
            },
        },
        run_dir=run_dir,
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["summary"] == "GateKeeper reported residual risk without a named owner, follow-up, or acceptance path."
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": "Ownerless manual billing export remains visible.",
            "reason": "Residual risk was reported without enough management detail to accept it.",
            "managed": False,
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []


def test_task_verdict_does_not_accept_residual_risk_when_run_contract_disallows_it(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_disallowed_residual_risk"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {"id": "done_when.check_001", "label": "Required proof", "status": "covered", "required": True},
                {"id": "gatekeeper.finish", "label": "GateKeeper finish", "status": "covered", "required": True},
            ],
            "risk_signals": [],
            "latest_gatekeeper": {
                "id": "ev_gatekeeper",
                "result": "passed",
                "residual_risk": "Manual billing export remains visible as a follow-up owned by Support.",
            },
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "compiled_spec_json": {
                "residual_risk": "No residual risk is acceptable; any remaining risk must fail closed.",
            },
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "GateKeeper accepted a managed residual risk.",
                "residual_risks": ["Manual billing export remains visible as a follow-up owned by Support."],
            },
        },
        run_dir=run_dir,
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["summary"] == "GateKeeper reported residual risk even though the run contract disallows accepted residual risk."
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": "Manual billing export remains visible as a follow-up owned by Support.",
            "reason": "Residual risk was reported even though the run contract disallows accepted residual risk.",
            "residual_risk_policy": "disallowed",
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []


def test_task_verdict_does_not_erase_negated_residual_risk_with_exception(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_excepted_residual_risk"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {"id": "done_when.check_001", "label": "Required proof", "status": "covered", "required": True},
                {"id": "gatekeeper.finish", "label": "GateKeeper finish", "status": "covered", "required": True},
            ],
            "risk_signals": [],
            "latest_gatekeeper": {
                "id": "ev_gatekeeper",
                "result": "passed",
                "residual_risk": "No blocking residual risk except untested billing export.",
            },
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "GateKeeper used a negated phrase while naming an unowned exception.",
                "residual_risks": ["No blocking residual risk except untested billing export."],
            },
        },
        run_dir=run_dir,
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["summary"] == "GateKeeper reported residual risk without a named owner, follow-up, or acceptance path."
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": "No blocking residual risk except untested billing export.",
            "reason": "Residual risk was reported without enough management detail to accept it.",
            "managed": False,
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []


def test_task_verdict_classifies_unmanaged_coverage_risk_signal_as_weak(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_unmanaged_coverage_risk"
    _write_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {"id": "done_when.check_001", "label": "Required proof", "status": "covered", "required": True},
                {"id": "gatekeeper.finish", "label": "GateKeeper finish", "status": "covered", "required": True},
            ],
            "risk_signals": ["Some residual risk remains."],
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "GateKeeper passed without accepting a residual risk.",
            },
        },
        run_dir=run_dir,
    )

    assert task_verdict["status"] == "passed"
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": "Some residual risk remains.",
            "reason": "Residual risk was observed without enough management detail to accept it.",
            "managed": False,
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []
