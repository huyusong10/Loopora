from __future__ import annotations

from http import HTTPStatus
import json
from pathlib import Path
import shutil
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from loopora.executor import FakeCodexExecutor
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.utils import read_json
from loopora.web import build_app

from web_api_test_support import _start_agent_first_loop, _wait_for_run_success


def _mark_run_as_unresolved(service, run_id: str) -> None:
    run = service.get_run(run_id)
    coverage_path = Path(run["runs_dir"]) / "evidence" / "coverage.json"
    coverage = read_json(coverage_path)
    target = next(item for item in coverage["targets"] if item["status"] != "covered")
    service.repository.update_run(
        run_id,
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "A required coverage target remains unproven.",
            "buckets": {"unproven": [{"id": target["id"], "summary": target["reason"]}]},
        },
    )


def _assert_recorded_advisory_role_prompt_contract(run_dir: Path, continuation: dict) -> None:
    step_context_paths = sorted(run_dir.glob("iterations/*/steps/*/step_instruction_context.json"))
    prompt_paths = sorted(run_dir.glob("iterations/*/steps/*/prompt.md"))
    assert step_context_paths
    assert prompt_paths
    for context_path in step_context_paths:
        step_continuation = json.loads(context_path.read_text(encoding="utf-8"))["continuation"]
        assert step_continuation["reason"] == "recorded_advisory_follow_up"
        assert step_continuation["focus_target_count"] == continuation["focus_target_count"]
    prompts = [path.read_text(encoding="utf-8") for path in prompt_paths]
    assert all("Recorded advisory follow-up policy:" in prompt for prompt in prompts)
    assert all("previous passing verdict is historical closure evidence" in prompt for prompt in prompts)
    assert all("Follow-up focus targets" in prompt for prompt in prompts)
    assert any("Current role for this policy: builder" in prompt for prompt in prompts)
    assert any("Current role for this policy: inspector" in prompt for prompt in prompts)
    assert any("Current role for this policy: gatekeeper" in prompt for prompt in prompts)
    assert any("Do not repeat already proven required work" in prompt for prompt in prompts)
    assert any("report coverage_results for each target attempted" in prompt for prompt in prompts)
    assert any("Do not call this follow-up successful merely because" in prompt for prompt in prompts)


def test_run_detail_keeps_generic_rerun_for_passing_terminal_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Passing Detail Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    service.repository.update_run(
        run["id"],
        task_verdict={
            "status": "passed",
            "source": "gatekeeper",
            "summary": "Required proof is complete.",
            "buckets": {"proven": [{"label": "all required checks"}]},
        },
    )
    client = TestClient(build_app(service=service))

    page_response = client.get(f"/runs/{run['id']}")

    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="run-rerun-button"' in page_response.text
    assert '<span data-lang="en">Rerun</span>' in page_response.text
    assert "Run next evidence pass" not in page_response.text
    assert "Record passing verdict" in page_response.text
    next_run = service.start_next_run(loop["id"])
    assert service.run_continuation_state(next_run["id"])["active"] is False


def test_recorded_passing_run_starts_advisory_continuation_with_role_context(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = service.import_bundle_text(
        FakeCodexExecutor._alignment_bundle_yaml(str(sample_workdir.resolve()))
    )
    loop = service.get_loop(bundle["loop_id"])
    previous_run = service.rerun(loop["id"])
    accepted = service.accept_run_result(previous_run["id"])
    assert accepted["recorded_advisory_follow_up_available"] is True
    client = TestClient(build_app(service=service))

    previous_page = client.get(f"/runs/{previous_run['id']}")
    loop_page = client.get(f"/loops/{loop['id']}")
    assert 'data-testid="run-recorded-advisory-rerun-button"' in previous_page.text
    assert 'name="follow_up_kind" value="advisory"' in previous_page.text
    assert f'action="/runs/{previous_run["id"]}/rerun?' in loop_page.text

    response = client.post(
        f"/runs/{previous_run['id']}/rerun",
        data={"follow_up_kind": "advisory"},
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    new_run_id = urlsplit(response.headers["location"]).path.removeprefix("/runs/")
    assert new_run_id != previous_run["id"]
    _wait_for_run_success(client, new_run_id)
    continuation = service.run_continuation_state(new_run_id)
    assert continuation["active"] is True
    assert continuation["reason"] == "recorded_advisory_follow_up"
    assert continuation["previous_run_id"] == previous_run["id"]
    assert continuation["focus_kind"] == "advisory"
    assert continuation["action_mode"] == "advisory_follow_up"
    assert continuation["focus_target_count"] > 0
    assert len(continuation["focus_targets"]) == continuation["focus_target_count"]
    assert all(target["required"] is False for target in continuation["focus_targets"])
    assert all(target["status"] != "covered" for target in continuation["focus_targets"])

    stored = service.get_run(new_run_id)
    _assert_recorded_advisory_role_prompt_contract(Path(stored["runs_dir"]), continuation)

    outcome = service.run_continuation_outcome(new_run_id)
    assert outcome["status"] == "no_progress"
    assert outcome["focus_target_count"] == continuation["focus_target_count"]
    assert outcome["improved_target_count"] == 0
    assert outcome["resolved_target_count"] == 0
    assert outcome["remaining_target_count"] == continuation["focus_target_count"]

    continued_page = client.get(f"/runs/{new_run_id}")
    assert 'data-testid="run-continuation-state"' in continued_page.text
    assert 'data-continuation-reason="recorded_advisory_follow_up"' in continued_page.text
    assert 'data-continuation-outcome="no_progress"' in continued_page.text
    assert "The original historical pass does not count as progress here." in continued_page.text
    assert "Record follow-up without progress" in continued_page.text
    assert f'/runs/{previous_run["id"]}?' in continued_page.text

    home_page = client.get("/")
    assert 'data-testid="home-active-loop"' in home_page.text
    assert 'data-attention-reason-kind="advisory_follow_up_no_progress"' in home_page.text
    assert 'data-attention-action-kind="review_advisory_follow_up"' in home_page.text
    assert "The original task verdict still passes; this advisory follow-up made no evidence progress." in home_page.text


def test_advisory_continuation_rejects_unrecorded_source_run(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = service.import_bundle_text(
        FakeCodexExecutor._alignment_bundle_yaml(str(sample_workdir.resolve()))
    )
    previous_run = service.rerun(bundle["loop_id"])
    client = TestClient(build_app(service=service))

    response = client.post(
        f"/runs/{previous_run['id']}/rerun",
        data={"follow_up_kind": "advisory"},
        headers={"accept": "application/json"},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["error"] == "recorded advisory follow-up is unavailable for this run"
    assert len(service.get_loop(bundle["loop_id"])["runs"]) == 1


def test_saved_loop_api_and_page_start_continue_latest_evidence_gaps(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = service.import_bundle_text(FakeCodexExecutor._alignment_bundle_yaml(str(sample_workdir.resolve())))
    previous_run = service.rerun(bundle["loop_id"])
    _mark_run_as_unresolved(service, previous_run["id"])
    client = TestClient(build_app(service=service))

    api_response = client.post(f"/api/loops/{bundle['loop_id']}/runs")

    assert api_response.status_code == HTTPStatus.CREATED
    api_run_id = api_response.json()["id"]
    api_continuation = service.run_continuation_state(api_run_id)
    assert api_continuation["reason"] == "terminal_task_verdict_requires_next_run"
    assert api_continuation["previous_run_id"] == previous_run["id"]
    assert api_continuation["focus_target_count"] > 0
    assert all(item["status"] != "covered" for item in api_continuation["focus_targets"])
    assert api_continuation["action_mode"] == "close_gaps"
    assert api_continuation["prior_run_progress"]["status"] == "baseline"
    _wait_for_run_success(client, api_run_id)

    _mark_run_as_unresolved(service, api_run_id)
    page_response = client.post(f"/loops/{bundle['loop_id']}/runs", follow_redirects=False)

    assert page_response.status_code == HTTPStatus.SEE_OTHER
    page_run_id = urlsplit(page_response.headers["location"]).path.removeprefix("/runs/")
    page_continuation = service.run_continuation_state(page_run_id)
    assert page_continuation["previous_run_id"] == api_run_id
    assert page_continuation["focus_target_count"] > 0
    assert all(item["status"] != "covered" for item in page_continuation["focus_targets"])
    assert page_continuation["action_mode"] == "change_approach"
    assert page_continuation["prior_run_progress"]["status"] == "no_progress"
    assert page_continuation["prior_run_progress"]["prior_run_id"] == previous_run["id"]
    _wait_for_run_success(client, page_run_id)
    detail = client.get(f"/runs/{page_run_id}")
    api_detail = client.get(f"/api/runs/{page_run_id}")
    status_kind, status_run = service.get_status(page_run_id)
    assert 'data-continuation-action-mode="change_approach"' in detail.text
    assert 'data-continuation-progress-status="no_progress"' in detail.text
    assert 'data-testid="run-continuation-prior-run-link"' in detail.text
    assert api_detail.json()["continuation"] == page_continuation
    assert status_kind == "run"
    assert status_run["continuation"] == page_continuation
    prompt_paths = sorted(Path(service.get_run(page_run_id)["runs_dir"]).glob("iterations/*/steps/*/prompt.md"))
    assert prompt_paths
    prompts = [path.read_text(encoding="utf-8") for path in prompt_paths]
    assert all("Cross-run action mode: change_approach" in prompt for prompt in prompts)
    assert all("Do not repeat the previous approach as-is" in prompt for prompt in prompts)


def test_saved_loop_start_keeps_recorded_result_closed_by_default(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = service.import_bundle_text(FakeCodexExecutor._alignment_bundle_yaml(str(sample_workdir.resolve())))
    previous_run = service.rerun(bundle["loop_id"])
    _mark_run_as_unresolved(service, previous_run["id"])
    accepted = service.accept_run_result(previous_run["id"])

    new_run = service.start_next_run(bundle["loop_id"])

    assert accepted["accepted"] is True
    assert service.run_continuation_state(new_run["id"])["active"] is False


def test_saved_loop_service_rerun_carries_latest_unresolved_context(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = service.import_bundle_text(FakeCodexExecutor._alignment_bundle_yaml(str(sample_workdir.resolve())))
    previous_run = service.rerun(bundle["loop_id"])
    _mark_run_as_unresolved(service, previous_run["id"])

    new_run = service.rerun(bundle["loop_id"])

    continuation = service.run_continuation_state(new_run["id"])
    assert continuation["reason"] == "terminal_task_verdict_requires_next_run"
    assert continuation["previous_run_id"] == previous_run["id"]
    assert continuation["focus_target_count"] > 0
    assert continuation["action_mode"] == "close_gaps"


def test_run_detail_rerun_routes_agent_first_terminal_run_back_to_slash_command(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    started = _start_agent_first_loop(service, tmp_path=tmp_path, workdir=sample_workdir)
    service.repository.update_run(
        started["run"]["id"],
        status="succeeded",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Required coverage still lacks direct evidence.",
            "buckets": {
                "proven": [],
                "weak": [],
                "unproven": [{"id": "coverage.required", "summary": "Required coverage is still missing."}],
                "blocking": [],
                "residual_risk": [],
            },
        },
        summary_md="# Loopora Run Summary\n\nLifecycle closed; task evidence still belongs to the Agent-native lane.\n",
    )
    client = TestClient(build_app(service=service))

    page_response = client.get(f"/runs/{started['run']['id']}")

    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="run-agent-entry-start-guide"' in page_response.text
    assert 'data-testid="run-agent-entry-copy-command-hero"' in page_response.text
    assert 'data-testid="run-agent-entry-copy-command"' in page_response.text
    assert "/loopora-run" in page_response.text
    assert "loopora agent codex run" in page_response.text
    assert "--context-id web-api-agent-first" in page_response.text
    assert "开启下一轮" in page_response.text
    assert "复制续跑命令" in page_response.text
    assert "data-agent-entry-command-copy" in page_response.text
    assert 'data-copy-value="' in page_response.text
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in page_response.text
    assert "loopora agent codex run" in page_response.text
    assert 'data-testid="run-rerun-button"' not in page_response.text

    api_response = client.post(
        f"/runs/{started['run']['id']}/rerun",
        headers={"accept": "application/json"},
    )

    assert api_response.status_code == HTTPStatus.CONFLICT
    api_payload = api_response.json()
    assert "Agent-native Loop runs" in api_payload["error"]
    assert "same host Agent" in api_payload["error"]
    assert api_payload["agent_entry_start"]["next_loop_action"] == "start_next_run_for_unproven_verdict"
    assert api_payload["agent_entry_start"]["linked_task_verdict_status"] == "insufficient_evidence"

    rerun_response = client.post(f"/runs/{started['run']['id']}/rerun", follow_redirects=False)

    assert rerun_response.status_code == HTTPStatus.SEE_OTHER
    rerun_parts = urlsplit(rerun_response.headers["location"])
    assert rerun_parts.path == f"/runs/{started['run']['id']}"
    rerun_query = parse_qs(rerun_parts.query)
    assert rerun_query["run_action_error"]
    assert rerun_query["workdir"] == [str(sample_workdir)]
    error_page = client.get(rerun_response.headers["location"])
    assert error_page.status_code == HTTPStatus.OK
    assert 'data-testid="run-action-error"' in error_page.text
    assert "Agent-native Loop runs" in error_page.text
    assert "same host Agent" in error_page.text
    assert 'data-testid="run-agent-entry-start-guide"' in error_page.text
    assert len(service.get_loop(started["run"]["loop_id"])["runs"]) == 1


def test_run_detail_rerun_explains_missing_saved_workdir(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Missing Workdir Rerun Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    shutil.rmtree(sample_workdir)
    client = TestClient(build_app(service=service))

    json_response = client.post(f"/runs/{run['id']}/rerun", headers={"accept": "application/json"})

    assert json_response.status_code == HTTPStatus.BAD_REQUEST
    payload = json_response.json()
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["surface"] == "web_loop_start"
    assert payload["loop_id"] == loop["id"]
    assert payload["next_actions"][-1]["kind"] == "retry_web_run_start"

    page_response = client.post(f"/runs/{run['id']}/rerun", follow_redirects=True)

    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="run-action-error"' in page_response.text
    assert 'data-testid="run-action-recovery"' in page_response.text
    assert 'data-recovery-action-kind="create_workdir"' in page_response.text
    assert 'data-recovery-action-kind="confirm_readiness"' in page_response.text
    assert 'data-recovery-action-kind="retry_web_run_start"' in page_response.text
    assert "mkdir -p" in page_response.text
    assert "loopora doctor --workdir" in page_response.text
    assert "workdir does not exist:" not in page_response.text
    assert not sample_workdir.exists()
    assert len(service.get_loop(loop["id"])["runs"]) == 1


def test_run_detail_rerun_redirects_to_failed_new_run_when_worker_cannot_start(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Rerun Dispatch Failure Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    private_path = tmp_path / "private" / "thread-start"
    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: _failing_run_thread(private_path))
    client = TestClient(build_app(service=service))

    page_response = client.post(f"/runs/{run['id']}/rerun", follow_redirects=False)

    assert page_response.status_code == HTTPStatus.SEE_OTHER
    parts = urlsplit(page_response.headers["location"])
    assert parts.path.startswith("/runs/")
    assert parse_qs(parts.query)["run_action_error"] == [BACKGROUND_WORKER_START_ERROR]
    assert parse_qs(parts.query)["workdir"] == [str(sample_workdir)]
    new_run_id = parts.path.removeprefix("/runs/")
    assert new_run_id != run["id"]
    stored = service.get_run(new_run_id)
    assert stored["status"] == "failed"
    assert stored["error_message"] == BACKGROUND_WORKER_START_ERROR
    assert "permission denied" not in page_response.headers["location"]
    assert str(private_path) not in page_response.headers["location"]


def test_run_detail_rerun_json_returns_failed_new_run_when_worker_cannot_start(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Rerun JSON Dispatch Failure Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    private_path = tmp_path / "private" / "thread-start"
    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: _failing_run_thread(private_path))
    client = TestClient(build_app(service=service))

    response = client.post(f"/runs/{run['id']}/rerun", headers={"accept": "application/json"})

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    payload = response.json()
    assert payload["error"] == BACKGROUND_WORKER_START_ERROR
    assert payload["run_start_error"] == BACKGROUND_WORKER_START_ERROR
    assert payload["run_recovery"] == "retry_run_start"
    assert payload["next_actions"] == [
        {
            "kind": "retry_web_run_start",
            "target": "web_loop_start",
            "action": "rerun",
            "loop_id": loop["id"],
        }
    ]
    assert payload["web_run_start_recovery_summary"]["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert payload["next_action_ready_after_actions"] == {}
    assert payload["run"]["status"] == "failed"
    assert payload["run"]["status_label"] == "run_start_failed"
    assert payload["run"]["run_recovery"] == "retry_run_start"
    assert payload["run"]["next_actions"] == payload["next_actions"]
    assert payload["run"]["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert payload["run"]["error_message"] == BACKGROUND_WORKER_START_ERROR
    assert payload["redirect_url"].startswith(f"/runs/{payload['run']['id']}?")
    assert "permission denied" not in response.text
    assert str(private_path) not in response.text


def _failing_run_thread(private_path: Path):
    class FailingRunThread:
        name = "run-start-failure"

        def start(self) -> None:
            raise OSError(f"permission denied: {private_path}")

    return FailingRunThread()
