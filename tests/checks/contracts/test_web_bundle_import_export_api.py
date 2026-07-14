from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import shutil
from urllib.parse import parse_qs, quote, urlsplit

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora import agent_adapter_command_prefix
from loopora.web import build_app

from bundle_lifecycle_test_support import _bundle_yaml
from web_api_test_support import (
    _assert_bundle_preview_control_summary,
    _assert_recovery_summary_actions,
    _assert_web_delete_preview_action_projection,
)


def _assert_redirect_workdir(redirect_url: str, *, path: str, workdir: Path) -> None:
    redirect_parts = urlsplit(redirect_url)
    assert redirect_parts.path == path
    assert parse_qs(redirect_parts.query).get("workdir") == [str(workdir.resolve())]


def test_api_bundles_import_export_and_delete(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Export Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    bundle_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="Imported Bundle",
            description="Bundle import from API.",
            collaboration_summary="Prefer evidence before declaring done.",
        )
    )

    client = TestClient(build_app(service=service))
    preview_response = client.post("/api/bundles/preview", json={"bundle_yaml": bundle_yaml})
    assert preview_response.status_code == HTTPStatus.OK
    preview = preview_response.json()
    assert preview["ok"] is True
    assert preview["metadata"]["name"] == "Imported Bundle"
    assert str(preview["preview_review_token"]).startswith("v1.")
    assert preview["bundle"]["loop"]["workdir"] == str(sample_workdir.resolve())
    assert preview["roles"]
    assert preview["workflow_preview"]["steps"]
    assert preview["spec_rendered_html"].strip()
    _assert_bundle_preview_control_summary(preview)

    import_response = client.post("/api/bundles/import", json={"bundle_yaml": bundle_yaml})

    assert import_response.status_code == HTTPStatus.CREATED
    import_payload = import_response.json()
    bundle = import_payload["bundle"]
    assert bundle["name"] == "Imported Bundle"
    assert bundle["collaboration_summary"] == "Prefer evidence before declaring done."
    _assert_redirect_workdir(import_payload["redirect_url"], path=f"/bundles/{bundle['id']}", workdir=sample_workdir)

    list_response = client.get("/api/bundles")
    assert list_response.status_code == HTTPStatus.OK
    listed_bundle = next(item for item in list_response.json() if item["id"] == bundle["id"])
    assert listed_bundle["loop_id"]
    assert "governance_summary" not in listed_bundle

    get_response = client.get(f"/api/bundles/{bundle['id']}")
    assert get_response.status_code == HTTPStatus.OK
    assert get_response.json()["id"] == bundle["id"]

    export_response = client.get(f"/api/bundles/{bundle['id']}/export")
    assert export_response.status_code == HTTPStatus.OK
    assert "Imported Bundle" in export_response.text
    assert "Prefer evidence before declaring done." in export_response.text
    assert export_response.headers["content-type"].startswith("application/yaml")

    delete_preview_response = client.get(f"/api/bundles/{bundle['id']}/delete-preview")
    assert delete_preview_response.status_code == HTTPStatus.OK
    delete_preview = delete_preview_response.json()
    assert delete_preview["delete_allowed"] is True
    assert delete_preview["would_delete"]["bundle"] == bundle["id"]
    assert delete_preview["would_delete"]["linked_loop"] == bundle["loop_id"]
    assert delete_preview["does_not_delete"] == [
        "original_exported_yaml_file",
        "source_project_workdir",
        "non_bundle_owned_assets",
        "external_provider_history",
    ]
    _assert_web_delete_preview_action_projection(
        delete_preview,
        expected_kind="delete_bundle",
        expected_endpoint=f"/api/bundles/{quote(bundle['id'], safe='')}",
    )

    delete_response = client.delete(f"/api/bundles/{bundle['id']}")
    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()["deleted"] is True

    missing_response = client.get(f"/api/bundles/{bundle['id']}")
    assert missing_response.status_code == HTTPStatus.NOT_FOUND
    assert "unknown bundle" in missing_response.json()["error"]


def test_browser_bundle_export_route_downloads_yaml(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Browser Bundle Export Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Browser Export Download Plan",
                description="Keep browser export links on browser routes.",
                collaboration_summary="Download YAML without leaving the Web surface.",
            )
        )
    )

    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}/export")

    assert response.status_code == HTTPStatus.OK
    assert "Browser Export Download Plan" in response.text
    assert "Download YAML without leaving the Web surface." in response.text
    assert response.headers["content-type"].startswith("application/yaml")


def test_bundle_library_filtered_empty_state_can_clear_target_context(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Filtered Library Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Filtered Library Plan",
                description="Visible when the target filter is cleared.",
                collaboration_summary="Do not make filtered assets look missing.",
            )
        )
    )
    other_workdir = tmp_path / "other-target"
    other_workdir.mkdir()
    encoded_other_workdir = quote(str(other_workdir.resolve()), safe="")
    client = TestClient(build_app(service=service))

    filtered_response = client.get(f"/bundles?workdir={encoded_other_workdir}")
    unfiltered_response = client.get("/bundles")

    assert filtered_response.status_code == HTTPStatus.OK
    assert unfiltered_response.status_code == HTTPStatus.OK
    assert f'data-testid="bundle-exchange-item-{imported["id"]}"' not in filtered_response.text
    assert f'data-testid="bundle-exchange-item-{imported["id"]}"' in unfiltered_response.text
    assert 'data-testid="bundles-empty-show-all-link"' in filtered_response.text
    assert 'data-testid="bundle-derive-show-all-link"' in filtered_response.text
    assert 'href="/bundles" data-testid="bundles-empty-show-all-link"' in filtered_response.text
    assert 'href="/bundles" data-testid="bundle-derive-show-all-link"' in filtered_response.text
    assert f'href="/loops/new?workdir={encoded_other_workdir}" data-testid="bundle-derive-create-loop-link"' in filtered_response.text
    assert 'data-testid="global-workdir-context"' in filtered_response.text


def test_api_bundle_export_generation_failure_returns_structured_recovery(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="API Export Failure Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="API Export Failure Plan",
                description="Keep API recovery structured.",
                collaboration_summary="Do not leak local paths on generation failure.",
            )
        )
    )
    local_path = tmp_path / "private" / "bundle-export.yml"

    def fail_export_bundle(bundle_id: str) -> dict:
        assert bundle_id == imported["id"]
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "export_bundle", fail_export_bundle)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.get(f"/api/bundles/{imported['id']}/export")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    expected_actions = ["review_plan_file", "retry_plan_file_export", "open_plan_file_library"]
    expected_ready_after = {"retry_plan_file_export": "review_plan_file"}
    assert payload["ok"] is False
    assert payload["error"] == "plan file could not be generated"
    assert payload["resource_recovery"] == "plan_file_export_generation_failed"
    assert payload["status"] == "blocked_by_plan_file_generation"
    assert payload["surface"] == "web_bundle_export"
    assert payload["resource"] == "Plan File"
    assert payload["action"] == "export"
    assert payload["bundle_id"] == imported["id"]
    assert [item["kind"] for item in payload["next_actions"]] == expected_actions
    _assert_redirect_workdir(
        payload["next_actions"][0]["redirect_url"],
        path=f"/bundles/{quote(imported['id'], safe='')}",
        workdir=sample_workdir,
    )
    assert payload["next_actions"][1]["endpoint"] == f"/api/bundles/{quote(imported['id'], safe='')}/export"
    assert payload["next_actions"][1]["after_action"] == "review_plan_file"
    _assert_redirect_workdir(payload["next_actions"][2]["redirect_url"], path="/bundles", workdir=sample_workdir)
    assert payload["next_action_kinds"] == expected_actions
    assert payload["next_action_ready_now_kinds"] == ["review_plan_file", "open_plan_file_library"]
    assert payload["next_action_ready_after_actions"] == expected_ready_after
    assert payload["web_bundle_export_recovery_summary"]["next_action_kinds"] == expected_actions
    assert payload["web_bundle_export_recovery_summary"]["next_action_ready_after_actions"] == expected_ready_after
    assert "permission denied" not in response.text
    assert str(local_path) not in response.text


def test_browser_bundle_export_failure_returns_html_recovery(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Browser Export Recovery Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Browser Export Recovery Plan",
                description="Keep browser download failures recoverable.",
                collaboration_summary="Do not strand users on API JSON.",
            )
        )
    )
    local_path = tmp_path / "private" / "bundle-export.yml"
    client = TestClient(build_app(service=service), raise_server_exceptions=False)
    detail_response = client.get(f"/bundles/{imported['id']}")
    library_response = client.get("/bundles")

    def fail_export_bundle(bundle_id: str) -> dict:
        assert bundle_id == imported["id"]
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "export_bundle", fail_export_bundle)

    response = client.get(f"/bundles/{imported['id']}/export")
    encoded_bundle_id = quote(imported["id"], safe="")
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")

    assert detail_response.status_code == HTTPStatus.OK
    assert (
        f'href="/bundles/{encoded_bundle_id}/export?workdir={encoded_workdir}" data-testid="bundle-export-yaml-link" data-workdir-context-link="workdir"'
        in detail_response.text
    )
    assert library_response.status_code == HTTPStatus.OK
    assert f'href="/bundles/{encoded_bundle_id}/export?workdir={encoded_workdir}"' in library_response.text
    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundles-page"' in response.text
    assert 'data-testid="bundle-derive-recovery"' in response.text
    assert 'data-recovery-action-kind="review_plan_file"' in response.text
    assert 'data-recovery-action-kind="retry_plan_file_export"' in response.text
    assert 'data-recovery-action-kind="open_plan_file_library"' in response.text
    assert f'href="/bundles/{encoded_bundle_id}?workdir={encoded_workdir}"' in response.text
    assert f'href="/bundles/{encoded_bundle_id}/export?workdir={encoded_workdir}"' in response.text
    assert f'href="/bundles?workdir={encoded_workdir}"' in response.text
    assert f'href="/api/bundles/{encoded_bundle_id}/export"' not in response.text
    assert "plan file could not be generated" in response.text
    assert "permission denied" not in response.text
    assert str(local_path) not in response.text


def test_api_bundles_import_reports_plan_file_workdir_recovery_without_side_effects(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    missing_workdir = tmp_path / "missing-project"
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    response = client.post("/api/bundles/import", json={"bundle_yaml": _bundle_yaml(missing_workdir)})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["surface"] == "web_bundle_import"
    assert payload["action"] == "import_bundle"
    assert "workdir does not exist:" not in payload["error"]
    assert "Target project directory does not exist yet" in payload["error"]
    assert str(missing_workdir.resolve()) == payload["workdir"]
    _assert_recovery_summary_actions(
        payload,
        summary_key="web_workdir_recovery_summary",
        state_key="workdir_state_status",
        state="missing",
        expected=["create_workdir", "retry_web_compose", "confirm_readiness"],
    )
    assert payload["next_actions"][1]["target"] == "web_bundle_import"
    assert payload["next_actions"][2]["after_action"] == "retry_web_compose"
    assert f"{source_entry} doctor --workdir" in payload["next_actions"][2]["command"]
    assert not missing_workdir.exists()
    assert service.list_bundles() == []
    assert service.list_loops() == []

    blank_response = client.post("/api/bundles/import", json={"bundle_yaml": _bundle_yaml("")})

    assert blank_response.status_code == HTTPStatus.BAD_REQUEST
    blank_payload = blank_response.json()
    assert blank_payload["loop_recovery"] == "target_workdir_unavailable"
    assert blank_payload["status"] == "blocked_by_workdir"
    assert blank_payload["workdir"] == ""
    assert blank_payload["workdir_state"]["status"] == "required"
    _assert_recovery_summary_actions(
        blank_payload,
        summary_key="web_workdir_recovery_summary",
        state_key="workdir_state_status",
        state="required",
        expected=["choose_workdir", "retry_web_compose", "confirm_readiness"],
    )
    assert "command" not in blank_payload["next_actions"][1]
    assert "command" not in blank_payload["next_actions"][2]
    assert service.list_bundles() == []
    assert service.list_loops() == []


def test_bundle_derive_save_preserves_workdir_recovery_actions(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    project_workdir = tmp_path / "missing-derived-source"
    project_workdir.mkdir()
    loop = service.create_loop(
        name="Missing Workdir Derive Source",
        spec_path=sample_spec_file,
        workdir=project_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    shutil.rmtree(project_workdir)

    response = TestClient(build_app(service=service)).post(
        "/bundles/derive",
        data={
            "loop_id": loop["id"],
            "name": "Blocked Derived Plan",
            "description": "Do not save when the source project is missing.",
            "collaboration_summary": "Show repair actions instead.",
            "derive_action": "save",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-derive-error"' in response.text
    assert 'data-testid="bundle-derive-recovery"' in response.text
    assert 'data-recovery-action-kind="create_workdir"' in response.text
    assert 'data-recovery-action-kind="confirm_readiness"' in response.text
    assert 'data-recovery-action-kind="retry_web_compose"' in response.text
    assert "data-recovery-action-form" in response.text
    assert 'form="bundle-derive-form-fields"' in response.text
    assert 'formaction="/bundles/derive"' in response.text
    assert 'formmethod="post"' in response.text
    assert "mkdir -p" in response.text
    assert "loopora doctor --workdir" in response.text
    assert "workdir does not exist:" not in response.text
    assert service.list_bundles() == []


def test_run_detail_export_loop_preserves_workdir_on_download_failure(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Run Detail Export Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    local_path = tmp_path / "private" / "bundle-export.yml"

    def fail_derive_bundle_from_loop(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "derive_bundle_from_loop", fail_derive_bundle_from_loop)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    page_response = client.get(f"/runs/{run['id']}")
    export_response = client.get(
        f"/bundles/derive/export?loop_id={loop['id']}&workdir={encoded_workdir}",
    )

    assert page_response.status_code == HTTPStatus.OK
    assert (f'href="/bundles/derive/export?loop_id={loop["id"]}&amp;workdir={encoded_workdir}" data-testid="run-export-loop-button"') in page_response.text
    assert export_response.status_code == HTTPStatus.OK
    assert 'data-testid="bundles-page"' in export_response.text
    assert 'data-testid="global-workdir-context"' in export_response.text
    assert f'action="/bundles/derive?workdir={encoded_workdir}"' in export_response.text
    assert "plan file could not be generated" in export_response.text
    assert "permission denied" not in export_response.text
    assert str(local_path) not in export_response.text


def test_bundle_export_sanitizes_download_filename(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Filename Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name='Bad/Name" \r\n injected',
                description="Filename safety.",
                collaboration_summary="Export headers stay parseable.",
            )
        )
    )
    client = TestClient(build_app(service=service))

    response = client.get(f"/api/bundles/{imported['id']}/export")

    assert response.status_code == HTTPStatus.OK
    disposition = response.headers["content-disposition"]
    assert disposition == 'attachment; filename="Bad-Name-injected.yml"'
    assert "\n" not in disposition
    assert "\r" not in disposition
    assert "/" not in disposition


def test_bundle_export_preserves_safe_unicode_download_filename(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Unicode Filename Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="计划 Review",
                description="Filename i18n.",
                collaboration_summary="Export headers preserve safe multilingual filenames.",
            )
        )
    )
    client = TestClient(build_app(service=service))

    response = client.get(f"/api/bundles/{imported['id']}/export")

    assert response.status_code == HTTPStatus.OK
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="Review.yml"')
    assert "filename*=UTF-8''%E8%AE%A1%E5%88%92%20Review.yml" in disposition
    assert "计划" not in disposition
