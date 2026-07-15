from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.web import build_app


def _assert_page(response, *testids: str) -> None:
    assert response.status_code == 200, response.text[:500]
    for testid in testids:
        assert f'data-testid="{testid}"' in response.text


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


def _import_bundle(service, loop_id: str) -> dict:
    bundle = service.derive_bundle_from_loop(
        loop_id,
        name="Web Plan File",
        description="Plan file page smoke test.",
        collaboration_summary="Prefer evidence and visible proof.",
    )
    return service.import_bundle_text(bundle_to_yaml(bundle))


def test_current_web_surfaces_are_reachable(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.rerun(loop["id"])
    bundle = _import_bundle(service, loop["id"])
    client = TestClient(build_app(service=service))

    surfaces = {
        "/": ("top-nav", "home-workbench"),
        "/loops/new": ("loop-create-page", "loop-create-choice-page"),
        "/loops/new/bundle": ("loop-create-page", "alignment-start-form"),
        "/loops/new/manual": ("loop-create-page", "manual-compose-section", "loop-create-form"),
        "/tools": ("agent-adapters-panel", "agent-adapter-grid", "wake-lock-panel-section"),
        "/tutorial": ("tutorial-page", "tutorial-guide-panel", "tutorial-actions-panel"),
        "/roles": ("role-definitions-page", "builtin-role-templates-list"),
        "/orchestrations": ("orchestrations-page", "builtin-orchestrations-list"),
        "/bundles": ("bundles-page", "bundle-list"),
        f"/bundles/{bundle['id']}": ("bundle-detail-page", "bundle-spec-preview", "bundle-yaml-preview"),
        f"/loops/{loop['id']}": ("loop-detail-page", "loop-detail-history-panel"),
        f"/runs/{run['id']}": ("run-detail-page", "run-console-panel", "run-timeline-panel"),
    }

    for path, testids in surfaces.items():
        _assert_page(client.get(path), *testids)

    _assert_page(client.get("/runs"), "home-workbench")
    for retired_path in ("/same-agent", "/fit-guide", "/support"):
        assert client.get(retired_path).status_code == 404


def test_task_verdict_remains_primary_when_process_status_succeeds(
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

    _assert_page(home, "home-workbench")
    _assert_page(loop_page, "loop-detail-page", "loop-latest-verdict-pill")
    _assert_page(run_page, "run-detail-page", "run-task-verdict-card")
    combined = home.text + loop_page.text + run_page.text
    assert "Missing audit proof." in combined
    assert "All done according to the Agent summary." not in home.text + loop_page.text
