from __future__ import annotations

from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, json, yaml
from alignment_test_support import _wait_for_status
from loopora.bundles import load_bundle_text
from loopora.bundles import lint_alignment_bundle_semantics
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)


SCHEDULE_TASK_TEXT = (
    "我要做 weekly digest 定时发送。成功必须证明每个用户按自己的 timezone 本地周一 09:00 收到，"
    "DST/夏令时切换前后不会提前或延后，错过执行后 catch-up 只补一次，重试不会重复发送，"
    "取消订阅或禁用用户不会发送，audit log 能追踪 scheduled_at / sent_at；"
    "只有 cron expression 配好或本地触发一次必须阻断。"
)


def test_alignment_agreement_requires_schedule_timezone_recurrence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a weekly digest scheduler so a cron trigger sends one sample email.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means a weekly digest scheduler sends at each user's timezone-local Monday 09:00, "
                    "handles DST/daylight saving boundaries, missed-run catch-up, retry idempotency, "
                    "subscription filtering, and scheduled_at/sent_at audit log evidence."
                ),
                "fake_done_risks": (
                    "Only configuring a cron expression or proving one local trigger without timezone, DST, "
                    "catch-up, duplicate-send, subscription, and audit evidence must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include timezone-local schedule checks, DST boundary cases, missed-run catch-up, "
                    "duplicate retry prevention, subscription filtering, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "schedule/timezone-recurrence" in issue for issue in issues)
    assert any("fake-done risks" in issue and "schedule/timezone-recurrence" in issue for issue in issues)
    assert any("evidence preferences" in issue and "schedule/timezone-recurrence" in issue for issue in issues)


def test_agent_first_traceability_blocks_cron_only_scheduled_digest(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a weekly digest scheduler so a cron trigger sends one sample email.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: timezone-local delivery, DST boundaries, missed-run catch-up, "
        "duplicate-send prevention, subscription filtering, and audit proof can be handled later.\n"
        "  Owner: lifecycle messaging owner\n"
        "  Follow-up: create a scheduler correctness ticket.\n"
        "  Acceptance path: GateKeeper can pass after one cron-triggered local digest sends.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat timezone-local delivery, DST, catch-up, subscription filtering, and audit as later residual risk.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(SCHEDULE_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "schedule/timezone-recurrence" in issue for issue in issues)
    assert any("fake-done risks" in issue and "schedule/timezone-recurrence" in issue for issue in issues)
    assert any("evidence preferences" in issue and "schedule/timezone-recurrence" in issue for issue in issues)
    assert any("success criteria" in issue and "notification/subscription-deliverability" in issue for issue in issues)


def test_default_task_anchored_plan_projects_schedule_phase_workflow(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "default-schedule-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before scheduler changes.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nScheduler boundaries.\n", encoding="utf-8")
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=SCHEDULE_TASK_TEXT
        + " 这次请按证据阶段判断：Schedule Contract Inspector 先固定 timezone、DST、missed-run、catch-up、"
        + "subscription 和 audit 样本；Digest Scheduler Builder 再实现调度、发送、补偿、幂等和审计；"
        + "Schedule Evidence Inspector 验证多时区、本地时间、DST 前后、错过执行补偿、重复触发、退订/禁用用户和 audit log。",
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    service.append_alignment_message(created["id"], "确认，采用这个方向。")
    ready = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle_text = Path(ready["bundle_path"]).read_text(encoding="utf-8")
    bundle = load_bundle_text(bundle_text)
    steps = bundle["workflow"]["steps"]
    gatekeeper_inputs = steps[-1]["inputs"]

    assert ready["validation"]["ok"] is True
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]
    assert lint_alignment_bundle_semantics(bundle) == []
    assert alignment_bundle_agreement_traceability_issues(ready, bundle) == []
    assert [step["id"] for step in steps] == [
        "schedule_contract_inspection_step",
        "digest_scheduler_builder_step",
        "temporal_correctness_inspection_step",
        "delivery_audit_inspection_step",
        "schedule_gatekeeper_step",
    ]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "schedule-contract-inspector",
        "digest-scheduler-builder",
        "temporal-correctness-inspector",
        "delivery-audit-inspector",
        "schedule-gatekeeper",
    ]
    assert "build_task_loop" not in {step["id"] for step in steps}
    assert "contract-first workflow" in bundle["workflow"]["collaboration_intent"]
    assert "parallel_group" in bundle["workflow"]["collaboration_intent"]
    assert "cron-only" in bundle["workflow"]["collaboration_intent"]
    assert gatekeeper_inputs["handoffs_from"] == [
        "schedule_contract_inspection_step",
        "digest_scheduler_builder_step",
        "temporal_correctness_inspection_step",
        "delivery_audit_inspection_step",
    ]
    gatekeeper_verifies = gatekeeper_inputs["evidence_query"]["verifies"]
    for verify_ref in [
        "done_when",
        "fake_done",
        "timezone-recurrence",
        "subscription-deliverability",
        "message-delivery",
        "provider-contract",
        "idempotency",
        "audit-log",
        "monitoring",
        "retry-timeout",
        "queue-recovery",
        "locale-i18n",
        "migration-rollback",
        "negative_evidence",
        "local-governance",
    ]:
        assert verify_ref in gatekeeper_verifies
    spec_markdown = bundle["spec"]["markdown"]
    assert "# Execution Strategy" in spec_markdown
    assert "DST" in spec_markdown
    assert "missed-run catch-up" in spec_markdown
    assert "Temporal Correctness Inspector" in spec_markdown
    assert "Delivery Audit Inspector" in spec_markdown
    for audit_field in ("scheduled_at", "due_at", "sent_at", "skipped_reason", "timezone_version", "job_run_id"):
        assert audit_field in spec_markdown
    assert "cron expression" in spec_markdown or "cron-only" in spec_markdown
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Repair Builder" not in bundle_text
    assert "修复 Builder" not in bundle_text
    assert "Guide 只把弱证据" not in bundle_text
    assert "确认，采用这个方向" not in bundle_text


def test_cli_agent_plan_schedule_timezone_rounds_use_parallel_recurrence_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-schedule-timezone",
    }
    task_message = (
        "我要做 weekly digest 定时发送。成功必须证明每个用户按自己的 timezone 本地周一 09:00 收到，"
        "DST/夏令时切换前后不会提前或延后，错过执行后 catch-up 只补一次，"
        "重试/provider replay 不会重复发送，取消订阅、禁用用户、tenant filter、locale filter 都不会误发；"
        "audit log 能追踪 scheduled_at、due_at、sent_at、skipped_reason、timezone_version 和 job_run_id；"
        "monitoring 能发现 missed-run、duplicate-send、timezone drift、DST drift、queue backlog 和 provider failure。"
        "假完成是 cron expression 配好、本地触发一次、只测 UTC、只测一个时区、只看 provider accepted、"
        "没有 DST boundary、没有 catch-up/idempotency negative、没有 unsubscribe/disabled negative、"
        "没有 audit/monitoring/local governance proof。"
    )

    first_summary = _invoke_schedule_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_schedule_plan_round(
        runner,
        sample_workdir,
        message=(
            "补充判断：采用 schedule timezone recurrence contract-first workflow。先由只读 Schedule Contract Inspector "
            "固定 timezone source、user timezone fallback、local Monday 09:00 semantics、DST spring-forward/fall-back samples、"
            "missed-run catch-up window、retry/provider replay idempotency key、subscription/disabled/tenant/locale filters、"
            "provider accepted/delivered/bounced failure surface、scheduled_at/due_at/sent_at/skipped_reason/timezone_version/"
            "job_run_id audit fields、monitoring alerts、migration/backward compatibility 和 local-governance proof targets。"
            "Digest Scheduler Builder 只能读取该 handoff 后实现。然后 Temporal Correctness Inspector 与 Delivery Audit Inspector "
            "并行检查同一个产物：Temporal 验证 multiple timezones、local-time conversion、DST before/after、"
            "missed-run catch-up once、duplicate retry/replay negatives、timezone database/version drift；Delivery Audit 验证 "
            "unsubscribe/disabled/tenant/locale negatives、provider accepted/delivered/failure reconciliation、audit fields、"
            "monitoring alerts、migration compatibility 和 governance。GateKeeper 必须在 cron-only、local-trigger-only、"
            "UTC-only、single-timezone-only、provider-accepted-only、missing DST boundary、missing catch-up/idempotency negative、"
            "missing unsubscribe/disabled negative、missing audit/monitoring、missing migration 或 skipped governance 时 fail closed。"
        ),
        env=env,
    )
    _assert_schedule_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_schedule_plan_round(
        runner,
        sample_workdir,
        message="确认，采用这个方向。",
        env=env,
    )
    _assert_schedule_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _schedule_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_schedule_bundle(bundle_text)


def _invoke_schedule_plan_round(
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


def _assert_schedule_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Schedule Contract Inspector" in agreement_text
    assert "Digest Scheduler Builder" in agreement_text
    assert "Temporal Correctness Inspector" in agreement_text
    assert "Delivery Audit Inspector" in agreement_text
    assert "parallel" in agreement_text or "并行" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Repair Builder" not in agreement_text


def _assert_schedule_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("timezone", "DST", "catch-up", "subscription", "audit", "monitoring"):
        assert term in ready_projection_text
    assert "确认，采用这个方向" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _schedule_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_schedule_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "schedule-contract-inspector",
        "digest-scheduler-builder",
        "temporal-correctness-inspector",
        "delivery-audit-inspector",
        "schedule-gatekeeper",
    ]
    names_by_key = {role["key"]: role["name"] for role in bundle["role_definitions"]}
    assert names_by_key["temporal-correctness-inspector"] == "时间正确性 Inspector"
    assert names_by_key["delivery-audit-inspector"] == "投递审计 Inspector"
    assert workflow["preset"] == "schedule-timezone-contract-parallel-recurrence"
    assert [step["id"] for step in workflow["steps"]] == [
        "schedule_contract_inspection_step",
        "digest_scheduler_builder_step",
        "temporal_correctness_inspection_step",
        "delivery_audit_inspection_step",
        "schedule_gatekeeper_step",
    ]
    assert workflow["steps"][2]["parallel_group"] == "schedule_timezone_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "schedule_timezone_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "schedule_contract_inspection_step",
        "digest_scheduler_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "schedule_contract_inspection_step",
        "digest_scheduler_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "schedule_contract_inspection_step",
        "digest_scheduler_builder_step",
        "temporal_correctness_inspection_step",
        "delivery_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "timezone-recurrence",
        "subscription-deliverability",
        "message-delivery",
        "provider-contract",
        "idempotency",
        "retry-timeout",
        "queue-recovery",
        "locale-i18n",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Temporal Correctness Inspector" in bundle_text
    assert "Delivery Audit Inspector" in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Repair Builder" not in bundle_text
    assert "修复 Builder" not in bundle_text
    assert "Guide 只把弱证据" not in bundle_text
    assert "usage-quota-contract-parallel-metering" not in bundle_text
