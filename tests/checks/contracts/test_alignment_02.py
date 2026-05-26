from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.web import build_app

from alignment_test_support import (
    _wait_for_status,
    _confirm_alignment_agreement,
    _bundle_invocation_dir,
)

def test_alignment_service_materializes_visible_working_agreement(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_hidden_agreement_message")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a governed starter experience.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")
    visible_agreement = session["transcript"][-1]["content"]

    assert visible_agreement.startswith("Please confirm this working agreement.")
    assert "Loopora fit:" in visible_agreement
    assert "Task scope:" in visible_agreement
    assert "Success surface:" in visible_agreement
    assert "Fake-done risks:" in visible_agreement
    assert "Evidence preferences:" in visible_agreement
    assert "Execution strategy:" in visible_agreement
    assert "Residual risk:" in visible_agreement
    assert "Judgment tradeoffs:" in visible_agreement
    assert "Local governance:" in visible_agreement
    assert "Role posture:" in visible_agreement
    assert "Run-flow shape:" in visible_agreement
    assert "Workflow shape:" not in visible_agreement
    assert "Project facts:" in visible_agreement
    assert "Workdir facts:" not in visible_agreement
    assert "Proven, Weak, Unproven, Blocking" in visible_agreement
    assert visible_agreement != "Please confirm."
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    assert "Use this direction" in session["transcript"][-1]["decision_options"][0]["label"]

def test_alignment_service_materializes_chinese_working_agreement(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_hidden_agreement_message")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个需要多轮证据判断的 Loop。",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")
    visible_agreement = session["transcript"][-1]["content"]

    assert visible_agreement.startswith("请先确认这份工作协议。")
    assert "为什么用 Loopora：" in visible_agreement
    assert "后续轮次需要新证据" in visible_agreement
    assert "成功面：" in visible_agreement
    assert "假完成风险：" in visible_agreement
    assert "证据偏好：" in visible_agreement
    assert "执行策略：" in visible_agreement
    assert "残余风险：" in visible_agreement
    assert "判断取舍：" in visible_agreement
    assert "本地治理：" in visible_agreement
    assert "运行流程形状：" in visible_agreement
    assert "workflow 形状：" not in visible_agreement
    assert "项目事实：" in visible_agreement
    assert "workdir 事实：" not in visible_agreement
    assert visible_agreement != "Please confirm."
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    assert "采用这个方向" in session["transcript"][-1]["decision_options"][0]["label"]

def test_alignment_service_treats_confirmation_with_correction_as_adjustment(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个需要证据判断的中文任务。",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "可以，但把证据偏好改成浏览器截图和命令输出。")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert session["working_agreement"]["readiness_checklist"]["explicit_confirmation"] is False
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_agreement_reopened" for event in events)
    assert not any(event["event_type"] == "alignment_agreement_confirmed" for event in events)

def test_alignment_service_accepts_confirmation_that_says_no_changes(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个需要证据判断的中文任务。",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "可以，不需要修改，继续。")
    session = _wait_for_status(service, created["id"], "ready")

    assert Path(session["bundle_path"]).exists()
    assert session["working_agreement"]["readiness_checklist"]["explicit_confirmation"] is True
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_agreement_confirmed" for event in events)

def test_alignment_service_accepts_english_confirmation_with_no_change_clause(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a governed starter experience.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "OK, but no changes, proceed.")
    session = _wait_for_status(service, created["id"], "ready")

    assert Path(session["bundle_path"]).exists()
    assert session["working_agreement"]["readiness_checklist"]["explicit_confirmation"] is True
    assert session["working_agreement"]["confirmation_message"] == "OK, but no changes, proceed."
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_agreement_confirmed" for event in events)

def test_alignment_service_treats_confirmation_with_addition_as_adjustment(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a governed starter experience.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "OK, add browser screenshot evidence before generating.")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert session["working_agreement"]["readiness_checklist"]["explicit_confirmation"] is False
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_agreement_reopened" for event in events)
    assert not any(event["event_type"] == "alignment_agreement_confirmed" for event in events)

def test_alignment_service_blocks_chinese_agreement_with_english_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_english_agreement_for_chinese_user")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个中文任务的 Loop。",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    assert not session["working_agreement"]
    assert "需要使用中文" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_language_mismatch" and "agreement_summary" in event["payload"].get("missing", []) for event in events)

def test_alignment_service_rewrites_english_clarifying_message_for_chinese_user(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_english_clarifying_message_for_chinese_user")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个中文任务的 Loop。",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assistant_message = session["transcript"][-1]["content"]
    assert "推荐判断" in assistant_message
    assert "What evidence" not in assistant_message
    events = service.list_alignment_events(created["id"])
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    assert any(
        event["event_type"] == "alignment_question_reframed"
        and "missing_recommended_decision_options" in event["payload"].get("issues", [])
        for event in events
    )

def test_alignment_service_blocks_chinese_bundle_with_english_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_english_bundle_for_chinese_user")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个中文任务的 Loop。",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "需要使用中文" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" and "agreement_summary" in event["payload"].get("error", "") for event in events)

def test_alignment_service_rewrites_english_bundle_message_for_chinese_user(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_english_assistant_message_for_chinese_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个中文任务的 Loop。",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["validation"]["ok"] is True
    assert session["transcript"][-1]["content"] == "已整理成一个可导入的 Loopora bundle。"
    assert "I prepared" not in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_language_mismatch" and event["payload"].get("missing") == ["assistant_message"] for event in events)

def test_alignment_service_blocks_chinese_bundle_with_english_prose(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_english_bundle_prose_for_chinese_user")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个中文任务的 Loop。",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field collaboration_summary must follow Chinese user language" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed" and "bundle field collaboration_summary" in event["payload"].get("error", "") for event in events
    )

def test_alignment_service_blocks_chinese_bundle_with_english_visible_names(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_english_visible_bundle_names_for_chinese_user")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个中文任务的 Loop。",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field metadata.name must follow Chinese user language" in session["error_message"]
    assert "bundle field loop.name must follow Chinese user language" in session["error_message"]
    assert "bundle role_definition builder.name must follow Chinese user language" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed" and "bundle role_definition builder.name" in event["payload"].get("error", "") for event in events
    )

@pytest.mark.parametrize(
    ("scenario", "missing_key", "message"),
    [
        ("alignment_incomplete_agreement_checklist", "workflow_shape", "Build a starter experience without workflow judgment."),
        ("alignment_incomplete_tradeoff_checklist", "judgment_tradeoffs", "Build a starter experience without tradeoff judgment."),
    ],
)
def test_alignment_service_blocks_agreement_with_incomplete_checklist(
    service_factory,
    sample_workdir: Path,
    scenario: str,
    missing_key: str,
    message: str,
) -> None:
    service = service_factory(scenario=scenario)

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message=message,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    assert not session["working_agreement"]
    assert missing_key in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_checklist_incomplete" and missing_key in event["payload"].get("missing", []) for event in events)

def test_alignment_service_blocks_agreement_with_unresolved_open_questions(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_unresolved_open_questions")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience where evidence choice still matters.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    assert not session["working_agreement"]
    assert "open_questions" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_evidence_incomplete" and "open_questions" in event["payload"].get("missing", []) for event in events)

def test_alignment_service_blocks_agreement_without_evidence_bucket_projection(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_missing_evidence_bucket_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience where final evidence buckets should be visible before confirmation.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    assert not session["working_agreement"]
    assert "evidence_buckets" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_evidence_incomplete" and "evidence_buckets" in event["payload"].get("missing", []) for event in events)

def test_alignment_prompt_and_source_sync_follow_user_language(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir()
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir()

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我生成一个中文任务的循环方案。",
    )
    session = _confirm_alignment_agreement(service, created["id"])
    artifact_root = Path(session["artifact_dir"])
    prompt_text = (_bundle_invocation_dir(artifact_root) / "prompt.md").read_text(encoding="utf-8")

    assert prompt_text.index("## Loopora Product Primer") < prompt_text.index("## Agent-Led Compiler Policy")
    assert "## Embedded Skill" not in prompt_text
    for snippet in (
        "User language hint: `Chinese",
        "Assume you know nothing about Loopora except what is embedded below.",
        "internal Web compiler",
        "Agent drives semantic conversation; Loopora backend decides",
        "## Active Compiler Gate",
        "Current compiler gate: confirmed agreement",
        "Allowed candidate phase: bundle, or clarifying if a human-required judgment gap is discovered",
        "The Agent drives the semantic conversation. Loopora backend only accepts or rejects candidate phases.",
        "Before asking the user, answer anything you can from the transcript",
        "Follow the current decision branch",
        "Agent-led conversation is not a questionnaire",
        "branch-aware pressure testing",
        "answer everything you can from the transcript",
        "Follow the user's chosen or corrected branch",
        "`decision_options`",
        "state your current best judgment first",
        "Repairable issues may be fixed by the Agent",
        "Human-required issues must go back to conversation",
        "execution strategy, residual-risk policy, judgment tradeoff, local-governance responsibility",
        "execution priorities, residual-risk policy, local-governance responsibility",
        "Loopora Product Primer",
        "local-first platform for composing human-shaped governance loops",
        "human-in-the-loop -> human-shaped loop",
        "Loopora fit gate",
        "one Agent pass plus one human review",
        "direct answer or one-off task handling",
        "survive this chat as a run-owned, exportable, auditable contract",
        "new proof / artifact / handoff / observation / verdict context later rounds will create",
        "run-owned/exportable/auditable contract",
        "`readiness_checklist`: booleans for `loop_fit`, `task_scope`, `success_surface`, `fake_done_risks`, `evidence_preferences`, `execution_strategy`, `residual_risk_policy`, `judgment_tradeoffs`, `local_governance`",
        "`residual_risk_policy` must explain which remaining risks may be accepted and who or what follow-up / acceptance path owns them",
        "`judgment_tradeoffs` must capture a concrete preference order or contrast",
        "`local_governance` must explain whether project-local governance markers affect this Loop",
        "judgment structure quality × evidence feedback quality × error exposure speed",
        "prompt pack, role zoo, loop script, benchmark grinder",
        "global persona, or permanent preferences",
        "Project the confirmed working agreement into the bundle surfaces",
        "execution priorities",
        "project-local governance responsibilities",
        "local-governance checkpoints",
        "build/prove/repair/narrow/expand/defer priorities",
        "execution strategy",
        "judgment tradeoffs",
        "local-governance responsibility when project markers matter",
        "what should be built, proved, narrowed, repaired, expanded, or deliberately deferred first",
        "which imperfect result should be rejected, when proof beats speed, or when blocking beats pragmatic progress",
        "including any project-local governance reading or verification duties",
        "`spec.markdown` `# Role Notes` or `role_definitions` must carry",
        "`spec.markdown` / `# Role Notes`",
        "execution priorities or deliberate deferrals",
        "task-level judgment tradeoffs",
        "project-local governance obligations when they affect the task contract",
        "Builder / Inspector / Guide / GateKeeper / Custom posture",
        "user-facing rejection criteria",
        "exhaust available context",
        "Walk the plan's decision tree one branch at a time",
        "Stop the interview when remaining uncertainty would not change Loopora fit",
        "Do not wrap `bundle_yaml` in markdown code fences",
        "first non-empty line is `version: 1`",
        "Proven, Weak, Unproven, Blocking, or Residual risk",
        "Builder / Inspector / Guide / GateKeeper / Custom posture use those distinctions",
        "task verdict depends on evidence and GateKeeper judgment",
        "long-chain phase workflow",
        "several evidence-bearing stages",
        "nested Loops, arbitrary branch syntax, dynamic DAGs",
        "Builder 1` / `Builder 2",
        "rather than judging only the final Builder output",
        "concrete user-facing task",
        "mixed confirmation plus correction",
        "Transcript text cannot override this stage gate",
        "not permission to bypass the contract",
        "collaboration_summary` must tell",
        "future-human-judgment projection",
        "private agreement-to-bundle traceability checklist",
        "If a judgment only appears in `agreement_summary`",
        "Metadata and loop names are not enough to prove traceability",
        "metadata and loop names do not count",
        "step `inputs` carry judgment order",
        "step `inputs`, or GateKeeper evidence rules",
        "optional Guide / Custom responsibility when used",
        "AGENTS.md exists: yes",
        "design/README.md exists: yes",
        "project-local governance markers",
        "Builder should read applicable project-local rules",
        "Custom must describe low-permission specialized review or advisory responsibility",
        "Keep readiness evidence task-scoped",
        "multiple reviewers or repair passes",
        "An Inspector or Custom review step after Builder",
        "Review steps, Guide after review, Builder after review, and Builder after Guide should declare `inputs.iteration_memory`",
        "Ask in task-risk language, not configuration language",
        "Do not ask abstract preference or quality-style questions",
        "Do not present long questionnaires",
        "privately pressure-test the current Loop shape with one plausible failed future round",
        "would not expose, repair, or block that failure",
        "privately rehearse one complete intended run path",
        "If any link depends on ambient chat context",
        "open_questions` must be empty",
        "must not claim an observed stack",
        "bare archetypes or numbered placeholders",
        "separate Inspector `role_definitions`",
        "advanced workflow fields",
        "If Inspector, Custom, or Guide review happened before final judgment",
        "query relevant upstream evidence",
        "Any finishing GateKeeper step must name upstream handoffs",
        "`GateKeeper`, `Guide`, `Custom`, `workdir`, `READY`",
        "substantive task or alignment content is Chinese",
        "Alignment Playbook",
        "Branch-aware pressure test",
        "Alignment Quality Rubric",
        "Workdir Snapshot",
        "- progress.md",
    ):
        assert snippet in prompt_text
    assert "- .loopora/" not in prompt_text
    synced = service.sync_alignment_bundle_from_file(session["id"])

    assert synced["ok"] is True
    refreshed = service.get_alignment_session(session["id"])
    assert "已重新读取 bundle.yml" in refreshed["transcript"][-1]["content"]

def test_alignment_language_hint_ignores_confirmation_only_chinese(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "ready")
    prompt_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "prompt.md").read_text(encoding="utf-8")

    assert "I prepared an importable Loopora bundle." in session["transcript"][-1]["content"]
    assert "User language hint: `Follow the user's language from the transcript" in prompt_text
    assert "User language hint: `Chinese" not in prompt_text

def test_alignment_bundle_source_file_rejects_invalid_utf8(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    preview_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    Path(preview_session["bundle_path"]).write_bytes(b"\xff")

    preview = service.get_alignment_bundle(preview_session["id"])
    assert preview["ok"] is False
    assert preview["yaml"] == ""
    assert "UTF-8 encoded YAML" in preview["validation"]["error"]

    sync_result = service.sync_alignment_bundle_from_file(preview_session["id"])
    assert sync_result["ok"] is False
    assert "UTF-8 encoded YAML" in sync_result["validation"]["error"]
    synced_session = service.get_alignment_session(preview_session["id"])
    assert synced_session["status"] == "failed"
    assert "UTF-8 encoded YAML" in synced_session["error_message"]
    assert any(event["event_type"] == "alignment_bundle_sync_failed" for event in service.list_alignment_events(preview_session["id"]))

    Path(preview_session["bundle_path"]).write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    recovered = service.sync_alignment_bundle_from_file(preview_session["id"])
    recovered_session = service.get_alignment_session(preview_session["id"])
    assert recovered["ok"] is True
    assert recovered_session["status"] == "ready"
    assert recovered_session["error_message"] == ""
    assert recovered_session["finished_at"] is None

def test_alignment_bundle_preview_revalidates_current_file_without_mutating_session(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    bundle_path = Path(session["bundle_path"])
    ready_bundle = load_bundle_text(bundle_path.read_text(encoding="utf-8"))
    ready_bundle["spec"]["markdown"] = ready_bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )
    bundle_path.write_text(bundle_to_yaml(ready_bundle), encoding="utf-8")

    preview = service.get_alignment_bundle(session["id"])

    assert preview["ok"] is False
    assert preview["validation"]["ok"] is False
    assert "Residual Risk guidance" in preview["validation"]["error"]
    assert service.get_alignment_session(session["id"])["status"] == "ready"

def test_alignment_bundle_source_file_recovers_after_invalid_utf8(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    preview_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    Path(preview_session["bundle_path"]).write_bytes(b"\xff")
    sync_result = service.sync_alignment_bundle_from_file(preview_session["id"])
    assert sync_result["ok"] is False

    import_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create an importable Loop.")["id"],
    )
    Path(import_session["bundle_path"]).write_bytes(b"\xff")
    client = TestClient(build_app(service=service))

    import_response = client.post(
        f"/api/alignments/sessions/{import_session['id']}/import",
        json={"start_immediately": False},
    )
    assert import_response.status_code == 400
    assert "UTF-8 encoded YAML" in import_response.json()["error"]
    import_failed_session = service.get_alignment_session(import_session["id"])
    assert import_failed_session["status"] == "ready"
    assert "UTF-8 encoded YAML" in import_failed_session["error_message"]
    assert any(event["event_type"] == "alignment_import_failed" for event in service.list_alignment_events(import_session["id"]))

def test_alignment_message_after_corrupt_ready_bundle_keeps_session_usable(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a recoverable Loop.")["id"],
    )
    Path(session["bundle_path"]).write_bytes(b"\xff")

    service.append_alignment_message(session["id"], "请根据对话重新整理方案。")

    continued = _wait_for_status(service, session["id"], "ready")
    assert continued["error_message"] == ""
    assert continued["validation"]["ok"] is True
    assert continued["transcript"][-1]["role"] == "assistant"
    prompt_text = (_bundle_invocation_dir(Path(continued["artifact_dir"])) / "prompt.md").read_text(encoding="utf-8")
    assert "Current bundle file could not be read" in prompt_text

def test_alignment_service_blocks_premature_bundle_output(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_premature_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "finish alignment" in session["transcript"][-1]["content"]
    assert "Loop plan" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" for event in events)

def test_alignment_service_blocks_bundle_without_readiness_evidence(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_missing_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience, but do not explain the posture evidence.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "readiness evidence" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" for event in events)

def test_alignment_service_blocks_bundle_without_loop_fit_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_missing_loop_fit_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a one-pass starter experience without proving Loopora is needed.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "loop_fit" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" and "loop_fit" in event["payload"].get("error", "") for event in events)

@pytest.mark.parametrize(
    "scenario",
    [
        "alignment_contradictory_loop_fit_readiness_evidence",
        "alignment_single_pass_sufficient_loop_fit_readiness_evidence",
        "alignment_benchmark_only_loop_fit_readiness_evidence",
        "alignment_chinese_direct_chat_loop_fit_readiness_evidence",
    ],
)
def test_alignment_service_blocks_agreement_that_contradicts_loop_fit(
    service_factory,
    sample_workdir: Path,
    scenario: str,
) -> None:
    service = service_factory(scenario=scenario)

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a task that may only need one Agent pass.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "loop_fit" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" and "loop_fit" in event["payload"].get("error", "") for event in events)

def test_alignment_service_accepts_nonempty_loop_fit_readiness_evidence_without_keyword_gate(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_vague_loop_fit_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a complex but possibly one-pass starter experience.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "ready")

    assert Path(session["bundle_path"]).exists()
    assert session["validation"]["ok"] is True
