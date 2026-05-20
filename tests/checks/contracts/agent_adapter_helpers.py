from __future__ import annotations
import hashlib
import json
import shlex
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner
import yaml
from loopora import cli
from loopora import cli_agent_adapter_commands
from loopora import cli_agent_native
import loopora.agent_adapters as agent_adapters
import loopora.agent_web as agent_web
import loopora.service_agent_native as service_agent_native
from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.service_agent_native import AgentNativeStepClaimRequest, AgentNativeStepSubmitRequest, ServiceAgentNativeMixin
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.utils import append_jsonl
from loopora.web import build_app
from loopora.workflows import WorkflowError
AGENT_ENTRY_GEN_CONTRACT_SNIPPETS = (
    "Enter Loopora's planning stage",
    "Compile, revise, repair, or tighten",
    "change the judgment structure",
    "tell them to use `/loopora-run`",
    "start fresh, recreate the bundle, or not reuse the old Loop",
    '--message "<non-empty short task summary>"',
    'with `--message "<non-empty short task summary>"` but without `--bundle-file`',
    "Loopora fit must say why one Agent pass, one review, direct chat / direct answer, one-off task handling, or benchmark/test-harness-only validation is not enough",
    "new evidence, handoffs, or a GateKeeper verdict",
    "compile them into Builder reading, Inspector / Custom verification, and GateKeeper Weak / Unproven / Blocking responsibility rather than a marker list",
    "Loopora fit reason, high-signal objects, success outcome categories, fake-done risk categories, concrete evidence modes, execution priorities, judgment tradeoffs, local governance responsibilities, and risk terms",
    "Check Loopora fit and judgment sufficiency before authoring a Loop plan file",
    "If Loopora fit is false",
    "ask one focused question",
    "return a Web review prefill",
    "execution strategy",
    "what to build, prove, repair, narrow, expand, or defer first",
    "judgment tradeoffs",
    "local governance responsibilities",
    "owner, follow-up, or acceptance path",
    "do not let a bundle pass merely because it repeats one or two object words from the task",
    "Do not invent human judgment just to pass validation",
    "ready_review_projection",
    "same-session run command",
    "`loop_recovery=plan_message_required`",
    "task_message_template",
    "first_task_message_example",
    "debug_cli_example_command",
    "review_status",
    "after_review_slash_command",
    "after_review_cli_command",
    "after_review_command",
    "ready_slash_command",
    "ready_cli_command",
    "ready_next_step",
    "repair_slash_command",
    "repair_cli_command",
    "repair_task_message",
    "preserves `repair_task_message` and `repair_focus`",
    "review_before_loop",
    "confirm that review summary and preview URL",
    "do not start the run from Web",
    "repair the plan file",
    "Loop preview",
    "Web review",
)
AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS = (
    "Enter Loopora's run stage",
    "run, resume, continue, keep going, close evidence gaps",
    "tell them to use `/loopora-plan` or Web review first",
    "Do not silently rewrite the Loop from `/loopora-run`",
    "agent_run_summary",
    "loopora_host_dispatch",
    "role_dispatch.target_agent",
    "role_dispatch.target_agent_config_exists",
    "judgment_contract",
    "next_step.judgment_contract",
    "next_step.required_coverage",
    "next_step.output_schema",
    "next_step.action_policy",
    "next_step.known_evidence_ids",
    "next_step.known_evidence_refs",
    "next_step.submit_hint.result_template_absolute_path",
    "Read the returned JSON, even if the command exits nonzero",
    "`loop_recovery=choose_recoverable_context`",
    "selection_hint",
    "runnable/non-runnable counts",
    "non-runnable choices' `preview_path`, `validation_error`, `repair_focus`",
    "`loop_recovery=plan_first`",
    "Report `required_inputs`, `ask_user`, `example_user_reply`, `task_message_template`, `first_task_message_example`, and `next_plan_command`",
    "`loop_recovery=active_run_conflict`",
    "`loop_recovery=finish_web_review`",
    "review_status",
    "after_review_command",
    "`loop_recovery=repair_candidate_plan_file`",
    "repair_task_message",
    "preserves `repair_task_message` and `repair_focus`",
    "Do not collapse these recovery states into a generic",
    "terminal `task_verdict_status` / `task_verdict_summary`",
    "If the command returns `loop_recovery`, report that recovery path and stop",
    "loopora_result_contract",
    "Do not hand-write the wrapper from memory",
    "Fill only the `result` object",
    "submit_repair=repair_result_json",
    "agent_submit_summary",
    "agent_submit_repair_summary",
    "agent_next_summary",
    "agent_next_recovery_summary",
    "next_agent_command",
    "task_proven",
    "task_outcome",
    "lifecycle_vs_task",
    "agent_run_summary.continuation",
    "next_step.iteration_repair",
    "next_step.submit_hint.command",
    "run.task_verdict",
    "task_next_action",
    "task_next_action.kind",
    "task_next_action.next_loop_command",
    "continue_evidence",
    "already_passed",
    "submitted_step.evidence_refs",
    "submitted_step.handoff_absolute_path",
    "submitted_step.blocking_items",
    "submitted_step.recommended_next_action",
    "next_step.prompt",
    "next_step.context_absolute_path",
)
AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS = (
    "next_step.judgment_contract",
    "next_step.prompt",
    "next_step.output_schema",
    "next_step.action_policy",
    "next_step.known_evidence_ids",
    "next_step.known_evidence_refs",
    "next_step.submit_hint.result_template_absolute_path",
    "loopora_result_contract",
    "schema-shaped `result` scaffold",
    "replace every `null` placeholder",
    "submit_repair=repair_result_json",
    "task_next_action.kind=continue_evidence",
    "task_next_action.kind=already_passed",
    "context_absolute_path",
)
def _error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output
def _labeled_value(output: str, label: str) -> str:
    prefix = f"{label}: "
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.removeprefix(prefix)
    raise AssertionError(f"missing {label}: line in output")
def _assert_loopora_agent_command(
    command: str,
    action: str,
    *,
    adapter: str = "codex",
    entry_source: str = "codex_project_skill",
    json_mode: bool = True,
) -> None:
    assert f"loopora agent {adapter} {action}" in command
    assert f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source}" in command
    assert f"--entry-source {entry_source}" in command
    if json_mode:
        assert "--json" in command
def _assert_labeled_loopora_agent_command(output: str, label: str, action: str, **kwargs) -> str:
    command = _labeled_value(output, label)
    _assert_loopora_agent_command(command, action, **kwargs)
    return command
def _assert_loopora_cli_command(command: str, command_body: str, *, loopora_home: Path | str | None = None) -> None:
    assert command_body in command
    if loopora_home is not None:
        assert command.startswith(f"LOOPORA_HOME={shlex.quote(str(loopora_home))} ")
def _assert_recovery_choice_has_copyable_commands(choice: dict) -> None:
    option_id = str(choice.get("option_id") or "")
    assert option_id.startswith("agent_run:")
    assert choice.get("runnable") is True
    assert str(choice.get("next_command") or "").startswith("/loopora-run option:agent_run:")
    assert str(choice.get("next_slash_command") or "").startswith("/loopora-run option:agent_run:")
    assert "--source-option-id" in str(choice.get("next_cli_command") or "")
    assert option_id in str(choice.get("next_cli_command") or "")
def _assert_not_ready_recovery_choice_routes_to_plan(choice: dict) -> None:
    _assert_non_runnable_recovery_choice_routes_to_plan(choice, expected_status="not_ready")
def _assert_non_runnable_recovery_choice_routes_to_plan(choice: dict, *, expected_status: str) -> None:
    assert choice.get("choice_status") == expected_status
    assert choice.get("runnable") is False
    assert choice.get("next_plan_command") == "/loopora-plan"
    assert choice.get("next_command") == ""
    assert choice.get("next_slash_command") == ""
    assert choice.get("next_cli_command") == ""
    assert choice.get("agent_cli_command") == ""
def _assert_recovery_choice_has_status_hint(choice: dict, *, expected_status: str) -> None:
    assert choice.get("choice_status") == expected_status
    assert choice.get("choice_hint_en")
    assert choice.get("choice_hint_zh")
    assert isinstance(choice.get("runnable"), bool)
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
    assert (
        "task_anchor_status: task anchor preserved from /loopora-plan; "
        "no candidate plan has projected it into a runnable Loop yet"
    ) in output
    assert f"task_anchor_preview: {task_message}" in output
    assert "review_scope: review_focus lists Loop surfaces to compile from the task anchor, not missing chat input" in output
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
    assert "Web alignment" not in output
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in output
    assert "candidate_url:" not in output
def _assert_web_review_json_payload(payload: dict, *, task_message: str) -> None:
    payload_keys = list(payload)
    assert payload_keys.index("agent_plan_summary") < payload_keys.index("session")
    summary = payload["agent_plan_summary"]
    assert summary["loop_recovery"] == "finish_web_review"
    assert summary["review_status"] == "not runnable; no candidate plan file was submitted"
    assert payload["review_status"] == summary["review_status"]
    assert summary["review_focus"] == payload["review_focus"]
    assert summary["task_anchor_status"] == payload["task_anchor_status"]
    assert summary["task_anchor_status"].endswith("no candidate plan has projected it into a runnable Loop yet")
    assert summary["task_anchor_preview"] == task_message
    assert summary["review_scope"] == "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input"
    assert summary["review_recommended_action"] == "Continue evidence-first review (Recommended)"
    assert summary["review_reply_preview"].startswith("Continue Web review from this /loopora-plan task anchor:")
    assert summary["after_review_ready"].startswith("return to this Agent session")
    assert summary["after_review_slash_command"] == "/loopora-run"
    _assert_loopora_agent_command(summary["after_review_cli_command"], "run")
    _assert_loopora_agent_command(summary["after_review_command"], "run")
    assert payload["ready"] is False
    assert payload["requires_web_alignment"] is True
    assert payload["loop_recovery"] == "finish_web_review"
    assert payload["review_status"] == "not runnable; no candidate plan file was submitted"
    assert payload["review_focus"]
    assert payload["task_anchor_preview"] == task_message
    assert payload["next_review_step"].startswith("open the preview URL")
    assert payload["after_review_slash_command"] == "/loopora-run"
def _write_ready_bundle(tmp_path: Path, sample_workdir: Path) -> tuple[Path, dict[str, int | str]]:
    bundle_file = tmp_path / "bundle.yml"
    bundle_text = alignment_bundle_yaml(str(sample_workdir.resolve()))
    candidate_sha, candidate_bytes = _candidate_digest(bundle_text)
    ready_sha, ready_bytes = _ready_candidate_digest(bundle_text)
    bundle_file.write_text(bundle_text, encoding="utf-8")
    return bundle_file, {
        "candidate_sha": candidate_sha,
        "candidate_bytes": candidate_bytes,
        "ready_sha": ready_sha,
        "ready_bytes": ready_bytes,
    }
def _assert_ready_plan_summary(payload: dict) -> None:
    assert next(iter(payload)) == "agent_plan_summary"
    summary = payload["agent_plan_summary"]
    assert summary["ready"] is True
    assert summary["ready_review_projection"] == payload["ready_review_projection"]
    assert "happy-path claim" in summary["ready_review_projection"]["fake_done_risks"][0]
    assert summary["ready_review_projection"]["gatekeeper"]["requires_evidence_refs"] is True
    assert summary["review_before_loop"] == "confirm the preview carries these judgments before running /loopora-run"
    assert summary["ready_next_step"].startswith("return to this Agent session and run /loopora-run")
    assert summary["ready_slash_command"] == "/loopora-run"
    assert "loopora agent codex run" in summary["ready_cli_command"]
    assert "--json" in summary["ready_cli_command"]
    assert summary["ready_run_command"] == summary["ready_cli_command"]
def _assert_ready_plan_payload(payload: dict, expected: dict[str, int | str]) -> None:
    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["requires_web_alignment"] is False
    assert payload["requires_candidate_repair"] is False
    assert payload["candidate_sha256"] == expected["candidate_sha"]
    assert payload["candidate_bytes"] == expected["candidate_bytes"]
    assert payload["ready_candidate_sha256"] == expected["ready_sha"]
    assert payload["ready_candidate_bytes"] == expected["ready_bytes"]
    assert payload["binding"]["candidate_sha256"] == expected["candidate_sha"]
    assert payload["binding"]["candidate_bytes"] == expected["candidate_bytes"]
    assert payload["binding"]["ready_candidate_sha256"] == expected["ready_sha"]
    assert payload["binding"]["ready_candidate_bytes"] == expected["ready_bytes"]
    assert payload["session"].get("agent_entry_review", {}) == {}
    assert payload["session"]["agent_entry_launch"]["ready_candidate_sha256"] == expected["ready_sha"]
    assert payload["session"]["agent_entry_launch"]["ready_candidate_bytes"] == expected["ready_bytes"]
def _assert_ready_review_projection(review: dict) -> None:
    assert "Future iterations stay anchored" in review["loopora_fit_reasons"][0]
    assert "happy-path claim" in review["fake_done_risks"][0]
    assert "project-owned checks" in review["evidence_preferences"][0]
    assert review["coverage"]["check_count"] == 2
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
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in output
def _assert_invalid_candidate_repair_payload(payload: dict, *, task_message: str, bundle_file: Path) -> None:
    payload_keys = list(payload)
    assert payload_keys.index("agent_plan_summary") < payload_keys.index("session")
    summary = payload["agent_plan_summary"]
    assert summary["ready"] is False
    assert summary["loop_recovery"] == "repair_candidate_plan_file"
    assert summary["requires_candidate_repair"] is True
    assert summary["repair_task_message"] == task_message
    assert summary["repair_focus"]
    assert summary["plan_file_to_repair"] == str(bundle_file)
    _assert_plan_repair_retry_payload(summary, bundle_file)
    assert payload["ready"] is False
    assert payload["requires_candidate_repair"] is True
    assert payload["loop_recovery"] == "repair_candidate_plan_file"
    assert payload["validation_error"]
    assert payload["repair_task_message"] == task_message
    assert payload["repair_focus"]
    assert payload["repair_focus"][0].startswith("add these missing task objects from --message")
    assert "refund" in payload["repair_focus"][0]
    assert payload["plan_file_to_repair"] == str(bundle_file)
    assert payload["preview_plan_copy"].endswith("/artifacts/bundle.yml")
    _assert_plan_repair_retry_payload(payload, bundle_file)
def _assert_invalid_candidate_run_recovery(stdout: str, *, task_message: str, validation_error: str, repair_focus: list, bundle_file: Path) -> None:
    run_payload = json.loads(stdout)
    run_summary = run_payload["agent_loop_recovery_summary"]
    assert run_summary["loop_recovery"] == "repair_candidate_plan_file"
    assert run_summary["validation_error"] == validation_error
    assert run_summary["repair_focus"] == repair_focus
    assert run_summary["repair_task_message"] == task_message
    assert run_summary["plan_file_to_repair"] == str(bundle_file)
    assert run_summary["preview_plan_copy"].endswith("/artifacts/bundle.yml")
    assert "repair_task_message and repair_focus" in run_summary["next_repair_step"]
def _write_agent_submit_repair_fixture(tmp_path: Path) -> dict[str, Path | RunArtifactLayout]:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_submit_repair")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    active_template = workdir / ".loopora" / "agent_outbox" / "codex" / "run_submit_repair__contract_inspection_step.result.template.json"
    active_template.parent.mkdir(parents=True, exist_ok=True)
    active_template.write_text("{}", encoding="utf-8")
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps({"active_step": {"capsule": _agent_submit_repair_active_capsule(layout, active_template)}}, ensure_ascii=False),
        encoding="utf-8",
    )
    stale_result_file = tmp_path / "builder-stale.result.json"
    stale_result_file.write_text(json.dumps(_stale_builder_result_wrapper()), encoding="utf-8")
    bad_ref_file = tmp_path / "inspector-bad-ref.result.json"
    bad_ref_file.write_text(json.dumps(_bad_ref_inspector_result_wrapper()), encoding="utf-8")
    return {
        "workdir": workdir,
        "layout": layout,
        "active_template": active_template,
        "stale_result_file": stale_result_file,
        "bad_ref_file": bad_ref_file,
    }
def _agent_submit_repair_active_capsule(layout: RunArtifactLayout, active_template: Path) -> dict:
    return {
        "iter": 0,
        "step_id": "contract_inspection_step",
        "step_order": 1,
        "role": {"name": "Contract Inspector", "id": "contract_inspector", "archetype": "inspector"},
        "role_dispatch": {"target_agent": "loopora-inspector"},
        "context_absolute_path": str(layout.step_context_path(0, 1, "contract_inspection_step")),
        "known_evidence_ids": ["ev_000_00_builder_step"],
        "known_evidence_refs": [
            {
                "id": "ev_000_00_builder_step",
                "step_id": "builder_step",
                "role_name": "Focused Builder",
                "result": "completed",
                "claim": "Builder proof exists but is weak for this repair fixture.",
                "gatekeeper_support": "non_supporting",
                "gatekeeper_support_reason": "no proof artifact",
                "coverage_target_ids": ["done_when.check_001"],
            }
        ],
        "judgment_contract": {
            "coverage_targets": [
                {"id": "done_when.check_001", "text": "Vendor billing callback flow works."},
                {"id": "done_when.check_002", "text": "Failed callbacks are replayable."},
            ]
        },
        "submit_hint": {"result_template_absolute_path": str(active_template)},
    }
def _stale_builder_result_wrapper() -> dict:
    return {
        "loopora_host_dispatch": {
            "adapter": "codex",
            "run_id": "run_submit_repair",
            "iter": 0,
            "step_id": "builder_step",
            "step_order": 0,
            "target_agent": "loopora-builder",
            "actual_agent": "loopora-builder",
            "dispatch_mode": "host_subagent",
            "inline": False,
        },
        "result": {"summary": "stale builder file"},
    }
def _bad_ref_inspector_result_wrapper() -> dict:
    return {
        "loopora_host_dispatch": {
            "adapter": "codex",
            "run_id": "run_submit_repair",
            "step_id": "contract_inspection_step",
            "target_agent": "loopora-inspector",
            "actual_agent": "loopora-inspector",
            "dispatch_mode": "host_subagent",
            "inline": False,
        },
        "result": {
            "coverage_results": [
                {
                    "target_id": "done_when.check_001",
                    "status": "covered",
                    "evidence_refs": ["invented_ev"],
                    "note": "Invented ref for repair UX.",
                }
            ]
        },
    }
def _invoke_codex_submit(runner: CliRunner, workdir: Path, **options):
    args = [
        "agent",
        "codex",
        "submit",
        "--workdir",
        str(workdir),
        "--run-id",
        str(options["run_id"]),
        "--step-id",
        str(options["step_id"]),
        "--result-file",
        str(options["result_file"]),
        "--entry-source",
        "codex_project_skill",
        "--no-web",
    ]
    if options.get("json_output", True):
        args.append("--json")
    return runner.invoke(cli.app, args)
def _assert_stale_submit_repair_payload(payload: dict, *, active_template: Path) -> None:
    assert next(iter(payload)) == "agent_submit_repair_summary"
    summary = payload["agent_submit_repair_summary"]
    assert summary["active_step_id"] == "contract_inspection_step"
    assert summary["active_iter"] == 0
    assert summary["active_step_order"] == 1
    assert summary["active_result_template"] == str(active_template)
    assert summary["submitted_dispatch"]["step_id"] == "builder_step"
    assert summary["submitted_dispatch"]["iter"] == 0
    assert summary["submitted_dispatch"]["step_order"] == 0
    assert payload["submitted_dispatch"] == summary["submitted_dispatch"]
    assert "discard the stale result file" in summary["next_repair_step"]
    assert "submitted file is for builder_step (iter 0, step_order 0)" in summary["next_repair_step"]
    assert "active step is contract_inspection_step (iter 0, step_order 1)" in summary["next_repair_step"]
    assert "contract_inspection_step" in summary["next_repair_step"]
    assert "loopora agent codex next" in summary["schema_lookup"]
    assert summary["active_known_evidence_refs"][0]["id"] == "ev_000_00_builder_step"
    assert summary["active_known_evidence_refs"][0]["gatekeeper_support"] == "non_supporting"
    assert summary["active_known_evidence_refs"][0]["gatekeeper_support_reason"] == "no proof artifact"
def _assert_bad_ref_submit_repair_payload(payload: dict) -> None:
    summary = payload["agent_submit_repair_summary"]
    assert summary["active_known_evidence_ids"] == ["ev_000_00_builder_step"]
    assert summary["active_known_evidence_refs"][0]["id"] == "ev_000_00_builder_step"
    assert summary["active_known_evidence_refs"][0]["gatekeeper_support"] == "non_supporting"
    assert "replace invented evidence_refs" in summary["next_repair_step"]
    assert "ev_000_00_builder_step" in summary["next_repair_step"]
    assert "use only known_evidence_ids in evidence_refs: ev_000_00_builder_step" in summary["repair_focus"]
def _assert_plain_bad_ref_submit_repair(error_text: str) -> None:
    assert "active_known_evidence_ids:" in error_text
    assert "- ev_000_00_builder_step" in error_text
    assert "active_known_evidence_refs:" in error_text
    assert "- ev_000_00_builder_step result=completed support=non_supporting reason=no proof artifact" in error_text
    assert "claim: Builder proof exists but is weak for this repair fixture." in error_text
    assert "coverage_targets: done_when.check_001" in error_text
    assert "active_coverage_target_ids:" in error_text
    assert "- done_when.check_001" in error_text
    assert "- done_when.check_002" in error_text
def _assert_terminal_recovery_choice(choice: dict, *, expected: dict) -> None:
    assert choice["action"] == expected["action"]
    assert choice["choice_status"] == expected["status"]
    assert expected["hint_text"] in choice["choice_hint_en"]
    assert choice["linked_run_id"] == expected["previous_run_id"]
    assert choice["linked_run_status"] == "succeeded"
    assert choice["task_verdict_status"] == expected["verdict"]
    assert expected["summary_text"] in choice["task_verdict_summary"]
    assert choice["label_en"].startswith(expected["label_prefix"])
def _assert_ambiguous_agent_recovery_choices(
    ambiguous: dict,
    *,
    generated_a: dict,
    generated_b: dict,
    started_a: dict,
) -> dict:
    assert ambiguous["action"] == "choose_recoverable_context"
    assert ambiguous["confidence"] == "ambiguous"
    assert ambiguous["requires_user_choice"] is True
    assert ambiguous["choice_count"] == len(ambiguous["choices"])
    assert ambiguous["runnable_choice_count"] >= 1
    assert "runnable context" in ambiguous["selection_hint"]
    choices_by_session = {choice["alignment_session_id"]: choice for choice in ambiguous["choices"]}
    assert choices_by_session[generated_a["session"]["id"]]["action"] == "resume_active_run"
    assert choices_by_session[generated_a["session"]["id"]]["linked_run_id"] == started_a["run"]["id"]
    _assert_recovery_choice_has_status_hint(choices_by_session[generated_a["session"]["id"]], expected_status="active_run")
    assert choices_by_session[generated_b["session"]["id"]]["linked_run_id"] == ""
    if choices_by_session[generated_b["session"]["id"]]["choice_status"] in {"not_ready", "needs_repair"}:
        _assert_non_runnable_recovery_choice_routes_to_plan(
            choices_by_session[generated_b["session"]["id"]],
            expected_status=choices_by_session[generated_b["session"]["id"]]["choice_status"],
        )
    else:
        _assert_recovery_choice_has_copyable_commands(choices_by_session[generated_b["session"]["id"]])
        assert choices_by_session[generated_b["session"]["id"]]["choice_status"] == "ready_preview"
    assert choices_by_session[generated_b["session"]["id"]]["choice_hint_en"]
    return choices_by_session
def _candidate_digest(bundle_text: str) -> tuple[str, int]:
    normalized = bundle_text.rstrip() + "\n" if bundle_text.strip() else ""
    data = normalized.encode("utf-8")
    return (hashlib.sha256(data).hexdigest(), len(data)) if data else ("", 0)
def _ready_candidate_digest(bundle_text: str) -> tuple[str, int]:
    return _candidate_digest(bundle_to_yaml(load_bundle_text(bundle_text)))
def _wait_for_alignment_status(service, session_id: str, *statuses: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    expected = set(statuses)
    while time.time() < deadline:
        session = service.get_alignment_session(session_id)
        if session["status"] in expected:
            return session
        time.sleep(0.05)
    session = service.get_alignment_session(session_id)
    raise AssertionError(f"alignment session stayed in {session['status']}, expected {sorted(expected)}")
def _assert_cli_handoff_contract_paths(
    stdout: str,
    *,
    capsule_fragment: str,
    template_fragment: str,
    outbox_fragment: str,
) -> None:
    assert "next_capsule_path:" in stdout
    assert capsule_fragment in stdout
    assert "result_template_path:" in stdout
    assert template_fragment in stdout
    assert "result_outbox_dir:" in stdout
    assert outbox_fragment in stdout
def _assert_cli_list(output: str, key: str, *items: str) -> None:
    assert f"{key}:\n" in output
    assert f"{key}: [" not in output
    for item in items:
        assert f"- {item}" in output
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
def _codex_skill_paths(workdir: Path) -> dict[str, Path]:
    return {
        "plan": workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md",
        "run": workdir / ".agents" / "skills" / "loopora-run" / "SKILL.md",
    }
def _claude_skill_paths(workdir: Path) -> dict[str, Path]:
    return {
        "plan": workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md",
        "run": workdir / ".claude" / "skills" / "loopora-run" / "SKILL.md",
    }
def _opencode_command_paths(workdir: Path) -> dict[str, Path]:
    return {
        "plan": workdir / ".opencode" / "commands" / "loopora-plan.md",
        "run": workdir / ".opencode" / "commands" / "loopora-run.md",
    }
def _alignment_bundle_yaml_with_gatekeeper_control(
    workdir: Path,
    *,
    after: str = "0s",
    signal: str = "gatekeeper_rejected",
    control_id: str = "gatekeeper_repair",
    trigger_window: int | None = None,
) -> str:
    payload = yaml.safe_load(alignment_bundle_yaml(str(workdir.resolve())))
    if trigger_window is not None:
        payload["loop"]["trigger_window"] = trigger_window
    payload["role_definitions"].append(
        {
            "key": "repair-guide",
            "name": "Repair Guide",
            "description": "Turns a rejected verdict into a narrow repair direction.",
            "archetype": "guide",
            "prompt_ref": "guide.md",
            "prompt_markdown": (
                "---\n"
                "version: 1\n"
                "archetype: guide\n"
                "---\n\n"
                "Read the rejected GateKeeper verdict and provide one narrow repair direction without changing the workspace."
            ),
            "posture_notes": "Prefer the smallest evidence-producing repair over broad re-planning.",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_cli": "",
            "command_args_text": "",
            "model": "",
            "reasoning_effort": "",
        }
    )
    payload["workflow"]["roles"].append({"id": "repair_guide", "role_definition_key": "repair-guide"})
    payload["workflow"]["controls"] = [
        {
            "id": control_id,
            "when": {"signal": signal, "after": after},
            "call": {"role_id": "repair_guide"},
            "mode": "repair_guidance",
            "max_fires_per_run": 1,
        }
    ]
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
def _alignment_bundle_yaml_with_peer_visible_parallel_review_inputs(workdir: Path) -> str:
    payload = yaml.safe_load(alignment_bundle_yaml(str(workdir.resolve())))
    for step in payload["workflow"]["steps"]:
        if step.get("id") in {"contract_inspection_step", "evidence_inspection_step"}:
            step["parallel_group"] = "inspection_pack"
            step["inputs"] = {
                "handoffs_from": ["builder_step", "contract_inspection_step"],
                "evidence_query": {"archetypes": ["builder", "inspector"], "limit": 12},
                "iteration_memory": "summary_only",
            }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
def _claude_settings_has_loopora_session_hook(settings: dict) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    session_start = hooks.get("SessionStart")
    if not isinstance(session_start, list):
        return False
    for group in session_start:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        if any(
            isinstance(handler, dict)
            and str(handler.get("command") or "").strip() == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/loopora-session-context.py"'
            for handler in handlers
        ):
            return True
    return False
def _agent_native_step_output(step: dict) -> dict:
    step_id = str(step["step_id"])
    role = step.get("role") if isinstance(step.get("role"), dict) else {}
    archetype = str(role.get("archetype") or "")
    if archetype == "guide":
        return {
            "created_at_iter": int(step.get("iter") or 0),
            "mode": "repair_guidance",
            "consumed": False,
            "analysis": {
                "stagnation_pattern": "gatekeeper_rejected",
                "recommended_shift": "Add direct evidence for the rejected Done When target.",
                "risk_note": "GateKeeper rejected the current evidence set.",
            },
            "seed_question": "Which missing proof can Builder produce next?",
            "meta_note": "Agent-native workflow control fired.",
        }
    if archetype == "inspector" or "inspection" in step_id:
        return {
            "execution_summary": {"total_checks": 1, "passed": 1, "failed": 0, "errored": 0, "total_duration_ms": 1},
            "check_results": [
                {
                    "id": "agent_native_path",
                    "title": "Agent-native path",
                    "status": "passed",
                    "notes": "The host Agent submitted structured inspection evidence through Loopora Core.",
                }
            ],
            "dynamic_checks": [],
            "tester_observations": "The Agent-native adapter path produced structured inspection evidence.",
            "coverage_results": [],
        }
    if archetype == "gatekeeper" or "gatekeeper" in step_id:
        evidence_refs = [
            str(item)
            for item in list(step.get("known_evidence_ids") or [])
            if str(item).strip() and "gatekeeper" not in str(item)
        ]
        return {
            "passed": True,
            "decision_summary": "Agent-native adapter path passed with inspector evidence.",
            "feedback_to_builder": "",
            "feedback_to_generator": "",
            "blocking_issues": [],
            "metrics": [{"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True}],
            "metric_scores": {
                "check_pass_rate": {"value": 1.0, "threshold": 1.0, "passed": True},
                "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
            },
            "hard_constraint_violations": [],
            "failed_check_ids": [],
            "priority_failures": [],
            "composite_score": 1.0,
            "evidence_refs": evidence_refs[-4:],
            "evidence_claims": ["The inspector evidence confirms the host Agent submitted a structured result."],
            "residual_risks": [],
            "coverage_results": [],
        }
    return {
        "attempted": "Prepared the workspace under the Loopora Agent-native capsule.",
        "abandoned": "",
        "assumption": "The unit test simulates host-native role execution without launching a nested Agent CLI.",
        "summary": "Builder produced a structured handoff for downstream inspection.",
        "changed_files": [],
        "proof_files": [],
        "proof_artifacts": [],
        "artifact_paths": [],
    }
def _agent_native_rejected_gatekeeper_output(step: dict) -> dict:
    output = _agent_native_step_output(step)
    output.update(
        {
            "passed": False,
            "decision_summary": "The task still lacks required evidence.",
            "feedback_to_builder": "Produce direct proof for the primary user flow.",
            "feedback_to_generator": "Produce direct proof for the primary user flow.",
            "blocking_issues": ["missing_primary_flow_evidence"],
            "composite_score": 0.42,
            "metrics": [{"name": "quality_score", "value": 0.42, "threshold": 0.9, "passed": False}],
            "evidence_claims": [],
        }
    )
    return output
def _drive_agent_native_until_archetype(service, result: dict, *, adapter: str, workdir: Path, archetype: str) -> dict:
    while True:
        step = result["next_step"]
        if step["role"]["archetype"] == archetype:
            return result
        result = service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter=adapter,
                workdir=workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=_agent_native_host_dispatch(adapter, step),
                entry_source=f"{adapter}_project_skill" if adapter != "opencode" else "opencode_project_command",
            )
        )
def _agent_native_host_dispatch(adapter: str, step: dict) -> dict:
    role_dispatch = step.get("role_dispatch") if isinstance(step.get("role_dispatch"), dict) else {}
    target_agent = str(role_dispatch.get("target_agent") or "")
    return {
        "schema_version": 1,
        "adapter": adapter,
        "run_id": str(step["run_id"]),
        "iter": int(step.get("iter") or 0),
        "step_id": str(step["step_id"]),
        "step_order": int(step.get("step_order") or 0),
        "target_agent": target_agent,
        "actual_agent": target_agent,
        "dispatch_mode": "host_subagent",
        "inline": False,
        "attestation": "The test simulates host-native role agent dispatch without launching a nested Agent CLI.",
    }
def _drive_agent_native_run_to_success(service, *, adapter: str, started: dict, workdir: Path, context_id: str = "") -> dict:
    result = started
    seen_steps = []
    while not result.get("complete"):
        step = result.get("next_step")
        assert isinstance(step, dict)
        step_id = str(step["step_id"])
        role = step.get("role") if isinstance(step.get("role"), dict) else {}
        role_dispatch = step.get("role_dispatch") if isinstance(step.get("role_dispatch"), dict) else {}
        assert role_dispatch.get("required") is True
        assert role_dispatch.get("inline_allowed") is False
        assert role_dispatch.get("target_agent")
        assert role_dispatch.get("target_agent_config_path")
        assert role_dispatch.get("target_agent_config_absolute_path")
        if role.get("archetype") == "gatekeeper":
            evidence_rule_ids = {
                str(item.get("id"))
                for item in list(step.get("evidence_rules") or [])
                if isinstance(item, dict)
            }
            assert "evidence_refs.must_be_exact_known_ids" in evidence_rule_ids
            assert "gatekeeper.pass_requires_supporting_upstream_evidence" in evidence_rule_ids
            assert "gatekeeper.finish_coverage_is_core_derived" in evidence_rule_ids
            assert step.get("evidence_ref_contract", {}).get("unknown_ids_are_blocking") is True
        seen_steps.append(step_id)
        result = service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                run_id=str(step["run_id"]),
                step_id=step_id,
                output=_agent_native_step_output(step),
                host_dispatch=_agent_native_host_dispatch(adapter, step),
                entry_source=f"{adapter}_project_skill" if adapter != "opencode" else "opencode_project_command",
            )
        )
    assert seen_steps[0] == "builder_step"
    assert any("gatekeeper" in item for item in seen_steps)
    assert result["run"]["status"] == "succeeded"
    assert result["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    return result
def _assert_claude_gen_entry(gen_skill: str, plan_contract: str) -> None:
    assert "disable-model-invocation: true" in gen_skill
    assert "allowed-tools:" in gen_skill
    assert "Bash(LOOPORA_HOME=* loopora agent claude plan *)" in gen_skill
    assert "Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *)" in gen_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill" in gen_skill
    assert 'loopora agent claude plan --workdir "$PWD"' in gen_skill
    assert '--context-id "${CLAUDE_SESSION_ID}"' in gen_skill
    assert "--entry-source claude_project_skill" in gen_skill
    assert "Create, revise, repair, or tighten the current Claude Code Loop preview" in gen_skill
    assert "thin dispatcher" in gen_skill
    assert "references/loopora-plan-contract.md" in gen_skill
    assert len(gen_skill.splitlines()) <= 80
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    assert "authoring YAML" not in gen_skill
    assert "fix the YAML" not in gen_skill
    assert "YAML" not in gen_skill
    assert "Web alignment URL" not in gen_skill
def _assert_claude_loop_entry(loop_skill: str, run_contract: str) -> None:
    assert "reviewed Loop preview" in loop_skill
    assert "preserves this Claude Code task judgment and evidence requirements" in loop_skill
    assert "confirmed Loop preview" not in loop_skill
    assert "READY bundle" not in loop_skill
    assert "Bash(LOOPORA_HOME=* loopora agent claude *)" in loop_skill
    assert "Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *)" in loop_skill
    assert "Bash(LOOPORA_HOME=* loopora init claude *)" in loop_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill" in loop_skill
    assert 'loopora agent claude run --workdir "$PWD"' in loop_skill
    assert "loopora agent claude submit" in run_contract
    assert "Task" in loop_skill
    assert "thin dispatcher" in loop_skill
    assert "references/loopora-run-contract.md" in loop_skill
    assert "references/loopora-recovery-matrix.md" in loop_skill
    assert "--source-option-id" in loop_skill
    assert len(loop_skill.splitlines()) <= 80
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract
    assert '--context-id "${CLAUDE_SESSION_ID}"' in loop_skill
    assert "--entry-source claude_project_skill" in loop_skill
def _assert_claude_agent_prompts(builder_agent: Path, orchestrator_agent: Path) -> None:
    builder_agent_text = builder_agent.read_text(encoding="utf-8")
    orchestrator_agent_text = orchestrator_agent.read_text(encoding="utf-8")
    assert "Loopora Builder" in builder_agent_text
    assert "tools: Read, Glob, Grep, Bash, Write, Edit, MultiEdit" in builder_agent_text
    assert "Loopora Orchestrator" in orchestrator_agent_text
    assert "tools: Task, Read, Write, Bash" in orchestrator_agent_text
    for snippet in AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS:
        assert snippet in orchestrator_agent_text
def _assert_claude_manifest(manifest_path: Path) -> str:
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    assert {item["path"] for item in json.loads(first_manifest)["managed_files"]} == {
        ".claude/skills/loopora-plan/SKILL.md",
        ".claude/skills/loopora-plan/references/loopora-plan-contract.md",
        ".claude/skills/loopora-run/SKILL.md",
        ".claude/skills/loopora-run/references/loopora-run-contract.md",
        ".claude/skills/loopora-run/references/loopora-recovery-matrix.md",
        ".claude/skills/loopora-run/references/loopora-result-template-guide.md",
        ".claude/skills/loopora-run/references/loopora-role-dispatch-guide.md",
        ".claude/hooks/loopora-session-context.py",
        ".claude/agents/loopora-builder.md",
        ".claude/agents/loopora-inspector.md",
        ".claude/agents/loopora-gatekeeper.md",
        ".claude/agents/loopora-guide.md",
        ".claude/agents/loopora-orchestrator.md",
    }
    return first_manifest
def _assert_claude_managed_install(workdir: Path, skill_paths: dict[str, Path]) -> tuple[Path, str]:
    gen_skill = skill_paths["plan"].read_text(encoding="utf-8")
    loop_skill = skill_paths["run"].read_text(encoding="utf-8")
    plan_contract = (workdir / ".claude" / "skills" / "loopora-plan" / "references" / "loopora-plan-contract.md").read_text(encoding="utf-8")
    run_contract = (workdir / ".claude" / "skills" / "loopora-run" / "references" / "loopora-run-contract.md").read_text(encoding="utf-8")
    recovery_matrix = (workdir / ".claude" / "skills" / "loopora-run" / "references" / "loopora-recovery-matrix.md").read_text(encoding="utf-8")
    settings = json.loads((workdir / ".claude" / "settings.json").read_text(encoding="utf-8"))
    gen_command = workdir / ".claude" / "commands" / "loopora-plan.md"
    loop_command = workdir / ".claude" / "commands" / "loopora-run.md"
    old_gen_skill = workdir / ".claude" / "skills" / "loopora-gen" / "SKILL.md"
    old_loop_skill = workdir / ".claude" / "skills" / "loopora-loop" / "SKILL.md"
    session_hook = workdir / ".claude" / "hooks" / "loopora-session-context.py"
    builder_agent = workdir / ".claude" / "agents" / "loopora-builder.md"
    orchestrator_agent = workdir / ".claude" / "agents" / "loopora-orchestrator.md"
    assert "LOOPORA-MANAGED: claude-code-adapter" in gen_skill
    assert not gen_command.exists()
    assert not loop_command.exists()
    assert not old_gen_skill.exists()
    assert not old_loop_skill.exists()
    for path in (session_hook, builder_agent, orchestrator_agent):
        assert path.exists()
    assert "CLAUDE_SESSION_ID" in session_hook.read_text(encoding="utf-8")
    assert _claude_settings_has_loopora_session_hook(settings)
    _assert_claude_gen_entry(gen_skill, plan_contract)
    assert "READY bundle" not in gen_skill
    _assert_claude_loop_entry(loop_skill, run_contract + recovery_matrix)
    _assert_claude_agent_prompts(builder_agent, orchestrator_agent)
    manifest_path = workdir / ".loopora" / "adapters" / "claude" / "manifest.json"
    return manifest_path, _assert_claude_manifest(manifest_path)
def _assert_opencode_managed_install(workdir: Path, command_paths: dict[str, Path]) -> tuple[Path, str]:  # noqa: PLR0915
    gen_command = command_paths["plan"].read_text(encoding="utf-8")
    loop_command = command_paths["run"].read_text(encoding="utf-8")
    plan_contract = (workdir / ".opencode" / "loopora" / "references" / "loopora-plan-contract.md").read_text(encoding="utf-8")
    run_contract = (workdir / ".opencode" / "loopora" / "references" / "loopora-run-contract.md").read_text(encoding="utf-8")
    recovery_matrix = (workdir / ".opencode" / "loopora" / "references" / "loopora-recovery-matrix.md").read_text(encoding="utf-8")
    builder_agent = workdir / ".opencode" / "agents" / "loopora-builder.md"
    orchestrator_agent = workdir / ".opencode" / "agents" / "loopora-orchestrator.md"
    old_gen_command = workdir / ".opencode" / "commands" / "loopora-gen.md"
    old_loop_command = workdir / ".opencode" / "commands" / "loopora-loop.md"
    assert "LOOPORA-MANAGED: opencode-adapter" in gen_command
    assert builder_agent.exists()
    assert orchestrator_agent.exists()
    assert not old_gen_command.exists()
    assert not old_loop_command.exists()
    assert "description:" in gen_command
    assert "agent: build" not in gen_command
    assert "$ARGUMENTS" in gen_command
    assert "LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command" in gen_command
    assert 'loopora agent opencode plan --workdir "$PWD"' in gen_command
    assert '--context-id "${OPENCODE_SESSION_ID:-}"' in gen_command
    assert "--entry-source opencode_project_command" in gen_command
    assert "Create, revise, repair, or tighten the current OpenCode Loop preview" in gen_command
    assert "thin dispatcher" in gen_command
    assert ".opencode/loopora/references/loopora-plan-contract.md" in gen_command
    assert len(gen_command.splitlines()) <= 80
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    assert "authoring YAML" not in gen_command
    assert "fix the YAML" not in gen_command
    assert "YAML" not in gen_command
    assert "reviewed Loop preview" in loop_command
    assert "preserves this OpenCode task judgment and evidence requirements" in loop_command
    assert "confirmed Loop preview" not in loop_command
    assert "READY bundle" not in gen_command
    assert "READY bundle" not in loop_command
    assert "LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command" in loop_command
    assert "agent: loopora-orchestrator" in loop_command
    assert "subtask: true" in loop_command
    assert 'loopora agent opencode run --workdir "$PWD"' in loop_command
    assert "loopora agent opencode submit" in run_contract
    assert "thin dispatcher" in loop_command
    assert ".opencode/loopora/references/loopora-run-contract.md" in loop_command
    assert ".opencode/loopora/references/loopora-recovery-matrix.md" in loop_command
    assert "--source-option-id" in loop_command
    assert len(loop_command.splitlines()) <= 80
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract + recovery_matrix
    assert '--context-id "${OPENCODE_SESSION_ID:-}"' in loop_command
    assert "--entry-source opencode_project_command" in loop_command
    builder_agent_text = builder_agent.read_text(encoding="utf-8")
    orchestrator_agent_text = orchestrator_agent.read_text(encoding="utf-8")
    assert "Loopora Builder" in builder_agent_text
    assert "mode: subagent" in builder_agent_text
    assert "task: deny" in builder_agent_text
    assert "Loopora Orchestrator" in orchestrator_agent_text
    assert "mode: subagent" in orchestrator_agent_text
    assert "loopora-builder: allow" in orchestrator_agent_text
    for snippet in AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS:
        assert snippet in orchestrator_agent_text
    manifest_path = workdir / ".loopora" / "adapters" / "opencode" / "manifest.json"
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    assert {item["path"] for item in json.loads(first_manifest)["managed_files"]} == {
        ".opencode/commands/loopora-plan.md",
        ".opencode/loopora/references/loopora-plan-contract.md",
        ".opencode/commands/loopora-run.md",
        ".opencode/loopora/references/loopora-run-contract.md",
        ".opencode/loopora/references/loopora-recovery-matrix.md",
        ".opencode/loopora/references/loopora-result-template-guide.md",
        ".opencode/loopora/references/loopora-role-dispatch-guide.md",
        ".opencode/agents/loopora-builder.md",
        ".opencode/agents/loopora-inspector.md",
        ".opencode/agents/loopora-gatekeeper.md",
        ".opencode/agents/loopora-guide.md",
        ".opencode/agents/loopora-orchestrator.md",
    }
    return manifest_path, first_manifest
def _assert_codex_managed_install(workdir: Path, skill_paths: dict[str, Path]) -> tuple[Path, str]:
    codex_builder_agent = workdir / ".codex" / "agents" / "loopora-builder.toml"
    codex_orchestrator_agent = workdir / ".codex" / "agents" / "loopora-orchestrator.toml"
    old_gen_skill = workdir / ".agents" / "skills" / "loopora-gen" / "SKILL.md"
    old_loop_skill = workdir / ".agents" / "skills" / "loopora-loop" / "SKILL.md"
    assert codex_builder_agent.exists()
    assert codex_orchestrator_agent.exists()
    assert not old_gen_skill.exists()
    assert not old_loop_skill.exists()
    gen_skill = skill_paths["plan"].read_text(encoding="utf-8")
    loop_skill = skill_paths["run"].read_text(encoding="utf-8")
    plan_contract = (workdir / ".agents" / "skills" / "loopora-plan" / "references" / "loopora-plan-contract.md").read_text(encoding="utf-8")
    run_contract = (workdir / ".agents" / "skills" / "loopora-run" / "references" / "loopora-run-contract.md").read_text(encoding="utf-8")
    recovery_matrix = (workdir / ".agents" / "skills" / "loopora-run" / "references" / "loopora-recovery-matrix.md").read_text(encoding="utf-8")
    assert "LOOPORA-MANAGED: codex-adapter" in gen_skill
    assert "name: loopora-plan" in gen_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in gen_skill
    assert 'loopora agent codex plan --workdir "$PWD"' in gen_skill
    assert "--bundle-file" in gen_skill
    assert "--entry-source codex_project_skill" in gen_skill
    assert "create, revise, repair, or tighten the reviewed Loop preview" in gen_skill
    assert "thin dispatcher" in gen_skill
    assert "references/loopora-plan-contract.md" in gen_skill
    assert len(gen_skill.splitlines()) <= 80
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    assert "authoring YAML" not in gen_skill
    assert "fix the YAML" not in gen_skill
    assert "YAML" not in gen_skill
    assert "reviewed Loop preview" in loop_skill
    assert "preserves the current task judgment and evidence requirements" in loop_skill
    assert "confirmed Loop preview" not in loop_skill
    assert "READY bundle" not in gen_skill
    assert "READY bundle" not in loop_skill
    assert "name: loopora-run" in loop_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in loop_skill
    assert 'loopora agent codex run --workdir "$PWD"' in loop_skill
    assert "loopora agent codex submit" in run_contract
    assert "loopora-builder" in run_contract
    assert "thin dispatcher" in loop_skill
    assert "references/loopora-run-contract.md" in loop_skill
    assert "references/loopora-recovery-matrix.md" in loop_skill
    assert "--source-option-id" in loop_skill
    assert len(loop_skill.splitlines()) <= 80
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract + recovery_matrix
    assert "Codex native dispatch guidance" in run_contract
    assert "omit `fork_context`" in run_contract
    assert "bounded timeout" in run_contract
    assert "--entry-source codex_project_skill" in loop_skill
    _assert_codex_role_agent_files(codex_builder_agent, codex_orchestrator_agent)
    return _assert_codex_manifest(workdir)
def _assert_codex_role_agent_files(codex_builder_agent: Path, codex_orchestrator_agent: Path) -> None:
    codex_builder_agent_text = codex_builder_agent.read_text(encoding="utf-8")
    assert "loopora-builder" in codex_builder_agent_text
    assert 'developer_instructions = """' in codex_builder_agent_text
    assert '\ninstructions = """' not in codex_builder_agent_text
    codex_orchestrator_agent_text = codex_orchestrator_agent.read_text(encoding="utf-8")
    assert "Loopora Orchestrator" in codex_orchestrator_agent_text
    for snippet in AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS:
        assert snippet in codex_orchestrator_agent_text
def _assert_codex_manifest(workdir: Path) -> tuple[Path, str]:
    manifest_path = workdir / ".loopora" / "adapters" / "codex" / "manifest.json"
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    manifest_payload = json.loads(first_manifest)
    assert manifest_payload["version"] == agent_adapters.ADAPTER_VERSION
    assert {item["path"] for item in manifest_payload["managed_files"]} == {
        ".agents/skills/loopora-plan/SKILL.md",
        ".agents/skills/loopora-plan/references/loopora-plan-contract.md",
        ".agents/skills/loopora-run/SKILL.md",
        ".agents/skills/loopora-run/references/loopora-run-contract.md",
        ".agents/skills/loopora-run/references/loopora-recovery-matrix.md",
        ".agents/skills/loopora-run/references/loopora-result-template-guide.md",
        ".agents/skills/loopora-run/references/loopora-role-dispatch-guide.md",
        ".codex/agents/loopora-builder.toml",
        ".codex/agents/loopora-inspector.toml",
        ".codex/agents/loopora-gatekeeper.toml",
        ".codex/agents/loopora-guide.toml",
        ".codex/agents/loopora-orchestrator.toml",
    }
    assert all(len(item["sha256"]) == 64 for item in manifest_payload["managed_files"])
    return manifest_path, first_manifest
def _assert_agent_run_summary_for_started_run(started: dict) -> None:
    summary = started["agent_run_summary"]
    assert summary["run_id"] == started["run"]["id"]
    assert summary["run_status"] == "awaiting_agent"
    assert summary["started_new_run"] is True
    assert summary["complete"] is False
    assert summary["next_step_id"] == "builder_step"
    assert summary["next_target_agent"] == "loopora-builder"
def _assert_agent_run_summary_continuation(
    summary: dict,
    *,
    previous_run_id: str,
    previous_task_verdict_status: str,
    missing_required_check_count: int | None = None,
) -> dict:
    continuation = summary["continuation"]
    assert continuation["active"] is True
    assert continuation["previous_run_id"] == previous_run_id
    assert continuation["previous_task_verdict_status"] == previous_task_verdict_status
    if missing_required_check_count is None:
        assert continuation["missing_required_check_count"] > 0
    else:
        assert continuation["missing_required_check_count"] == missing_required_check_count
    return continuation
def _assert_agent_native_observation_current_step(current_step: dict) -> None:
    assert current_step["step_id"] == "builder_step"
    assert current_step["role"]["name"] == "Focused Builder"
    assert current_step["target_agent"] == "loopora-builder"
    assert current_step["target_agent_config_path"] == ".codex/agents/loopora-builder.toml"
    assert current_step["target_agent_config_absolute_path"].endswith(".codex/agents/loopora-builder.toml")
    assert current_step["target_agent_config_exists"] is False
    assert current_step["role_dispatch"]["target_agent_config_path"] == ".codex/agents/loopora-builder.toml"
    assert current_step["role_dispatch"]["target_agent_config_exists"] is False
    assert current_step["action_policy"]["workspace"] == "workspace_write"
    assert current_step["required_coverage"]["missing_check_count"] == 2
    assert current_step["required_coverage"]["top_gaps"][0]["target_id"] == "done_when.check_001"
    assert current_step["context_path"].endswith("input.context.json")
    assert current_step["capsule_path"].endswith("capsule.json")
    assert current_step["submit_hint"]["result_template_path"].endswith(".result.template.json")
    assert current_step["submit_hint"]["result_file_path"].endswith(".result.json")
    assert current_step["submit_hint"]["result_outbox_dir"].endswith(".loopora/agent_outbox/codex")
    assert current_step["submit_hint"]["result_outbox_absolute_dir"].endswith(".loopora/agent_outbox/codex")
    assert current_step["submit_hint"]["result_file_absolute_path"].endswith(".result.json")
    assert current_step["submit_hint"]["result_file_contract"] == (
        "Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; "
        "replace null placeholders before submit."
    )
    assert isinstance(current_step["known_evidence_count"], int)
    _assert_submit_hint_command_requests_json(current_step["submit_hint"]["command"])
    assert "prompt" not in current_step
    assert "output_schema" not in current_step
def _assert_agent_native_observation_artifacts(service, current_step: dict, started: dict, sample_workdir: Path) -> None:
    capsule_path = Path(current_step["capsule_absolute_path"])
    template_path = Path(current_step["submit_hint"]["result_template_absolute_path"])
    assert capsule_path.exists()
    assert template_path.exists()
    capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
    assert capsule["step_id"] == "builder_step"
    assert capsule["entry_source"] == "codex_project_skill"
    assert capsule["role_dispatch"]["target_agent"] == "loopora-builder"
    assert capsule["known_evidence_count"] == 0
    assert capsule["known_evidence_ids"] == []
    assert capsule["role_dispatch"]["target_agent_config_absolute_path"].endswith(".codex/agents/loopora-builder.toml")
    assert capsule["role_dispatch"]["target_agent_config_exists"] is False
    _assert_capsule_submit_hint_uses_safe_filled_result_path(capsule["submit_hint"], step_stem="iter000__step00__builder_step")
    assert "prompt" in capsule
    assert "output_schema" in capsule
    template = json.loads(template_path.read_text(encoding="utf-8"))
    _assert_result_template_dispatch(template, run_id=started["run"]["id"])
    assert template["loopora_result_contract"]["ignored_on_submit"] is True
    assert template["loopora_result_contract"]["result_must_match_output_schema"] is True
    assert template["loopora_result_contract"]["result_is_schema_shaped_scaffold"] is True
    assert template["loopora_result_contract"]["result_scaffold_uses_null_placeholders"] is True
    assert template["loopora_result_contract"]["replace_null_placeholders_before_submit"] is True
    assert template["loopora_result_contract"]["step_id"] == "builder_step"
    assert template["loopora_result_contract"]["role"]["name"] == "Focused Builder"
    assert template["loopora_result_contract"]["action_policy"]["workspace"] == "workspace_write"
    assert template["loopora_result_contract"]["required_coverage"]["missing_check_count"] == 2
    assert template["loopora_result_contract"]["required_coverage"]["top_gaps"][0]["target_id"] == "done_when.check_001"
    assert template["loopora_result_contract"]["result_file_to_write"] == capsule["submit_hint"]["result_file_absolute_path"]
    assert template["loopora_result_contract"]["submit_command"] == capsule["submit_hint"]["command"]
    assert template["loopora_result_contract"]["result_template_path"] == capsule["submit_hint"]["result_template_absolute_path"]
    _assert_result_template_contract_targets(template)
    assert "known_evidence_ids" in template["loopora_result_contract"]
    assert template["loopora_result_contract"]["evidence_ref_contract"]["must_copy_exact_ids"] is True
    assert template["loopora_result_contract"]["output_schema"]["required"] == capsule["output_schema"]["required"]
    abandoned_schema = template["loopora_result_contract"]["output_schema"]["properties"]["abandoned"]
    assert "deliberate scope limits" in abandoned_schema["description"]
    assert "prompt" not in template["loopora_result_contract"]
    assert template["result"] == {
        "attempted": None,
        "abandoned": None,
        "assumption": None,
        "summary": None,
        "changed_files": [None],
        "proof_files": [None],
        "proof_artifacts": [None],
        "artifact_paths": [None],
    }
    with pytest.raises(
        LooporaConflictError,
        match=r"agent-native result does not match output_schema: \$\.attempted expected string, got null",
    ):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                context_id="thread-handoff",
                run_id=started["run"]["id"],
                step_id="builder_step",
                output=template["result"],
                host_dispatch=template["loopora_host_dispatch"],
                entry_source="codex_project_skill",
            )
        )
    assert not Path(capsule["result_output_path"]).is_absolute()
    assert not (Path(started["run"]["runs_dir"]) / capsule["result_output_path"]).exists()
    assert f"--workdir {sample_workdir.resolve()}" in capsule["submit_hint"]["command"]

    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    role_requests = read_jsonl(layout.role_requests_path)
    assert role_requests[-1]["context_path"].endswith("input.context.json")
    claimed = [event for event in read_jsonl(layout.legacy_events_path) if event["event_type"] == "agent_native_step_claimed"][-1]
    assert claimed["payload"]["target_agent"] == "loopora-builder"
    assert claimed["payload"]["capsule_path"].endswith("capsule.json")
    assert claimed["payload"]["result_template_path"].endswith(".result.template.json")
def _assert_capsule_submit_hint_uses_safe_filled_result_path(submit_hint: dict, *, step_stem: str = "") -> None:
    assert submit_hint["result_file_path"].endswith(".result.json")
    assert submit_hint["result_file_absolute_path"].endswith(".result.json")
    if step_stem:
        assert step_stem in Path(submit_hint["result_template_path"]).name
        assert step_stem in Path(submit_hint["result_file_path"]).name
    _assert_submit_hint_command_requests_json(submit_hint["command"])
def _assert_result_template_dispatch(template: dict, *, run_id: str) -> None:
    dispatch = template["loopora_host_dispatch"]
    assert dispatch["run_id"] == run_id
    assert dispatch["iter"] == 0
    assert dispatch["step_id"] == "builder_step"
    assert dispatch["step_order"] == 0
    assert dispatch["actual_agent"] == "loopora-builder"
    assert dispatch["inline"] is False
def _assert_result_template_contract_targets(template: dict) -> None:
    result_contract = template["loopora_result_contract"]
    assert "judgment_contract" not in result_contract
    assert result_contract["coverage_target_ids"][0] == "done_when.check_001"
    assert result_contract["coverage_targets"][0] == {
        "id": "done_when.check_001",
        "kind": "done_when",
        "required": True,
        "text": "The primary user flow works end to end.",
    }
def _assert_submit_hint_command_requests_json(command: str) -> None:
    _assert_loopora_agent_command(command, "submit")
    assert ".result.json" in command
    assert "<result-json>" not in command
def _write_agent_native_cli_contract(layout: RunArtifactLayout) -> None:
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "source_bundle": {
                    "id": "bundle_agent",
                    "name": "Agent Native Refund Bundle",
                    "revision": 2,
                    "source_bundle_id": "",
                    "imported_from_path": "/tmp/loopora/bundle.yml",
                },
                "collaboration_summary": "Prefer frozen judgment over lifecycle optimism.",
                "loop_fit_reasons": ["Future Agent rounds keep the same proof bar active."],
                "judgment_tradeoffs": ["Evidence beats fast closure."],
                "execution_strategy": ["Prove the refund path first, then expand after audit evidence is strong."],
                "local_governance": ["GateKeeper treats skipped AGENTS.md checks as Blocking."],
                "role_postures": [{"role_name": "GateKeeper", "archetype": "gatekeeper", "posture_notes": "Fail closed when evidence is weak."}],
                "completion_mode": "gatekeeper",
                "workflow": {
                    "preset": "quality_gate",
                    "collaboration_intent": "Linear review must feed GateKeeper before closure.",
                },
                "compiled_spec": {
                    "check_mode": "specified",
                    "checks": [{"id": "check_001"}, {"id": "check_002"}],
                    "coverage_targets": [
                        {"id": "done_when.check_001", "required": True},
                        {"id": "gatekeeper.finish", "required": True},
                    ],
                    "success_surface": ["Support admin can approve a refund."],
                    "fake_done_states": ["CSV export without permission audit is fake done."],
                    "evidence_preferences": ["Require browser journey and audit log command evidence."],
                    "residual_risk": "No residual risk is acceptable.",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
def _assert_agent_native_cli_output(
    stdout: str,
    layout: RunArtifactLayout,
    *,
    adapter: str = "codex",
    loopora_home: Path | str | None = None,
) -> None:
    assert "run_start: started_new_agent_native_run" in stdout
    assert f"run_contract_path: {layout.run_contract_path}" in stdout
    assert "source_plan: Agent Native Refund Bundle (bundle_agent, rev 2)" in stdout
    assert "source_plan_path: /tmp/loopora/bundle.yml" in stdout
    assert 'source_plan: {"id":' not in stdout
    assert "judgment_contract_summary: Prefer frozen judgment over lifecycle optimism." in stdout
    assert "check_mode: specified" in stdout
    assert "completion_mode: gatekeeper" in stdout
    assert "workflow_preset: quality_gate" in stdout
    assert "workflow_collaboration_intent: Linear review must feed GateKeeper before closure." in stdout
    assert "check_count: 2" in stdout
    _assert_cli_list(stdout, "coverage_targets", "done_when.check_001 (required)", "gatekeeper.finish (required)")
    _assert_cli_list(stdout, "loop_fit_reasons", "Future Agent rounds keep the same proof bar active.")
    _assert_cli_list(stdout, "judgment_tradeoffs", "Evidence beats fast closure.")
    _assert_cli_list(
        stdout,
        "execution_strategy",
        "Prove the refund path first, then expand after audit evidence is strong.",
    )
    _assert_cli_list(stdout, "local_governance", "GateKeeper treats skipped AGENTS.md checks as Blocking.")
    _assert_cli_list(stdout, "role_postures", "GateKeeper: Fail closed when evidence is weak.")
    _assert_cli_list(stdout, "success_surface", "Support admin can approve a refund.")
    _assert_cli_list(stdout, "fake_done_states", "CSV export without permission audit is fake done.")
    _assert_cli_list(stdout, "evidence_preferences", "Require browser journey and audit log command evidence.")
    assert "residual_risk: No residual risk is acceptable." in stdout
    assert "run_url: /runs/run_agent" in stdout
    assert "next_step_id: builder_step" in stdout
    assert "next_target_agent: loopora-builder" in stdout
    assert "next_target_agent_config:" in stdout
    assert ".codex/agents/loopora-builder.toml" in stdout
    assert "next_target_agent_config_exists: false" in stdout
    _assert_cli_dispatch_unavailable(stdout, adapter=adapter, loopora_home=loopora_home)
    assert "continuation_previous_run: run_previous" in stdout
    assert "continuation_task_verdict: insufficient_evidence" in stdout
    assert "continuation_required_coverage: 1 covered / 2 missing" in stdout
    assert "continuation_next_focus:" in stdout
    assert "- done_when.check_001: Support admin path still lacks direct proof." in stdout
    assert "next_action_policy: workspace_write" in stdout
    assert "required_coverage: pending; required checks 0 covered / 2 missing" in stdout
    assert "top_coverage_gaps:" in stdout
    assert "- done_when.check_001: Support admin can approve a refund." in stdout
    assert "next_context_path:" in stdout
    assert "input.context.json" in stdout
    assert "known_evidence_count: 3" in stdout
    assert "known_evidence_ids:" not in stdout
    assert "result_template_contract: Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit." in stdout
    assert "result_template_fill: open the template, replace null placeholders in result, keep loopora_host_dispatch, then submit the filled copy" in stdout
    _assert_cli_handoff_contract_paths(
        stdout,
        capsule_fragment="capsule.json",
        template_fragment="run_agent__builder_step.result.template.json",
        outbox_fragment=".loopora/agent_outbox/codex",
    )
    assert "submit_hint: loopora agent codex submit --run-id run_agent --step-id builder_step" in stdout
def _assert_agent_run_json_summary_reports_missing_dispatch(
    payload: dict,
    *,
    adapter: str,
    workdir: Path,
    loopora_home: Path | str | None = None,
) -> None:
    summary = payload["agent_run_summary"]
    assert summary["next_target_agent"] == "loopora-builder"
    assert summary["next_target_agent_config"].endswith(".codex/agents/loopora-builder.toml")
    assert summary["next_target_agent_config_exists"] is False
    assert "dispatch_next" not in summary
    assert summary["next_context_path"].endswith("input.context.json")
    assert summary["next_capsule_path"].endswith("capsule.json")
    assert summary["next_result_template"].endswith("run_agent__builder_step.result.template.json")
    assert summary["next_submit_command"] == "loopora agent codex submit --run-id run_agent --step-id builder_step"
    next_step_summary = summary["next_step"]
    assert next_step_summary["step_id"] == "builder_step"
    assert next_step_summary["target_agent"] == "loopora-builder"
    assert "dispatch_next" not in next_step_summary
    assert next_step_summary["context_path"].endswith("input.context.json")
    assert next_step_summary["capsule_path"].endswith("capsule.json")
    assert next_step_summary["result_template"].endswith("run_agent__builder_step.result.template.json")
    assert next_step_summary["result_template_contract"].startswith("Write one wrapper JSON object")
    assert "replace null placeholders" in next_step_summary["result_template_fill"]
    assert next_step_summary["result_outbox_dir"].endswith(".loopora/agent_outbox/codex")
    assert next_step_summary["submit_command"] == "loopora agent codex submit --run-id run_agent --step-id builder_step"
    assert next_step_summary["top_coverage_gaps"][0]["target_id"] == "done_when.check_001"
    assert next_step_summary["top_coverage_gaps"][0]["text"] == "Support admin can approve a refund."
    assert next_step_summary["dispatch_unavailable"]["reason"] == "target_agent_config_missing"
    _assert_loopora_cli_command(
        next_step_summary["dispatch_unavailable"]["check_command"],
        f"loopora agent {adapter} check --workdir {workdir}",
        loopora_home=loopora_home,
    )
    _assert_loopora_cli_command(
        next_step_summary["dispatch_unavailable"]["repair_command"],
        f"loopora init {adapter} --workdir {workdir}",
        loopora_home=loopora_home,
    )
    assert summary["dispatch_unavailable"]["reason"] == "target_agent_config_missing"
    assert summary["dispatch_unavailable"]["target_agent"] == "loopora-builder"
    _assert_loopora_cli_command(
        summary["dispatch_unavailable"]["check_command"],
        f"loopora agent {adapter} check --workdir {workdir}",
        loopora_home=loopora_home,
    )
    _assert_loopora_cli_command(
        summary["dispatch_unavailable"]["repair_command"],
        f"loopora init {adapter} --workdir {workdir}",
        loopora_home=loopora_home,
    )
    assert "do not submit inline role work" in summary["dispatch_unavailable"]["next"]
def _assert_cli_dispatch_unavailable(
    stdout: str,
    *,
    adapter: str,
    loopora_home: Path | str | None = None,
) -> None:
    assert "dispatch_unavailable: loopora-builder config is missing;" in stdout
    if loopora_home is not None:
        assert f"LOOPORA_HOME={shlex.quote(str(loopora_home))} " in stdout
    assert f'loopora agent {adapter} check --workdir "$PWD"' in stdout
    assert f'loopora init {adapter} --workdir "$PWD"' in stdout
    assert "dispatch_next: invoke loopora-builder" not in stdout
def _assert_agent_next_json_summary(stdout: str) -> None:
    payload = json.loads(stdout)
    payload_keys = list(payload)
    assert payload_keys[0] == "agent_next_summary"
    assert "agent_submit_summary" not in payload
    summary = payload["agent_next_summary"]
    assert summary["handoff_kind"] == "current_step"
    assert summary["run_id"] == "run_next"
    assert summary["run_status"] == "awaiting_agent"
    assert summary["run_url"] == "/runs/run_next"
    assert summary["task_verdict_status"] == "failed"
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_active_task_not_proven"
    assert summary["next_evidence_focus"] == "Previous GateKeeper rejected the pass because evidence was non-supporting."
    next_summary = summary["next_step"]
    assert next_summary["step_id"] == "inspector_step"
    assert next_summary["role"] == "Inspector"
    assert next_summary["target_agent"] == "loopora-inspector"
    assert next_summary["target_agent_config"] == ".codex/agents/loopora-inspector.toml"
    assert next_summary["dispatch_next"] == (
        "invoke loopora-inspector with the next context/capsule paths below; do not perform this role inline"
    )
    assert next_summary["action_policy"] == "read_only, can_block"
    assert next_summary["context_path"] == "iterations/iter_000/steps/01__inspector_step/input.context.json"
    assert next_summary["capsule_path"] == "iterations/iter_000/steps/01__inspector_step/capsule.json"
    assert next_summary["result_template"] == ".loopora/agent_outbox/codex/run_next__inspector_step.result.template.json"
    assert next_summary["result_template_contract"].startswith("Write one wrapper JSON object")
    assert "replace null placeholders" in next_summary["result_template_fill"]
    assert next_summary["result_outbox_dir"] == ".loopora/agent_outbox/codex"
    assert next_summary["submit_command"] == "loopora agent codex submit --run-id run_next"
    assert next_summary["known_evidence_count"] == 4
    assert next_summary["known_evidence_ids"] == ["ev_builder", "ev_contract"]
    assert next_summary["known_evidence_scope"] == "filtered by evidence_query archetypes=builder limit=12"
    assert next_summary["known_evidence_refs"][0]["id"] == "ev_builder"
    assert next_summary["known_evidence_refs"][0]["gatekeeper_support"] == "non_supporting"
    assert next_summary["known_evidence_refs"][0]["gatekeeper_support_reason"] == "no proof artifact"
    assert next_summary["known_evidence_refs"][0]["artifact_refs"] == [
        {"label": "proof-file:tests/browser-journey.json", "path": "tests/browser-journey.json"}
    ]
    assert next_summary["known_evidence_refs"][1]["id"] == "ev_contract"
    assert next_summary["known_evidence_refs"][1]["result"] == "blocked"
    assert next_summary["known_evidence_refs"][1]["coverage_target_ids"] == ["done_when.check_001"]
    assert next_summary["top_coverage_gaps"] == [
        {
            "target_id": "done_when.check_001",
            "status": "weak",
            "text": "Authorization proof is still weak.",
        }
    ]
    repair = next_summary["iteration_repair"]
    assert repair["source_step_id"] == "gatekeeper_step"
    assert repair["source_role"] == "GateKeeper"
    assert repair["blocking_items"] == [
        "gatekeeper_pass_refs_not_supporting_evidence: a pass must cite upstream evidence that is not blocked, failed, rejected, or errored; produce direct project-owned proof or mark passed=false"
    ]
    assert repair["recommended_next_action"] == "Produce direct project-owned proof before asking GateKeeper to pass again."
    assert repair["evidence_refs"] == ["ev_gatekeeper_block"]
    assert repair["top_gaps"][0]["target_id"] == "done_when.check_001"
    assert next_summary["required_coverage"] == "weak; required checks 1 covered / 1 missing"

__all__ = [name for name in globals() if not name.startswith("__")]
