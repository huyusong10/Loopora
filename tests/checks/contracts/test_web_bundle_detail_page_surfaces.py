from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import shutil
from urllib.parse import parse_qs, quote, urlsplit

from fastapi.testclient import TestClient

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.bundles import bundle_to_yaml
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service import LooporaError
from loopora.settings import app_home
from loopora.web import build_app
from loopora.web_bundle_import_form_routes import CREATE_LOOP_IMPORT_START_PREVIEW_REQUIRED

from web_bundle_detail_test_support import create_bundle_detail_loop, import_agent_first_bundle, import_derived_bundle


def test_bundle_detail_stays_open_when_managed_spec_is_unreadable(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Broken Spec Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Broken Spec Bundle",
        description="The managed spec file can be repaired from the detail page.",
        collaboration_summary="Keep the plan detail page usable.",
    )
    (app_home() / "bundles" / imported["id"] / "spec.md").write_bytes(b"\xff")

    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in response.text
    assert 'data-testid="bundle-detail-form"' in response.text
    assert "bundle spec file could not be read" in response.text
    assert "bundle spec file could not be read:" not in response.text
    assert '<textarea name="spec_markdown" rows="18"># Task' in response.text
    assert "Ship the requested behavior." in response.text


def test_bundle_detail_explains_missing_managed_spec_without_hiding_editor(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Missing Spec Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Missing Spec Bundle",
        description="The managed spec file can be recreated from the detail page.",
        collaboration_summary="Keep the plan detail page usable.",
    )
    spec_path = app_home() / "bundles" / imported["id"] / "spec.md"
    spec_path.unlink()

    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in response.text
    assert 'data-testid="bundle-detail-form"' in response.text
    assert "bundle spec file does not exist" in response.text
    assert '<textarea name="spec_markdown" rows="18"># Task' in response.text
    assert "Ship the requested behavior." in response.text
    assert str(spec_path) not in response.text


def test_bundles_page_makes_replace_import_context_explicit(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Replace Intent Source",
    )
    bundle = import_derived_bundle(
        service,
        loop["id"],
        name="Replace Intent Bundle",
        description="Replacement should be explicit before commit.",
        collaboration_summary="Keep plan-file replacement unambiguous.",
    )
    response = TestClient(build_app(service=service)).get(f"/bundles?replace_bundle_id={bundle['id']}")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-import-form"' in response.text
    assert 'data-import-intent="replace"' in response.text
    assert 'data-testid="bundle-replace-target-note"' in response.text
    assert f"<code>{bundle['id']}</code>" in response.text
    assert 'name="import_intent" value="replace"' in response.text
    assert f'type="hidden" id="bundle-import-replace-id" name="replace_bundle_id" value="{bundle["id"]}"' in response.text
    assert "Replace plan id" not in response.text
    assert "Preview Replacement" in response.text
    assert "Replace Plan File" in response.text
    assert "Replace With Preview" in response.text
    assert "Import Preview" not in response.text


def test_bundle_api_and_detail_hide_legacy_lineage_surfaces(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Lineage Source",
    )
    source = import_derived_bundle(
        service,
        loop["id"],
        name="Lineage Source Bundle",
        description="Original lineage source.",
        collaboration_summary="Original governance posture.",
    )
    legacy_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="Lineage Revision Bundle",
            description="Revision source should remain hidden.",
            collaboration_summary="Updated governance posture.",
        )
    ).replace(
        "metadata:\n  name: Lineage Revision Bundle\n  description: Revision source should remain hidden.",
        "metadata:\n"
        "  name: Lineage Revision Bundle\n"
        "  description: Revision source should remain hidden.\n"
        f"  source_bundle_id: {source['id']}\n"
        f"  revision: {source['revision'] + 1}",
    )
    imported = service.import_bundle_text(legacy_yaml)
    client = TestClient(build_app(service=service))

    api_response = client.get(f"/api/bundles/{imported['id']}")
    list_response = client.get("/bundles")
    page_response = client.get(f"/bundles/{imported['id']}")

    assert api_response.status_code == HTTPStatus.OK
    assert "revision_summary" not in api_response.json()
    assert api_response.json()["source_bundle_id"] == ""
    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-revision-lineage"' not in page_response.text
    assert "Plan version" not in page_response.text
    assert 'data-testid="bundle-surface-diff"' not in page_response.text
    assert f'value="{source["id"]}"' not in page_response.text
    assert 'data-testid="bundle-revision-delta-summary"' not in page_response.text
    assert list_response.status_code == HTTPStatus.OK
    assert f'data-testid="bundle-exchange-item-{imported["id"]}"' in list_response.text
    assert 'data-testid="bundle-governance-failure"' not in list_response.text
    assert 'data-testid="bundle-governance-evidence"' not in list_response.text
    assert 'data-testid="bundle-governance-coverage"' not in list_response.text
    assert 'data-testid="bundle-governance-residual-risk"' not in list_response.text
    assert 'data-testid="bundle-governance-execution-strategy"' not in list_response.text
    assert 'data-testid="bundle-governance-local"' not in list_response.text
    assert 'data-testid="bundle-governance-workflow"' not in list_response.text
    assert 'data-testid="bundle-governance-gatekeeper"' not in list_response.text
    assert 'data-testid="bundle-governance-changed-surfaces"' not in list_response.text


def test_bundle_detail_replace_yaml_link_preserves_source_workdir(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Replace Context Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Replace Context Bundle",
        description="Replace YAML should keep the source workdir.",
        collaboration_summary="Keep replace/import context grounded in the same project.",
    )
    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}")

    assert response.status_code == HTTPStatus.OK
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    assert (
        f'href="/bundles?replace_bundle_id={imported["id"]}&amp;workdir={encoded_workdir}#bundle-import-panel"'
        ' data-testid="bundle-replace-yaml-link" data-workdir-context-link="workdir"' in response.text
    )


def test_bundle_detail_empty_judgment_projection_offers_repair_paths(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Projection Repair Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Projection Repair Bundle",
        description="Empty judgment projection should remain repairable.",
        collaboration_summary="Keep projection repair local to the plan file.",
    )
    monkeypatch.setattr(
        service,
        "_bundle_control_summary",
        lambda _bundle: {
            "traceability": {"items": [], "mapped_count": 0, "required_count": 0},
            "diagnostics": [],
        },
    )

    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}")

    assert response.status_code == HTTPStatus.OK
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    assert 'data-testid="bundle-review-surface"' in response.text
    assert 'data-testid="bundle-judgment-grid"' in response.text
    assert 'data-testid="bundle-traceability-empty"' in response.text
    assert 'href="#bundle-detail-form" data-testid="bundle-traceability-empty-edit-link"' in response.text
    assert (
        f'href="/bundles?replace_bundle_id={imported["id"]}&amp;workdir={encoded_workdir}#bundle-import-panel" '
        'data-testid="bundle-traceability-empty-replace-link" data-workdir-context-link="workdir"' in response.text
    )
    assert f'action="/bundles/{imported["id"]}/revise?workdir={encoded_workdir}"' in response.text
    assert 'data-testid="bundle-traceability-empty-improve-button"' in response.text
    assert 'id="bundle-detail-form"' in response.text
    assert 'data-workdir-context-form="workdir"' in response.text


def test_network_mode_bundle_detail_managed_source_path_is_copy_only(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Remote Source Path",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Remote Source Path Bundle",
        description="Remote users should copy the server-side source folder.",
        collaboration_summary="Keep plan source inspection usable over network Web.",
    )
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get(f"/bundles/{imported['id']}", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-reveal-dir-button"' in response.text
    assert 'data-path-action-mode="copy"' in response.text
    button = response.text.split('data-testid="bundle-reveal-dir-button"', 1)[1].split("</button>", 1)[0]
    assert 'aria-disabled="true"' not in button
    assert "Copy plan folder path" in button


def test_bundle_detail_reviews_judgment_before_run_and_defers_source_management(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Decision First Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Decision First Plan",
        description="Review the frozen judgment before starting another Run.",
        collaboration_summary="Keep success, fake done, evidence, and closure ahead of source management.",
    )

    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}")

    assert response.status_code == HTTPStatus.OK
    assert all(
        marker in response.text
        for marker in (
            'data-testid="bundle-review-surface"',
            'data-testid="bundle-review-tabs"',
            'data-testid="bundle-review-judgment-panel"',
            'data-testid="bundle-review-workflow-panel"',
            'data-testid="bundle-review-contract-panel"',
            'data-testid="bundle-run-decision" data-launch-mode="web"',
            'data-testid="bundle-plan-management"',
        )
    )
    assert all(
        f'data-review-field="{field}"' in response.text
        for field in ("success", "fake_done", "evidence", "strategy", "closure", "tradeoffs")
    )
    tabs_tag = response.text.split('data-testid="bundle-review-tabs"', 1)[1].split(">", 1)[0]
    assert "hidden" in tabs_tag
    for panel_testid in (
        "bundle-review-judgment-panel",
        "bundle-review-workflow-panel",
        "bundle-review-contract-panel",
    ):
        panel_tag = response.text.split(f'data-testid="{panel_testid}"', 1)[1].split(">", 1)[0]
        assert "hidden" not in panel_tag
    hero = response.text.split('<section class="hero hero-tight bundle-detail-hero">', 1)[1].split(
        "</section>",
        1,
    )[0]
    assert "bundle-start-run-button" not in hero
    assert "bundle-export-yaml-link" not in hero
    assert "data-delete-bundle" not in hero
    review_index = response.text.index('data-testid="bundle-review-surface"')
    decision_index = response.text.index('data-testid="bundle-run-decision"')
    management_index = response.text.index('data-testid="bundle-plan-management"')
    assert review_index < decision_index < management_index
    start_button_tag = response.text.split('data-testid="bundle-start-run-button"', 1)[0].rsplit("<button", 1)[1]
    improve_button_tag = response.text.split('data-testid="bundle-improve-chat-button"', 1)[0].rsplit("<button", 1)[1]
    assert 'class="primary-button"' in start_button_tag
    assert 'class="secondary-button"' in improve_button_tag
    management_tag = response.text.split('data-testid="bundle-plan-management"', 1)[0].rsplit("<details", 1)[1]
    assert " open" not in management_tag


def test_bundle_detail_can_start_managed_loop_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Runnable Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Runnable Plan Detail",
        description="Plan files should continue into the main run workflow.",
        collaboration_summary="Run the managed copy directly from its plan page.",
    )
    client = TestClient(build_app(service=service))

    page_response = client.get(f"/bundles/{imported['id']}")
    run_response = client.post(f"/bundles/{imported['id']}/runs", follow_redirects=False)

    assert page_response.status_code == HTTPStatus.OK
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    assert f'action="/bundles/{imported["id"]}/runs?workdir={encoded_workdir}"' in page_response.text
    assert 'data-testid="bundle-start-run-form"' in page_response.text
    assert 'data-workdir-context-form="workdir"' in page_response.text
    assert 'data-testid="bundle-start-run-button"' in page_response.text
    assert (
        f'href="/bundles/{imported["id"]}/export?workdir={encoded_workdir}" data-testid="bundle-export-yaml-link" data-workdir-context-link="workdir"'
        in page_response.text
    )
    assert page_response.text.count(f'href="/bundles/{imported["id"]}/export?workdir={encoded_workdir}"') == 2
    assert run_response.status_code == HTTPStatus.SEE_OTHER
    redirect_parts = urlsplit(run_response.headers["location"])
    assert redirect_parts.path.startswith("/runs/")
    assert parse_qs(redirect_parts.query)["workdir"] == [str(sample_workdir)]
    run_id = redirect_parts.path.rsplit("/", 1)[-1]
    assert service.get_run(run_id)["loop_id"] == imported["loop_id"]


def test_bundle_detail_start_run_error_stays_on_plan_page(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Run Failure Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Run Failure Plan Detail",
        description="Run failure should stay visible on the plan page.",
        collaboration_summary="Keep recovery local to the plan file.",
    )

    def fail_start(*_args, **_kwargs):
        raise LooporaError("run slots are unavailable")

    monkeypatch.setattr(service, "start_run", fail_start)
    response = TestClient(build_app(service=service)).post(f"/bundles/{imported['id']}/runs")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in response.text
    assert 'data-testid="bundle-action-error"' in response.text
    assert "run slots are unavailable" in response.text


def test_bundle_detail_start_run_preserves_workdir_recovery_actions(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    project_workdir = tmp_path / "project"
    project_workdir.mkdir()
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=project_workdir,
        name="Bundle Missing Workdir Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Missing Workdir Plan Detail",
        description="Run recovery should stay visible on the plan page.",
        collaboration_summary="Keep workdir repair local to the plan file.",
    )
    shutil.rmtree(project_workdir)

    response = TestClient(build_app(service=service)).post(f"/bundles/{imported['id']}/runs")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in response.text
    assert 'data-testid="bundle-action-error"' in response.text
    assert 'data-testid="bundle-action-recovery"' in response.text
    assert 'data-recovery-action-kind="create_workdir"' in response.text
    assert 'data-recovery-action-kind="confirm_readiness"' in response.text
    assert 'data-recovery-action-kind="retry_web_run_start"' in response.text
    assert "data-recovery-action-form" in response.text
    assert 'form="bundle-start-run-form-fields"' in response.text
    assert f'formaction="/bundles/{imported["id"]}/runs' in response.text
    assert 'formmethod="post"' in response.text
    assert "mkdir -p" in response.text
    assert "loopora doctor --workdir" in response.text
    assert "workdir does not exist:" not in response.text
    assert service.get_loop(imported["loop_id"])["runs"] == []


def test_create_loop_page_import_redirects_to_failed_run_when_worker_cannot_start(
    monkeypatch,
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    private_path = tmp_path / "private" / "thread-start"
    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: _failing_run_thread(private_path))
    client = TestClient(build_app(service=service))
    bundle_yaml = _bundle_yaml(sample_workdir)
    preview = client.post("/api/bundles/preview", json={"bundle_yaml": bundle_yaml}).json()
    assert str(preview["preview_review_token"]).startswith("v1.")

    response = client.post(
        "/loops/new/import-bundle",
        data={
            "bundle_yaml": bundle_yaml,
            "bundle_preview_reviewed": preview["preview_review_token"],
            "start_immediately": "1",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    run_id = _assert_failed_run_redirect(response.headers["location"], service, private_path)
    assert service.get_run(run_id)["error_message"] == BACKGROUND_WORKER_START_ERROR
    assert service.list_bundles()


def test_create_loop_page_import_requires_preview_before_starting_immediately(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    for preview_token in ("", "1"):
        response = client.post(
            "/loops/new/import-bundle",
            data={
                "bundle_yaml": _bundle_yaml(sample_workdir),
                "bundle_preview_reviewed": preview_token,
                "start_immediately": "1",
            },
        )

        assert response.status_code == HTTPStatus.OK
        assert CREATE_LOOP_IMPORT_START_PREVIEW_REQUIRED in response.text
        assert 'data-testid="bundle-preview-reviewed"' in response.text
        assert 'data-testid="bundle-import-start-review-note"' in response.text
        assert service.list_bundles() == []
        assert service.list_loops() == []


def test_create_loop_page_import_rejects_preview_token_for_different_plan_file(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    reviewed_yaml = _bundle_yaml(sample_workdir)
    changed_yaml = reviewed_yaml.replace(
        "Ship the requested behavior without creating brittle structure.",
        "Ship a changed Plan File after preview.",
    )
    assert changed_yaml != reviewed_yaml
    preview = client.post("/api/bundles/preview", json={"bundle_yaml": reviewed_yaml}).json()

    response = client.post(
        "/loops/new/import-bundle",
        data={
            "bundle_yaml": changed_yaml,
            "bundle_preview_reviewed": preview["preview_review_token"],
            "start_immediately": "1",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert CREATE_LOOP_IMPORT_START_PREVIEW_REQUIRED in response.text
    assert service.list_bundles() == []
    assert service.list_loops() == []


def test_bundle_detail_redirects_to_failed_run_when_worker_cannot_start(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Dispatch Failure Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Dispatch Failure Plan Detail",
        description="Worker dispatch failures should land on the failed run.",
        collaboration_summary="Once a Run exists, show the Run state.",
    )
    private_path = tmp_path / "private" / "thread-start"
    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: _failing_run_thread(private_path))
    client = TestClient(build_app(service=service))

    response = client.post(f"/bundles/{imported['id']}/runs", follow_redirects=False)

    assert response.status_code == HTTPStatus.SEE_OTHER
    _assert_failed_run_redirect(
        response.headers["location"],
        service,
        private_path,
        expected_workdir=sample_workdir,
    )
    page_response = client.get(response.headers["location"])
    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="run-action-error"' in page_response.text
    encoded = response.headers["location"] + page_response.text
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded


def test_bundle_detail_start_run_explains_missing_saved_workdir(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Missing Workdir Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Missing Workdir Plan Detail",
        description="Missing workdir should stay recoverable from the plan page.",
        collaboration_summary="Do not recreate the target project when starting a saved Loop.",
    )
    shutil.rmtree(sample_workdir)

    response = TestClient(build_app(service=service)).post(f"/bundles/{imported['id']}/runs")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in response.text
    assert 'data-testid="bundle-action-error"' in response.text
    assert "Target project directory does not exist yet" in response.text
    assert "workdir does not exist:" not in response.text
    assert not sample_workdir.exists()
    assert service.get_loop(imported["loop_id"])["runs"] == []


def test_bundle_detail_routes_agent_first_plan_to_agent_run_guide(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = import_agent_first_bundle(service, tmp_path=tmp_path, sample_workdir=sample_workdir)
    bundle = imported["bundle"]
    client = TestClient(build_app(service=service))

    page_response = client.get(f"/bundles/{bundle['id']}")
    run_response = client.post(f"/bundles/{bundle['id']}/runs")

    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-open-agent-run-guide"' in page_response.text
    assert 'data-testid="bundle-run-decision" data-launch-mode="same_agent"' in page_response.text
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    assert (
        f'href="/loops/{bundle["loop_id"]}?workdir={encoded_workdir}" '
        f'data-testid="bundle-open-agent-run-guide" data-workdir-context-link="workdir"' in page_response.text
    )
    assert "Open same-Agent run guide" in page_response.text
    assert "Open Agent run guide" not in page_response.text
    assert 'data-testid="bundle-start-run-form"' not in page_response.text
    assert 'data-testid="bundle-start-run-button"' not in page_response.text
    assert run_response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in run_response.text
    assert 'data-testid="bundle-action-error"' in run_response.text
    assert "Agent-native Plan File runs must be started or continued with /loopora-run" in run_response.text
    assert "same host Agent" in run_response.text


def test_bundles_list_exposes_run_action_for_managed_plan_files(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="List Run Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="List Runnable Plan",
        description="Managed plan cards should continue into the run workflow.",
        collaboration_summary="Run from the plan list without opening expert details first.",
    )

    response = TestClient(build_app(service=service)).get("/bundles")

    assert response.status_code == HTTPStatus.OK
    assert f'action="/bundles/{imported["id"]}/runs?workdir={quote(str(sample_workdir.resolve()), safe="")}"' in response.text
    assert (
        f'href="/bundles/{imported["id"]}/export?workdir={quote(str(sample_workdir.resolve()), safe="")}" data-workdir-context-link="workdir"' in response.text
    )
    assert (
        f'href="/bundles/{imported["id"]}?workdir={quote(str(sample_workdir.resolve()), safe="")}" tabindex="-1" aria-hidden="true" data-workdir-context-link="workdir"'
        in response.text
    )
    assert all(
        fragment in response.text
        for fragment in (f'data-testid="bundle-list-start-run-form-{imported["id"]}"', f'data-testid="bundle-list-start-run-button-{imported["id"]}"')
    )


def test_bundles_list_routes_agent_first_plan_files_to_agent_run_guide(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = import_agent_first_bundle(service, tmp_path=tmp_path, sample_workdir=sample_workdir)
    bundle = imported["bundle"]

    response = TestClient(build_app(service=service)).get("/bundles")

    assert response.status_code == HTTPStatus.OK
    assert f'data-testid="bundle-list-open-agent-run-guide-{bundle["id"]}"' in response.text
    assert (
        f'href="/loops/{bundle["loop_id"]}?workdir={quote(str(sample_workdir.resolve()), safe="")}" data-testid="bundle-list-open-agent-run-guide-{bundle["id"]}"'
        in response.text
    )
    assert f'data-testid="bundle-list-start-run-form-{bundle["id"]}"' not in response.text
    assert f'data-testid="bundle-list-start-run-button-{bundle["id"]}"' not in response.text


def _assert_failed_run_redirect(
    location: str,
    service,
    private_path: Path,
    *,
    expected_workdir: Path | None = None,
) -> str:
    parts = urlsplit(location)
    assert parts.path.startswith("/runs/")
    assert parse_qs(parts.query)["run_action_error"] == [BACKGROUND_WORKER_START_ERROR]
    if expected_workdir is not None:
        assert parse_qs(parts.query)["workdir"] == [str(expected_workdir)]
    run_id = parts.path.removeprefix("/runs/")
    assert service.get_run(run_id)["status"] == "failed"
    assert "permission denied" not in location
    assert str(private_path) not in location
    return run_id


def _failing_run_thread(private_path: Path):
    class FailingRunThread:
        name = "run-start-failure"

        def start(self) -> None:
            raise OSError(f"permission denied: {private_path}")

    return FailingRunThread()
