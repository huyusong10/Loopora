from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_key_rotation_rounds_use_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-key-rotation-contract",
    }
    task_message = (
        "Plan a governed Loop for customer API key and service account secret rotation. Success must prove old key "
        "and new key have a controlled overlap window, zero-downtime rotation keeps existing calls working, compromised "
        "keys can be immediately revoked, revoked keys cannot continue calling APIs, key scope and tenant binding are "
        "correct, secrets are stored only as hash or KMS encrypted values, rotation schedule, expiry, last-used telemetry, "
        "and audit logs capture key id, actor, scope, tenant, created/rotated/revoked/failed reason. Rollback must not "
        "re-enable revoked keys, and monitoring must catch rotation failure and stale keys. Fake done is UI shows a new "
        "key, env var changes, one happy-path API call works, or docs say rotation is supported without revoke and "
        "storage proof."
    )

    first_summary = _invoke_key_rotation_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_key_rotation_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with a read-only Key Rotation Contract Inspector that freezes overlap window, "
            "old/new key compatibility, compromised-key revoke, revoked-key negative calls, scope and tenant binding, "
            "hash/KMS storage, rotation schedule, expiry, last-used telemetry, rollback safety, audit fields, and monitoring "
            "proof targets. Builder should only implement after that handoff. Then run Rotation Lifecycle Evidence Inspector "
            "and Secret Storage Audit Inspector in parallel: Lifecycle Inspector verifies old/new key calls, revoked-key "
            "denial, compromised revoke, scope/tenant negatives, expiry, last-used telemetry, rollback safety, rotation "
            "failure alert, and stale-key alert; Storage Audit Inspector verifies secret hash/KMS storage, no plaintext leak, "
            "audit log key id/actor/scope/tenant/reason, privacy redaction, and local governance. GateKeeper must fail "
            "closed on new-key-only UI, env-var-only, happy-path API call only, missing revoked-key negative, missing "
            "overlap proof, missing storage proof, missing audit fields, or missing monitoring proof."
        ),
        env=env,
    )
    _assert_key_rotation_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_key_rotation_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this key rotation contract-first parallel evidence direction.",
        env=env,
    )
    _assert_key_rotation_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _key_rotation_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_key_rotation_bundle(bundle_text)


def _invoke_key_rotation_plan_round(
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


def _assert_key_rotation_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Key Rotation Contract Inspector" in agreement_text
    assert "Rotation Lifecycle Evidence Inspector" in agreement_text
    assert "Secret Storage Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_key_rotation_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in (
        "controlled overlap window",
        "revoked keys cannot continue",
        "hash or KMS encrypted",
        "last-used telemetry",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this key rotation" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _key_rotation_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_key_rotation_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert bundle["metadata"]["name"] == "Key Rotation Secret Lifecycle Loop"
    assert workflow["preset"] == "key-rotation-contract-parallel-controls"
    assert [step["id"] for step in workflow["steps"]] == [
        "key_rotation_contract_inspection_step",
        "secret_rotation_builder_step",
        "rotation_lifecycle_evidence_inspection_step",
        "secret_storage_audit_inspection_step",
        "key_rotation_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["key_rotation_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "key_rotation_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "key_rotation_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "key_rotation_contract_inspection_step",
        "secret_rotation_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "key_rotation_contract_inspection_step",
        "secret_rotation_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "key_rotation_contract_inspection_step",
        "secret_rotation_builder_step",
        "rotation_lifecycle_evidence_inspection_step",
        "secret_storage_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "key-rotation",
        "privacy-redaction",
        "permission-auth",
        "audit-log",
        "monitoring",
        "backward-compatibility",
        "eval-set",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Key Rotation GateKeeper Notes" in bundle_text
    assert "Confirm; use this key rotation" not in bundle_text
    for generic_repair_token in (
        "Task Evidence Repair Loop",
        "Repair Builder",
        "Guide 只把弱证据",
        "task-evidence-repair",
        "Builder -> Inspector -> Guide",
    ):
        assert generic_repair_token not in bundle_text
