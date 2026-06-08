from __future__ import annotations

import json
import time
from pathlib import Path


from loopora.bundles import bundle_to_yaml

RUN_REVISION_MISSING_CHECK_COUNT = 2

def _wait_for_status(service, session_id: str, *statuses: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    expected = set(statuses)
    while time.time() < deadline:
        session = service.get_alignment_session(session_id)
        if session["status"] in expected:
            return session
        time.sleep(0.05)
    session = service.get_alignment_session(session_id)
    raise AssertionError(f"alignment session stayed in {session['status']}, expected {sorted(expected)}")

def _confirm_alignment_agreement(service, session_id: str, *final_statuses: str) -> dict:
    agreement = _wait_for_status(service, session_id, "waiting_user")
    assert agreement["alignment_stage"] == "agreement_ready"
    assert agreement["working_agreement"]["summary"]
    for evidence_key in ("loop_fit", "task_scope", "residual_risk_policy", "local_governance"):
        assert agreement["working_agreement"]["readiness_evidence"][evidence_key]
    service.append_alignment_message(session_id, "确认")
    confirmed = _wait_for_status(service, session_id, *(final_statuses or ("ready",)))
    assert confirmed["working_agreement"]["readiness_checklist"]["explicit_confirmation"] is True
    return confirmed

def _assert_alignment_stage_blocked(service, session_id: str) -> None:
    assert any(
        event["event_type"] == "alignment_stage_blocked"
        for event in service.list_alignment_events(session_id)
    )

def _assert_alignment_stage_blocked_for_key(service, session_id: str, key: str) -> None:
    events = service.list_alignment_events(session_id)
    assert any(
        event["event_type"] == "alignment_stage_blocked"
        and (key in event["payload"].get("missing", []) or key in event["payload"].get("error", ""))
        for event in events
    )

def _bundle_invocation_dir(artifact_root: Path) -> Path:
    bundle_invocations: list[Path] = []
    for invocation_dir in sorted((artifact_root / "invocations").iterdir()):
        output_path = invocation_dir / "output.json"
        if not output_path.is_file():
            continue
        try:
            output = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if output.get("bundle_written") is True:
            bundle_invocations.append(invocation_dir)
    if not bundle_invocations:
        raise AssertionError("no bundle-writing alignment invocation was recorded")
    return bundle_invocations[-1]

def _assert_run_succeeds_and_joins(service, run_id: str, *, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    run = service.get_run(run_id)
    while time.time() < deadline:
        run = service.get_run(run_id)
        if run["status"] in {"succeeded", "failed", "stopped"}:
            break
        time.sleep(0.05)
    thread = service._threads.get(run_id)
    if thread is not None:
        thread.join(timeout=max(0.0, deadline - time.time()))
    run = service.get_run(run_id)
    assert run["status"] == "succeeded"

def _assert_alignment_preview_control_summary(preview: dict) -> None:
    control_summary = preview["control_summary"]
    assert control_summary["gatekeeper"]["requires_evidence_refs"] is True
    assert control_summary["coverage"]["check_count"] >= 1
    assert control_summary["coverage"]["target_count"] >= control_summary["coverage"]["check_count"]
    assert any(target["id"].startswith("done_when.") for target in control_summary["coverage"]["targets"])
    assert any("fail closed" in item for item in control_summary["residual_risk_policy"])
    assert any("smaller proven flow" in item for item in control_summary["judgment_tradeoffs"])
    assert any("Focused Builder (builder): Keep implementation narrow" in item for item in control_summary["role_postures"])
    assert any("final feedback is too slow to be the only control signal" in item for item in control_summary["loop_fit_reasons"])
    assert any("weak-proof control points" in item for item in control_summary["loop_fit_reasons"])
    assert preview["traceability"] == control_summary["traceability"]
    assert any(item["key"] == "loop_fit" and item["mapped"] for item in preview["traceability"]["items"])
    assert any(item["key"] == "coverage_targets" and item["mapped"] for item in preview["traceability"]["items"])
    assert any(item["key"] == "judgment_tradeoffs" and item["mapped"] for item in preview["traceability"]["items"])
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]

def _create_alignment_improvement_source_bundle(
    service,
    sample_spec_file: Path,
    sample_workdir: Path,
    *,
    completion_mode: str = "gatekeeper",
) -> dict:
    loop = service.create_loop(
        name="Improvement Source Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
        completion_mode=completion_mode,
    )
    return service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Improvement Source Bundle",
                description="Start from an existing bundle.",
                collaboration_summary="Prefer evidence before changing posture.",
            )
        )
    )

def _write_run_revision_coverage(coverage_path: Path) -> None:
    coverage_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ledger_path": "evidence/ledger.jsonl",
                "coverage_path": "evidence/coverage.json",
                "status": "partial",
                "summary": {"reason": "Required refund audit and payment failure checks still lack direct proof."},
                "evidence_count": 4,
                "check_count": 3,
                "covered_check_count": 1,
                "missing_check_count": 2,
                "covered_check_ids": ["check_permission"],
                "missing_check_ids": ["check_payment_failure", "check_audit_trail"],
                "target_count": 6,
                "covered_target_count": 2,
                "weak_target_count": 1,
                "missing_target_count": 2,
                "blocked_target_count": 1,
                "top_gaps": [
                    {
                        "target_id": "done_when.check_payment_failure",
                        "text": "Payment failure handoff has no direct proof.",
                    },
                    {
                        "target_id": "done_when.check_audit_trail",
                        "text": "Audit trail cannot yet reconstruct a refund.",
                    },
                ],
                "evidence_kind_counts": {"artifact": 2, "summary": 2},
                "artifact_ref_count": 2,
                "residual_risk_count": 1,
                "risk_signals": ["Payment provider retry path remains visible."],
                "latest_gatekeeper": {"id": "ev_gatekeeper", "result": "blocked"},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

def _assert_run_revision_coverage_agreement(agreement: dict) -> None:
    coverage_summary = agreement["source"]["coverage_summary"]
    assert coverage_summary["ledger_path"] == "evidence/ledger.jsonl"
    assert coverage_summary["coverage_path"] == "evidence/coverage.json"
    assert coverage_summary["covered_check_count"] == 1
    assert coverage_summary["missing_check_count"] == RUN_REVISION_MISSING_CHECK_COUNT
    assert coverage_summary["covered_check_ids"] == ["check_permission"]
    assert coverage_summary["missing_check_ids"] == ["check_payment_failure", "check_audit_trail"]
    assert coverage_summary["weak_target_count"] == 1
    assert coverage_summary["blocked_target_count"] == 1
    assert coverage_summary["risk_signals"] == ["Payment provider retry path remains visible."]
    assert any(item["artifact_refs"] for item in agreement["source"]["evidence_summary"])
    assert agreement["source"]["task_verdict"]["status"]
    assert "gatekeeper_verdict" in agreement["source"]
    assert agreement["source"]["gatekeeper_verdict"]["decision_summary"]

def _assert_run_revision_context_text(context_text: str, run: dict, agreement: dict) -> None:
    assert f"Source run status: {run['status']}" in context_text
    assert "Artifact paths:" in context_text
    assert "evidence/task_verdict.json" in context_text
    assert "Frozen judgment contract:" in context_text
    assert "Use GateKeeper evidence to improve the plan." in context_text
    assert "Repair evidence gaps before broad polishing." in context_text
    assert "GateKeeper treats skipped AGENTS.md evidence as Blocking." in context_text
    assert "`execution_strategy` should say what the next version should build" in context_text
    assert "`local_governance` should preserve or revise project-local governance responsibilities" in context_text
    assert f'"missing_check_count": {RUN_REVISION_MISSING_CHECK_COUNT}' in context_text
    assert "check_payment_failure" in context_text
    assert "Payment failure handoff has no direct proof." in context_text
    assert "Payment provider retry path remains visible." in context_text
    assert "Task verdict:" in context_text
    assert agreement["source"]["task_verdict"]["status"] in context_text
    assert "GateKeeper verdict:" in context_text
    assert "decision_summary" in context_text

__all__ = [
    '_assert_alignment_preview_control_summary',
    '_assert_alignment_stage_blocked',
    '_assert_alignment_stage_blocked_for_key',
    '_assert_run_revision_context_text',
    '_assert_run_revision_coverage_agreement',
    '_assert_run_succeeds_and_joins',
    '_bundle_invocation_dir',
    '_confirm_alignment_agreement',
    '_create_alignment_improvement_source_bundle',
    '_wait_for_status',
    '_write_run_revision_coverage',
]
