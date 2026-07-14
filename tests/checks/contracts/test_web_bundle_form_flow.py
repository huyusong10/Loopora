from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.service import LooporaError
from loopora.settings import app_home
from loopora.web import build_app

from bundle_lifecycle_test_support import _bundle_yaml
from web_bundle_detail_test_support import create_bundle_detail_loop, import_derived_bundle


def _assert_recovery_actions(response_text: str, testid: str, action_kinds: tuple[str, ...]) -> None:
    assert f'data-testid="{testid}"' in response_text
    for action_kind in action_kinds:
        assert f'data-recovery-action-kind="{action_kind}"' in response_text
        assert f"<strong>{action_kind.replace('_', ' ')}</strong>" not in response_text


def _assert_workdir_recovery_actions(response_text: str, testid: str) -> None:
    _assert_recovery_actions(response_text, testid, ("create_workdir", "retry_web_compose", "confirm_readiness"))


def _assert_recovery_submit_control(response_text: str, *, form_id: str, form_action: str) -> None:
    assert all(fragment in response_text for fragment in ("data-recovery-action-form", f'form="{form_id}"', f'formaction="{form_action}"', 'formmethod="post"'))


def test_bundles_page_exposes_direct_plan_file_import_form(service_factory) -> None:
    service = service_factory(scenario="success")
    response = TestClient(build_app(service=service)).get("/bundles")
    assert response.status_code == HTTPStatus.OK
    assert 'href="#bundle-import-panel" data-testid="bundles-import-plan-link"' in response.text
    assert 'data-testid="bundles-create-loop-import-link"' in response.text
    assert 'id="bundle-import-panel"' in response.text
    assert 'data-testid="bundle-import-panel"' in response.text
    assert 'data-testid="bundle-import-form"' in response.text
    assert 'id="bundle-import-form-fields"' in response.text
    assert 'data-import-intent="import"' in response.text
    assert 'action="/bundles/import"' in response.text
    assert 'data-testid="bundle-preview-button"' in response.text
    assert 'data-testid="alignment-ready-preview"' in response.text
    assert 'data-testid="alignment-workflow-diagram"' in response.text
    assert 'data-testid="alignment-spec-preview"' in response.text
    assert 'data-testid="alignment-role-list"' in response.text
    assert "pages/alignment.css" in response.text
    assert "pages/bundle_import.js" in response.text
    assert "pages/workflow_diagram.js" in response.text
    assert 'name="bundle_path"' in response.text
    assert 'name="bundle_yaml"' in response.text
    assert 'name="import_intent" value="import"' in response.text
    assert 'name="replace_bundle_id"' not in response.text
    assert "Replace plan id" not in response.text
    assert "Import Preview" in response.text
    assert "Replace With Preview" not in response.text


def test_manual_loop_form_explains_unusable_workdir_before_create(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    spec_path = tmp_path / "spec.md"
    missing_workdir = tmp_path / "missing project"
    workdir_file = tmp_path / "not-a-project"
    spec_path.write_text("# Task\n\nShip it.\n", encoding="utf-8")
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    original_file = workdir_file.read_text(encoding="utf-8")

    missing_response = client.post(
        "/loops/new/manual",
        data={
            "name": "Missing Workdir Loop",
            "workdir": str(missing_workdir),
            "spec_path": str(spec_path),
            "executor_kind": "codex",
            "executor_mode": "preset",
            "start_immediately": "false",
        },
    )

    assert missing_response.status_code == HTTPStatus.OK
    assert not missing_workdir.exists()
    assert service.list_loops() == []
    assert "workdir does not exist:" not in missing_response.text
    assert "Target project directory does not exist yet" in missing_response.text
    assert "First run:" in missing_response.text
    assert "mkdir -p" in missing_response.text
    assert str(missing_workdir.resolve()) in missing_response.text
    _assert_workdir_recovery_actions(missing_response.text, "manual-loop-recovery")
    _assert_recovery_submit_control(missing_response.text, form_id="new-loop-form", form_action="/loops/new/manual")

    file_response = client.post(
        "/loops/new/manual",
        data={
            "name": "File Workdir Loop",
            "workdir": str(workdir_file),
            "spec_path": str(spec_path),
            "executor_kind": "codex",
            "executor_mode": "preset",
            "start_immediately": "false",
        },
    )

    assert file_response.status_code == HTTPStatus.OK
    assert workdir_file.read_text(encoding="utf-8") == original_file
    assert service.list_loops() == []
    assert "workdir does not exist:" not in file_response.text
    assert "Target project path exists but is not a directory" in file_response.text
    assert "mkdir -p" not in file_response.text
    assert "loopora doctor --workdir" not in file_response.text
    _assert_recovery_actions(
        file_response.text,
        "manual-loop-recovery",
        ("choose_workdir", "retry_web_compose", "confirm_readiness"),
    )
    _assert_recovery_submit_control(file_response.text, form_id="new-loop-form", form_action="/loops/new/manual")
    blank_response = client.post("/loops/new/manual", data={"name": "Blank Workdir Loop", "workdir": "", "spec_path": str(spec_path)})
    assert blank_response.status_code == HTTPStatus.OK
    assert "Target project directory is required" in blank_response.text
    _assert_recovery_actions(blank_response.text, "manual-loop-recovery", ("choose_workdir", "retry_web_compose", "confirm_readiness"))
    _assert_recovery_submit_control(blank_response.text, form_id="new-loop-form", form_action="/loops/new/manual")


def test_manual_loop_form_explains_unusable_spec_before_create(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    workdir = tmp_path / "workdir"
    missing_spec = tmp_path / "missing-spec.md"
    spec_directory = tmp_path / "spec-directory"
    workdir.mkdir()
    spec_directory.mkdir()

    missing_response = client.post(
        "/loops/new/manual",
        data={
            "name": "Missing Spec Loop",
            "workdir": str(workdir),
            "spec_path": str(missing_spec),
            "orchestration_id": "builtin:repair_loop",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "start_immediately": "false",
        },
    )

    assert missing_response.status_code == HTTPStatus.OK
    assert not missing_spec.exists()
    assert service.list_loops() == []
    assert "spec does not exist:" not in missing_response.text
    assert "Spec file does not exist yet" in missing_response.text
    assert "First run:" in missing_response.text
    assert "loopora spec init" in missing_response.text
    assert str(missing_spec.resolve()) in missing_response.text
    assert "--orchestration-id builtin:repair_loop" in missing_response.text
    _assert_recovery_actions(
        missing_response.text,
        "manual-loop-recovery",
        ("create_spec", "retry_web_compose", "choose_spec"),
    )
    _assert_recovery_submit_control(missing_response.text, form_id="new-loop-form", form_action="/loops/new/manual")

    directory_response = client.post(
        "/loops/new/manual",
        data={
            "name": "Directory Spec Loop",
            "workdir": str(workdir),
            "spec_path": str(spec_directory),
            "executor_kind": "codex",
            "executor_mode": "preset",
            "start_immediately": "false",
        },
    )

    assert directory_response.status_code == HTTPStatus.OK
    assert service.list_loops() == []
    assert "spec does not exist:" not in directory_response.text
    assert "Spec path exists but is not a file" in directory_response.text
    assert "loopora spec init" not in directory_response.text
    _assert_recovery_actions(
        directory_response.text,
        "manual-loop-recovery",
        ("choose_spec", "retry_web_compose"),
    )
    _assert_recovery_submit_control(directory_response.text, form_id="new-loop-form", form_action="/loops/new/manual")
    blank_response = client.post("/loops/new/manual", data={"name": "Blank Spec Loop", "workdir": str(workdir), "spec_path": ""})
    assert blank_response.status_code == HTTPStatus.OK
    assert "Spec path is required" in blank_response.text
    _assert_recovery_actions(blank_response.text, "manual-loop-recovery", ("choose_spec", "retry_web_compose"))
    _assert_recovery_submit_control(blank_response.text, form_id="new-loop-form", form_action="/loops/new/manual")


def test_manual_loop_form_redacts_low_level_storage_errors(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "loopora.sqlite"

    def fail_create_loop(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "create_loop", fail_create_loop)
    response = TestClient(build_app(service=service)).post(
        "/loops/new/manual",
        data={
            "name": "Manual Storage Error Loop",
            "workdir": str(sample_workdir),
            "spec_path": str(sample_spec_file),
            "executor_kind": "codex",
            "executor_mode": "preset",
            "start_immediately": "false",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "Loop could not be created" in response.text
    assert "Manual Storage Error Loop" in response.text
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text
    assert service.list_loops() == []


def test_bundles_page_uses_recovery_empty_state_when_no_loop_can_be_exported(service_factory) -> None:
    service = service_factory(scenario="success")
    response = TestClient(build_app(service=service)).get("/bundles")

    assert response.status_code == HTTPStatus.OK
    assert all(
        fragment in response.text
        for fragment in (
            'data-testid="bundle-derive-empty-state"',
            'data-testid="bundle-derive-create-loop-link"',
            'href="/loops/new" data-testid="bundle-derive-create-loop-link"',
            'href="#bundle-import-panel" data-testid="bundles-empty-import-plan-link"',
            'href="/loops/new" data-testid="bundles-empty-create-choice-link"',
            'href="/same-agent" data-testid="bundles-empty-agent-setup-link"',
        )
    )
    assert 'data-testid="bundle-derive-form"' not in response.text


def test_bundles_page_exposes_loop_export_picker_when_source_loops_exist(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Exportable Loop",
    )
    response = TestClient(build_app(service=service)).get("/bundles")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-derive-form"' in response.text
    assert 'data-workdir-context-form="workdir"' in response.text
    assert 'data-testid="bundle-derive-loop-select"' in response.text
    assert 'name="derive_action" value="save" data-testid="bundle-derive-save-button"' in response.text
    assert 'name="derive_action" value="download" data-testid="bundle-derive-download-button"' in response.text
    assert f'value="{loop["id"]}"' in response.text
    assert "Exportable Loop" in response.text
    assert 'data-testid="bundle-derive-empty-state"' not in response.text


def test_bundle_form_import_and_edit_flow(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Form Source",
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
            name="Form Bundle",
            description="Imported through the HTML form.",
            collaboration_summary="Prefer compact but convincing evidence.",
        )
    )

    client = TestClient(build_app(service=service))
    import_response = client.post("/bundles/import", data={"bundle_yaml": bundle_yaml}, follow_redirects=False)

    assert import_response.status_code == HTTPStatus.SEE_OTHER
    bundle_location = import_response.headers["location"]
    bundle_id = urlsplit(bundle_location).path.rsplit("/", 1)[-1]
    bundle = service.get_bundle(bundle_id)
    assert bundle["name"] == "Form Bundle"

    edit_response = client.post(
        f"/bundles/{bundle_id}/edit",
        data={
            "description": "Updated bundle description.",
            "collaboration_summary": "Take fake done seriously.",
            "spec_markdown": "# Task\n\nShip the update.\n\n# Done When\n- It works.\n",
        },
        follow_redirects=False,
    )

    assert edit_response.status_code == HTTPStatus.SEE_OTHER
    updated_bundle = service.get_bundle(bundle_id)
    assert updated_bundle["description"] == "Updated bundle description."
    assert updated_bundle["collaboration_summary"] == "Take fake done seriously."
    spec_path = app_home() / "bundles" / bundle_id / "spec.md"
    assert spec_path.read_text(encoding="utf-8").startswith("# Task")


def test_bundle_edit_form_redacts_low_level_storage_errors(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "bundle.yml"
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Edit Storage Error Source",
    )
    bundle = import_derived_bundle(
        service,
        loop["id"],
        name="Edit Storage Error Plan",
        description="The detail page should stay usable.",
        collaboration_summary="No local storage path should be shown.",
    )

    def fail_update_bundle(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "update_bundle", fail_update_bundle)
    response = TestClient(build_app(service=service)).post(
        f"/bundles/{bundle['id']}/edit",
        data={
            "description": "Updated bundle description.",
            "collaboration_summary": "Take fake done seriously.",
            "spec_markdown": "# Task\n\nShip the update.\n\n# Done When\n- It works.\n",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in response.text
    assert "plan file could not be saved" in response.text
    assert "Updated bundle description." in response.text
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text


def test_bundles_page_import_error_stays_on_plan_file_surface(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/bundles/import",
        data={"bundle_yaml": "", "bundle_path": ""},
    )

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundles-page"' in response.text
    assert 'data-testid="bundle-import-form"' in response.text
    assert 'data-testid="bundle-import-error"' in response.text
    assert "bundle path or bundle YAML is required" in response.text
    assert 'name="replace_bundle_id"' not in response.text
    assert 'data-testid="loop-bundle-import-form"' not in response.text


def test_bundles_page_import_missing_file_uses_stable_error(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    missing_bundle = tmp_path / "missing-bundle.yml"

    response = TestClient(build_app(service=service)).post(
        "/bundles/import",
        data={"bundle_yaml": "", "bundle_path": str(missing_bundle)},
    )

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundles-page"' in response.text
    assert 'data-testid="bundle-import-error"' in response.text
    assert "bundle file does not exist" in response.text
    assert "No such file" not in response.text
    assert "bundle file does not exist:" not in response.text
    assert service.list_bundles() == []
    assert service.list_loops() == []


def test_bundles_page_import_preserves_workdir_recovery_actions(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    missing_workdir = tmp_path / "missing-project"

    response = TestClient(build_app(service=service)).post(
        "/bundles/import",
        data={"bundle_yaml": _bundle_yaml(missing_workdir), "bundle_path": ""},
    )

    assert response.status_code == HTTPStatus.OK
    assert not missing_workdir.exists()
    assert service.list_bundles() == []
    assert service.list_loops() == []
    _assert_workdir_recovery_actions(response.text, "bundle-import-recovery")
    _assert_recovery_submit_control(response.text, form_id="bundle-import-form-fields", form_action="/bundles/import")
    assert "mkdir -p" in response.text
    assert "loopora doctor --workdir" in response.text
    assert "workdir does not exist:" not in response.text


def test_bundles_page_import_redacts_low_level_storage_errors(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "loopora.sqlite"
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Import Storage Error Source",
    )
    bundle_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="Import Storage Error Plan",
            description="Import should keep storage failures stable.",
            collaboration_summary="No local storage path should be shown.",
        )
    )

    def fail_import_bundle_text(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "import_bundle_text", fail_import_bundle_text)

    response = TestClient(build_app(service=service)).post("/bundles/import", data={"bundle_yaml": bundle_yaml})

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-import-error"' in response.text
    assert "plan file could not be imported" in response.text
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text
    assert service.list_bundles() == []


def test_bundles_page_import_explains_blank_plan_file_workdir_before_create(
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/bundles/import",
        data={"bundle_yaml": _bundle_yaml("")},
    )

    assert response.status_code == HTTPStatus.OK
    assert service.list_bundles() == []
    assert service.list_loops() == []
    assert 'data-testid="bundle-import-error"' in response.text
    assert "Target project directory is required" in response.text
    assert "mkdir -p" not in response.text
    _assert_recovery_actions(response.text, "bundle-import-recovery", ("choose_workdir", "retry_web_compose", "confirm_readiness"))
    _assert_recovery_submit_control(response.text, form_id="bundle-import-form-fields", form_action="/bundles/import")


def test_bundles_page_rejects_replace_id_without_explicit_replace_intent(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Explicit Replace Guard Source",
    )
    original = import_derived_bundle(
        service,
        loop["id"],
        name="Original Managed Plan",
        description="Replacement must be explicit.",
        collaboration_summary="Protect ordinary imports from accidental overwrite.",
    )
    replacement_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="Replacement Managed Plan",
            description="Replacement submitted through the fixed replace flow.",
            collaboration_summary="Only explicit replace intent may overwrite.",
        )
    )
    client = TestClient(build_app(service=service))

    rejected = client.post(
        "/bundles/import",
        data={"bundle_yaml": replacement_yaml, "replace_bundle_id": original["id"]},
    )

    assert rejected.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-import-error"' in rejected.text
    assert "plan replacement must start from an explicit replace action" in rejected.text
    assert service.get_bundle(original["id"])["name"] == "Original Managed Plan"
    assert 'name="replace_bundle_id"' not in rejected.text

    accepted = client.post(
        "/bundles/import",
        data={
            "bundle_yaml": replacement_yaml,
            "replace_bundle_id": original["id"],
            "import_intent": "replace",
        },
        follow_redirects=False,
    )

    assert accepted.status_code == HTTPStatus.SEE_OTHER
    assert (urlsplit(accepted.headers["location"]).path, parse_qs(urlsplit(accepted.headers["location"]).query).get("workdir")) == (f"/bundles/{original['id']}", [str(sample_workdir.resolve())])
    assert service.get_bundle(original["id"])["name"] == "Replacement Managed Plan"


def test_bundle_revise_form_routes_service_error_back_to_visible_page_error(
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
        name="Bundle Revise Source",
    )
    bundle = import_derived_bundle(
        service,
        loop["id"],
        name="Bundle Revise Failure",
        description="Revise failures should stay visible on the bundle page.",
        collaboration_summary="Keep recovery local to the current plan.",
    )

    def fail_revision(*_args, **_kwargs):
        raise LooporaError("revision session is not available")

    monkeypatch.setattr(service, "create_bundle_revision_session", fail_revision)
    client = TestClient(build_app(service=service))

    response = client.post(f"/bundles/{bundle['id']}/revise", follow_redirects=False)

    assert response.status_code == HTTPStatus.SEE_OTHER
    redirect_parts = urlsplit(response.headers["location"])
    assert redirect_parts.path == f"/bundles/{bundle['id']}"
    redirect_query = parse_qs(redirect_parts.query)
    assert redirect_query["bundle_action_error"]
    assert redirect_query["workdir"] == [str(sample_workdir)]
    page_response = client.get(response.headers["location"])
    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-action-error"' in page_response.text
    assert "revision session is not available" in page_response.text


def test_create_loop_page_imports_bundle_as_loop_creation_flow(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source_loop = service.create_loop(
        name="Create Page Bundle Source",
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
            source_loop["id"],
            name="Create Page Bundle",
            description="Imported from the unified create loop page.",
            collaboration_summary="Create loop and bundle import share one entry.",
        )
    )

    client = TestClient(build_app(service=service))
    import_response = client.post(
        "/loops/new/import-bundle",
        data={"bundle_yaml": bundle_yaml, "start_immediately": ""},
        follow_redirects=False,
    )

    assert import_response.status_code == HTTPStatus.SEE_OTHER
    assert import_response.headers["location"].startswith("/loops/")
    imported_bundle = next(bundle for bundle in service.list_bundles() if bundle["name"] == "Create Page Bundle")
    assert (urlsplit(import_response.headers["location"]).path, parse_qs(urlsplit(import_response.headers["location"]).query).get("workdir")) == (f"/loops/{imported_bundle['loop_id']}", [str(sample_workdir.resolve())])
    assert service.get_loop(imported_bundle["loop_id"])["name"] == "Create Page Bundle Source"


def test_bundle_export_download_redacts_low_level_generation_errors(
    service_factory,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "private" / "loopora.db"

    def fail_derive_bundle_from_loop(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "derive_bundle_from_loop", fail_derive_bundle_from_loop)

    response = TestClient(build_app(service=service), raise_server_exceptions=False).get(
        "/bundles/derive/export",
        params={"loop_id": "loop_private", "name": "Private Export"},
    )

    assert response.status_code == HTTPStatus.OK
    assert "plan file could not be generated" in response.text
    assert "permission denied" not in response.text
    assert str(local_path) not in response.text


def test_create_loop_page_import_explains_blank_plan_file_workdir_before_create(
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/loops/new/import-bundle",
        data={"bundle_yaml": _bundle_yaml(""), "start_immediately": ""},
    )

    assert response.status_code == HTTPStatus.OK
    assert service.list_bundles() == []
    assert service.list_loops() == []
    assert 'data-testid="loop-bundle-import-form"' in response.text
    assert "Target project directory is required" in response.text
    assert "mkdir -p" not in response.text
    _assert_recovery_actions(response.text, "loop-bundle-import-recovery", ("choose_workdir", "retry_web_compose", "confirm_readiness"))
    _assert_recovery_submit_control(response.text, form_id="bundle-import-form-fields", form_action="/loops/new/manual/import-bundle")
