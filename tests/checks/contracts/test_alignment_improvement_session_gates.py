from __future__ import annotations

from pathlib import Path

from alignment_test_support import (
    _confirm_alignment_agreement,
    _create_alignment_improvement_source_bundle,
    _wait_for_status,
)
from loopora.bundles import lint_alignment_bundle_semantics, load_bundle_text
from loopora.executor import FakeCodexExecutor
from loopora.executor_alignment_readiness_responses import alignment_chinese_improvement_readiness_evidence
from loopora.executor_alignment_responses import alignment_response


class VagueRefactorImprovementExecutor(FakeCodexExecutor):
    def _build_payload(self, request) -> dict:
        if request.role != "alignment":
            return super()._build_payload(request)
        payload = alignment_response(
            status="question",
            assistant_message="请确认这份改进协议。",
            needs_user_input=True,
            bundle_yaml="",
            phase="agreement",
        )
        payload["agreement_summary"] = "保留来源 Loop 的稳定意图，只基于用户反馈调整证据、角色和 workflow 治理面。"
        payload["readiness_checklist"] = {
            "loop_fit": True,
            "task_scope": True,
            "success_surface": True,
            "fake_done_risks": True,
            "evidence_preferences": True,
            "execution_strategy": True,
            "residual_risk_policy": True,
            "judgment_tradeoffs": True,
            "local_governance": True,
            "role_posture": True,
            "workflow_shape": True,
            "explicit_confirmation": False,
        }
        payload["readiness_evidence"] = {
            **alignment_chinese_improvement_readiness_evidence(open_questions="等待用户明确确认这份改进协议。"),
            "success_surface": (
                "成功意味着改进后的独立 bundle 保持既有用户目标，同时让 evidence gap、role handoff、"
                "workflow control point 和 GateKeeper blocker 都可观察、可验证。"
            ),
            "workdir_facts": "已观察到的来源上下文是当前 bundle；具体技术栈仍未知，需由后续角色验证。",
        }
        return payload


def test_alignment_improvement_session_blocks_generic_final_bundle(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_improvement_generic_bundle")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "what source intent, workdir, defaults, or posture is preserved" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "improvement bundle must state what source intent, workdir, defaults, or posture is preserved"
        in event["payload"].get("error", "")
        for event in events
    )


def test_alignment_improvement_session_blocks_vague_improvement_agreement(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_improvement_missing_delta")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop.",
        start_immediately=True,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_improvement_incomplete"
        and "improvement_delta" in event["payload"].get("missing", [])
        for event in events
    )


def test_alignment_improvement_session_requires_completion_mode_delta_for_rounds_source(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(
        service,
        sample_spec_file,
        sample_workdir,
        completion_mode="rounds",
    )

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    assert session["working_agreement"]["source"]["source_completion_mode"] == "rounds"
    assert "improvement completion mode delta" in session["transcript"][-1]["content"]
    assert "improvement_completion_mode_delta" not in session["transcript"][-1]["content"]
    prompt_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "prompt.md").read_text(encoding="utf-8")
    assert "Source completion mode: rounds" in prompt_text
    assert "conversion to evidence-backed GateKeeper task verdicts" in prompt_text
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_improvement_incomplete"
        and "improvement_completion_mode_delta" in event["payload"].get("missing", [])
        for event in events
    )


def test_alignment_improvement_session_blocks_vague_refactor_without_task_scoped_delta(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    service.executor_factory = lambda: VagueRefactorImprovementExecutor(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="这份 Loop 太保守，不够重构，帮我改激进一点。",
        start_immediately=True,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_improvement_incomplete"
        and "improvement_refactor_delta" in event["payload"].get("missing", [])
        for event in events
    )


def test_alignment_improvement_session_projects_detailed_refactor_feedback_to_long_chain_workflow(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "tests").mkdir(exist_ok=True)
    (sample_workdir / "AGENTS.md").write_text("# Rules\n\nRead design before search refactors.\n", encoding="utf-8")
    (sample_workdir / "design" / "README.md").write_text("# Design\n\nSearch relevance boundaries.\n", encoding="utf-8")
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message=(
            "这份 Loop 太保守，不够重构，帮我改激进一点。需要把过大的 Search Builder 拆成 baseline、"
            "query rewrite、retrieval、ranking、evidence hardening 几个阶段；成功不是角色变多，而是证明复杂度"
            "没有只是换地方、搜索结果没有回归、证据路径可复验。"
        ),
        start_immediately=True,
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    assert "任务范围内的重构 delta" in agreement["working_agreement"]["readiness_evidence"]["task_scope"]
    assert "复杂度只是换地方" in agreement["working_agreement"]["readiness_evidence"]["fake_done_risks"]
    assert "用户行为回归" in agreement["working_agreement"]["readiness_evidence"]["role_posture"]
    service.append_alignment_message(created["id"], "确认，采用这份重构改进协议。")
    ready = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle_text = Path(ready["bundle_path"]).read_text(encoding="utf-8")
    bundle = load_bundle_text(bundle_text)
    steps = bundle["workflow"]["steps"]
    gatekeeper_inputs = steps[-1]["inputs"]

    assert ready["validation"]["ok"] is True
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]
    assert lint_alignment_bundle_semantics(bundle) == []
    assert bundle["workflow"]["preset"] == "search-refactor-improvement-long-chain"
    assert [step["id"] for step in steps] == [
        "baseline_inspection_step",
        "query_rewrite_builder_step",
        "retrieval_builder_step",
        "ranking_builder_step",
        "regression_inspection_step",
        "evidence_hardening_builder_step",
        "refactor_gatekeeper_step",
    ]
    assert gatekeeper_inputs["handoffs_from"] == [
        "baseline_inspection_step",
        "regression_inspection_step",
        "evidence_hardening_builder_step",
    ]
    assert gatekeeper_inputs["evidence_query"]["verifies"] == [
        "task-scoped-refactor",
        "complexity-moved",
        "behavior-regression",
        "evidence-path",
        "local-governance",
    ]
    assert "复杂度没有只是换地方" in bundle_text
    assert "搜索结果没有回归" in bundle_text
    assert "证据路径可复验" in bundle_text
    assert "source_bundle_id:" not in bundle_text
    assert "revision:" not in bundle_text
