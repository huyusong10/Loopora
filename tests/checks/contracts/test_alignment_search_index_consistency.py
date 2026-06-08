from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from loopora.alignment_traceability_categories import agent_candidate_success_surface_categories
from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


SEARCH_INDEX_TASK_TEXT = (
    "我要给知识库做全文搜索索引和重建。成功必须证明新建、更新、删除文档会增量同步到 search index，"
    "权限和 tenant ACL 变化会立刻从结果中过滤，reindex/backfill 可重跑且幂等，"
    "index lag / stale index 有监控告警，搜索结果不会泄露已删除或无权限文档，排序和分页稳定，"
    "audit log 记录 reindex run、watermark/cursor 和失败重试；只有本地搜索能返回一个公开文档必须阻断。"
)


def test_cli_agent_plan_search_index_rounds_use_parallel_consistency_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-search-index-consistency",
    }
    task_message = (
        "Plan a governed Loop to add knowledge-base full-text search indexing and rebuild support. Success must prove "
        "create, update, and delete document events incrementally sync into the search index; tenant ACL and permission "
        "changes immediately filter results; reindex/backfill reruns are idempotent; watermark/cursor failure recovery "
        "works; index lag and stale index alerts exist; deleted or unauthorized documents never leak; pagination and "
        "sorting stay stable; audit logs cover reindex runs, cursor/watermark, and failed retries. Fake done is only "
        "local search returning one public document, a green index job, row-count sample, dashboard latest, missing ACL "
        "negative cases, missing deleted-document proof, missing reindex idempotency, missing cursor recovery, missing "
        "lag alert, or skipped local governance."
    )

    first_summary = _invoke_search_index_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_search_index_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a search-index contract-first workflow. Start with a read-only Search Index "
            "Contract Inspector freezing source document event schema, create/update/delete semantics, tenant ACL and "
            "permission-change rules, index alias/versioning, reindex/backfill cursor and idempotency, watermark recovery, "
            "lag SLO/alerts, pagination/sort stability samples, audit fields, retry/DLQ behavior, and local governance "
            "proof targets. Search Index Builder implements only after that handoff. Then run Index Consistency Inspector "
            "and Access Freshness Inspector in parallel: Index Consistency verifies create/update/delete fixtures, "
            "deleted-document negative search, reindex/backfill idempotent reruns, cursor recovery after failure, stale "
            "index lag alert, stable pagination and sorting; Access Freshness verifies tenant ACL changes, permission "
            "revocation, unauthorized-document negative results, cross-tenant negatives, audit logs, retry/DLQ evidence, "
            "and monitoring. GateKeeper must fail closed on local-search-only, green-index-job-only, row-count-sample-only, "
            "dashboard-latest-only, missing ACL negatives, missing deleted-document proof, missing reindex idempotency, "
            "missing cursor recovery, missing lag alert, missing audit, or skipped local governance."
        ),
        env=env,
    )
    _assert_search_index_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_search_index_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this search index direction.",
        env=env,
    )
    _assert_search_index_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _search_index_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_search_index_bundle(bundle_text)


def _invoke_search_index_plan_round(
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


def _assert_search_index_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Search Index Contract Inspector" in agreement_text
    assert "Search Index Builder" in agreement_text
    assert "Index Consistency Inspector" in agreement_text
    assert "Access Freshness Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Search Quality Builder" not in agreement_text
    assert "Evaluation Baseline Inspector" not in agreement_text


def _assert_search_index_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("search index", "ACL", "reindex", "cursor", "lag", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this search index direction" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _search_index_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_search_index_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "search-index-contract-inspector",
        "search-index-builder",
        "index-consistency-inspector",
        "access-freshness-inspector",
        "search-index-gatekeeper",
    ]
    assert workflow["preset"] == "search-index-contract-parallel-consistency"
    assert [step["id"] for step in workflow["steps"]] == [
        "search_index_contract_inspection_step",
        "search_index_builder_step",
        "index_consistency_inspection_step",
        "access_freshness_inspection_step",
        "search_index_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["search_index_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "search_index_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "search_index_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "search_index_contract_inspection_step",
        "search_index_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "search_index_contract_inspection_step",
        "search_index_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "search_index_contract_inspection_step",
        "search_index_builder_step",
        "index_consistency_inspection_step",
        "access_freshness_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "search-index",
        "permission-auth",
        "tenant-isolation",
        "idempotency",
        "monitoring",
        "audit-log",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Search Index Consistency Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "search-quality-evaluation" not in bundle_text
    assert "Evaluation Baseline Inspector" not in bundle_text
    assert "Confirm; use this search index direction" not in bundle_text


def test_success_categories_detect_search_index_consistency_without_quality_eval_false_positive() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means knowledge-base search index consistency proves incremental indexing for create/update/delete, "
            "tenant ACL filtering, deleted-document removal, reindex backfill idempotency, watermark cursor recovery, "
            "stale index monitoring, stable pagination, and audit proof."
        )
    ]
    quality_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means help-center semantic search Top-5 quality improves across an eval set with human review "
            "for relevance and hallucination risk."
        )
    ]

    assert "search/index-consistency" in labels
    assert "permission/auth" in labels
    assert "regression/monitoring-guard" in labels
    assert "search/index-consistency" not in quality_labels
    assert "evaluation/eval-set" in quality_labels


def test_fake_done_and_evidence_categories_detect_local_search_only_index_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(SEARCH_INDEX_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(SEARCH_INDEX_TASK_TEXT)
    ]

    assert "search/index-consistency" in fake_labels
    assert "search/index-consistency" in evidence_labels
    assert "permission/audit" in fake_labels
    assert "permission/auth" in evidence_labels


def test_alignment_agreement_requires_search_index_consistency_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a knowledge-base search box so local search returns one public document.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means full-text search index consistency proves create, update, and delete document events "
                    "incrementally sync to the search index, permission and tenant ACL changes filter results, "
                    "reindex/backfill reruns are idempotent, index lag and stale index monitoring alerts exist, "
                    "deleted or unauthorized documents never leak, sorting and pagination are stable, and audit records "
                    "reindex run, watermark/cursor, and failed retry proof."
                ),
                "fake_done_risks": (
                    "Only local search returning one public document without incremental indexing, ACL filtering, "
                    "deleted-document removal, reindex/backfill idempotency, watermark/cursor recovery, stale index "
                    "monitoring, stable pagination, audit, and retry proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include create/update/delete index sync, tenant ACL filtering, deleted-document "
                    "negative search, reindex/backfill idempotency, watermark/cursor recovery, index lag or stale index "
                    "monitoring, pagination stability, audit logs, and retry proof."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "search/index-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "search/index-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "search/index-consistency" in issue for issue in issues)


def test_agent_first_traceability_blocks_local_search_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a knowledge-base search box so local search returns one public document.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 暂不把 search index 的增量同步、ACL 过滤或重建一致性作为本轮阻断项。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: incremental indexing for create/update/delete, tenant ACL filtering, "
        "deleted-document removal, reindex/backfill idempotency, watermark/cursor recovery, stale index monitoring, "
        "stable pagination, audit, and retry proof can be handled later.\n"
        "  Owner: search owner\n"
        "  Follow-up: add search index hardening later.\n"
        "  Acceptance path: GateKeeper can pass after local search returns one public document.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现本地搜索返回一个公开文档，不处理 incremental indexing、tenant ACL filtering、deleted-document removal、"
        "reindex/backfill idempotency、watermark/cursor recovery、stale index monitoring、stable pagination、audit 或 retry proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat incremental indexing, tenant ACL filtering, deleted-document removal, reindex/backfill idempotency, "
        "watermark/cursor recovery, stale index monitoring, stable pagination, audit, and retry proof as later residual risk; "
        "only check local search returns one public document.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(SEARCH_INDEX_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "search/index-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "search/index-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "search/index-consistency" in issue for issue in issues)
    assert any("success criteria" in issue and "audit/log" in issue for issue in issues)
    assert any("evidence preferences" in issue and "permission/auth" in issue for issue in issues)
