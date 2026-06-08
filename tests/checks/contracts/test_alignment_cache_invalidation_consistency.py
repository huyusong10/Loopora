from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from loopora.alignment_traceability_categories import agent_candidate_success_surface_categories
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


PRICE_CACHE_TASK_TEXT = (
    "我要做商品价格更新后的缓存失效。成功必须证明管理员改价后 PDP、购物车、checkout、API 和 CDN/Redis/read-model "
    "缓存都在约定 TTL 内刷新，用户不能用旧价格下单，stale cache / stale read 必须触发回源或失效，"
    "地区和货币缓存 key 不能串，rollback 能恢复旧价并清理新缓存，"
    "audit log 能追踪 invalidation event 和 cache key；只有数据库价格更新成功或手动刷新页面看到新价必须阻断。"
)


def test_cli_agent_plan_cache_invalidation_rounds_use_parallel_consistency_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-cache-invalidation-consistency",
    }
    task_message = (
        "Plan a governed Loop for product price cache invalidation. Success must prove that after an admin price "
        "update, PDP, cart, checkout, public API, CDN cache, Redis cache, and read-model cache refresh within the "
        "agreed TTL; stale cache / stale read must refetch or invalidate; users cannot checkout with an old price; "
        "region and currency cache keys cannot cross-contaminate; rollback restores the old price and cleans new "
        "cache entries; audit log records invalidation event, cache keys, actor, old/new price, region/currency, "
        "and rollback; monitoring alerts on invalidation failure and stale-price checkout attempts. Fake done is only "
        "database update success, manual refresh showing a new price, purging one cache layer, one happy-path PDP, "
        "or docs-only TTL policy. Evidence should include cache-key inventory, TTL boundary checks, stale-read negatives, "
        "CDN/Redis/read-model invalidation proof, checkout old-price negative, region/currency key isolation, rollback "
        "cleanup proof, audit reviewability, monitoring alerts, and local governance."
    )

    first_summary = _invoke_cache_invalidation_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_cache_invalidation_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a cache consistency contract-first workflow. Start with Cache Contract Inspector "
            "freezing price surfaces, cache-key inventory, TTL/SLA, PDP/cart/checkout/API/CDN/Redis/read-model boundaries, "
            "stale-read behavior, region/currency key isolation, rollback cleanup, audit, monitoring, and local-governance "
            "proof targets. Price Cache Builder may implement only after that handoff. Then run Stale Read Evidence "
            "Inspector and Checkout Price Integrity Inspector in parallel: Stale Read verifies CDN/Redis/read-model "
            "invalidation, TTL boundary, refetch/invalidate behavior, region/currency key isolation, and rollback cleanup; "
            "Checkout Integrity verifies PDP/cart/checkout/API old-price negatives, payment/checkout blocking, audit "
            "reviewability, monitoring alerts, and governance. GateKeeper must fail closed on database-update-only, "
            "manual-refresh-only, single-cache-layer purge, one happy-path PDP, docs-only TTL, missing stale-read negatives, "
            "missing checkout old-price negative, missing key isolation, missing rollback cleanup, missing audit, or "
            "missing monitoring evidence."
        ),
        env=env,
    )
    _assert_cache_invalidation_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_cache_invalidation_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this cache consistency contract-first parallel evidence direction.",
        env=env,
    )
    _assert_cache_invalidation_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _cache_invalidation_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_cache_invalidation_bundle(bundle_text)


def _invoke_cache_invalidation_plan_round(
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


def _assert_cache_invalidation_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Cache Contract Inspector" in agreement_text
    assert "Stale Read Evidence Inspector" in agreement_text
    assert "Checkout Price Integrity Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_cache_invalidation_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("cache invalidation", "stale-read", "old price", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this cache consistency" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _cache_invalidation_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_cache_invalidation_bundle(bundle_text: str) -> None:
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "cache-invalidation-contract-parallel-consistency"
    assert [step["id"] for step in workflow["steps"]] == [
        "cache_contract_inspection_step",
        "price_cache_builder_step",
        "stale_read_evidence_inspection_step",
        "checkout_price_integrity_inspection_step",
        "cache_consistency_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["cache_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "cache_invalidation_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "cache_invalidation_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "cache_contract_inspection_step",
        "price_cache_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "cache_contract_inspection_step",
        "price_cache_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "cache_contract_inspection_step",
        "price_cache_builder_step",
        "stale_read_evidence_inspection_step",
        "checkout_price_integrity_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "cache-invalidation",
        "payment-refund-billing",
        "audit-log",
        "monitoring",
        "migration-rollback",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Cache Invalidation Consistency Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this cache consistency" not in bundle_text


def test_success_categories_separate_cache_invalidation_from_data_lifecycle() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means product price changes prove CDN cache, Redis cache, read-model invalidation, "
            "TTL freshness, stale read prevention, cache-key isolation, and rollback cache cleanup."
        )
    ]

    assert "cache/invalidation-consistency" in labels
    assert "data-lifecycle/deletion-retention" not in labels


def test_alignment_agreement_requires_price_cache_invalidation_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship product price editing so the database price updates successfully.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means product price editing proves PDP, cart, checkout, API, CDN cache, Redis cache, "
                    "and read-model invalidation refresh within TTL, stale reads refetch or invalidate, old prices cannot "
                    "be used at checkout, region and currency cache keys are isolated, rollback cleans the new cache, "
                    "and audit records invalidation event and cache key."
                ),
                "fake_done_risks": (
                    "Only proving database update success or manual page refresh without cache invalidation, TTL freshness, "
                    "stale read prevention, rollback cleanup, and audit evidence must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include cache invalidation across PDP, cart, checkout, API, CDN, Redis, read-model, "
                    "TTL freshness checks, stale read refetch proof, cache-key isolation, rollback cleanup, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "cache/invalidation-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "cache/invalidation-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "cache/invalidation-consistency" in issue for issue in issues)
    assert not any("data-lifecycle/deletion-retention" in issue for issue in issues)


def test_agent_first_traceability_blocks_database_only_price_cache_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship product price editing so the database price updates successfully.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: CDN cache, Redis cache, read-model invalidation, stale read prevention, TTL freshness, "
        "cache-key isolation, rollback cache cleanup, and invalidation audit can be handled later.\n"
        "  Owner: pricing owner\n"
        "  Follow-up: create cache invalidation follow-up.\n"
        "  Acceptance path: GateKeeper can pass after the database price update and manual refresh show the new price.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat cache invalidation, stale reads, TTL freshness, cache-key isolation, rollback cleanup, and audit "
        "as later residual risk; only check database update and manual refresh.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(PRICE_CACHE_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "cache/invalidation-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "cache/invalidation-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "cache/invalidation-consistency" in issue for issue in issues)
    assert not any("data-lifecycle/deletion-retention" in issue for issue in issues)
