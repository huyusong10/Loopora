from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app

from web_api_test_support import _start_agent_first_loop


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
        summary_md="# Loopora Run Summary\n\nLifecycle closed; task evidence still belongs to the Agent-first lane.\n",
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
    assert 'data-agent-entry-command-copy' in page_response.text
    assert 'data-copy-value="' in page_response.text
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in page_response.text
    assert "loopora agent codex run" in page_response.text
    assert 'data-testid="run-rerun-button"' not in page_response.text

    rerun_response = client.post(f"/runs/{started['run']['id']}/rerun")

    assert rerun_response.status_code == HTTPStatus.CONFLICT
    rerun_payload = rerun_response.json()
    assert "agent-first Loop runs" in rerun_payload["error"]
    assert rerun_payload["agent_entry_start"]["next_loop_action"] == "start_next_run_for_unproven_verdict"
    assert rerun_payload["agent_entry_start"]["linked_task_verdict_status"] == "insufficient_evidence"
    assert len(service.get_loop(started["run"]["loop_id"])["runs"]) == 1
