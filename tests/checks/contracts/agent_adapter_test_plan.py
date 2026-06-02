from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora.executor_fake_payloads import alignment_bundle_yaml
from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_common import (
    _assert_loopora_agent_command,
    _assert_labeled_loopora_agent_command,
)
from agent_adapter_test_surface import (
    _assert_codex_native_surface_summary,
    _assert_codex_native_surface_plain,
)


EXPECTED_READY_REVIEW_CHECK_COUNT = 2


def _assert_plan_repair_retry_text(output: str, bundle_file: Path) -> None:
    assert "next_plan_command: /loopora-plan" in output
    assert f"repair_slash_command: /loopora-plan {bundle_file}" in output
    command = _assert_labeled_loopora_agent_command(output, "repair_cli_command", "plan", entry_source="direct_cli")
    assert f"--bundle-file {bundle_file}" in command

def _assert_plan_repair_retry_payload(payload: dict, bundle_file: Path) -> None:
    assert payload["next_plan_command"] == "/loopora-plan"
    assert payload["repair_slash_command"] == f"/loopora-plan {bundle_file}"
    _assert_loopora_agent_command(payload["repair_cli_command"], "plan", entry_source="direct_cli")
    assert f"--bundle-file {bundle_file}" in payload["repair_cli_command"]

def _invoke_codex_plan(runner: CliRunner, workdir: Path, **options):
    args = ["agent", "codex", "plan", "--workdir", str(workdir)]
    message = str(options.get("message") or "")
    if message:
        args.extend(["--message", message])
    bundle_file = options.get("bundle_file")
    if bundle_file:
        args.extend(["--bundle-file", str(bundle_file)])
    entry_source = str(options.get("entry_source") or "")
    if entry_source:
        args.extend(["--entry-source", entry_source])
    if options.get("no_web", True):
        args.append("--no-web")
    if options.get("json_output"):
        args.append("--json")
    return runner.invoke(cli.app, args)

def _assert_web_review_plain_output(output: str, *, task_message: str) -> None:
    assert "Loopora Loop preview needs Web review" in output
    assert "not_fit:" not in output
    assert "review_status: not runnable; no candidate plan file was submitted" in output
    assert "task_anchor_status: task anchor preserved from /loopora-plan" in output
    assert "no candidate plan has projected it into a runnable Loop yet" in output
    assert f"task_anchor_preview: {task_message}" in output
    assert "review_scope: review_focus lists Loop surfaces to compile" in output
    assert "not missing chat input" in output
    for expected in ("review_focus:", "Success surface:", "Fake-done risks:", "Evidence expectations:"):
        assert expected in output
    assert "review_recommended_action: Continue evidence-first review (Recommended)" in output
    assert "review_reply_preview: Continue Web review from this /loopora-plan task anchor:" in output
    assert "\nUse the evidence-first path:" not in output
    assert "next_review_step: open the preview URL" in output
    assert "after_review_ready: return to this Agent session and run /loopora-run" in output
    assert "after_review_slash_command: /loopora-run" in output
    _assert_labeled_loopora_agent_command(output, "after_review_cli_command", "run")
    _assert_labeled_loopora_agent_command(output, "after_review_command", "run")
    _assert_codex_native_surface_plain(output)
    assert "Web alignment" not in output
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in output
    assert "candidate_url:" not in output

def _assert_web_review_json_payload(payload: dict, *, task_message: str) -> None:
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary")
    _assert_codex_native_surface_summary(summary)
    assert summary["loop_recovery"] == "finish_web_review"
    assert summary["review_status"] == "not runnable; no candidate plan file was submitted"
    assert summary["task_anchor_status"].endswith("no candidate plan has projected it into a runnable Loop yet")
    assert summary["task_anchor_preview"] == task_message
    assert summary["review_scope"] == "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input"
    assert summary["review_recommended_action"] == "Continue evidence-first review (Recommended)"
    assert summary["review_reply_preview"].startswith("Continue Web review from this /loopora-plan task anchor:")
    assert summary["after_review_ready"].startswith("return to this Agent session")
    assert summary["after_review_slash_command"] == "/loopora-run"
    _assert_loopora_agent_command(summary["after_review_cli_command"], "run")
    _assert_loopora_agent_command(summary["after_review_command"], "run")
    assert summary["ready"] is False
    assert summary["requires_web_alignment"] is True
    assert summary["review_focus"]
    assert summary["next_review_step"].startswith("open the preview URL")

def _write_ready_bundle(tmp_path: Path, sample_workdir: Path) -> Path:
    bundle_file = tmp_path / "bundle.yml"
    bundle_text = alignment_bundle_yaml(str(sample_workdir.resolve()))
    bundle_file.write_text(bundle_text, encoding="utf-8")
    return bundle_file

def _assert_ready_plan_summary(payload: dict) -> None:
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    _assert_codex_native_surface_summary(summary)
    assert summary["ready"] is True
    assert "happy-path claim" in summary["ready_review_projection"]["fake_done_risks"][0]
    assert summary["ready_review_projection"]["gatekeeper"]["requires_evidence_refs"] is True
    assert summary["review_before_loop"] == "confirm the preview carries these judgments before running /loopora-run"
    assert summary["ready_next_step"].startswith("return to this Agent session and run /loopora-run")
    assert summary["ready_slash_command"] == "/loopora-run"
    assert "loopora agent codex run" in summary["ready_cli_command"]
    assert "--json" in summary["ready_cli_command"]
    assert summary["ready_run_command"] == summary["ready_cli_command"]

def _assert_ready_plan_payload(payload: dict) -> None:
    payload, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["requires_web_alignment"] is False
    assert payload["requires_candidate_repair"] is False

def _assert_ready_review_projection(review: dict) -> None:
    assert "Future iterations stay anchored" in review["loopora_fit_reasons"][0]
    assert "happy-path claim" in review["fake_done_risks"][0]
    assert "project-owned checks" in review["evidence_preferences"][0]
    assert review["coverage"]["check_count"] == EXPECTED_READY_REVIEW_CHECK_COUNT
    assert review["coverage"]["target_count"] >= review["coverage"]["check_count"]
    assert review["traceability"]["mapped_count"] == review["traceability"]["required_count"]
    assert review["gatekeeper"]["enabled"] is True
    assert review["gatekeeper"]["requires_evidence_refs"] is True

def _assert_invalid_candidate_repair_plain_output(output: str, *, task_message: str, bundle_file: Path) -> None:
    assert "Loopora Loop preview needs plan file repair before /loopora-run" in output
    assert "needs candidate repair" not in output
    for expected in ("validation_error:", "plan_file_to_repair:", "preview_plan_copy:", "repair_focus:", "next_repair_step:"):
        assert expected in output
    assert f"repair_task_message: {task_message}" in output
    _assert_plan_repair_retry_text(output, bundle_file)
    assert "repair_task_message and repair_focus" in output
    assert "host Agent task summary" in output
    assert "add these missing task objects from --message" in output
    assert all(item in output for item in ("refund", "authorization"))
    _assert_codex_native_surface_plain(output)
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in output

def _assert_invalid_candidate_repair_payload(payload: dict, *, task_message: str, bundle_file: Path) -> None:
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary")
    _assert_codex_native_surface_summary(summary)
    assert summary["ready"] is False
    assert summary["loop_recovery"] == "repair_candidate_plan_file"
    assert summary["requires_candidate_repair"] is True
    assert summary["repair_task_message"] == task_message
    assert summary["repair_focus"]
    assert summary["plan_file_to_repair"] == str(bundle_file)
    _assert_plan_repair_retry_payload(summary, bundle_file)
    assert summary["validation_error"]
    assert summary["repair_focus"][0].startswith("add these missing task objects from --message")
    assert "refund" in summary["repair_focus"][0]
    assert summary["preview_plan_copy"].endswith("/artifacts/bundle.yml")

def _assert_invalid_candidate_run_recovery(stdout: str, *, task_message: str, validation_error: str, repair_focus: list, bundle_file: Path) -> None:
    run_payload = json.loads(stdout)
    run_summary, _legacy = assert_agent_v3_envelope(
        run_payload, kind="agent_recovery", summary_key="agent_loop_recovery_summary", status="blocked"
    )
    assert run_summary["loop_recovery"] == "repair_candidate_plan_file"
    assert run_summary["validation_error"] == validation_error
    assert run_summary["repair_focus"] == repair_focus
    assert run_summary["repair_task_message"] == task_message
    assert run_summary["plan_file_to_repair"] == str(bundle_file)
    assert run_summary["preview_plan_copy"].endswith("/artifacts/bundle.yml")
    assert "repair_task_message and repair_focus" in run_summary["next_repair_step"]

def _assert_missing_candidate_agent_review(review: dict, *, task_message: str) -> None:
    assert review["source"] == "agent_entry"
    assert review["review_mode"] == "missing_candidate_plan"
    assert review["requires_web_alignment"] is True
    assert review["requires_candidate_repair"] is False
    assert review["has_candidate_yaml"] is False
    assert review["not_runnable"] is True
    assert review["adapter"] == "codex"
    assert review["entry_source"] == "codex_project_skill"
    assert review["task_message"] == task_message
    assert task_message in review["suggested_reply"]
    assert review["decision_options"][0]["id"] == "continue_web_review_evidence_first"
    assert review["decision_options"][0]["recommended"] is True
    assert task_message in review["decision_options"][0]["user_reply"]
    assert review["decision_options"][1]["id"] == "recheck_loop_fit"
    assert review["missing_judgment_item_ids"] == [
        "success_surface",
        "fake_done_risks",
        "evidence_preferences",
        "loop_fit",
        "execution_strategy",
        "judgment_tradeoffs",
        "residual_risk_policy",
        "local_governance",
    ]

def _assert_not_fit_agent_review(review: dict) -> None:
    assert review["source"] == "agent_entry"
    assert review["review_mode"] == "not_fit"
    assert review["requires_web_alignment"] is True
    assert review["loopora_fit_contradiction"] is True
    assert review["not_runnable"] is True
    assert review["decision_options"][0]["id"] == "skip_loop"
    assert review["decision_options"][0]["recommended"] is True
    assert review["decision_options"][1]["id"] == "reframe_as_loop"
