from __future__ import annotations

from pathlib import Path

from alignment_test_support import _wait_for_status
from loopora.alignment_traceability_rules import alignment_bundle_agreement_traceability_issues
from loopora.bundles import lint_alignment_bundle_semantics, load_bundle_text


SEARCH_QUALITY_TASK_TEXT = (
    "我要优化 help-center semantic search。成功必须证明 Top-5 结果质量提升，eval set 覆盖真实查询、负例和回归样本，"
    "人工评审要看 relevance、groundedness 和 hallucination risk；只有一个 demo query 看起来更好或 benchmark 分数单点上涨必须阻断。"
)


def test_search_quality_alignment_agreement_and_bundle_use_eval_first_workflow(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "search-quality-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before search changes.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nSearch quality boundaries.\n", encoding="utf-8")
    service = service_factory(scenario="success")

    created = service.create_alignment_session(workdir=workdir, message=SEARCH_QUALITY_TASK_TEXT)
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    assert not Path(agreement["bundle_path"]).exists()
    agreement_text = agreement["working_agreement"]["summary"]
    agreement_evidence = agreement["working_agreement"]["readiness_evidence"]
    assert "eval-first Loop" in agreement_text
    assert "Evaluation Baseline Inspector -> Search Quality Builder -> Quality Evidence Inspector -> Search Quality GateKeeper" in agreement_evidence["workflow_shape"]
    assert "Guide -> Repair Builder" not in agreement_text
    assert "Guide -> Repair Builder" not in agreement_evidence["workflow_shape"]

    service.append_alignment_message(created["id"], "确认，采用这个方向。")
    ready = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle = load_bundle_text(Path(ready["bundle_path"]).read_text(encoding="utf-8"))
    steps = bundle["workflow"]["steps"]
    gatekeeper_inputs = steps[-1]["inputs"]
    spec_markdown = bundle["spec"]["markdown"]
    final_message = ready["transcript"][-1]["content"]

    assert ready["validation"]["ok"] is True
    assert "eval-first search quality workflow" in final_message
    assert "Guide 修复轮次" not in final_message
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]
    assert lint_alignment_bundle_semantics(bundle) == []
    assert alignment_bundle_agreement_traceability_issues(ready, bundle) == []
    assert bundle["workflow"]["preset"] == "search-quality-evaluation"
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "evaluation-baseline-inspector",
        "search-quality-builder",
        "quality-evidence-inspector",
        "search-quality-gatekeeper",
    ]
    assert [step["id"] for step in steps] == [
        "evaluation_baseline_step",
        "search_quality_builder_step",
        "quality_evidence_step",
        "search_quality_gatekeeper_step",
    ]
    assert steps[1]["inputs"]["handoffs_from"] == ["evaluation_baseline_step"]
    assert gatekeeper_inputs["handoffs_from"] == [
        "evaluation_baseline_step",
        "search_quality_builder_step",
        "quality_evidence_step",
    ]
    assert gatekeeper_inputs["evidence_query"]["verifies"] == [
        "eval-set",
        "human-review",
        "search-index",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ]
    assert "demo-query-only" in spec_markdown
    assert "single-score-only" in spec_markdown
    assert "修复 Guide Notes" not in spec_markdown
    assert "修复 Builder Notes" not in spec_markdown
