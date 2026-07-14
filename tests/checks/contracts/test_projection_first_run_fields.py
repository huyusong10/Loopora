from __future__ import annotations

import errno
import json
import shlex
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli
from loopora.cli_first_use_compact_output import compact_first_use_lines
from loopora.fit_guidance import fit_guidance_payload, fit_guidance_web_context
from loopora.start_guidance import start_guidance_lines, start_guidance_payload
from loopora.cli_agent_step_results import _attach_agent_run_summary
from loopora.run_projection_fields import projection_first_run_record_fields, run_status_from_run, task_verdict_from_run

from cli_first_use_docs_test_support import result_error_text


def _event_projection_bundle() -> dict:
    return {
        "run_snapshot": {
            "schema_version": 1,
            "kind": "event_replayed_run_snapshot",
            "source_sequence": 12,
            "run_id": "run_projection_first",
            "loop_id": "loop_event",
            "lifecycle_status": "closed",
            "current_iteration": 2,
        },
        "task_verdict": {
            "schema_version": 1,
            "kind": "event_replayed_task_verdict",
            "source_sequence": 12,
            "status": "continue_required",
            "source": "system",
            "summary": "Projection still needs proof.",
        },
    }


def test_run_record_hydration_uses_event_projection_to_fill_missing_verdict() -> None:
    run = {
        "id": "run_projection_first",
        "status": "failed",
        "run_status": "failed",
    }

    run.update(projection_first_run_record_fields(_event_projection_bundle(), run=run))

    assert run_status_from_run(run) == "succeeded"
    assert task_verdict_from_run(run)["status"] == "insufficient_evidence"
    assert task_verdict_from_run(run)["source"] == "run_status"
    assert task_verdict_from_run(run)["summary"] == "Projection still needs proof."


def test_run_record_hydration_ignores_stale_projection_schema() -> None:
    projections = _event_projection_bundle()
    projections["run_snapshot"] = {**projections["run_snapshot"], "schema_version": 0}
    projections["task_verdict"] = {**projections["task_verdict"], "schema_version": 0}
    run = {
        "id": "run_projection_first",
        "status": "failed",
        "run_status": "failed",
    }

    run.update(projection_first_run_record_fields(projections, run=run))

    assert run_status_from_run(run) == "failed"
    assert task_verdict_from_run(run) == {}


def test_agent_run_summary_keeps_record_verdict_when_projection_cache_disagrees() -> None:
    result = {
        "adapter": "codex",
        "run": {
            "id": "run_projection_first",
            "status": "failed",
            "run_status": "failed",
            "workdir": "/workspace",
            "task_verdict_json": {"status": "failed", "source": "gatekeeper", "summary": "Record verdict wins."},
            "event_projections": _event_projection_bundle(),
        },
        "complete": True,
    }

    _attach_agent_run_summary(result)

    summary = result["agent_run_summary"]
    assert summary["run_status"] == "succeeded"
    assert summary["task_verdict_status"] == "failed"
    assert summary["task_verdict_summary"] == "Record verdict wins."
    assert summary["agent_work_panel"]["task_proven"] is False


def test_cli_fit_incomplete_review_marks_first_task_message_preview_only() -> None:
    runner = CliRunner()
    cli_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    json_result = runner.invoke(cli.app, ["fit", "--task", "Migrate billing callbacks", "--json"])
    plain_result = runner.invoke(cli.app, ["fit", "--task", "Migrate billing callbacks"])
    start_result = runner.invoke(cli.app, ["start", "--task", "Migrate billing callbacks", "--json"])
    start_plain = runner.invoke(cli.app, ["start", "--task", "Migrate billing callbacks"])
    assert json_result.exit_code == 0, result_error_text(json_result)
    payload = json.loads(json_result.stdout)
    review = payload["task_fit_review"]
    summary = review["task_fit_review_summary"]
    assert {
        key: payload[key]
        for key in (
            "primary_first_task_message_source",
            "primary_first_task_message_ready",
            "primary_first_task_message_copy_allowed",
            "primary_first_task_message_status",
        )
    } == {
        "primary_first_task_message_source": "task_review_draft",
        "primary_first_task_message_ready": False,
        "primary_first_task_message_copy_allowed": False,
        "primary_first_task_message_status": "preview_only_until_review_inputs_complete",
    }
    assert (
        summary["setup_allowed"],
        payload["command_fields_are_local_only"],
        payload["command_fields_public_pasteable"],
        payload["fit_guidance_summary"]["command_fields_are_local_only"],
        payload["fit_guidance_summary"]["command_fields_public_pasteable"],
    ) == (False, True, False, True, False)
    assert (
        payload["task_review_supplied"],
        payload["task_review_status"],
        payload["setup_allowed"],
        payload["fit_guidance_summary"]["task_review_supplied"],
        payload["fit_guidance_summary"]["task_review_status"],
        payload["fit_guidance_summary"]["setup_allowed"],
    ) == (True, "preview_only_until_review_inputs_complete", False, True, "preview_only_until_review_inputs_complete", False)
    assert (summary["draft_first_task_message_copy_allowed"], summary["draft_first_task_message_status"]) == (
        False,
        "preview_only_until_review_inputs_complete",
    )
    assert ([action["kind"] for action in payload["next_actions"]], payload["next_actions"][1]["command"], payload["next_actions"][2]["command"]) == (
        ["complete_review_inputs", "choose_workdir", "support", "continue_if_strong_fit"],
        f"{cli_entry} fit --workdir \"$PWD\" --task 'Migrate billing callbacks'",
        f"{cli_entry} support",
    )
    expected_incomplete_next_blockers = {
        "complete_review_inputs": ["review_inputs_required"],
        "continue_if_strong_fit": ["review_inputs_required"],
    }
    assert (
        payload["next_action_ready_kinds"],
        payload["next_action_ready_now_kinds"],
        payload["next_action_blocked_kinds"],
        payload["next_action_command_blockers"],
    ) == (["choose_workdir", "support"], ["choose_workdir", "support"], ["complete_review_inputs", "continue_if_strong_fit"], expected_incomplete_next_blockers)
    assert (
        payload["fit_guidance_summary"]["next_action_ready_kinds"],
        payload["fit_guidance_summary"]["next_action_blocked_kinds"],
        payload["fit_guidance_summary"]["next_action_command_blockers"],
    ) == (["choose_workdir", "support"], ["complete_review_inputs", "continue_if_strong_fit"], expected_incomplete_next_blockers)
    assert "install_agent_entry" not in {action["kind"] for action in payload["next_actions"]}
    assert plain_result.exit_code == 0, result_error_text(plain_result)
    assert "Fit review: needs human judgment." in plain_result.stdout
    assert "Still needed: fit reason, fake-done risk, required evidence, judgment tradeoffs." in plain_result.stdout
    assert "Setup, creation, and run stay blocked until the fit review is complete." in plain_result.stdout
    assert "Copyable one-message /loopora-plan handoff:" not in plain_result.stdout
    assert ("Recommended: continue from the target project" in plain_result.stdout, f"{cli_entry} fit --workdir \"$PWD\" --task 'Migrate billing callbacks'" in plain_result.stdout) == (
        True,
        True,
    )
    assert "Next if fit is strong:" not in plain_result.stdout
    assert start_result.exit_code == 0, result_error_text(start_result)
    assert (
        start_plain.exit_code,
        "Setup, creation, and run stay blocked until the fit review is complete." in start_plain.stdout,
        f"{cli_entry} fit --workdir \"$PWD\" --task 'Migrate billing callbacks'" in start_plain.stdout,
        "loopora init <agent>" not in start_plain.stdout,
        "Fit Guide/Web choices" not in start_plain.stdout,
    ) == (0, True, True, True, True), result_error_text(start_plain)
    start_payload = json.loads(start_result.stdout)
    start_summary = start_payload["start_guidance_summary"]
    assert {
        key: start_summary[key]
        for key in (
            "read_only",
            "starts_web",
            "installs_agent_entry",
            "classifies_task",
            "command_fields_are_local_only",
            "command_fields_public_pasteable",
            "workdir_supplied",
            "workdir_ready",
            "target_project_required",
            "route_commands_are_placeholders",
            "setup_commands_ready",
            "setup_command_blockers",
            "route_preview_executable",
            "route_preview_blockers",
            "direct_path_next_action_kinds",
        )
    } == {
        "read_only": True,
        "starts_web": False,
        "installs_agent_entry": False,
        "classifies_task": False,
        "command_fields_are_local_only": True,
        "command_fields_public_pasteable": False,
        "workdir_supplied": False,
        "workdir_ready": False,
        "target_project_required": True,
        "route_commands_are_placeholders": True,
        "setup_commands_ready": False,
        "setup_command_blockers": ["review_inputs_required", "target_project_required"],
        "route_preview_executable": False,
        "route_preview_blockers": ["review_inputs_required", "target_project_required"],
        "direct_path_next_action_kinds": ["record_direct_decision", "use_direct_agent_or_hard_checks"],
    }
    assert (
        start_payload["setup_allowed"],
        start_payload["setup_commands_ready"],
        start_payload["setup_command_blockers"],
        start_payload["route_preview_executable"],
        start_payload["route_preview_blockers"],
        start_summary["primary_first_task_message_state"]["status"],
        start_payload["primary_first_task_message_state"]["ready"],
        start_payload["command_fields_are_local_only"],
        start_payload["command_fields_public_pasteable"],
        start_payload["fit_guidance"]["command_fields_are_local_only"],
    ) == (
        False,
        False,
        ["review_inputs_required", "target_project_required"],
        False,
        ["review_inputs_required", "target_project_required"],
        "preview_only_until_review_inputs_complete",
        False,
        True,
        False,
        True,
    )
    assert (
        start_payload["setup_gate_ready"],
        start_payload["setup_gate_blockers"],
        start_summary["setup_gate_ready"],
        start_summary["setup_gate_blockers"],
        start_payload["fit_guidance"]["setup_gate_ready"],
        start_payload["fit_guidance"]["setup_gate_blockers"],
    ) == (
        False,
        ["review_inputs_required", "target_project_required"],
        False,
        ["review_inputs_required", "target_project_required"],
        False,
        ["review_inputs_required", "target_project_required"],
    )
    start_next_kinds = [action["kind"] for action in start_payload["next_actions"]]
    start_route_kinds = [action["kind"] for action in start_payload["route_actions_after_strong_fit"]]
    assert (
        start_next_kinds,
        start_summary["next_action_kinds"],
        start_payload["next_actions"][1]["command"],
        start_payload["fit_guidance"]["next_actions"][1]["command"],
        start_payload["next_actions"][2]["command"],
        [action.get("local_only") for action in start_payload["next_actions"] if action.get("command") or action.get("command_template")],
    ) == (
        ["complete_review_inputs", "choose_workdir", "support", "continue_if_strong_fit"],
        ["complete_review_inputs", "choose_workdir", "support", "continue_if_strong_fit"],
        f"{cli_entry} fit --workdir \"$PWD\" --task 'Migrate billing callbacks'",
        f"{cli_entry} fit --workdir \"$PWD\" --task 'Migrate billing callbacks'",
        f"{cli_entry} support",
        [True, True, True],
    )
    assert (
        start_payload["next_action_ready_kinds"],
        start_payload["next_action_ready_now_kinds"],
        start_payload["next_action_blocked_kinds"],
        start_payload["next_action_command_blockers"],
    ) == (["choose_workdir", "support"], ["choose_workdir", "support"], ["complete_review_inputs", "continue_if_strong_fit"], expected_incomplete_next_blockers)
    assert (
        start_summary["next_action_ready_kinds"],
        start_summary["next_action_blocked_kinds"],
        start_payload["fit_guidance"]["fit_guidance_summary"]["next_action_command_blockers"],
    ) == (["choose_workdir", "support"], ["complete_review_inputs", "continue_if_strong_fit"], expected_incomplete_next_blockers)
    assert (
        start_route_kinds
        == start_summary["route_action_kinds"]
        == ["check_fit_first", "open_web_creation_choices", "install_agent_entry", "confirm_readiness", "return_to_agent", "run_after_review", "support"]
    )
    assert (
        [action["kind"] for action in start_payload["fit_guidance"]["next_actions"]],
        start_payload["fit_guidance"]["fit_guidance_summary"]["next_action_kinds"],
        start_payload["fit_guidance"]["fit_guidance_summary"]["primary_first_task_message_state"]["copy_allowed"],
    ) == (start_next_kinds, start_next_kinds, False)
    assert (
        start_payload["workdir_arg"],
        start_payload["target_project_required"],
        start_payload["route_commands_are_placeholders"],
        start_payload["setup_commands_ready"],
        start_payload["setup_command_blockers"],
        start_payload["route_preview_executable"],
        start_payload["route_preview_blockers"],
    ) == (
        "'<project-dir>'",
        True,
        True,
        False,
        ["review_inputs_required", "target_project_required"],
        False,
        ["review_inputs_required", "target_project_required"],
    )


def test_incomplete_review_exposes_web_review_without_unlocking_setup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "app-home"))
    monkeypatch.setattr("loopora.fit_guidance.web_bind_preflight.probe_web_bind", lambda *_args: None)
    workdir = tmp_path / "project"
    workdir.mkdir()
    pending_inputs = {"task": "Migrate billing callbacks"}
    fit = fit_guidance_payload(pending_inputs["task"], workdir=workdir, preflight_web_route=True)
    start = start_guidance_payload(pending_inputs, workdir=workdir, preflight_web_route=True)

    for payload in (fit, start):
        action = payload["review_actions"][0]
        assert payload["review_action_kinds"] == ["continue_fit_review_in_web"]
        assert payload["review_action_ready_now_kinds"] == ["continue_fit_review_in_web"]
        assert (action["route_path"], action["route_contexts"], action["command_ready"], action["opens_browser"]) == (
            "/fit-guide",
            ["fit_review"],
            True,
            True,
        )
        assert action["command"].startswith("loopora serve --open --workdir ")
        assert " --open-path '/fit-guide?" in action["command"]
        open_url = urlparse(action["open_url"])
        review_context = json.loads(unquote(open_url.fragment.removeprefix("fit-review=")))
        assert parse_qs(open_url.query)["workdir"] == [str(workdir.resolve())]
        assert review_context["task"] == pending_inputs["task"]
        assert action["review_context_transport"] == "url_fragment"
        assert payload["setup_gate_ready"] is False
        assert {"fit_review_required", "review_inputs_required"} & set(payload["setup_gate_blockers"])

    completed = start_guidance_payload(
        {
            **pending_inputs,
            "fit_reason": "Later rounds need replay evidence.",
            "fake_done": "Happy path passes while duplicate delivery is unproven.",
            "evidence": "Replay, idempotency, and rollback evidence.",
            "tradeoffs": "Fail closed when rollback remains unproven.",
        },
        workdir=workdir,
    )
    direct = start_guidance_payload(
        {**pending_inputs, "prefer_direct": True, "direct_path": "Existing integration tests fully judge it."},
        workdir=workdir,
    )

    assert completed["review_actions"] == []
    assert completed["setup_gate_ready"] is True
    assert direct["review_actions"] == []
    assert direct["setup_gate_ready"] is False

    monkeypatch.setattr(
        "loopora.fit_guidance.web_bind_preflight.probe_web_bind",
        lambda *_args: (_ for _ in ()).throw(OSError(errno.EADDRINUSE, "busy")),
    )
    monkeypatch.setattr("loopora.fit_guidance.web_bind_preflight.next_available_web_port", lambda **_kwargs: None)
    blocked = fit_guidance_payload(pending_inputs["task"], workdir=workdir, preflight_web_route=True)
    assert blocked["review_actions"][0]["command_ready"] is False
    assert blocked["review_action_command_blockers"] == {
        "continue_fit_review_in_web": ["web_port_unavailable"]
    }


def test_cli_fit_json_projects_task_review_status_to_top_level(tmp_path: Path) -> None:
    runner = CliRunner()
    incomplete = runner.invoke(cli.app, ["fit", "--task", "Migrate billing callbacks", "--json"])
    direct_input = runner.invoke(cli.app, ["fit", "--workdir", str(tmp_path), "--task", "Rename one CSS class", "--prefer-direct", "--json"])

    assert (incomplete.exit_code, direct_input.exit_code) == (0, 0)
    incomplete_payload = json.loads(incomplete.stdout)
    direct_input_payload = json.loads(direct_input.stdout)
    assert (
        incomplete_payload["task_review_supplied"],
        incomplete_payload["task_review_status"],
        incomplete_payload["setup_allowed"],
        incomplete_payload["fit_guidance_summary"]["task_review_status"],
        incomplete_payload["fit_guidance_summary"]["setup_allowed"],
    ) == (True, "preview_only_until_review_inputs_complete", False, "preview_only_until_review_inputs_complete", False)
    assert (
        direct_input_payload["setup_command_blockers"],
        direct_input_payload["task_review_status"],
        direct_input_payload["setup_allowed"],
        direct_input_payload["fit_guidance_summary"]["task_review_status"],
        direct_input_payload["fit_guidance_summary"]["setup_allowed"],
        [action["kind"] for action in direct_input_payload["next_actions"]],
        direct_input_payload["next_actions"][0]["command_ready"],
        direct_input_payload["next_actions"][0]["command_blockers"],
    ) == (
        ["missing_direct_decision_input"],
        "direct_path_needs_decision_input",
        False,
        "direct_path_needs_decision_input",
        False,
        ["complete_direct_decision", "support"],
        False,
        ["direct_decision_input_required"],
    )
    assert (
        direct_input_payload["direct_path_next_action_ready_now_kinds"],
        direct_input_payload["direct_path_next_action_blocked_kinds"],
        direct_input_payload["direct_path_next_action_command_blockers"],
        direct_input_payload["fit_guidance_summary"]["direct_path_next_action_ready_now_kinds"],
        direct_input_payload["fit_guidance_summary"]["direct_path_next_action_blocked_kinds"],
        direct_input_payload["fit_guidance_summary"]["direct_path_next_action_command_blockers"],
    ) == (
        ["use_direct_agent_or_hard_checks"],
        ["record_direct_decision"],
        {"record_direct_decision": ["direct_decision_input_required"]},
        ["use_direct_agent_or_hard_checks"],
        ["record_direct_decision"],
        {"record_direct_decision": ["direct_decision_input_required"]},
    )


def test_cli_first_use_json_projects_action_kinds_and_readiness_to_top_level() -> None:
    runner = CliRunner()
    fit_result = runner.invoke(cli.app, ["fit", "--task", "Migrate billing callbacks", "--json"])
    start_result = runner.invoke(cli.app, ["start", "--task", "Migrate billing callbacks", "--json"])

    assert (fit_result.exit_code, start_result.exit_code) == (0, 0)
    fit_payload = json.loads(fit_result.stdout)
    start_payload = json.loads(start_result.stdout)
    web_context = fit_guidance_web_context()
    assert (
        fit_payload["workdir_state"]["status"],
        start_payload["workdir_state"]["status"],
        start_payload["fit_guidance"]["workdir_state"]["status"],
        web_context["workdir_state"]["status"],
    ) == ("required", "required", "required", "required")
    for payload, summary_key in (
        (fit_payload, "fit_guidance_summary"),
        (start_payload, "start_guidance_summary"),
        (start_payload["fit_guidance"], "fit_guidance_summary"),
        (web_context, "fit_guidance_summary"),
    ):
        _assert_top_level_action_kind_projection(payload, summary_key=summary_key)
    assert (
        web_context["task_review_supplied"],
        web_context["task_review_status"],
        web_context["setup_allowed"],
        web_context["setup_gate_ready"],
        web_context["setup_gate_blockers"],
    ) == (False, "example_only_no_task_review", False, False, ["fit_review_required", "target_project_required"])


def _assert_top_level_action_kind_projection(payload: dict[str, object], *, summary_key: str) -> None:
    summary = payload[summary_key]
    assert isinstance(summary, dict)
    expected = {
        "next_action_kinds": [action["kind"] for action in payload["next_actions"]],
        "route_action_kinds": [action["kind"] for action in payload["route_actions_after_strong_fit"]],
        "direct_path_next_action_kinds": [action["kind"] for action in payload["direct_path_next_actions"]],
    }
    expected.update(
        {
            "direct_path_next_action_ready_kinds": [
                action["kind"] for action in payload["direct_path_next_actions"] if action.get("command_ready") is not False
            ],
            "direct_path_next_action_ready_now_kinds": [
                action["kind"] for action in payload["direct_path_next_actions"] if action.get("command_ready") is not False and not action.get("after_action")
            ],
            "direct_path_next_action_ready_after_actions": {
                action["kind"]: action["after_action"]
                for action in payload["direct_path_next_actions"]
                if action.get("command_ready") is not False and action.get("after_action")
            },
            "direct_path_next_action_blocked_kinds": [action["kind"] for action in payload["direct_path_next_actions"] if action.get("command_ready") is False],
            "direct_path_next_action_command_blockers": {
                action["kind"]: action.get("command_blockers", []) for action in payload["direct_path_next_actions"] if action.get("command_ready") is False
            },
        }
    )
    assert {key: payload[key] for key in expected} == expected
    assert {key: summary[key] for key in expected} == expected
    if "workdir_state" in payload:
        status = payload["workdir_state"]["status"]
        expected_ready = status == "ready"
        assert (payload.get("workdir_ready", expected_ready), summary["workdir_ready"], summary["workdir_state_status"]) == (
            expected_ready,
            expected_ready,
            status,
        )


def test_cli_start_json_projects_review_gate_fields_to_top_level(tmp_path: Path) -> None:
    runner = CliRunner()
    no_review = runner.invoke(cli.app, ["start", "--workdir", str(tmp_path), "--json"])
    incomplete_review = runner.invoke(cli.app, ["start", "--task", "Migrate billing callbacks", "--json"])

    assert (no_review.exit_code, incomplete_review.exit_code) == (0, 0)
    no_review_payload = json.loads(no_review.stdout)
    incomplete_payload = json.loads(incomplete_review.stdout)
    _assert_start_review_gate_projection(
        no_review_payload,
        expected={"task_review_supplied": False, "fit_setup_allowed": True, "setup_allowed": True},
    )
    _assert_start_review_gate_projection(
        incomplete_payload,
        expected={"task_review_supplied": True, "fit_setup_allowed": False, "setup_allowed": False},
    )


def _assert_start_review_gate_projection(payload: dict[str, object], *, expected: dict[str, object]) -> None:
    summary = payload["start_guidance_summary"]
    assert isinstance(summary, dict)
    assert {key: payload[key] for key in expected} == expected
    assert {key: summary[key] for key in expected} == expected


def test_cli_start_complete_review_actions_skip_fit_recheck(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODEX_THREAD_ID", "redacted-contract-signal")
    review = {
        "task": "Migrate billing callbacks",
        "fit_reason": "Multi-round idempotency and rollback evidence is needed",
        "fake_done": "Happy path works but retry evidence is missing",
        "evidence": "Replay proof and rollback dry-run",
        "tradeoffs": "Fail closed on unproven idempotency",
    }
    payload = start_guidance_payload(review, workdir=tmp_path)
    next_kinds = [action["kind"] for action in payload["next_actions"]]
    route_kinds = [action["kind"] for action in payload["route_actions_after_strong_fit"]]
    targetless = start_guidance_payload(review)
    compact_text = "\n".join(compact_first_use_lines(payload, surface="start"))
    targetless_compact_text = "\n".join(compact_first_use_lines(targetless, surface="start"))
    assert (
        targetless["setup_command_blockers"],
        targetless["fit_guidance"]["setup_command_blockers"],
        targetless["next_actions"][0]["kind"],
        targetless["next_actions"][0]["command"],
        targetless["primary_first_task_message_ready"],
        "check_fit_first" not in [action["kind"] for action in targetless["route_actions_after_strong_fit"]],
        targetless["setup_gate_ready"],
        targetless["setup_gate_blockers"],
        targetless["start_guidance_summary"]["setup_gate_ready"],
        targetless["fit_guidance"]["setup_gate_blockers"],
    ) == (
        ["target_project_required"],
        ["target_project_required"],
        "choose_workdir",
        "loopora start --workdir \"$PWD\" --task 'Migrate billing callbacks' --fit-reason 'Multi-round idempotency and rollback evidence is needed' --fake-done 'Happy path works but retry evidence is missing' --evidence 'Replay proof and rollback dry-run' --tradeoffs 'Fail closed on unproven idempotency'",
        True,
        True,
        False,
        ["target_project_required"],
        False,
        ["target_project_required"],
    )

    assert (
        payload["setup_allowed"],
        payload["primary_first_task_message_ready"],
        payload["route_preview_executable"],
        payload["route_preview_blockers"],
        payload["start_guidance_summary"]["route_preview_executable"],
        payload["start_guidance_summary"]["route_preview_blockers"],
        payload["start_guidance_summary"]["primary_first_task_message_state"]["completed_review"],
        payload["setup_gate_ready"],
        payload["setup_gate_blockers"],
        payload["start_guidance_summary"]["setup_gate_ready"],
        payload["fit_guidance"]["setup_gate_ready"],
        payload["fit_guidance"]["setup_gate_blockers"],
    ) == (True, True, True, [], True, [], True, True, [], True, True, [])
    assert (
        compact_text.index("Outside an Agent session, continue in Web:")
        < compact_text.index("Set up or verify the detected current host first:")
        < compact_text.index("Reviewed handoff prepared;")
        < compact_text.index("/loopora-plan\n\nLoopora fit:")
        < compact_text.index("Run only after the READY preview")
    )
    assert "Same-Agent handoff (paste as one message):" not in compact_text
    assert targetless_compact_text.index("choose the target project") < targetless_compact_text.index("Reviewed handoff prepared;")
    assert "paste it only after choosing the target and same-Agent setup reports ready" in targetless_compact_text
    assert (payload["route_action_ready_kinds"], payload["route_action_ready_now_kinds"], payload["route_action_ready_after_actions"]) == (
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness", "support"],
        ["open_web_creation_choices", "install_agent_entry", "support"],
        {"confirm_readiness": "install_agent_entry"},
    )
    assert (payload["next_action_ready_kinds"], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness", "support"],
        ["open_web_creation_choices", "install_agent_entry", "support"],
        {"confirm_readiness": "install_agent_entry"},
    )
    assert (
        payload["start_guidance_summary"]["route_action_ready_now_kinds"],
        payload["start_guidance_summary"]["route_action_ready_after_actions"],
        payload["fit_guidance"]["fit_guidance_summary"]["route_action_ready_after_actions"],
    ) == (payload["route_action_ready_now_kinds"], payload["route_action_ready_after_actions"], payload["route_action_ready_after_actions"])
    assert (
        payload["start_guidance_summary"]["next_action_ready_now_kinds"],
        payload["fit_guidance"]["fit_guidance_summary"]["next_action_ready_after_actions"],
    ) == (payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"])
    assert (next_kinds[:3], payload["route_actions_after_strong_fit"][2]["after_action"]) == (
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness"],
        "install_agent_entry",
    )
    assert (payload["start_guidance_summary"]["next_action_kinds"], payload["start_guidance_summary"]["route_action_kinds"]) == (next_kinds, route_kinds)
    line_text = "\n".join(start_guidance_lines(payload))
    assert (
        "check_fit_first" not in next_kinds,
        route_kinds[0],
        "check_fit_first" not in route_kinds,
        "Preview only:" not in line_text,
        line_text.index("Copyable first /loopora-plan task message:")
        < line_text.index("If review says Loopora is not needed:")
        < line_text.index("Choose the route:"),
        "- Ready now: Fit Guide/Web choices; detected same-Agent setup; support route." in line_text,
        "- After detected same-Agent setup: doctor readiness check." in line_text,
        "- Blocked until prerequisites are resolved: /loopora-plan (same-Agent project entry); /loopora-run (READY preview review)." in line_text,
        "Usage/setup help: loopora support --workdir" in line_text,
        "Fit Guide/Web choices (outside an Agent session, import, or manual expert path):" in line_text,
        "Plan File import" in line_text,
        "These Web paths do not require a same-Agent project entry or doctor check" in line_text,
        payload["route_actions_after_strong_fit"][0]["route_contexts"],
        payload["route_actions_after_strong_fit"][0]["requires_doctor"],
        [action["command_ready"] for action in payload["route_actions_after_strong_fit"]],
        (payload["route_actions_after_strong_fit"][3]["command_blockers"], payload["route_actions_after_strong_fit"][4]["command_blockers"]),
        "After installing the matching same-Agent project entry, confirm readiness before /loopora-plan:" in line_text,
        "  - After READY preview review in that Agent:" in line_text,
    ) == (
        True,
        "open_web_creation_choices",
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        ["web_conversation", "plan_file_import", "manual_expert"],
        False,
        [True, True, True, False, False, True],
        (["same_agent_entry_required"], ["ready_review_required"]),
        True,
        True,
    )
    assert (
        [action["kind"] for action in payload["fit_guidance"]["next_actions"]],
        payload["fit_guidance"]["fit_guidance_summary"]["next_action_kinds"],
        [action["kind"] for action in payload["fit_guidance"]["route_actions_after_strong_fit"]],
        payload["fit_guidance"]["fit_guidance_summary"]["route_action_kinds"],
    ) == (next_kinds, next_kinds, route_kinds, route_kinds)

    direct_payload = start_guidance_payload({**review, "prefer_direct": True, "direct_path": "One Agent pass plus hard checks is enough"})
    direct_text = "\n".join(start_guidance_lines(direct_payload))
    assert (
        direct_payload["setup_allowed"],
        direct_payload["target_project_required"],
        direct_payload["route_commands_are_placeholders"],
        direct_payload["start_guidance_summary"]["route_action_kinds"],
        direct_payload["fit_guidance"]["fit_guidance_summary"]["route_action_kinds"],
        direct_payload["setup_command_blockers"],
        direct_payload["task_review_status"],
        direct_payload["primary_first_task_message"],
        [action["kind"] for action in direct_payload["next_actions"]],
        direct_payload["next_actions"][1]["command"],
        direct_payload["fit_guidance"]["task_fit_review"]["task_fit_review_summary"]["fit_decision"],
        direct_payload["direct_path_next_action_kinds"],
        direct_payload["direct_path_next_action_blocked_kinds"],
        direct_payload["fit_guidance"]["direct_path_next_action_blocked_kinds"],
    ) == (
        False,
        False,
        False,
        [],
        [],
        ["prefer_direct_path"],
        "direct_path_selected",
        "",
        ["use_direct_agent_or_hard_checks", "support"],
        "loopora support",
        "prefer_direct_path",
        ["use_direct_agent_or_hard_checks"],
        [],
        [],
    )
    assert (
        "Decision: use the direct path:" in direct_text,
        "Review inputs:" in direct_text,
        "- goal: Migrate billing callbacks" in direct_text,
        "- direct-path decision: One Agent pass plus hard checks is enough" in direct_text,
        "Target project:" not in direct_text,
        "Direct Agent or hard checks" in direct_text,
        "Usage/setup help: loopora support" in direct_text,
        "Choose the route:" not in direct_text,
    ) == (True, True, True, True, True, True, True, True)
    direct_input_payload = start_guidance_payload({"prefer_direct": True, "task": "Migrate billing callbacks"})
    direct_input_text = "\n".join(start_guidance_lines(direct_input_payload))
    assert (
        direct_input_payload["target_project_required"],
        direct_input_payload["route_commands_are_placeholders"],
        direct_input_payload["start_guidance_summary"]["route_action_kinds"],
        direct_input_payload["fit_guidance"]["fit_guidance_summary"]["route_action_kinds"],
        direct_input_payload["setup_command_blockers"],
        direct_input_payload["task_review_status"],
        direct_input_payload["primary_first_task_message"],
        [action["kind"] for action in direct_input_payload["next_actions"]],
        "command" in direct_input_payload["next_actions"][0],
        direct_input_payload["next_actions"][0]["command_ready"],
        direct_input_payload["next_actions"][0]["command_blockers"],
        direct_input_payload["next_actions"][0]["note"],
        direct_input_payload["next_actions"][1]["command"],
        "--direct-path '<what direct Agent, /goal, hard checks, or project process is enough>'" in direct_input_payload["next_actions"][0]["command_template"],
        "--task 'Migrate billing callbacks'" in direct_input_payload["next_actions"][0]["command_template"],
        "--task '<task goal>'" not in direct_input_payload["next_actions"][0]["command_template"],
    ) == (
        False,
        False,
        [],
        [],
        ["missing_direct_decision_input"],
        "direct_path_needs_decision_input",
        "",
        ["complete_direct_decision", "support"],
        False,
        False,
        ["direct_decision_input_required"],
        "add a direct-path reason before recording that Loopora is not needed",
        "loopora support",
        True,
        True,
        True,
    )
    assert (
        "Next before recording the direct-path decision:" in direct_input_text,
        "Complete direct-path decision:" in direct_input_text,
        "Usage/setup help: loopora support" in direct_input_text,
        "Target project:" not in direct_input_text,
        "Route shape" not in direct_input_text,
        "Choose the route" not in direct_input_text,
    ) == (True, True, True, True, True, True)


def test_start_fit_routes_preserve_app_home_language_and_current_host(monkeypatch, tmp_path: Path) -> None:
    home, project = tmp_path / "home with spaces", tmp_path / "project with spaces"
    home.mkdir()
    project.mkdir()
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    monkeypatch.setenv("CODEX_THREAD_ID", "redacted-contract-signal")
    review = ["--task", "Migrate billing callbacks", "--fit-reason", "Multi-round replay proof", "--fake-done", "Happy path only", "--evidence", "Replay and rollback proof", "--tradeoffs", "Fail closed"]
    runner = CliRunner()
    start = runner.invoke(cli.app, ["start", "--workdir", str(project), "--language", "zh", *review, "--json"])
    fit = runner.invoke(cli.app, ["fit", "--workdir", str(project), "--language", "zh", *review, "--json"])
    plain = runner.invoke(cli.app, ["start", "--workdir", str(project), "--language", "zh", *review])
    details = runner.invoke(cli.app, ["fit", "--workdir", str(project), "--language", "zh", *review, "--details"])
    prefix = f"LOOPORA_HOME={shlex.quote(str(home.resolve()))} "
    for result in (start, fit):
        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        actions = payload["route_actions_after_strong_fit"]
        setup = actions[1]
        commands = [actions[index]["command"] for index in (0, 1, 2, 5)] + [choice["command"] for choice in setup["adapter_choices"]]
        assert all(command.startswith(prefix) and "--language zh" in command for command in commands)
        assert " init current " in setup["command"]
        assert (setup["selection_required"], setup["adapter_fallback_available"]) == (False, False)
    setup_command = json.loads(start.stdout)["route_actions_after_strong_fit"][1]["command"]
    fit_setup_command = json.loads(fit.stdout)["route_actions_after_strong_fit"][1]["command"]
    assert (plain.exit_code, details.exit_code, setup_command in plain.stdout, fit_setup_command in details.stdout) == (0, 0, True, True)
    web_context = fit_guidance_web_context(cli_entry=agent_adapter_command_prefix.current_copyable_loopora_cli_entry(), workdir=project)
    assert web_context["fit_completion_cli_entry"].startswith(prefix)
