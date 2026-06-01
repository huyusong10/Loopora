from __future__ import annotations

from pathlib import Path

from loopora.alignment_readiness_rules import alignment_governance_marker_responsibilities_present
from loopora.service_alignment_agreement_stage import (
    alignment_agreement_ready_stage_plan,
    alignment_agreement_readiness_checklist_issues,
    alignment_agreement_text_snippet,
    alignment_agreement_working_agreement,
    alignment_merge_improvement_context,
    alignment_message_confirms_agreement,
    alignment_user_message_stage_plan,
    alignment_visible_agreement_message,
)
from loopora.service_alignment_language import (
    alignment_agreement_language_issues,
    alignment_assistant_message_language_issue,
    alignment_bundle_language_issues,
)
from loopora.service_alignment_stage import (
    AlignmentAgreementBlockCandidate,
    AlignmentBundleStageGate,
    alignment_agreement_block_plan,
    alignment_block_message,
    alignment_bundle_stage_error,
    alignment_bundle_workdir_fact_issues,
    alignment_clarifying_reframe_message,
    alignment_clarifying_stage_plan,
    alignment_fallback_assistant_message,
    alignment_improvement_bundle_issues,
    alignment_output_message_plan,
)
from loopora.service_alignment_traceability_projection import (
    alignment_bundle_agreement_projection_text,
    alignment_bundle_runtime_responsibility_projection_text,
    alignment_governance_marker_responsibility_issues,
    alignment_session_user_task_text,
    alignment_traceability_term_is_present,
    normalize_alignment_traceability_text,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_stage_bundle_issue_selectors_have_dedicated_boundary() -> None:
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert alignment_bundle_workdir_fact_issues.__module__ == "loopora.service_alignment_stage_bundle_issues"
    assert alignment_improvement_bundle_issues.__module__ == "loopora.service_alignment_stage_bundle_issues"
    assert alignment_output_message_plan.__module__ == "loopora.service_alignment_stage_messages"
    assert AlignmentAgreementBlockCandidate.__module__ == "loopora.service_alignment_stage_messages"
    assert alignment_clarifying_stage_plan.__module__ == "loopora.service_alignment_stage_messages"
    assert alignment_governance_marker_responsibilities_present.__module__ == "loopora.alignment_readiness_governance"
    assert "service_alignment_stage_bundle_issues.py" in design_source
    assert "service_alignment_stage_messages.py" in design_source
    assert "alignment_readiness_governance.py" in design_source


def test_alignment_agreement_working_agreement_projects_stable_ready_payload() -> None:
    agreement = alignment_agreement_working_agreement(
        {
            "agreement_summary": "  Confirmed direction.  ",
            "readiness_checklist": {"loop_fit": True, "explicit_confirmation": True},
            "readiness_evidence": {"loop_fit": "Slow feedback needs governed evidence."},
        },
        captured_at="2026-05-29T00:00:00Z",
    )

    assert agreement == {
        "summary": "Confirmed direction.",
        "readiness_checklist": {"loop_fit": True, "explicit_confirmation": False},
        "readiness_evidence": {"loop_fit": "Slow feedback needs governed evidence."},
        "captured_at": "2026-05-29T00:00:00Z",
        "confirmed_at": "",
        "confirmation_message": "",
    }


def test_alignment_agreement_working_agreement_fails_closed_for_malformed_payload_parts() -> None:
    agreement = alignment_agreement_working_agreement(
        {
            "agreement_summary": None,
            "readiness_checklist": ["bad"],
            "readiness_evidence": ["bad"],
        },
        captured_at="now",
    )

    assert agreement["summary"] == ""
    assert agreement["readiness_checklist"] == {"explicit_confirmation": False}
    assert agreement["readiness_evidence"] == {}


def test_alignment_agreement_ready_stage_plan_projects_confirmation_boundary() -> None:
    working_agreement = {
        "summary": "Confirmed direction.",
        "readiness_checklist": {"loop_fit": True, "explicit_confirmation": False},
    }

    plan = alignment_agreement_ready_stage_plan(
        working_agreement,
        assistant_message="Please confirm this working agreement.",
        prefers_chinese=False,
    )

    assert plan.update_fields == {
        "alignment_stage": "agreement_ready",
        "working_agreement": working_agreement,
    }
    assert plan.output_updates["assistant_message"] == "Please confirm this working agreement."
    assert plan.output_updates["needs_user_input"] is True
    assert plan.output_updates["bundle_yaml"] == ""
    assert [option["id"] for option in plan.output_updates["decision_options"]] == [
        "confirm_agreement",
        "adjust_agreement",
    ]
    assert plan.output_updates["decision_options"][0]["recommended"] is True
    assert plan.event_type == "alignment_agreement_ready"
    assert plan.event_payload == {
        "alignment_stage": "agreement_ready",
        "working_agreement": working_agreement,
    }


def test_alignment_merge_improvement_context_preserves_source_metadata() -> None:
    previous = {
        "mode": "improvement",
        "source": {"source_bundle_id": "bundle_source"},
        "seed_bundle_metadata": {"name": "Source"},
    }
    working_agreement = {
        "summary": "New improvement agreement.",
        "source": {"source_bundle_id": "explicit_new_source"},
    }

    merged = alignment_merge_improvement_context(previous, working_agreement)

    assert merged == {
        "summary": "New improvement agreement.",
        "mode": "improvement",
        "source": {"source_bundle_id": "explicit_new_source"},
        "seed_bundle_metadata": {"name": "Source"},
    }
    assert working_agreement == {
        "summary": "New improvement agreement.",
        "source": {"source_bundle_id": "explicit_new_source"},
    }


def test_alignment_merge_improvement_context_ignores_non_improvement_previous_agreement() -> None:
    working_agreement = {"summary": "Fresh agreement."}

    assert alignment_merge_improvement_context({"mode": "standard", "source": {"id": "ignored"}}, working_agreement) is working_agreement
    assert alignment_merge_improvement_context(["bad"], working_agreement) is working_agreement


def test_alignment_visible_agreement_message_projects_english_confirmation_surface() -> None:
    message = alignment_visible_agreement_message(
        {
            "summary": "Confirmed direction.",
            "readiness_evidence": {
                "loop_fit": "Later rounds need new evidence.",
                "workflow_shape": "Builder, Inspector, GateKeeper.",
                "workdir_facts": "AGENTS.md exists.",
            },
        },
        prefers_chinese=False,
    )

    assert message.startswith("Please confirm this working agreement.")
    assert "Summary: Confirmed direction." in message
    assert "Loopora fit: Later rounds need new evidence." in message
    assert "Run-flow shape: Builder, Inspector, GateKeeper." in message
    assert "Workflow shape:" not in message
    assert "Project facts: AGENTS.md exists." in message


def test_alignment_visible_agreement_message_projects_chinese_confirmation_surface() -> None:
    message = alignment_visible_agreement_message(
        {
            "summary": "已确认方向。",
            "readiness_evidence": {
                "loop_fit": "后续轮次需要新证据。",
                "workflow_shape": "Builder 到 GateKeeper。",
                "workdir_facts": "存在 AGENTS.md。",
            },
        },
        prefers_chinese=True,
    )

    assert message.startswith("请先确认这份工作协议。")
    assert "摘要：已确认方向。" in message
    assert "为什么用 Loopora：后续轮次需要新证据。" in message
    assert "运行流程形状：Builder 到 GateKeeper。" in message
    assert "workflow 形状：" not in message
    assert "项目事实：存在 AGENTS.md。" in message


def test_alignment_agreement_text_snippet_collapses_space_and_truncates() -> None:
    assert alignment_agreement_text_snippet("  a   b\nc  ", limit=20) == "a b c"
    assert alignment_agreement_text_snippet("abcdef", limit=4) == "abc…"


def test_alignment_message_confirmation_allows_no_change_clause() -> None:
    assert alignment_message_confirms_agreement("可以，不需要修改，继续。") is True
    assert alignment_message_confirms_agreement("可以，但是不需要修改，继续。") is True
    assert alignment_message_confirms_agreement("Approved, no changes, proceed.") is True


def test_alignment_message_confirmation_treats_requested_changes_as_adjustments() -> None:
    assert alignment_message_confirms_agreement("可以，但把证据偏好改成浏览器截图和命令输出。") is False
    assert alignment_message_confirms_agreement("Looks good, but add a stricter proof gate.") is False
    assert alignment_message_confirms_agreement("no") is False


def test_alignment_user_message_stage_plan_confirms_agreement() -> None:
    plan = alignment_user_message_stage_plan(
        {
            "alignment_stage": "agreement_ready",
            "status": "waiting_user",
            "working_agreement": {"readiness_checklist": {"loop_fit": True}},
        },
        "确认，就这样继续。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    agreement = plan.update_fields["working_agreement"]

    assert plan.update_fields["alignment_stage"] == "confirmed"
    assert agreement["readiness_checklist"]["explicit_confirmation"] is True
    assert agreement["confirmed_at"] == "2026-05-29T00:00:00Z"
    assert agreement["confirmation_message"] == "确认，就这样继续。"
    assert plan.event_type == "alignment_agreement_confirmed"
    assert plan.event_payload == {"alignment_stage": "confirmed"}


def test_alignment_user_message_stage_plan_reopens_agreement_for_adjustment() -> None:
    plan = alignment_user_message_stage_plan(
        {
            "alignment_stage": "agreement_ready",
            "status": "waiting_user",
            "working_agreement": {
                "readiness_checklist": {"loop_fit": True, "explicit_confirmation": True},
                "confirmed_at": "old",
                "confirmation_message": "old",
            },
        },
        "先别确认，把证据偏好调整成命令输出优先。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    agreement = plan.update_fields["working_agreement"]

    assert plan.update_fields["alignment_stage"] == "clarifying"
    assert agreement["readiness_checklist"]["explicit_confirmation"] is False
    assert agreement["confirmed_at"] == ""
    assert agreement["confirmation_message"] == ""
    assert plan.event_type == "alignment_agreement_reopened"
    assert plan.event_payload == {"alignment_stage": "clarifying"}


def test_alignment_user_message_stage_plan_starts_ready_review() -> None:
    plan = alignment_user_message_stage_plan(
        {
            "alignment_stage": "ready",
            "status": "ready",
            "bundle_path": "/tmp/alignment.yaml",
            "working_agreement": {"summary": "Confirmed direction."},
        },
        "请按当前 bundle 再审查一次证据边界。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    agreement = plan.update_fields["working_agreement"]

    assert plan.update_fields["alignment_stage"] == "ready_review"
    assert agreement["ready_review"] == {
        "feedback": "请按当前 bundle 再审查一次证据边界。",
        "requested_at": "2026-05-29T00:00:00Z",
        "source_status": "ready",
    }
    assert plan.event_type == "alignment_ready_review_started"
    assert plan.event_payload == {
        "alignment_stage": "ready_review",
        "feedback": "请按当前 bundle 再审查一次证据边界。",
        "bundle_path": "/tmp/alignment.yaml",
    }


def test_alignment_user_message_stage_plan_reopens_unconfirmed_failed_session() -> None:
    plan = alignment_user_message_stage_plan(
        {"alignment_stage": "clarifying", "status": "failed"},
        "继续补齐。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    assert plan.update_fields == {"alignment_stage": "clarifying"}
    assert plan.event_type == ""
    assert plan.event_payload is None


def test_alignment_agreement_readiness_checklist_issues_ignore_confirmation_gate() -> None:
    readiness_keys = ["loop_fit", "task_scope", "explicit_confirmation"]

    assert alignment_agreement_readiness_checklist_issues(["bad"], readiness_keys=readiness_keys) == ["readiness_checklist"]
    assert alignment_agreement_readiness_checklist_issues(
        {"loop_fit": True, "task_scope": False, "explicit_confirmation": False},
        readiness_keys=readiness_keys,
    ) == ["task_scope"]


def test_alignment_agreement_language_issues_are_disabled_when_chinese_is_not_preferred() -> None:
    assert (
        alignment_agreement_language_issues(
            {
                "agreement_summary": "English agreement.",
                "readiness_evidence": {"loop_fit": "English evidence."},
            },
            evidence_keys=["loop_fit"],
            prefers_chinese=False,
        )
        == []
    )


def test_alignment_agreement_language_issues_report_user_visible_non_chinese_fields() -> None:
    assert alignment_agreement_language_issues(
        {
            "agreement_summary": "English agreement.",
            "readiness_evidence": {
                "loop_fit": "需要持续证据。",
                "task_scope": "English scope.",
            },
        },
        evidence_keys=["loop_fit", "task_scope"],
        prefers_chinese=True,
    ) == ["agreement_summary", "task_scope"]


def test_alignment_agreement_language_issues_fail_closed_for_missing_evidence() -> None:
    assert alignment_agreement_language_issues(
        {"agreement_summary": "协议已经明确。", "readiness_evidence": ["bad"]},
        evidence_keys=["loop_fit"],
        prefers_chinese=True,
    ) == ["readiness_evidence"]


def test_alignment_bundle_language_issues_are_disabled_when_chinese_is_not_preferred() -> None:
    assert alignment_bundle_language_issues({"collaboration_summary": "English summary."}, prefers_chinese=False) == []


def test_alignment_bundle_language_issues_report_non_chinese_bundle_surfaces() -> None:
    issues = alignment_bundle_language_issues(
        {
            "metadata": {"name": "Starter", "description": "English description."},
            "loop": {"name": "Starter Loop"},
            "collaboration_summary": "English collaboration summary.",
            "spec": {"markdown": "中文 spec。"},
            "workflow": {"collaboration_intent": "中文 workflow。"},
            "role_definitions": [
                {
                    "key": "builder",
                    "name": "Builder",
                    "description": "中文描述。",
                    "prompt_markdown": "English prompt.",
                    "posture_notes": "中文姿态。",
                }
            ],
        },
        prefers_chinese=True,
    )

    assert issues == [
        "bundle field metadata.name must follow Chinese user language",
        "bundle field metadata.description must follow Chinese user language",
        "bundle field loop.name must follow Chinese user language",
        "bundle field collaboration_summary must follow Chinese user language",
        "bundle role_definition builder.name must follow Chinese user language",
        "bundle role_definition builder.prompt_markdown must follow Chinese user language",
    ]


def test_alignment_bundle_workdir_fact_issues_ignore_supported_or_unknown_stack_claims() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "collaboration_summary": "Observed React frontend.",
            "spec": {"markdown": "Observed Python tests."},
            "workflow": {"collaboration_intent": "Unknown stack must be verified during the run."},
            "role_definitions": [
                {
                    "key": "builder",
                    "description": "Observed FastAPI service.",
                    "prompt_markdown": "Assumption: React details are unknown.",
                    "posture_notes": "Observed test coverage expectations.",
                },
                "ignore malformed role",
            ],
        },
        workdir_snapshot="package.json\npyproject.toml\nrequirements.txt\ngo.mod\ntests/ exists: yes",
    )

    assert issues == []


def test_alignment_bundle_workdir_fact_issues_report_unsupported_observed_stack_claims() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "collaboration_summary": "Observed React frontend.",
            "spec": {"markdown": "Observed Django service."},
            "workflow": {"collaboration_intent": "Unknown stack must be verified during the run."},
            "role_definitions": [
                {
                    "key": "builder",
                    "description": "Observed FastAPI service.",
                    "prompt_markdown": "Assumption: React details are unknown.",
                    "posture_notes": "看到 Go service.",
                }
            ],
        },
        workdir_snapshot="tests/ exists: yes",
    )

    assert issues == [
        "bundle field collaboration_summary must not claim an observed workdir stack unsupported by Workdir Snapshot",
        "bundle field spec.markdown must not claim an observed workdir stack unsupported by Workdir Snapshot",
        "bundle field role_definition builder.description must not claim an observed workdir stack unsupported by Workdir Snapshot",
        "bundle field role_definition builder.posture_notes must not claim an observed workdir stack unsupported by Workdir Snapshot",
    ]


def test_alignment_bundle_traceability_projection_texts_expose_only_runnable_surfaces() -> None:
    bundle = {
        "collaboration_summary": "Refund risk must reach GateKeeper.",
        "spec": {"markdown": "# Spec\n\n## Role Notes\nBuilder reads AGENTS.md before editing."},
        "workflow": {
            "collaboration_intent": "Builder then GateKeeper.",
            "steps": [
                {
                    "role": "builder",
                    "inputs": {"iteration_memory": "previous gaps"},
                    "action_policy": {"can_finish_run": False},
                    "control": {"handoff": "gatekeeper"},
                    "private": "not stable",
                },
                "ignore malformed step",
            ],
            "controls": [{"after": "builder", "then": "gatekeeper"}],
        },
        "role_definitions": [
            {
                "key": "builder",
                "name": "Builder",
                "description": "Builds refund controls.",
                "prompt_markdown": "Read AGENTS.md and cite evidence.",
                "posture_notes": "Do not treat process success as proof.",
            },
            "ignore malformed role",
        ],
    }

    agreement_text = alignment_bundle_agreement_projection_text(bundle)
    runtime_text = alignment_bundle_runtime_responsibility_projection_text(bundle)
    normalized = normalize_alignment_traceability_text("  Refund\n\nRisk  ")

    assert "Refund risk must reach GateKeeper." in agreement_text
    assert "Builds refund controls." in agreement_text
    assert '"inputs": {"iteration_memory": "previous gaps"}' in agreement_text
    assert "Read AGENTS.md and cite evidence." in runtime_text
    assert '"private"' not in agreement_text
    assert normalized == "refund risk"
    assert alignment_traceability_term_is_present("refund", normalized_bundle_text=normalize_alignment_traceability_text(agreement_text))
    assert alignment_traceability_term_is_present("AGENTS.md", normalized_bundle_text=normalize_alignment_traceability_text(runtime_text))
    assert not alignment_traceability_term_is_present("fund", normalized_bundle_text=normalize_alignment_traceability_text(agreement_text))


def test_alignment_session_user_task_text_projects_first_user_messages() -> None:
    session = {
        "transcript": [
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": "  First task.  "},
            {"role": "assistant", "content": "ignored"},
            {"role": "user", "content": ""},
            {"role": "user", "content": "Second task."},
            {"role": "user", "content": "Third task."},
            {"role": "user", "content": "Fourth task."},
            {"role": "user", "content": "Fifth task."},
            "ignore malformed",
        ]
    }

    assert alignment_session_user_task_text(session) == "First task.\nSecond task.\nThird task.\nFourth task."
    assert alignment_session_user_task_text({"transcript": "bad"}) == ""


def test_alignment_governance_marker_responsibility_issues_require_runtime_ownership() -> None:
    evidence = {
        "local_governance": "AGENTS.md, design/README.md, design/, and tests/ are visible governance markers.",
    }
    disconnected_runtime = normalize_alignment_traceability_text(
        "AGENTS.md, design/README.md, design/, and tests/. "
        + ("Neutral context keeps marker lists separate from role responsibilities. " * 10)
        + "Builder reads task notes. "
        "Inspector checks the result. GateKeeper blocks weak proof."
    )
    connected_runtime = normalize_alignment_traceability_text(
        "Builder reads AGENTS.md and design/README.md before editing. "
        "Inspector verifies design/ and tests/ obligations against the result. "
        "GateKeeper treats skipped AGENTS.md or tests/ validation as weak, unproven, or blocking."
    )

    assert alignment_governance_marker_responsibility_issues({}, normalized_runtime_text=disconnected_runtime) == []
    assert alignment_governance_marker_responsibility_issues(evidence, normalized_runtime_text=disconnected_runtime) == [
        "alignment bundle must convert project-local governance markers into Builder reading, "
        "Inspector or Custom verification, and GateKeeper gating responsibilities"
    ]
    assert alignment_governance_marker_responsibilities_present(connected_runtime)
    assert alignment_governance_marker_responsibility_issues(evidence, normalized_runtime_text=connected_runtime) == []


def test_alignment_agreement_block_plan_selects_first_issue_group() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=[],
                event_type="alignment_checklist_incomplete",
                fallback_message="缺少：{missing}",
            ),
            AlignmentAgreementBlockCandidate(
                issues=["loop_fit", "task_scope"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少证据：{missing}",
            ),
            AlignmentAgreementBlockCandidate(
                issues=["agreement_summary"],
                event_type="alignment_language_mismatch",
                fallback_message="缺少语言：{missing}",
            ),
        ],
        prefers_chinese=True,
    )

    assert plan is not None
    assert plan.event_type == "alignment_evidence_incomplete"
    assert plan.event_payload == {
        "alignment_stage": "clarifying",
        "missing": ["loop_fit", "task_scope"],
    }
    assert plan.output_updates == {
        "alignment_phase": "clarifying",
        "agreement_summary": "",
        "bundle_yaml": "",
        "needs_user_input": True,
        "alignment_missing_items": ["loop_fit", "task_scope"],
        "assistant_message": "缺少证据：loop_fit, task_scope",
    }


def test_alignment_agreement_block_plan_uses_event_semantics_for_english_messages() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=["readiness_evidence"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少：{missing}",
            ),
        ],
        prefers_chinese=False,
    )

    assert plan is not None
    assert "readiness evidence is not specific enough: readiness_evidence" in plan.output_updates["assistant_message"]


def test_alignment_agreement_block_plan_returns_none_without_issues() -> None:
    assert (
        alignment_agreement_block_plan(
            [
                AlignmentAgreementBlockCandidate(
                    issues=[],
                    event_type="alignment_checklist_incomplete",
                    fallback_message="缺少：{missing}",
                ),
            ],
            prefers_chinese=True,
        )
        is None
    )


def test_alignment_block_message_uses_language_and_event_semantics() -> None:
    assert alignment_block_message(
        prefers_chinese=True,
        event_type="alignment_evidence_incomplete",
        missing=["loop_fit"],
        fallback_zh="缺少：{missing}",
    ) == "缺少：loop_fit"

    evidence_message = alignment_block_message(
        prefers_chinese=False,
        event_type="alignment_evidence_incomplete",
        missing=["loop_fit"],
        fallback_zh="缺少：{missing}",
    )
    language_message = alignment_block_message(
        prefers_chinese=False,
        event_type="alignment_language_mismatch",
        missing=["agreement_summary"],
        fallback_zh="缺少：{missing}",
    )

    assert "readiness evidence is not specific enough: loop_fit" in evidence_message
    assert "user-facing agreement fields need the user's language: agreement_summary" in language_message


def test_alignment_stage_fallback_messages_preserve_semantic_paths() -> None:
    assert alignment_fallback_assistant_message(has_bundle=True, needs_user_input=False) == "已整理成一个可导入的 Loopora bundle。"
    assert "确认一个会改变 Loop 形状的点" in alignment_fallback_assistant_message(
        has_bundle=False,
        needs_user_input=True,
    )
    assert alignment_fallback_assistant_message(has_bundle=False, needs_user_input=False) == "我需要继续用中文对齐后再继续。"


def test_alignment_assistant_message_language_issue_tracks_chinese_preference() -> None:
    assert alignment_assistant_message_language_issue("I prepared the bundle.", prefers_chinese=True) is True
    assert alignment_assistant_message_language_issue("已整理方案。", prefers_chinese=True) is False
    assert alignment_assistant_message_language_issue("I prepared the bundle.", prefers_chinese=False) is False


def test_alignment_output_message_plan_preserves_bundle_and_missing_items() -> None:
    plan = alignment_output_message_plan(
        {
            "assistant_message": "已整理成 bundle。",
            "bundle_yaml": "version: 1\n",
        },
        stage_error="",
        missing_items=["task_scope"],
        prefers_chinese=True,
    )

    assert plan.assistant_message == "已整理成 bundle。"
    assert plan.bundle_yaml == "version: 1"
    assert plan.missing_items == ["task_scope"]
    assert plan.has_bundle_for_options is True
    assert plan.event_type == ""
    assert plan.use_default_decision_options is False


def test_alignment_output_message_plan_rewrites_non_chinese_assistant_message() -> None:
    plan = alignment_output_message_plan(
        {
            "assistant_message": "I prepared a follow-up question.",
            "needs_user_input": True,
        },
        stage_error="",
        missing_items=["loop_fit"],
        prefers_chinese=True,
    )

    assert "确认一个会改变 Loop 形状的点" in plan.assistant_message
    assert plan.bundle_yaml == ""
    assert plan.missing_items == ["loop_fit"]
    assert plan.has_bundle_for_options is False
    assert plan.event_type == "alignment_language_mismatch"
    assert plan.event_payload == {"missing": ["assistant_message"], "surface": "assistant_message"}
    assert plan.use_default_decision_options is True
    assert plan.force_needs_user_input is False


def test_alignment_output_message_plan_blocks_stage_error_before_bundle_handling() -> None:
    plan = alignment_output_message_plan(
        {
            "assistant_message": "已整理完成。",
            "bundle_yaml": "version: 1\n",
        },
        stage_error="需要先确认协议。",
        missing_items=["agreement_summary"],
        prefers_chinese=True,
    )

    assert plan.assistant_message == "需要先确认协议。"
    assert plan.bundle_yaml == ""
    assert plan.missing_items is None
    assert plan.has_bundle_for_options is False
    assert plan.event_type == "alignment_stage_blocked"
    assert plan.event_payload == {"status": "waiting_user", "error": "需要先确认协议。"}
    assert plan.force_needs_user_input is True
    assert plan.use_default_decision_options is True


def test_alignment_clarifying_reframe_message_preserves_recommended_default() -> None:
    assert "优先阻断" in alignment_clarifying_reframe_message(prefers_chinese=True)
    assert "block results that look done but lack evidence" in alignment_clarifying_reframe_message(prefers_chinese=False)


def test_alignment_clarifying_stage_plan_reframes_low_value_questions() -> None:
    plan = alignment_clarifying_stage_plan(
        {
            "needs_user_input": True,
            "assistant_message": "Configure workflow roles and parallel groups?",
            "decision_options": [],
            "bundle_yaml": "version: 1\n",
        },
        prefers_chinese=True,
    )

    assert plan.update_fields == {"alignment_stage": "clarifying"}
    assert "优先阻断" in plan.output_updates["assistant_message"]
    assert plan.output_updates["decision_options"][0]["recommended"] is True
    assert plan.output_updates["needs_user_input"] is True
    assert plan.output_updates["bundle_yaml"] == ""
    assert plan.event_type == "alignment_question_reframed"
    assert plan.event_payload == {
        "alignment_stage": "clarifying",
        "issues": ["mechanical_configuration_question", "missing_recommended_decision_options"],
    }


def test_alignment_clarifying_stage_plan_preserves_acceptable_question_output() -> None:
    plan = alignment_clarifying_stage_plan(
        {"assistant_message": "Here is an update.", "needs_user_input": False},
        prefers_chinese=False,
    )

    assert plan.update_fields == {"alignment_stage": "clarifying"}
    assert plan.output_updates == {}
    assert plan.event_type == ""
    assert plan.event_payload is None


def test_alignment_bundle_stage_error_prioritizes_stage_and_readiness_gates() -> None:
    kwargs = {
        "confirmed_stages": {"confirmed"},
        "phase": "bundle",
        "agreement_summary": "Agreement",
        "checklist": {"loop_fit": True},
        "readiness_keys": ["loop_fit"],
        "evidence_issues": [],
        "improvement_issues": [],
        "language_issues": [],
        "prefers_chinese": False,
    }

    assert "explicit confirmation" in alignment_bundle_stage_error(AlignmentBundleStageGate(stage="clarifying", **kwargs))
    assert "finish alignment before generating" in alignment_bundle_stage_error(AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "phase": "agreement"}))
    assert "confirmed working agreement summary" in alignment_bundle_stage_error(AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "agreement_summary": ""}))
    assert "readiness checklist" in alignment_bundle_stage_error(AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "checklist": []}))
    assert "readiness checks are incomplete: loop_fit" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "checklist": {"loop_fit": False}}),
    )
    assert alignment_bundle_stage_error(AlignmentBundleStageGate(stage="confirmed", **kwargs)) == ""


def test_alignment_bundle_stage_error_reports_evidence_improvement_and_language_gates() -> None:
    kwargs = {
        "stage": "confirmed",
        "confirmed_stages": {"confirmed"},
        "phase": "bundle",
        "agreement_summary": "Agreement",
        "checklist": {"loop_fit": True},
        "readiness_keys": ["loop_fit"],
        "prefers_chinese": True,
    }

    assert "readiness_evidence" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(**kwargs, evidence_issues=["readiness_evidence"], improvement_issues=[], language_issues=[]),
    )
    assert "improvement_delta" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(**kwargs, evidence_issues=[], improvement_issues=["improvement_delta"], language_issues=[]),
    )
    assert "需要使用中文：agreement_summary" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(**kwargs, evidence_issues=[], improvement_issues=[], language_issues=["agreement_summary"]),
    )
