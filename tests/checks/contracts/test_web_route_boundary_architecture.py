from __future__ import annotations

from service_architecture_test_support import assert_design_mentions, assert_markers_absent, assert_markers_present, loopora_source


def test_web_input_request_and_role_boundaries_have_dedicated_owner_modules() -> None:
    sources = {filename: loopora_source(filename) for filename in (
        "web_inputs.py", "web_request_context.py", "web_role_inputs.py", "web_strategy_inputs.py",
        "web_loop_inputs.py", "web_bundle_inputs.py", "web_common_inputs.py", "web_spec_documents.py",
        "web.py", "web_route_context_role_pages.py", "web_route_forms.py", "web_route_context_loop_pages.py", "web_spec_api.py",
    )}
    assert_markers_absent(
        sources["web_inputs.py"],
        "def _preferred_request_locale",
        "def _build_access_state",
        "def _normalize_role_definition_form",
        "def _role_definition_payload_from_mapping",
        "def _decorate_role_definition_overview",
        "def _strategy_source_from_mapping",
        "def _normalize_orchestration_form",
        "def _loop_payload_from_mapping",
        "def _normalize_loop_form",
        "def _normalize_bundle_import_form",
        "def _coerce_bool",
        "def _spec_document_payload",
    )
    assert_markers_present(sources["web_request_context.py"], "def _preferred_request_locale", "def _build_access_state")
    assert_markers_present(
        sources["web_role_inputs.py"],
        "def _normalize_role_definition_form",
        "def _role_definition_payload_from_mapping",
        "def _decorate_role_definition_overview",
    )
    assert_markers_present(sources["web_strategy_inputs.py"], "def _strategy_source_from_mapping", "def _normalize_orchestration_form")
    assert_markers_present(sources["web_loop_inputs.py"], "def _loop_payload_from_mapping", "def _normalize_loop_form")
    assert "def _normalize_bundle_import_form" in sources["web_bundle_inputs.py"]
    assert "def _coerce_bool" in sources["web_common_inputs.py"]
    assert_markers_present(
        sources["web_spec_documents.py"],
        "def _load_spec_markdown_document",
        "def _resolve_spec_markdown_path",
        "def _spec_document_payload",
    )
    assert_markers_absent(sources["web_spec_api.py"], "def _load_spec_markdown_document", "def _resolve_spec_markdown_path")
    assert "from loopora.web_request_context import" in sources["web.py"]
    assert "from loopora.web_role_inputs import" in sources["web_route_context_role_pages.py"]
    assert_markers_present(
        sources["web_route_forms.py"],
        "from loopora.web_improvement_form_routes import register_improvement_form_routes",
        "from loopora.web_loop_form_routes import register_loop_form_routes",
        "from loopora.web_bundle_form_routes import register_bundle_form_routes",
        "from loopora.web_role_form_routes import register_role_form_routes",
        "from loopora.web_orchestration_form_routes import register_orchestration_form_routes",
    )
    assert_markers_present(
        sources["web_route_context_loop_pages.py"],
        "from loopora.web_loop_inputs import",
        "from loopora.web_bundle_inputs import",
        "from loopora.web_strategy_inputs import",
    )
    assert "from loopora.web_spec_documents import" in sources["web_spec_api.py"]


def test_role_form_routes_have_dedicated_boundary() -> None:
    assert_form_route_boundary(
        "web_role_form_routes.py",
        "register_role_form_routes",
        owner_markers=("from loopora.web_role_inputs import", '"/roles/{role_definition_id}/edit"'),
        forbidden_markers=("from loopora.web_role_inputs import",),
    )


def test_orchestration_form_routes_have_dedicated_boundary() -> None:
    assert_form_route_boundary(
        "web_orchestration_form_routes.py",
        "register_orchestration_form_routes",
        owner_markers=("from loopora.web_strategy_inputs import", '"/orchestrations/{orchestration_id}/edit"'),
        forbidden_markers=("from loopora.web_strategy_inputs import",),
    )


def test_loop_form_routes_have_dedicated_boundary() -> None:
    assert_form_route_boundary(
        "web_loop_form_routes.py",
        "register_loop_form_routes",
        owner_markers=("from loopora.web_loop_inputs import", '"/loops/new/manual"'),
        forbidden_markers=("from loopora.web_loop_inputs import",),
    )


def test_bundle_form_routes_have_dedicated_boundary() -> None:
    assert_form_route_boundary(
        "web_bundle_form_routes.py",
        "register_bundle_form_routes",
        owner_markers=(
            "from loopora.web_bundle_inputs import",
            "from loopora.web_common_inputs import",
            '"/loops/new/import-bundle"',
            '"/bundles/{bundle_id}/edit"',
        ),
        forbidden_markers=("from loopora.web_bundle_inputs import", "from loopora.web_common_inputs import"),
    )


def test_improvement_form_routes_have_dedicated_boundary() -> None:
    assert_form_route_boundary(
        "web_improvement_form_routes.py",
        "register_improvement_form_routes",
        owner_markers=(
            "from loopora.service_types import LooporaConflictError",
            '"/runs/{run_id}/rerun"',
            '"/runs/{run_id}/accept"',
        ),
        forbidden_markers=("from loopora.service_types import LooporaConflictError",),
    )


def assert_form_route_boundary(
    route_module: str,
    register_function: str,
    *,
    owner_markers: tuple[str, ...],
    forbidden_markers: tuple[str, ...],
) -> None:
    forms_source = loopora_source("web_route_forms.py")
    route_source = loopora_source(route_module)
    route_module_name = route_module.removesuffix(".py")
    assert f"from loopora.{route_module_name} import {register_function}" in forms_source
    assert f"{register_function}(app, ctx)" in forms_source
    assert_markers_absent(forms_source, *forbidden_markers)
    assert_markers_present(route_source, f"def {register_function}", *owner_markers)
    assert_design_mentions(route_module)
