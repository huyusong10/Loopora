from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)


CONFLICT_TASK_TEXT = (
    "我要做协作文档编辑。成功必须证明两个用户同时编辑同一段时不会 silent overwrite，"
    "version conflict / optimistic locking 会提示冲突或安全 merge，离线编辑恢复后重放是幂等的，"
    "冲突解决保留两边内容，权限不同的用户不能覆盖别人改动，audit log 能追踪 base_version、resolved_by 和 merge outcome；"
    "只有单人保存成功或最后写入 wins 必须阻断。"
)


def test_cli_agent_plan_conflict_resolution_rounds_use_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-conflict-resolution",
    }
    task_message = (
        "Plan a governed Loop for collaborative document editing. Success must prove two users editing the same paragraph "
        "do not silently overwrite each other, version conflict or optimistic locking produces a safe conflict prompt or "
        "merge, offline edits replay idempotently after reconnect, both sides of a conflict are preserved, lower-permission "
        "users cannot overwrite someone else, and audit logs record base_version, resolved_by, merge outcome, retry/replay, "
        "and permission denials. Fake done is one user can save, last-write-wins, only a happy-path WebSocket update, no "
        "offline replay proof, no permission negative case, no audit proof, or skipped local governance."
    )

    first_summary = _invoke_conflict_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_conflict_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a conflict-resolution contract-first workflow. Start with a read-only Conflict "
            "Contract Inspector freezing two-user same-paragraph edit fixtures, version conflict and optimistic-lock "
            "semantics, safe merge versus reject rules, offline edit queue replay, idempotency keys, permission matrix, "
            "lower-permission overwrite negatives, audit fields for base_version/resolved_by/merge outcome/retry/replay, "
            "and local governance proof targets. Collaboration Builder implements only after that handoff. Then run "
            "Conflict Evidence Inspector and Permission Audit Inspector in parallel: Conflict Evidence verifies concurrent "
            "edit lost-update prevention, version conflict UI/API response, safe merge or preservation of both sides, "
            "offline replay idempotency, retry handling, and last-write-wins negative proof; Permission Audit verifies "
            "unauthorized overwrite rejection, permission downgrade/revocation cases, audit logs, base_version/resolved_by/"
            "merge outcome, replay audit, monitoring, and governance. GateKeeper must fail closed on single-user-save-only, "
            "last-write-wins, happy-path WebSocket-only, missing optimistic-lock proof, missing offline replay idempotency, "
            "missing both-sides-preserved proof, missing permission negative, missing audit, or skipped local governance."
        ),
        env=env,
    )
    _assert_conflict_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_conflict_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this collaborative conflict-resolution direction.",
        env=env,
    )
    _assert_conflict_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _conflict_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_conflict_bundle(bundle_text)


def _invoke_conflict_plan_round(
    runner: CliRunner,
    sample_workdir: Path,
    *,
    message: str,
    env: dict[str, str],
) -> dict:
    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)["summary"]


def _assert_conflict_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Conflict Contract Inspector" in agreement_text
    assert "Collaboration Builder" in agreement_text
    assert "Conflict Evidence Inspector" in agreement_text
    assert "Permission Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Reservation Contract Inspector" not in agreement_text
    assert "Quota Contract Inspector" not in agreement_text


def _assert_conflict_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("conflict", "optimistic", "offline", "permission", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this collaborative conflict-resolution direction" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _conflict_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_conflict_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "conflict-contract-inspector",
        "collaboration-builder",
        "conflict-evidence-inspector",
        "permission-audit-inspector",
        "conflict-resolution-gatekeeper",
    ]
    assert workflow["preset"] == "collaborative-conflict-contract-parallel-resolution"
    assert [step["id"] for step in workflow["steps"]] == [
        "conflict_contract_inspection_step",
        "collaboration_builder_step",
        "conflict_evidence_inspection_step",
        "permission_audit_inspection_step",
        "conflict_resolution_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["conflict_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "conflict_resolution_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "conflict_resolution_review_pack"
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "conflict_contract_inspection_step",
        "collaboration_builder_step",
        "conflict_evidence_inspection_step",
        "permission_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "conflict-resolution",
        "idempotency",
        "permission-auth",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Collaborative Conflict Resolution Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "inventory-reservation-contract-parallel-consistency" not in bundle_text
    assert "usage-quota-contract-parallel-metering" not in bundle_text
    assert "Confirm; use this collaborative conflict-resolution direction" not in bundle_text


def test_alignment_agreement_requires_concurrency_conflict_resolution(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship collaborative note editing so two users can save note changes.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means collaborative document editing proves concurrent edits on the same paragraph "
                    "do not silently overwrite, version conflict or optimistic locking is handled, offline replay "
                    "is idempotent, both sides of a conflict are preserved, permissions block unauthorized overwrites, "
                    "and audit records base_version, resolved_by, and merge outcome."
                ),
                "fake_done_risks": (
                    "Only proving single-user save or last-write-wins collaborative editing without conflict "
                    "resolution, optimistic locking, offline replay, permission, and audit evidence must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include collaborative editing with two users, same-paragraph version conflicts, "
                    "offline replay idempotency, unauthorized overwrite rejection, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "concurrency/conflict-resolution" in issue for issue in issues)
    assert any("fake-done risks" in issue and "concurrency/conflict-resolution" in issue for issue in issues)
    assert any("evidence preferences" in issue and "concurrency/conflict-resolution" in issue for issue in issues)


def test_agent_first_traceability_blocks_last_write_wins_collaboration(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship collaborative note editing so two users can save note changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: concurrent same-paragraph conflict resolution, optimistic locking, offline replay, "
        "permission overwrite checks, and audit proof can be handled later.\n"
        "  Owner: collaboration owner\n"
        "  Follow-up: create a conflict-resolution correctness ticket.\n"
        "  Acceptance path: GateKeeper can pass after one user saves successfully and last write wins.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat concurrent edit conflicts, optimistic locking, offline replay, permissions, and audit as later residual risk.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(CONFLICT_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "concurrency/conflict-resolution" in issue for issue in issues)
    assert any("fake-done risks" in issue and "concurrency/conflict-resolution" in issue for issue in issues)
    assert any("evidence preferences" in issue and "concurrency/conflict-resolution" in issue for issue in issues)
    assert any("success criteria" in issue and "audit/log" in issue for issue in issues)
