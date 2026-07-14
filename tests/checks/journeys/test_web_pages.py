from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import quote, urlencode
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.settings import load_recent_workdirs, save_recent_workdirs
from loopora.web import build_app


def _assert_ok(response) -> None:
    assert response.status_code == 200, response.text[:500]


def _assert_testids(html: str, *testids: str) -> None:
    for testid in testids:
        assert f'data-testid="{testid}"' in html


def _home_run_href_fragment(run_id: object, workdir: object, *, testid: str) -> str:
    encoded_workdir = quote(str(Path(str(workdir)).resolve()), safe="")
    return f'href="/runs/{run_id}?workdir={encoded_workdir}" data-testid="{testid}"'


def _create_loop(service, spec_path: Path, workdir: Path, *, name: str = "Web Journey Loop") -> dict:
    return service.create_loop(
        name=name,
        spec_path=spec_path,
        workdir=workdir,
        model="",
        reasoning_effort="",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )


def _import_web_bundle(service, spec_path: Path, workdir: Path) -> dict:
    loop = _create_loop(service, spec_path, workdir, name="Plan File Source")
    bundle = service.derive_bundle_from_loop(
        loop["id"],
        name="Web Plan File",
        description="Plan file page smoke test.",
        collaboration_summary="Prefer evidence and visible proof.",
    )
    return service.import_bundle_text(bundle_to_yaml(bundle))


def _start_agent_first_loop(service, *, tmp_path: Path, workdir: Path) -> dict:
    bundle_file = tmp_path / "agent-first-bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=workdir,
            message=(
                "Ship the focused starter experience. The primary user flow must work end to end, "
                "use project-owned evidence, avoid happy-path claim only, keep a clear handoff, "
                "and let GateKeeper reject weak proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    return service.start_agent_loop("codex", workdir=workdir, entry_source="codex_project_skill", execute_async=False)


def test_web_full_function_surfaces_are_reachable(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.rerun(loop["id"])
    imported = _import_web_bundle(service, sample_spec_file, sample_workdir)
    client = TestClient(build_app(service=service))

    surfaces = {
        "/": ("top-nav", "nav-compose-link", "home-workbench"),
        "/loops/new": ("loop-create-page", "loop-create-choice-page"),
        "/loops/new/bundle": ("loop-create-page", "alignment-start-form", "alignment-history-panel"),
        "/loops/new/manual": ("loop-create-page", "manual-compose-section", "loop-create-form"),
        "/same-agent": ("agent-adapters-panel", "agent-adapter-draft-handoff", "agent-adapter-grid", "wake-lock-panel-section"),
        "/fit-guide": (
            "tutorial-page",
            "tutorial-page-intro",
            "tutorial-fit-guide",
            "tutorial-fit-task-review",
            "tutorial-actions-panel",
        ),
        "/tutorial": (
            "tutorial-page",
            "tutorial-page-intro",
            "tutorial-fit-guide",
            "tutorial-fit-task-review",
            "tutorial-actions-panel",
        ),
        "/roles": ("role-definitions-page", "builtin-role-templates-list"),
        "/orchestrations": ("orchestrations-page", "builtin-orchestrations-list"),
        "/bundles": ("bundles-page", "bundle-list"),
        f"/bundles/{imported['id']}": ("bundle-detail-page", "bundle-spec-preview", "bundle-yaml-preview"),
        f"/loops/{loop['id']}": ("loop-detail-page", "loop-detail-history-panel"),
        f"/runs/{run['id']}": ("run-detail-page", "run-console-panel", "run-timeline-panel"),
    }

    for path, testids in surfaces.items():
        response = client.get(path)
        _assert_ok(response)
        _assert_testids(response.text, *testids)


def test_run_pages_prioritize_loop_verdict_over_process_success(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Verdict Journey")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Missing audit proof.",
            "buckets": {"unproven": [{"label": "audit proof missing"}]},
        },
        summary_md="# Loopora Run Summary\n\nAll done according to the Agent summary.",
    )
    client = TestClient(build_app(service=service))

    home = client.get("/")
    loop_page = client.get(f"/loops/{loop['id']}")
    run_page = client.get(f"/runs/{run['id']}")
    for response in (home, loop_page, run_page):
        _assert_ok(response)

    assert "Missing audit proof." in home.text + loop_page.text + run_page.text
    assert "All done according to the Agent summary." not in home.text + loop_page.text
    _assert_testids(home.text, "home-active-loop-verdict", "home-active-loop-excerpt")
    assert 'data-testid="home-recent-loop-verdict"' not in home.text
    _assert_testids(
        loop_page.text,
        "loop-latest-verdict-pill",
        "loop-run-history-verdict",
        "loop-improve-latest-run-button",
        "loop-start-next-evidence-run-button",
        "loop-open-evidence-run",
    )
    assert 'data-testid="loop-start-run-button"' not in loop_page.text
    encoded_workdir = quote(str(sample_workdir), safe="")
    assert f'action="/runs/{run["id"]}/revise?workdir={encoded_workdir}"' in loop_page.text
    _assert_testids(run_page.text, "run-improve-chat-button", "run-rerun-button", "run-accept-result-button", "takeaway-empty-progress-link", "takeaway-empty-console-link", "timeline-empty-console-link")

    accept_response = client.post(f"/runs/{run['id']}/accept", follow_redirects=False)
    assert accept_response.status_code == 303
    accepted_event = service.recent_run_events(run["id"], event_types={"run_result_accepted"})[-1]
    assert accepted_event["payload"]["task_verdict_status"] == "insufficient_evidence"
    assert accepted_event["payload"]["recorded_verdict_kind"] == "unproven_verdict_recorded"
    home_after_accept = client.get("/")
    loop_after_accept = client.get(f"/loops/{loop['id']}")
    for response in (home_after_accept, loop_after_accept):
        _assert_ok(response)
    assert _home_run_href_fragment(run["id"], loop["workdir"], testid="home-active-loop") not in home_after_accept.text
    assert _home_run_href_fragment(run["id"], loop["workdir"], testid="home-recent-loop") in home_after_accept.text
    _assert_testids(home_after_accept.text, "home-recent-loop-recorded-result", "loop-card-recorded-result")
    _assert_testids(loop_after_accept.text, "loop-start-run-button")
    _assert_testids(loop_after_accept.text, "loop-recorded-result-state")
    assert 'data-testid="loop-improve-latest-run-button"' not in loop_after_accept.text
    run_after_accept = client.get(f"/runs/{run['id']}")
    _assert_ok(run_after_accept)
    _assert_testids(run_after_accept.text, "run-accepted-result-state")
    assert 'data-testid="run-recorded-advisory-rerun-button"' not in run_after_accept.text
    assert 'data-testid="run-improve-chat-button"' not in run_after_accept.text
    assert 'data-testid="run-evidence-improve-button"' not in run_after_accept.text
    assert 'data-testid="run-rerun-button"' not in run_after_accept.text
    _assert_testids(loop_after_accept.text, "loop-reopen-recorded-result-button")
    assert 'data-recorded-follow-up="advisory"' not in loop_after_accept.text
    assert 'data-testid="loop-recorded-advisory-summary"' not in loop_after_accept.text
    _assert_testids(run_after_accept.text, "run-reopen-recorded-result-button")

    _assert_web_owned_recorded_result_can_reopen(client, service, loop, run, recorded_event_id=accepted_event["id"])


def _assert_web_owned_recorded_result_can_reopen(client, service, loop: dict, run: dict, *, recorded_event_id: int) -> None:
    reopen_response = client.post(f"/runs/{run['id']}/reopen-result", follow_redirects=False)
    assert reopen_response.status_code == 303
    reopened_event = service.recent_run_events(run["id"], event_types={"run_result_acceptance_reopened"})[-1]
    assert reopened_event["payload"]["recorded_event_id"] == recorded_event_id
    home_after_reopen = client.get("/")
    loop_after_reopen = client.get(f"/loops/{loop['id']}")
    run_after_reopen = client.get(f"/runs/{run['id']}")
    for response in (home_after_reopen, loop_after_reopen, run_after_reopen):
        _assert_ok(response)
    assert _home_run_href_fragment(run["id"], loop["workdir"], testid="home-active-loop") in home_after_reopen.text
    assert 'data-testid="home-recent-loop-recorded-result"' not in home_after_reopen.text
    assert 'data-attention-reason-kind="needs_evidence"' in home_after_reopen.text
    assert 'data-attention-action-kind="continue_evidence"' in home_after_reopen.text
    _assert_testids(loop_after_reopen.text, "loop-improve-latest-run-button", "loop-start-next-evidence-run-button")
    assert 'data-testid="loop-recorded-result-state"' not in loop_after_reopen.text
    _assert_testids(run_after_reopen.text, "run-improve-chat-button", "run-rerun-button", "run-accept-result-button")
    assert 'data-testid="run-accepted-result-state"' not in run_after_reopen.text


def test_home_needs_attention_keeps_unproven_terminal_runs_visible_with_active_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    unproven_loop = _create_loop(service, sample_spec_file, sample_workdir, name="Unproven Terminal Loop")
    unproven_run = service.start_run(unproven_loop["id"])
    service.repository.update_run(
        unproven_run["id"],
        status="succeeded",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Terminal run still needs proof.",
        },
        summary_md="# Loopora Run Summary\n\nAgent says this is done.",
    )
    active_workdir = tmp_path / "active-workdir"
    active_workdir.mkdir()
    active_loop = _create_loop(service, sample_spec_file, active_workdir, name="Still Running Loop")
    active_run = service.start_run(active_loop["id"])
    awaiting_workdir = tmp_path / "awaiting-workdir"
    awaiting_workdir.mkdir()
    awaiting_loop = _create_loop(service, sample_spec_file, awaiting_workdir, name="Awaiting Agent Loop")
    awaiting_run = service.start_run(awaiting_loop["id"])
    service.repository.update_run(awaiting_run["id"], status="awaiting_agent")
    client = TestClient(build_app(service=service))

    home = client.get("/")

    _assert_ok(home)
    assert _home_run_href_fragment(unproven_run["id"], unproven_loop["workdir"], testid="home-active-loop") in home.text
    assert _home_run_href_fragment(active_run["id"], active_loop["workdir"], testid="home-active-loop") in home.text
    assert _home_run_href_fragment(awaiting_run["id"], awaiting_loop["workdir"], testid="home-active-loop") in home.text
    awaiting_index = home.text.index(_home_run_href_fragment(awaiting_run["id"], awaiting_loop["workdir"], testid="home-active-loop"))
    unproven_index = home.text.index(_home_run_href_fragment(unproven_run["id"], unproven_loop["workdir"], testid="home-active-loop"))
    active_index = home.text.index(_home_run_href_fragment(active_run["id"], active_loop["workdir"], testid="home-active-loop"))
    assert awaiting_index < unproven_index < active_index
    assert 'data-testid="home-active-loop-attention-reason"' in home.text
    assert 'data-testid="home-active-loop-action"' in home.text
    assert 'data-attention-priority="20"' in home.text
    assert 'data-attention-priority="30"' in home.text
    assert 'data-attention-priority="80"' in home.text
    assert 'data-attention-reason-kind="needs_evidence"' in home.text
    assert 'data-attention-reason-kind="run_active"' in home.text
    assert 'data-attention-reason-kind="awaiting_agent"' in home.text
    assert 'data-attention-action-kind="continue_evidence"' in home.text
    assert 'data-attention-action-kind="open_progress"' in home.text
    assert 'data-attention-action-kind="continue_agent"' in home.text
    assert 'data-testid="home-active-loop-excerpt"' in home.text
    assert "Terminal run still needs proof." in home.text
    assert "Agent says this is done." not in home.text


def test_home_recent_terminal_runs_follow_latest_run_recency_not_loop_order(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    older_loop = _create_loop(service, sample_spec_file, sample_workdir, name="Storage First Terminal Loop")
    older_run = service.start_run(older_loop["id"])
    service.repository.update_run(
        older_run["id"],
        status="succeeded",
        task_verdict={
            "status": "passed",
            "source": "gatekeeper",
            "summary": "Older result is complete.",
        },
        summary_md="# Loopora Run Summary\n\nOlder result is complete.",
    )
    newer_workdir = tmp_path / "newer-terminal-workdir"
    newer_workdir.mkdir()
    newer_loop = _create_loop(service, sample_spec_file, newer_workdir, name="Run Newer Terminal Loop")
    newer_run = service.start_run(newer_loop["id"])
    service.repository.update_run(
        newer_run["id"],
        status="succeeded",
        task_verdict={
            "status": "passed",
            "source": "gatekeeper",
            "summary": "Newer result is complete.",
        },
        summary_md="# Loopora Run Summary\n\nNewer result is complete.",
    )
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_definitions SET updated_at = ? WHERE id = ?",
            ("2026-06-16T04:00:00+00:00", older_loop["id"]),
        )
        connection.execute(
            "UPDATE loop_definitions SET updated_at = ? WHERE id = ?",
            ("2026-06-16T03:00:00+00:00", newer_loop["id"]),
        )
        connection.execute(
            "UPDATE loop_runs SET updated_at = ? WHERE id = ?",
            ("2026-06-16T01:00:00+00:00", older_run["id"]),
        )
        connection.execute(
            "UPDATE loop_runs SET updated_at = ? WHERE id = ?",
            ("2026-06-16T02:00:00+00:00", newer_run["id"]),
        )
    client = TestClient(build_app(service=service))

    home = client.get("/")

    _assert_ok(home)
    assert 'data-testid="home-active-loop"' not in home.text
    newer_index = home.text.index(_home_run_href_fragment(newer_run["id"], newer_loop["workdir"], testid="home-recent-loop"))
    older_index = home.text.index(_home_run_href_fragment(older_run["id"], older_loop["workdir"], testid="home-recent-loop"))
    assert newer_index < older_index


def test_home_attention_does_not_include_draft_loops(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Draft Loop")
    client = TestClient(build_app(service=service))

    home = client.get("/")

    _assert_ok(home)
    _assert_testids(home.text, "home-activity-empty", "home-saved-loops-section")
    assert 'data-testid="home-active-loop"' not in home.text
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    assert f'href="/loops/{loop["id"]}?workdir={encoded_workdir}"' in home.text
    _assert_testids(home.text, "loop-card-start-run-form", "loop-card-start-run-button")
    assert f'action="/loops/{loop["id"]}/runs?workdir={encoded_workdir}"' in home.text
    assert 'data-testid="loop-card-agent-run-guide-link"' not in home.text


def test_active_run_page_exposes_inline_stop_feedback(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Inline Stop Feedback")
    run = service.start_run(loop["id"])
    client = TestClient(build_app(service=service))

    run_page = client.get(f"/runs/{run['id']}")

    _assert_ok(run_page)
    _assert_testids(run_page.text, "run-stop-button", "run-stop-status", "run-action-refresh-notice")
    assert 'id="run-stop-status"' in run_page.text
    assert 'id="run-action-refresh-notice"' in run_page.text
    assert "aria-live=\"polite\"" in run_page.text


def test_agent_native_loop_pages_keep_command_handoff_instead_of_web_start(
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    started = _start_agent_first_loop(service, tmp_path=tmp_path, workdir=sample_workdir)
    service.repository.update_run(
        started["run"]["id"],
        status="succeeded",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Agent-first evidence is not proven yet.",
        },
        summary_md="# Loopora Run Summary\n\nAgent says done.",
    )
    client = TestClient(build_app(service=service))

    loop_page = client.get(f"/loops/{started['run']['loop_id']}")
    run_page = client.get(f"/runs/{started['run']['id']}")
    for response in (loop_page, run_page):
        _assert_ok(response)
        assert "/loopora-run" in response.text
        assert "codex_project_skill" in response.text
        assert 'action="/api/loops/' not in response.text
        assert f'action="/loops/{started["run"]["loop_id"]}/runs"' not in response.text

    _assert_testids(loop_page.text, "loop-agent-entry-start-guide", "loop-agent-entry-copy-command")
    _assert_testids(loop_page.text, "loop-improve-chat-button")
    assert 'data-agent-entry-primary-action="next-evidence"' in loop_page.text
    _assert_testids(run_page.text, "run-agent-handoff-card", "agent-handoff-copy-submit")

    web_start_response = client.post(f"/loops/{started['run']['loop_id']}/runs", follow_redirects=True)
    _assert_ok(web_start_response)
    _assert_testids(web_start_response.text, "loop-start-run-error", "loop-agent-entry-start-guide")
    assert "Agent-native Loop runs" in web_start_response.text
    assert len(service.get_loop(started["run"]["loop_id"])["runs"]) == 1

    accept_response = client.post(f"/runs/{started['run']['id']}/accept", follow_redirects=False)
    assert accept_response.status_code == 303
    loop_page_after_accept = client.get(f"/loops/{started['run']['loop_id']}")
    _assert_ok(loop_page_after_accept)
    _assert_testids(loop_page_after_accept.text, "loop-agent-entry-start-guide", "loop-recorded-result-state")
    assert 'data-testid="loop-improve-chat-button"' not in loop_page_after_accept.text
    assert 'data-agent-entry-primary-action="agent-command"' in loop_page_after_accept.text
    assert f'action="/loops/{started["run"]["loop_id"]}/runs"' not in loop_page_after_accept.text
    run_page_after_accept = client.get(f"/runs/{started['run']['id']}")
    _assert_ok(run_page_after_accept)
    _assert_testids(run_page_after_accept.text, "run-accepted-result-state")
    assert 'data-agent-entry-primary-action="agent-command"' in run_page_after_accept.text
    assert 'data-testid="run-improve-chat-button"' not in run_page_after_accept.text
    assert 'data-testid="run-evidence-improve-button"' not in run_page_after_accept.text

    reopen_response = client.post(f"/runs/{started['run']['id']}/reopen-result", follow_redirects=False)
    assert reopen_response.status_code == 303
    loop_page_after_reopen = client.get(f"/loops/{started['run']['loop_id']}")
    run_page_after_reopen = client.get(f"/runs/{started['run']['id']}")
    for response in (loop_page_after_reopen, run_page_after_reopen):
        _assert_ok(response)
        assert 'data-agent-entry-primary-action="next-evidence"' in response.text
        assert 'data-testid="run-accepted-result-state"' not in response.text
    _assert_testids(loop_page_after_reopen.text, "loop-improve-chat-button")
    _assert_testids(run_page_after_reopen.text, "run-result-decision", "run-improve-chat-button")
    assert run_page_after_reopen.text.count('data-testid="run-improve-chat-button"') == 1
    assert 'data-testid="run-evidence-improve-button"' not in run_page_after_reopen.text


def test_loop_detail_start_run_uses_web_form_without_javascript(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Progressive Start Loop")
    client = TestClient(build_app(service=service))

    loop_page = client.get(f"/loops/{loop['id']}")
    _assert_ok(loop_page)
    _assert_testids(loop_page.text, "loop-start-run-form", "loop-start-run-button", "loop-history-empty-start-run-form", "loop-history-empty-start-run-button")
    encoded_workdir = quote(str(sample_workdir), safe="")
    assert f'action="/loops/{loop["id"]}/runs?workdir={encoded_workdir}"' in loop_page.text
    assert 'data-workdir-context-form="workdir"' in loop_page.text
    assert 'action="/api/loops/' not in loop_page.text
    assert "onsubmit=" not in loop_page.text

    start_response = client.post(f"/loops/{loop['id']}/runs", follow_redirects=False)

    assert start_response.status_code == 303
    redirect_parts = urlsplit(start_response.headers["location"])
    assert redirect_parts.path.startswith("/runs/")
    assert parse_qs(redirect_parts.query)["workdir"] == [str(sample_workdir)]
    new_run_id = redirect_parts.path.removeprefix("/runs/")
    assert new_run_id
    assert service.get_run(new_run_id)["loop_id"] == loop["id"]


def test_loop_detail_start_run_conflict_returns_to_visible_page_error(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Start Conflict Loop")
    service.start_run(loop["id"])
    client = TestClient(build_app(service=service))

    start_response = client.post(f"/loops/{loop['id']}/runs", follow_redirects=False)

    assert start_response.status_code == 303
    redirect_parts = urlsplit(start_response.headers["location"])
    assert redirect_parts.path == f"/loops/{loop['id']}"
    redirect_query = parse_qs(redirect_parts.query)
    assert redirect_query["run_start_error"]
    assert redirect_query["workdir"] == [str(sample_workdir)]
    error_page = client.get(start_response.headers["location"])
    _assert_ok(error_page)
    _assert_testids(error_page.text, "loop-start-run-error", "loop-start-run-form")
    assert "active run" in error_page.text


def test_plan_file_surfaces_cover_preview_replace_export_and_diagnostics(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = _import_web_bundle(service, sample_spec_file, sample_workdir)
    service._bundle_spec_path(imported["id"]).write_bytes(b"\xff")

    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Diagnostic Source")
    weak_bundle = service.derive_bundle_from_loop(
        loop["id"],
        name="Weak Plan File",
        description="Projection test.",
        collaboration_summary="Prefer evidence and visible proof.",
    )
    for step in weak_bundle["workflow"]["steps"]:
        if step["id"] == "gatekeeper_step":
            step.pop("inputs", None)
    weak_import = service.import_bundle_text(bundle_to_yaml(weak_bundle))
    client = TestClient(build_app(service=service))

    list_page = client.get("/bundles")
    unreadable_detail = client.get(f"/bundles/{imported['id']}")
    diagnostic_detail = client.get(f"/bundles/{weak_import['id']}")
    export_response = client.get(f"/api/bundles/{weak_import['id']}/export")
    replace_redirect = client.get(f"/loops/new?replace_bundle_id={weak_import['id']}", follow_redirects=False)
    legacy_replace_redirect = client.get(
        f"/bundles?replace_bundle_id={weak_import['id']}&workdir=/tmp/demo&token=secret-token",
        follow_redirects=False,
    )
    clean_replace_page = client.get(f"/bundles?replace_bundle_id={weak_import['id']}&workdir=/tmp/demo")
    replace_page = client.get(f"/loops/new/manual?replace_bundle_id={weak_import['id']}")

    for response in (list_page, unreadable_detail, diagnostic_detail, export_response, clean_replace_page, replace_page):
        _assert_ok(response)
    assert replace_redirect.status_code == 303
    assert replace_redirect.headers["location"] == f"/loops/new/manual?replace_bundle_id={weak_import['id']}#bundle-import-form"
    assert legacy_replace_redirect.status_code == 303
    assert (
        legacy_replace_redirect.headers["location"]
        == f"/bundles?replace_bundle_id={weak_import['id']}&workdir=%2Ftmp%2Fdemo#bundle-import-panel"
    )
    assert "secret-token" not in legacy_replace_redirect.headers["location"]
    assert 'data-testid="bundle-import-form"' in clean_replace_page.text
    assert 'data-import-intent="replace"' in clean_replace_page.text
    assert 'data-testid="bundle-replace-target-note"' in clean_replace_page.text
    assert f'value="{weak_import["id"]}"' in clean_replace_page.text
    assert 'name="import_intent" value="replace"' in clean_replace_page.text
    assert "Replace plan id" not in clean_replace_page.text

    _assert_testids(list_page.text, "bundles-page", "bundle-list")
    _assert_testids(unreadable_detail.text, "bundle-detail-page")
    assert "bundle spec file could not be read" in unreadable_detail.text
    _assert_testids(diagnostic_detail.text, "bundle-diagnostic-projection", "bundle-diagnostic-row")
    assert "gatekeeper_missing_handoff_fan_in" in diagnostic_detail.text
    _assert_testids(replace_page.text, "bundle-replace-target-note")
    assert 'name="import_intent" value="replace"' in replace_page.text
    assert "Replace plan id" not in replace_page.text
    assert "workflow:" in export_response.text


def test_web_entry_redirects_keep_auth_out_of_urls_and_remote_paths_explicit(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    redirect = client.get("/loops/new?token=secret-token&workdir=/tmp/demo", follow_redirects=False)
    remote_manual = client.get("/loops/new/manual?token=secret-token")

    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/loops/new?workdir=%2Ftmp%2Fdemo"
    assert "secret-token" not in redirect.headers["location"]
    assert client.cookies.get("loopora_auth") == "secret-token"
    _assert_ok(remote_manual)
    _assert_testids(remote_manual.text, "remote-path-callout", "manual-workdir-remote-path-note", "manual-spec-remote-path-note")
    assert 'data-testid="workdir-browse-button"' not in remote_manual.text
    assert 'id="browse-spec"' not in remote_manual.text


def _assert_create_choice_bundle_target_context(bundle_html: str) -> None:
    assert 'data-testid="global-workdir-context"' in bundle_html
    assert 'value="/tmp/demo"' in bundle_html
    assert all(
        fragment in bundle_html
        for fragment in (
            'href="/same-agent?workdir=%2Ftmp%2Fdemo"',
            'data-compose-path-kind="same_agent_setup"',
            'data-testid="alignment-path-agent-setup"',
            'data-workdir-context-link="workdir"',
        )
    )
    assert 'data-compose-import-href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#bundle-import-form"' in bundle_html
    assert 'data-compose-manual-href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#manual-loop-form"' in bundle_html
    assert 'data-tutorial-fit-href="/fit-guide?workdir=%2Ftmp%2Fdemo#tutorial-decision-tree-panel"' in bundle_html
    assert 'data-workdir-context-dataset-urls="composeImportHref:workdir composeManualHref:workdir tutorialFitHref:workdir"' in bundle_html
    assert 'data-history-empty-start-href="/loops/new/bundle?alignment_workdir=%2Ftmp%2Fdemo"' in bundle_html
    assert 'data-workdir-context-dataset-urls="historyEmptyStartHref:alignment_workdir"' in bundle_html


def _assert_create_choice_manual_target_context(manual_html: str) -> None:
    assert all(fragment in manual_html for fragment in ('data-testid="global-workdir-context"', 'data-restore-draft="false"'))
    assert 'data-history-empty-start-href="/loops/new/bundle?alignment_workdir=%2Ftmp%2Fdemo"' in manual_html
    assert 'data-workdir-context-dataset-urls="historyEmptyStartHref:alignment_workdir"' in manual_html
    assert all(
        fragment in manual_html
        for fragment in (
            'href="/same-agent?workdir=%2Ftmp%2Fdemo"',
            'data-compose-path-kind="same_agent_setup"',
            'data-testid="alignment-path-agent-setup"',
            'data-workdir-context-link="workdir"',
        )
    )
    assert 'value="/tmp/demo"' in manual_html
    assert 'action="/loops/new/manual/import-bundle?workdir=%2Ftmp%2Fdemo"' in manual_html
    assert 'action="/loops/new/manual?workdir=%2Ftmp%2Fdemo"' in manual_html
    assert 'name="import_intent" value="import"' in manual_html
    assert 'name="replace_bundle_id"' not in manual_html
    assert (
        'href="/loops/new/bundle?alignment_workdir=%2Ftmp%2Fdemo" '
        'data-testid="manual-spec-web-guidance-link" data-workdir-context-link="alignment_workdir"'
    ) in manual_html
    assert 'data-compose-import-href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#bundle-import-form"' in manual_html
    assert 'data-compose-manual-href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#manual-loop-form"' in manual_html
    assert 'data-tutorial-fit-href="/fit-guide?workdir=%2Ftmp%2Fdemo#tutorial-decision-tree-panel"' in manual_html
    assert 'data-workdir-context-dataset-urls="composeImportHref:workdir composeManualHref:workdir tutorialFitHref:workdir"' in manual_html
    assert 'href="/roles?workdir=%2Ftmp%2Fdemo&amp;return_to=' in manual_html
    assert 'data-testid="manual-roles-link" data-workdir-context-link="workdir"' in manual_html
    assert 'href="/orchestrations?workdir=%2Ftmp%2Fdemo&amp;return_to=' in manual_html
    assert 'data-testid="manual-orchestrations-link" data-workdir-context-link="workdir"' in manual_html
    assert "%2Floops%2Fnew%2Fmanual%3Fworkdir%3D%252Ftmp%252Fdemo%23manual-loop-form" in manual_html
    assert 'href="/fit-guide?workdir=%2Ftmp%2Fdemo" data-testid="manual-fit-guide-link" data-workdir-context-link="workdir"' in manual_html
    assert 'href="/?workdir=%2Ftmp%2Fdemo" data-testid="manual-cancel-link" data-workdir-context-link="workdir"' in manual_html


def test_create_choice_preserves_workdir_without_forcing_expert_path(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    choice = client.get("/loops/new?workdir=/tmp/demo")
    bundle = client.get("/loops/new/bundle?workdir=/tmp/demo")
    judgment_page = client.get("/loops/new/bundle?workdir=/tmp/demo&alignment_task_goal=leak-goal&alignment_fake_done_risk=leak-risk&alignment_required_evidence=leak-evidence&alignment_judgment_tradeoffs=leak-tradeoff&alignment_message=leak-message")
    manual = client.get("/loops/new/manual?workdir=/tmp/demo")
    manual_redirect = client.get("/loops/new?workdir=/tmp/demo&spec_path=/tmp/spec.md", follow_redirects=False)
    _assert_ok(choice)
    _assert_testids(choice.text, "loop-create-choice-page")
    assert 'data-testid="global-workdir-context"' in choice.text
    assert (
        'href="/fit-guide?workdir=%2Ftmp%2Fdemo#tutorial-decision-tree-panel" '
        'data-testid="loop-create-fit-guide-link" data-workdir-context-link="workdir"'
    ) in choice.text
    assert (
        'href="/same-agent?workdir=%2Ftmp%2Fdemo" data-create-choice-setup-start '
        'data-testid="loop-create-agent-link" data-workdir-context-link="workdir"'
    ) in choice.text
    assert (
        'href="/loops/new/bundle?alignment_workdir=%2Ftmp%2Fdemo" data-create-choice-web-start '
        'data-testid="loop-create-bundle-link" data-workdir-context-link="alignment_workdir"'
    ) in choice.text
    assert (
        'href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#bundle-import-form" '
        'data-create-choice-expert-start data-testid="loop-create-import-link" data-workdir-context-link="workdir"'
    ) in choice.text
    assert (
        'href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#manual-loop-form" '
        'data-create-choice-expert-start data-testid="loop-create-manual-link" data-workdir-context-link="workdir"'
    ) in choice.text
    assert 'data-testid="loop-create-existing-empty-state"' in choice.text
    assert 'data-testid="loop-create-existing-attention-link"' not in choice.text
    assert 'const manualLoopFormHref = "/loops/new/manual?workdir=%2Ftmp%2Fdemo#manual-loop-form";' in choice.text
    assert 'const bundleImportHref = "/loops/new/manual?workdir=%2Ftmp%2Fdemo#bundle-import-form";' in choice.text
    _assert_ok(bundle)
    _assert_create_choice_bundle_target_context(bundle.text)
    _assert_ok(judgment_page)
    assert not any(value in judgment_page.text for value in ("leak-goal", "leak-risk", "leak-evidence", "leak-tradeoff", "leak-message"))
    assert 'value="/tmp/demo"' in judgment_page.text
    _assert_ok(manual)
    _assert_create_choice_manual_target_context(manual.text)
    assert manual_redirect.status_code == 303
    assert manual_redirect.headers["location"] == "/loops/new/manual?workdir=%2Ftmp%2Fdemo&spec_path=%2Ftmp%2Fspec.md#manual-loop-form"


def _assert_start_home_navigation_links(home_html: str, plain_home_html: str) -> None:
    assert (
        'href="/same-agent?workdir=%2Ftmp%2Fdemo" data-testid="home-agent-entry-link" '
        'data-workdir-context-link="workdir"'
    ) in home_html
    assert 'data-testid="global-workdir-context"' in home_html
    assert (
        'href="/loops/new/bundle?alignment_workdir=%2Ftmp%2Fdemo" data-testid="home-compose-loop-link" '
        'data-workdir-context-link="alignment_workdir"'
    ) in home_html
    assert (
        'href="/fit-guide?workdir=%2Ftmp%2Fdemo#tutorial-decision-tree-panel" '
        'data-testid="home-fit-guide-link" data-workdir-context-link="workdir"'
    ) in home_html
    assert 'href="/loops/new/bundle" data-testid="home-compose-loop-link" data-workdir-context-link="alignment_workdir"' in plain_home_html
    assert all('data-testid="home-activity-section"' not in html and 'data-testid="home-saved-loops-section"' not in html for html in (home_html, plain_home_html))
    assert 'href="/same-agent" data-testid="home-agent-entry-link" data-workdir-context-link="workdir"' in plain_home_html
    assert all(testid not in home_html for testid in ('data-testid="loops-empty-create-choice-link"', 'data-testid="loops-empty-agent-setup-link"', 'data-testid="loops-empty-import-plan-link"'))
    assert all(testid not in plain_home_html for testid in ('data-testid="loops-empty-create-choice-link"', 'data-testid="loops-empty-agent-setup-link"', 'data-testid="loops-empty-import-plan-link"'))
    assert 'data-testid="global-workdir-context" hidden' in plain_home_html
    assert 'href="/fit-guide" data-testid="nav-tutorial-link"' in plain_home_html
    assert 'href="/support" data-testid="nav-support-link"' in plain_home_html
    assert (
        'href="/fit-guide#tutorial-decision-tree-panel" data-testid="home-fit-guide-link" '
        'data-workdir-context-link="workdir"'
    ) in plain_home_html


def _assert_start_tools_navigation_links(
    tools_html: str,
    support_html: str,
    plain_support_html: str,
    recent_workdir: str,
) -> None:
    assert 'href="/?workdir=%2Ftmp%2Fdemo" data-testid="nav-loops-link"' in tools_html
    assert 'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="nav-compose-link"' in tools_html
    assert 'href="/bundles?workdir=%2Ftmp%2Fdemo"\n            id="nav-resource-toggle"' in tools_html
    assert 'href="/bundles?workdir=%2Ftmp%2Fdemo" data-testid="nav-menu-bundles-link"' in tools_html
    assert 'href="/fit-guide?workdir=%2Ftmp%2Fdemo" data-testid="nav-tutorial-link"' in tools_html
    assert (
        'href="/support?workdir=%2Ftmp%2Fdemo&amp;return_to=%2Fsame-agent%3Fworkdir%3D%252Ftmp%252Fdemo" data-testid="nav-support-link"'
        in tools_html
    )
    assert 'href="/roles?workdir=%2Ftmp%2Fdemo" data-testid="nav-menu-roles-link"' in tools_html
    assert 'href="/orchestrations?workdir=%2Ftmp%2Fdemo" data-testid="nav-menu-orchestrations-link"' in tools_html
    assert 'data-testid="agent-adapter-draft-handoff"' in tools_html
    assert 'href="/fit-guide?workdir=%2Ftmp%2Fdemo#tutorial-decision-tree-panel"' in tools_html
    assert 'data-testid="tools-fit-guide-link"' in tools_html
    assert 'data-agent-adapter-workdir-context-link="1"' in tools_html
    assert all(fragment in support_html for fragment in (
        'data-testid="support-page"',
        'data-testid="support-hero"',
        'data-testid="support-hero-target-context"',
        'data-support-target-project-required="false"',
        'data-testid="support-public-report-link"',
        'data-support-copy-public-report="true"',
        'data-support-target-summary',
        'data-support-target-description',
        'id="support-target-form"',
        'action="/support?workdir=%2Ftmp%2Fdemo"',
        'href="/support?workdir=%2Ftmp%2Fdemo" data-testid="nav-support-link"',
        'data-workdir-context-form="workdir"',
        'method="post"',
        'name="workdir"',
        'value="/tmp/demo"',
        'data-testid="support-browse-workdir"',
        'data-testid="support-target-status"',
        "Use Target",
        'data-testid="tools-support-panel"',
        'data-support-public-report-url="/api/diagnostics/public-issue-bundle?workdir=%2Ftmp%2Fdemo&amp;language=en"',
        'href="/same-agent?workdir=%2Ftmp%2Fdemo" data-testid="support-tools-link"',
        'static/pages/support.js',
    ))
    assert any(fragment in support_html for fragment in (
        "This page has target-project context",
        "You can copy a public issue support bundle as redacted evidence",
    ))
    assert "Copy Public Issue Bundle" in support_html
    assert all(fragment in plain_support_html for fragment in (
        'data-testid="support-page"',
        'data-testid="support-hero-target-context"',
        'data-support-target-project-status="required"',
        'data-support-target-project-required="true"',
        "A public report needs target-project context",
        'data-support-public-report-url=""',
        'data-support-target-summary',
        'data-support-target-description',
        'href="#support-target-form"',
        'data-testid="support-public-report-link"',
        "Choose Target First",
        'id="support-target-form"',
        'action="/support"',
        'data-workdir-context-form="workdir"',
        'method="post"',
        'name="workdir"',
        'value=""',
        'list="support-target-workdir-options"',
        'data-testid="support-browse-workdir"',
        'data-testid="support-target-status"',
        'data-testid="support-recent-workdirs"',
        'data-support-recent-workdir',
        recent_workdir,
        "Use Target",
        'href="/same-agent" data-testid="support-tools-link"',
    ))


def _assert_start_bundle_navigation_links(bundle_html: str) -> None:
    assert 'href="/same-agent?workdir=%2Ftmp%2Fdemo" data-testid="nav-tools-link"' in bundle_html
    assert 'data-testid="global-workdir-context"' in bundle_html
    assert 'href="/loops/new/bundle?alignment_workdir=%2Ftmp%2Fdemo"' in bundle_html
    assert 'data-compose-mode-link="chat"' in bundle_html
    assert 'href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#bundle-import-form"' in bundle_html
    assert 'data-compose-mode-link="import"' in bundle_html


def _assert_start_tutorial_navigation_links(tutorial_html: str) -> None:
    assert all(
        fragment in tutorial_html
        for fragment in (
            'data-testid="tutorial-page-intro"',
            'href="#tutorial-guide-panel" data-testid="tutorial-boundary-link"',
            'data-testid="tutorial-fit-task-use-tools"\n                data-workdir-context-link="workdir"',
            'data-testid="tutorial-fit-task-use-web"\n                data-workdir-context-link="workdir"',
            'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="tutorial-web-compose-link" data-workdir-context-link="workdir"',
            'href="/loops/new/manual?workdir=%2Ftmp%2Fdemo" data-testid="tutorial-manual-compose-link" data-workdir-context-link="workdir"',
            'href="/orchestrations?workdir=%2Ftmp%2Fdemo" data-testid="tutorial-workflow-examples-link" data-workdir-context-link="workdir"',
        )
    )
    assert 'href="/same-agent?workdir=%2Ftmp%2Fdemo" data-testid="tutorial-agent-entry-link" data-workdir-context-link="workdir"' in tutorial_html
    assert 'data-testid="global-workdir-context"' in tutorial_html
    assert 'data-testid="tutorial-fit-strong-signals"' in tutorial_html
    assert 'data-testid="tutorial-fit-direct-signals"' in tutorial_html
    assert 'data-testid="tutorial-fit-task-review"' in tutorial_html
    assert 'data-testid="tutorial-fit-signal-disclosure"' in tutorial_html
    assert 'data-testid="tutorial-flow-comparison-disclosure"' in tutorial_html
    assert all(fragment in tutorial_html for fragment in ('data-testid="tutorial-fit-task-input"', 'data-testid="tutorial-fit-loopora-fit-reason-input"'))
    assert 'data-testid="tutorial-fit-fake-done-risks-input"' in tutorial_html
    assert 'data-testid="tutorial-fit-required-evidence-input"' in tutorial_html
    assert 'data-testid="tutorial-fit-judgment-tradeoffs-input"' in tutorial_html
    assert 'data-testid="tutorial-fit-task-review-questions"' in tutorial_html
    assert "multi-round Agent work" in tutorial_html
    assert "stable tests, checks, proofs" in tutorial_html
    assert "Which strong-fit signal, if any, actually applies to this task?" in tutorial_html
    assert "secret-token" not in tutorial_html


def test_fit_guide_request_workdir_projects_machine_readable_context(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    target_workdir = tmp_path / "fit-target"
    target_workdir.mkdir()
    client = TestClient(build_app(service=service))

    page = client.get(f"/fit-guide?workdir={quote(str(target_workdir), safe='')}")

    _assert_ok(page)
    resolved_workdir = str(target_workdir.resolve())
    assert f'data-fit-workdir="{resolved_workdir}"' in page.text
    assert all(fragment in page.text for fragment in (
        'data-fit-workdir-state-status="ready"',
        'data-fit-workdir-ready="true"',
        'data-fit-target-project-required="false"',
        'data-fit-route-commands-placeholders="false"',
    ))
    startup_client = TestClient(build_app(service=service, startup_workdir=str(target_workdir)))
    startup_page = startup_client.get("/fit-guide")
    encoded_workdir = quote(resolved_workdir, safe="")

    _assert_ok(startup_page)
    assert (
        f'href="/same-agent?workdir={encoded_workdir}" '
        'data-testid="tutorial-agent-entry-link" data-workdir-context-link="workdir"'
    ) in startup_page.text
    assert f'data-fit-workdir="{resolved_workdir}"' in startup_page.text
    assert 'data-fit-workdir-state-status="ready"' in startup_page.text


def test_same_agent_setup_startup_workdir_initializes_target_context(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    target_workdir = tmp_path / "same-agent-target"
    target_workdir.mkdir()
    client = TestClient(build_app(service=service, startup_workdir=str(target_workdir)))

    page = client.get("/same-agent")

    _assert_ok(page)
    resolved_workdir = str(target_workdir.resolve())
    encoded_workdir = quote(resolved_workdir, safe="")
    assert f'data-agent-adapter-workdir-context="{resolved_workdir}"' in page.text
    assert f'href="/fit-guide?workdir={encoded_workdir}#tutorial-decision-tree-panel"' in page.text
    assert f'href="/loops/new?workdir={encoded_workdir}" data-testid="tools-create-choice-link"' in page.text
    assert 'data-testid="global-workdir-context"' in page.text


def test_global_project_scope_switches_targets_and_can_override_startup_default(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    startup_workdir = tmp_path / "startup project"
    other_workdir = tmp_path / "other project"
    startup_workdir.mkdir()
    other_workdir.mkdir()
    startup_loop = _create_loop(service, sample_spec_file, startup_workdir, name="Startup Project Loop")
    other_loop = _create_loop(service, sample_spec_file, other_workdir, name="Other Project Loop")
    client = TestClient(build_app(service=service, startup_workdir=str(startup_workdir)))

    scoped_home = client.get("/")
    _assert_ok(scoped_home)
    assert scoped_home.text.count('data-testid="loop-card"') == 1
    assert startup_loop["id"] in scoped_home.text
    assert other_loop["id"] not in scoped_home.text
    assert 'data-testid="global-project-scope"' in scoped_home.text
    assert 'data-testid="global-project-scope-form"' in scoped_home.text

    all_home = client.get("/?project_scope=all")
    _assert_ok(all_home)
    assert all_home.text.count('data-testid="loop-card"') == 2
    assert 'data-testid="global-workdir-context" hidden' in all_home.text
    assert 'href="/fit-guide?project_scope=all" data-testid="nav-tutorial-link"' in all_home.text

    entity_page = client.get(f"/loops/{other_loop['id']}?project_scope=all")
    _assert_ok(entity_page)
    other_resolved = str(other_workdir.resolve())
    assert f'<code title="{other_resolved}">{other_resolved}</code>' in entity_page.text
    nav_tutorial_href = entity_page.text.split('data-testid="nav-tutorial-link"', 1)[0].rsplit('href="', 1)[1]
    nav_tutorial_href = nav_tutorial_href.split('"', 1)[0].replace("&amp;", "&")
    assert parse_qs(urlsplit(nav_tutorial_href).query) == {"workdir": [other_resolved]}

    all_redirect = client.post("/project-scope", data={"workdir": ""}, follow_redirects=False)
    assert all_redirect.status_code == 303
    all_query = parse_qs(urlsplit(all_redirect.headers["location"]).query)
    assert all_query == {"project_scope": ["all"], "project_scope_feedback": ["all"]}

    invalid_redirect = client.post(
        "/project-scope",
        data={"workdir": "relative/project"},
        follow_redirects=False,
    )
    assert invalid_redirect.status_code == 303
    invalid_query = parse_qs(urlsplit(invalid_redirect.headers["location"]).query)
    assert invalid_query == {
        "project_scope": ["all"],
        "project_scope_feedback": ["target_unavailable"],
    }

    selected_redirect = client.post(
        "/project-scope",
        data={"workdir": str(other_workdir)},
        follow_redirects=False,
    )
    assert selected_redirect.status_code == 303
    selected_query = parse_qs(urlsplit(selected_redirect.headers["location"]).query)
    assert selected_query == {
        "workdir": [other_resolved],
        "project_scope_feedback": ["selected"],
    }
    assert load_recent_workdirs()[0] == other_resolved
    _assert_project_scope_safe_returns(client, other_workdir=other_workdir, startup_loop=startup_loop)


def _assert_project_scope_safe_returns(client: TestClient, *, other_workdir: Path, startup_loop: dict) -> None:
    other_resolved = str(other_workdir.resolve())
    same_agent_page = client.get("/same-agent")
    _assert_ok(same_agent_page)
    assert 'name="return_to" value="/same-agent"' in same_agent_page.text
    same_agent_redirect = client.post(
        "/project-scope",
        data={"workdir": str(other_workdir), "return_to": "/tools?token=secret"},
        follow_redirects=False,
    )
    same_agent_location = urlsplit(same_agent_redirect.headers["location"])
    assert same_agent_location.path == "/same-agent"
    assert parse_qs(same_agent_location.query) == {
        "workdir": [other_resolved],
        "project_scope_feedback": ["selected"],
    }
    deep_return_redirect = client.post(
        "/project-scope",
        data={"workdir": "", "return_to": f"/loops/{startup_loop['id']}?token=secret"},
        follow_redirects=False,
    )
    deep_return_location = urlsplit(deep_return_redirect.headers["location"])
    assert deep_return_location.path == "/"
    assert parse_qs(deep_return_location.query) == {
        "project_scope": ["all"],
        "project_scope_feedback": ["all"],
    }


def _assert_start_bundles_navigation_links(bundles_html: str) -> None:
    assert 'href="#bundle-import-panel" data-testid="bundles-import-plan-link"' in bundles_html
    assert (
        'href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#bundle-import-form" '
        'data-testid="bundles-create-loop-import-link"'
    ) in bundles_html
    assert 'data-testid="global-workdir-context"' in bundles_html
    assert 'action="/bundles/import?workdir=%2Ftmp%2Fdemo"' in bundles_html
    assert 'data-testid="bundle-import-form"' in bundles_html
    assert 'data-workdir-context-form="workdir"' in bundles_html
    assert 'data-testid="bundle-derive-empty-state"' in bundles_html
    assert 'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="bundle-derive-create-loop-link"' in bundles_html
    assert 'href="#bundle-import-panel" data-testid="bundles-empty-import-plan-link"' in bundles_html
    assert 'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="bundles-empty-create-choice-link"' in bundles_html
    assert 'href="/same-agent?workdir=%2Ftmp%2Fdemo" data-testid="bundles-empty-agent-setup-link"' in bundles_html
    assert 'href="/fit-guide?workdir=%2Ftmp%2Fdemo" data-testid="nav-tutorial-link"' in bundles_html


def test_start_navigation_preserves_workdir_between_peer_entry_surfaces(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    recent_workdir = str(tmp_path / "recent-support-target")
    save_recent_workdirs([recent_workdir])
    client = TestClient(build_app(service=service))

    home = client.get("/?workdir=/tmp/demo")
    tools = client.get("/same-agent?workdir=/tmp/demo")
    support = client.get("/support?workdir=/tmp/demo")
    plain_support = client.get("/support")
    bundle = client.get("/loops/new/bundle?alignment_workdir=/tmp/demo")
    tutorial = client.get("/fit-guide?Token=secret-token&workdir=/tmp/demo")
    bundles = client.get("/bundles?workdir=/tmp/demo")
    plain_home = client.get("/")

    _assert_ok(home)
    _assert_ok(tools)
    _assert_ok(support)
    _assert_ok(plain_support)
    _assert_ok(bundle)
    _assert_ok(tutorial)
    _assert_ok(bundles)
    _assert_ok(plain_home)
    _assert_start_home_navigation_links(home.text, plain_home.text)
    _assert_start_tools_navigation_links(tools.text, support.text, plain_support.text, recent_workdir)
    _assert_start_bundle_navigation_links(bundle.text)
    _assert_start_tutorial_navigation_links(tutorial.text)
    _assert_start_bundles_navigation_links(bundles.text)


def test_support_target_submission_promotes_recent_workdir_and_redirects(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    target = tmp_path / "support target"
    target.mkdir()
    client = TestClient(build_app(service=service))

    redirect = client.post("/support", data={"workdir": f" {target} "}, follow_redirects=False)

    encoded_workdir = urlencode({"workdir": str(target.resolve()), "support_target_feedback": "target_ready"})
    assert redirect.status_code == 303
    assert redirect.headers["location"] == f"/support?{encoded_workdir}"
    assert load_recent_workdirs()[:1] == [str(target.resolve())]

    support = client.get(redirect.headers["location"])
    _assert_ok(support)
    assert f'value="{target.resolve()}"' in support.text
    assert str(target.resolve()) in support.text
    assert 'data-support-target-feedback="target_ready"' in support.text
    assert 'data-return-feedback-param="support_target_feedback"' in support.text
    assert 'data-support-copy-public-report="true"' in support.text
    assert "Copy Public Issue Bundle" in support.text
    assert "Target project is ready and saved to recent targets." in support.text

    return_to = "/loops/new/manual?token=secret-token#bundle-import-form"
    return_redirect = client.post(
        f"/support?return_to={quote(return_to, safe='')}",
        data={"workdir": str(target)},
        follow_redirects=False,
    )
    expected_return_to = f"/loops/new/manual?{urlencode({'workdir': str(target.resolve())})}#bundle-import-form"
    encoded_return = urlencode(
        {
            "workdir": str(target.resolve()),
            "support_target_feedback": "target_ready",
            "return_to": expected_return_to,
        }
    )
    assert return_redirect.status_code == 303
    assert return_redirect.headers["location"] == f"/support?{encoded_return}"
    assert "secret-token" not in return_redirect.headers["location"]

    return_support = client.get(return_redirect.headers["location"])
    _assert_ok(return_support)
    assert f'href="{expected_return_to}" data-testid="support-return-link"' in return_support.text
    assert 'action="/support?' in return_support.text
    assert "return_to=" in return_support.text
    assert "secret-token" not in return_support.text

    missing_target = tmp_path / "missing support target"
    missing_redirect = client.post("/support", data={"workdir": str(missing_target)}, follow_redirects=False)
    missing_query = urlencode(
        {"workdir": str(missing_target.resolve(strict=False)), "support_target_feedback": "target_report_only"}
    )
    assert missing_redirect.status_code == 303
    assert missing_redirect.headers["location"] == f"/support?{missing_query}"
    assert load_recent_workdirs()[:1] == [str(target.resolve())]

    missing_support = client.get(missing_redirect.headers["location"])
    _assert_ok(missing_support)
    assert 'data-support-target-project-status="missing"' in missing_support.text
    assert 'data-support-target-project-report-only="true"' in missing_support.text
    assert 'data-support-target-feedback="target_report_only"' in missing_support.text
    assert "Copy Public Issue Bundle" in missing_support.text
    assert "was not saved to recent targets" in missing_support.text

    _assert_support_target_bad_inputs_clear_stale_context(client, target)


def _assert_support_target_bad_inputs_clear_stale_context(client: TestClient, target: Path) -> None:
    scoped_support_path = f"/support?workdir={quote(str(target.resolve()), safe='')}"
    required_redirect = client.post("/support", data={"workdir": " "}, follow_redirects=False)
    assert required_redirect.status_code == 303
    assert required_redirect.headers["location"] == (
        "/support?support_target_feedback=target_required#support-target-form"
    )
    required_scoped_redirect = client.post(
        scoped_support_path,
        data={"workdir": " "},
        follow_redirects=False,
    )
    assert required_scoped_redirect.status_code == 303
    assert required_scoped_redirect.headers["location"] == (
        "/support?support_target_feedback=target_required#support-target-form"
    )
    required_support = client.get("/support?support_target_feedback=target_required")
    _assert_ok(required_support)
    assert 'data-support-target-feedback="target_required"' in required_support.text
    assert "Enter a target project path first." in required_support.text

    unavailable_redirect = client.post("/support", data={"workdir": "bad\0target"}, follow_redirects=False)
    assert unavailable_redirect.status_code == 303
    assert unavailable_redirect.headers["location"] == (
        "/support?support_target_feedback=target_unavailable#support-target-form"
    )
    unavailable_scoped_redirect = client.post(
        scoped_support_path,
        data={"workdir": "bad\0target"},
        follow_redirects=False,
    )
    assert unavailable_scoped_redirect.status_code == 303
    assert unavailable_scoped_redirect.headers["location"] == (
        "/support?support_target_feedback=target_unavailable#support-target-form"
    )
    unavailable_support = client.get("/support?support_target_feedback=target_unavailable")
    _assert_ok(unavailable_support)
    assert 'data-support-target-feedback="target_unavailable"' in unavailable_support.text
    assert "The target project path could not be inspected" in unavailable_support.text
    assert "bad" not in unavailable_support.text

    relative_redirect = client.post(scoped_support_path, data={"workdir": "relative-target"}, follow_redirects=False)
    assert relative_redirect.status_code == 303
    assert relative_redirect.headers["location"] == (
        "/support?support_target_feedback=target_unavailable#support-target-form"
    )
    assert str(target.parent / "relative-target") not in relative_redirect.headers["location"]

    relative_support = client.get("/support?workdir=relative-target")
    _assert_ok(relative_support)
    assert 'data-support-target-feedback="target_unavailable"' in relative_support.text
    assert 'data-testid="global-workdir-context" hidden' in relative_support.text
    assert 'value="relative-target"' not in relative_support.text
    assert "workdir=relative-target" not in relative_support.text


def test_legacy_runs_redirect_keeps_workdir_context(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    redirect = client.get("/runs?workdir=/tmp/demo&token=secret-token", follow_redirects=False)

    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/?workdir=%2Ftmp%2Fdemo#activity"
    assert "secret-token" not in redirect.headers["location"]


def test_expert_form_errors_keep_workdir_context(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    loop_error = client.post(
        "/loops/new/manual?workdir=/tmp/demo",
        data={
            "name": "",
            "workdir": "/tmp/demo",
            "spec_path": "",
        },
    )
    bundle_import_error = client.post(
        "/loops/new/manual/import-bundle?workdir=/tmp/demo",
        data={"bundle_path": "", "bundle_yaml": ""},
    )
    derive_error = client.post("/bundles/derive?workdir=/tmp/demo", data={"loop_id": ""})

    for response in (loop_error, bundle_import_error, derive_error):
        _assert_ok(response)
        assert 'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="nav-compose-link"' in response.text
        assert 'href="/same-agent?workdir=%2Ftmp%2Fdemo" data-testid="nav-tools-link"' in response.text

    assert 'action="/loops/new/manual?workdir=%2Ftmp%2Fdemo"' in loop_error.text
    assert 'href="/roles?workdir=%2Ftmp%2Fdemo&amp;return_to=' in loop_error.text
    assert 'action="/loops/new/manual/import-bundle?workdir=%2Ftmp%2Fdemo"' in bundle_import_error.text
    assert 'data-testid="bundle-derive-empty-state"' in derive_error.text
    assert 'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="bundle-derive-create-loop-link"' in derive_error.text


def test_start_navigation_recovers_workdir_from_alignment_session(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Shape this project task into a Loop.",
        start_immediately=False,
    )
    client = TestClient(build_app(service=service))

    session_page = client.get(f"/loops/new/bundle?alignment_session_id={session['id']}")
    stale_session_page = client.get("/loops/new/bundle?alignment_session_id=missing-session")

    _assert_ok(session_page)
    _assert_ok(stale_session_page)
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    assert f'href="/same-agent?workdir={encoded_workdir}" data-testid="nav-tools-link"' in session_page.text
    assert f'href="/loops/new?workdir={encoded_workdir}" data-testid="nav-compose-link"' in session_page.text
    assert f'href="/loops/new/bundle?alignment_workdir={encoded_workdir}"' in session_page.text
    assert f'href="/loops/new/manual?workdir={encoded_workdir}#bundle-import-form"' in session_page.text
    assert f'data-compose-import-href="/loops/new/manual?workdir={encoded_workdir}#bundle-import-form"' in session_page.text
    assert 'href="/same-agent" data-testid="nav-tools-link"' in stale_session_page.text
    assert 'href="/loops/new/bundle"' in stale_session_page.text


def test_start_navigation_recovers_workdir_from_detail_entities(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Entity Context Loop")
    run = service.rerun(loop["id"])
    bundle = _import_web_bundle(service, sample_spec_file, sample_workdir)
    client = TestClient(build_app(service=service))

    loop_page = client.get(f"/loops/{loop['id']}")
    run_page = client.get(f"/runs/{run['id']}")
    bundle_page = client.get(f"/bundles/{bundle['id']}")

    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    for page in (loop_page, run_page, bundle_page):
        _assert_ok(page)
        assert f'href="/?workdir={encoded_workdir}" data-testid="nav-loops-link"' in page.text
        assert f'href="/loops/new?workdir={encoded_workdir}" data-testid="nav-compose-link"' in page.text
        assert f'href="/bundles?workdir={encoded_workdir}"' in page.text
        assert f'href="/same-agent?workdir={encoded_workdir}" data-testid="nav-tools-link"' in page.text
    assert f'href="/fit-guide?workdir={encoded_workdir}" data-testid="nav-tutorial-link"' in page.text


def test_asset_catalog_links_preserve_composer_return_context(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    composer_return_to = "/loops/new/manual?workdir=/tmp/demo#manual-loop-form"
    encoded_return_to = quote(composer_return_to, safe="")
    builtin_role = next(item for item in service.list_role_definitions() if item.get("source") == "builtin")
    builtin_orchestration = next(item for item in service.list_orchestrations() if item.get("source") == "builtin")

    roles = client.get(f"/roles?workdir=/tmp/demo&return_to={encoded_return_to}")
    orchestrations = client.get(f"/orchestrations?workdir=/tmp/demo&return_to={encoded_return_to}")
    role_editor = client.get(f"/roles/{builtin_role['id']}/edit?workdir=/tmp/demo&return_to={encoded_return_to}")
    orchestration_editor = client.get(
        f"/orchestrations/{builtin_orchestration['id']}/edit?workdir=/tmp/demo&return_to={encoded_return_to}"
    )
    returned_composer = client.get("/loops/new/manual?workdir=/tmp/demo&surface_updated=role%3Astale#manual-loop-form")

    _assert_ok(roles)
    _assert_ok(orchestrations)
    _assert_ok(role_editor)
    _assert_ok(orchestration_editor)
    _assert_ok(returned_composer)
    assert 'href="/roles/new?workdir=%2Ftmp%2Fdemo&amp;return_to=' in roles.text
    assert 'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="role-definitions-empty-compose-link" data-workdir-context-link="workdir"' in roles.text
    assert 'data-open-card="/roles/' in roles.text
    assert 'data-testid="role-definitions-empty-create-link"' in roles.text
    assert 'data-testid="role-definitions-empty-template-link"' in roles.text
    assert '&amp;return_to=%2Floops%2Fnew%2Fmanual%3Fworkdir%3D%252Ftmp%252Fdemo%23manual-loop-form' in roles.text
    assert 'href="/orchestrations/new?workdir=%2Ftmp%2Fdemo&amp;return_to=' in orchestrations.text
    assert 'href="/loops/new?workdir=%2Ftmp%2Fdemo" data-testid="orchestrations-empty-compose-link" data-workdir-context-link="workdir"' in orchestrations.text
    assert 'data-open-card="/orchestrations/' in orchestrations.text
    assert 'data-testid="orchestrations-empty-create-link"' in orchestrations.text
    assert 'data-testid="orchestrations-empty-template-link"' in orchestrations.text
    assert '&amp;return_to=%2Floops%2Fnew%2Fmanual%3Fworkdir%3D%252Ftmp%252Fdemo%23manual-loop-form' in orchestrations.text
    assert 'action="/roles/new?workdir=%2Ftmp%2Fdemo&amp;return_to=' in role_editor.text
    assert 'href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#manual-loop-form"' in role_editor.text
    assert 'href="/roles?workdir=%2Ftmp%2Fdemo&amp;return_to=' in orchestration_editor.text
    assert 'href="/loops/new/manual?workdir=%2Ftmp%2Fdemo#manual-loop-form"' in orchestration_editor.text
    assert 'href="/orchestrations/new?workflow_preset=' in orchestration_editor.text
    assert '&amp;workdir=%2Ftmp%2Fdemo&amp;return_to=' in orchestration_editor.text
    assert "surface_updated" not in returned_composer.text
    assert (
        'href="/roles?workdir=%2Ftmp%2Fdemo&amp;return_to=%2Floops%2Fnew%2Fmanual%3Fworkdir%3D%252Ftmp%252Fdemo%23manual-loop-form"'
        in returned_composer.text
    )
    assert (
        'href="/orchestrations?workdir=%2Ftmp%2Fdemo&amp;return_to=%2Floops%2Fnew%2Fmanual%3Fworkdir%3D%252Ftmp%252Fdemo%23manual-loop-form"'
        in returned_composer.text
    )
