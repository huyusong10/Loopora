from __future__ import annotations

from service_architecture_test_support import REPO_ROOT, assert_design_mentions, assert_markers_absent, assert_markers_present, loopora_source


def test_web_input_request_and_role_boundaries_have_dedicated_owner_modules() -> None:
    sources = {
        filename: loopora_source(filename)
        for filename in (
            "web_inputs.py",
            "web_request_context.py",
            "web_role_inputs.py",
            "web_strategy_inputs.py",
            "web_loop_inputs.py",
            "web_bundle_inputs.py",
            "web_common_inputs.py",
            "web_spec_documents.py",
            "web_spec_document_api_routes.py",
            "web_loop_create_context.py",
            "web.py",
            "web_route_context.py",
            "web_route_context_role_pages.py",
            "web_route_forms.py",
            "web_route_context_loop_pages.py",
            "web_route_context_orchestration_pages.py",
            "web_spec_api.py",
        )
    }
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
    assert "default_strategy_role_execution_settings" in sources["web_role_inputs.py"]
    assert "profile.command_only" not in sources["web_role_inputs.py"]
    assert "profile.cli_name" not in sources["web_role_inputs.py"]
    assert_markers_present(sources["web_strategy_inputs.py"], "def _strategy_source_from_mapping", "def _normalize_orchestration_form")
    assert_markers_present(sources["web_loop_inputs.py"], "def _loop_payload_from_mapping", "def _normalize_loop_form")
    assert "normalize_loop_compose_execution_options" in sources["web_loop_inputs.py"]
    assert "executor_profile" not in sources["web_loop_inputs.py"]
    assert "def _normalize_bundle_import_form" in sources["web_bundle_inputs.py"]
    assert "def _coerce_bool" in sources["web_common_inputs.py"]
    assert_markers_present(
        sources["web_spec_documents.py"],
        "def _load_spec_markdown_document",
        "def _resolve_spec_markdown_path",
        "def _spec_document_payload",
    )
    assert_markers_present(
        sources["web_loop_create_context.py"],
        "def loop_create_page_context",
        "def _create_choice_existing_work_state",
        "from loopora.web_home_attention import home_loop_sections",
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
        "from loopora.web_project_scope_routes import register_project_scope_routes",
        "register_project_scope_routes(app, ctx)",
    )
    assert "from loopora.web_route_context_orchestration_pages import" in sources["web_route_context.py"]
    assert_markers_present(
        sources["web_route_context_loop_pages.py"],
        "from loopora.web_loop_create_context import",
        "from loopora.web_loop_inputs import",
        "from loopora.web_bundle_inputs import",
    )
    assert_markers_present(
        sources["web_route_context_orchestration_pages.py"],
        "from loopora.web_strategy_inputs import",
        "render_spec_template_for_strategy_source",
        "available_strategy_prompt_templates",
        "def render_orchestrations",
        "def render_new_orchestration",
        "def _orchestration_field_labels",
    )
    assert_markers_absent(
        sources["web_route_context_loop_pages.py"],
        "def _create_choice_existing_work_state",
        "def _create_choice_links",
        "from loopora.web_home_attention import home_loop_sections",
        "from loopora.web_strategy_inputs import",
        "render_spec_template_for_strategy_source",
        "def render_orchestrations",
        "def render_new_orchestration",
    )
    assert "from loopora.web_spec_documents import" in sources["web_spec_document_api_routes.py"]
    assert_design_mentions("web_loop_create_context.py", "web_route_context_orchestration_pages.py", "web_project_scope_routes.py")


def test_page_route_surfaces_have_dedicated_owner_modules() -> None:
    sources = {
        filename: loopora_source(filename)
        for filename in (
            "web_route_pages.py",
            "web_home_create_page_routes.py",
            "web_library_page_routes.py",
            "web_support_page_routes.py",
            "web_bundle_export_page_routes.py",
            "web_page_query_redirects.py",
        )
    }

    assert_markers_present(
        sources["web_route_pages.py"],
        "from loopora.web_home_create_page_routes import register_home_create_page_routes",
        "from loopora.web_library_page_routes import register_library_page_routes",
        "from loopora.web_support_page_routes import register_support_page_routes",
        "from loopora.web_bundle_export_page_routes import register_bundle_export_page_routes",
        "register_home_create_page_routes(app, ctx)",
        "register_library_page_routes(app, ctx)",
        "register_bundle_export_page_routes(app, ctx)",
        "register_support_page_routes(app, ctx)",
        "register_loop_run_page_routes(app, ctx)",
    )
    assert_markers_absent(
        sources["web_route_pages.py"],
        "home_loop_sections",
        "safe_local_return_path",
        "is_sensitive_redirect_query_key",
        '"/loops/new"',
        '"/orchestrations"',
        '"/same-agent"',
        '"/support"',
        '"/bundles/{bundle_id}/export"',
    )
    assert_markers_present(
        sources["web_home_create_page_routes.py"],
        "def register_home_create_page_routes",
        "home_loop_sections",
        "new_loop_redirect",
        "new_loop_bundle_redirect",
        "clean_create_query_redirect",
        '"/loops/new"',
        '"/loops/new/bundle"',
        '"/loops/new/manual"',
    )
    assert_markers_present(
        sources["web_library_page_routes.py"],
        "def register_library_page_routes",
        "clean_bundles_query_redirect",
        '"/orchestrations"',
        '"/bundles"',
        '"/roles"',
    )
    assert_markers_present(
        sources["web_support_page_routes.py"],
        "def register_support_page_routes",
        "def _support_target_return_to",
        "def _support_target_redirect_url",
        '"/same-agent"',
        '"/tools"',
        '"/support"',
        '"/fit-guide"',
        '"/runs"',
    )
    assert_markers_present(
        sources["web_bundle_export_page_routes.py"],
        "def register_bundle_export_page_routes",
        "def _browser_bundle_export_response",
        "web_bundle_export_generation_recovery_payload",
        '"/bundles/derive/export"',
        '"/bundles/{bundle_id}/export"',
    )
    assert_markers_present(
        sources["web_page_query_redirects.py"],
        "def new_loop_redirect",
        "def clean_create_query_redirect",
        "def clean_bundles_query_redirect",
        "is_sensitive_redirect_query_key",
    )
    assert_design_mentions(
        "web_home_create_page_routes.py",
        "web_library_page_routes.py",
        "web_support_page_routes.py",
        "web_bundle_export_page_routes.py",
        "web_page_query_redirects.py",
    )


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
        owner_markers=("from loopora.web_loop_inputs import", '"/loops/new/manual"', '"/loops/{loop_id}/runs"'),
        forbidden_markers=("from loopora.web_loop_inputs import",),
    )


def test_bundle_form_routes_have_dedicated_boundary() -> None:
    assert_form_route_boundary(
        "web_bundle_form_routes.py",
        "register_bundle_form_routes",
        owner_markers=(
            "from loopora.web_bundle_derive_form_routes import",
            "from loopora.web_bundle_edit_form_routes import",
            "from loopora.web_bundle_import_form_routes import",
            "from loopora.web_bundle_run_routes import",
        ),
        forbidden_markers=("from loopora.web_bundle_inputs import", "from loopora.web_common_inputs import"),
    )


def test_bundle_edit_form_routes_have_dedicated_boundary() -> None:
    form_source = loopora_source("web_bundle_form_routes.py")
    edit_source = loopora_source("web_bundle_edit_form_routes.py")

    assert "from loopora.web_bundle_edit_form_routes import" in form_source
    assert "register_bundle_edit_form_routes(app, ctx)" in form_source
    assert_markers_absent(
        form_source,
        "def update_bundle_from_form",
        "asset_mutation_error_message",
        "request_resource_workdir_context_href",
        '"/bundles/{bundle_id}/edit"',
    )
    assert_markers_present(
        edit_source,
        "def register_bundle_edit_form_routes",
        "def update_bundle_from_form",
        "asset_mutation_error_message",
        "request_resource_workdir_context_href",
        '"/bundles/{bundle_id}/edit"',
    )
    assert_design_mentions("web_bundle_edit_form_routes.py")


def test_bundle_derive_form_routes_have_dedicated_boundary() -> None:
    form_source = loopora_source("web_bundle_form_routes.py")
    derive_source = loopora_source("web_bundle_derive_form_routes.py")

    assert "from loopora.web_bundle_derive_form_routes import" in form_source
    assert "register_bundle_derive_form_routes(app, ctx)" in form_source
    assert_markers_absent(
        form_source,
        "def _save_derived_bundle_from_form",
        "def _download_derived_bundle_redirect",
        "_normalize_bundle_derive_form",
        "web_bundle_import_text_workdir_recovery",
        '"/bundles/derive"',
    )
    assert_markers_present(
        derive_source,
        "def register_bundle_derive_form_routes",
        "def _save_derived_bundle_from_form",
        "def _download_derived_bundle_redirect",
        "_normalize_bundle_derive_form",
        "web_bundle_import_text_workdir_recovery",
        '"/bundles/derive"',
        '"/bundles/derive/export',
    )
    assert_design_mentions("web_bundle_derive_form_routes.py")


def test_bundle_import_form_routes_have_dedicated_boundary() -> None:
    form_source = loopora_source("web_bundle_form_routes.py")
    import_source = loopora_source("web_bundle_import_form_routes.py")

    assert "from loopora.web_bundle_import_form_routes import" in form_source
    assert "register_bundle_import_form_routes(app, ctx)" in form_source
    assert_markers_absent(
        form_source,
        "def _import_bundle_from_create_loop_form_response",
        "def _bundle_import_recovery_from_form",
        "CREATE_LOOP_IMPORT_START_PREVIEW_REQUIRED",
        '"/loops/new/import-bundle"',
        '"/bundles/import"',
        "_normalize_bundle_import_form",
    )
    assert_markers_present(
        import_source,
        "def register_bundle_import_form_routes",
        "def _import_bundle_from_create_loop_form_response",
        "def _register_bundle_import_routes",
        "CREATE_LOOP_IMPORT_START_PREVIEW_REQUIRED",
        '"/loops/new/import-bundle"',
        '"/bundles/import"',
        "web_bundle_import_file_workdir_recovery",
    )
    assert_design_mentions("web_bundle_import_form_routes.py")


def test_bundle_run_routes_have_dedicated_boundary() -> None:
    form_source = loopora_source("web_bundle_form_routes.py")
    run_source = loopora_source("web_bundle_run_routes.py")

    assert "from loopora.web_bundle_run_routes import" in form_source
    assert "def _start_bundle_run_from_form_response" not in form_source
    assert "AGENT_NATIVE_PLAN_FILE_WEB_START_ERROR" not in form_source
    assert '"/bundles/{bundle_id}/runs"' not in form_source
    assert_markers_present(
        run_source,
        "def register_bundle_run_routes",
        "def bundle_import_run_dispatch_response",
        "def _start_bundle_run_from_form_response",
        "AGENT_NATIVE_PLAN_FILE_WEB_START_ERROR",
        '"/bundles/{bundle_id}/runs"',
    )
    assert_design_mentions("web_bundle_run_routes.py")


def test_improvement_form_routes_have_dedicated_boundary() -> None:
    assert_form_route_boundary(
        "web_improvement_form_routes.py",
        "register_improvement_form_routes",
        owner_markers=(
            "from loopora.service import LooporaError",
            "from loopora.service_types import LooporaConflictError",
            '"/runs/{run_id}/rerun"',
            '"/runs/{run_id}/accept"',
            '"/runs/{run_id}/reopen-result"',
        ),
        forbidden_markers=(
            "from loopora.service import LooporaError",
            "from loopora.service_types import LooporaConflictError",
        ),
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


def test_fit_review_completion_commands_have_dedicated_boundary() -> None:
    guidance_source = loopora_source("fit_review_guidance.py")
    commands_source = loopora_source("fit_review_completion_commands.py")
    first_use_guide_source = loopora_source("dev_check_guide_first_use.py")

    assert "from loopora.fit_review_completion_commands import" in guidance_source
    assert_markers_absent(
        guidance_source,
        "def _fit_review_completion_command",
        "def _fit_direct_decision_completion_command",
        "def _fit_review_completion_action",
        "def _fit_supplied_review_option_args",
    )
    assert_markers_present(
        commands_source,
        "def _fit_review_completion_command",
        "def _fit_direct_decision_completion_command",
        "def _fit_review_completion_action",
        "def _fit_supplied_review_option_args",
        "normalize_loopora_cli_entry",
    )
    assert "src/loopora/fit_review_completion_commands.py" in first_use_guide_source
    assert_design_mentions("fit_review_completion_commands.py")


def test_fit_review_first_task_messages_have_dedicated_boundary() -> None:
    guidance_source = loopora_source("fit_review_guidance.py")
    messages_source = loopora_source("fit_review_first_task_messages.py")
    first_use_guide_source = loopora_source("dev_check_guide_first_use.py")

    assert "from loopora.fit_review_first_task_messages import" in guidance_source
    assert_markers_absent(
        guidance_source,
        "def _fit_review_draft_first_task_message",
        "def _fit_first_task_message_example",
        "def _primary_first_task_message",
        "def _project_primary_first_task_message_state",
    )
    assert_markers_present(
        messages_source,
        "def _fit_review_draft_first_task_message",
        "def _fit_first_task_message_example",
        "def _primary_first_task_message",
        "def _project_primary_first_task_message_state",
        "FIT_FIRST_TASK_MESSAGE_STATUS",
    )
    assert "src/loopora/fit_review_first_task_messages.py" in first_use_guide_source
    assert_design_mentions("fit_review_first_task_messages.py")


def _assert_tutorial_fit_guidance_boundary(
    template: str,
    route_source: str,
    fit_source: str,
    script: str,
    styles: str,
) -> None:
    assert "fit_guidance_web_context" in route_source
    assert all(
        fragment in route_source
        for fragment in ('"fit_guidance": fit_guidance_web_context(', "current_copyable_loopora_cli_entry()", "workdir=tutorial_workdir or None")
    )
    assert all(
        fragment in fit_source
        for fragment in (
            '"fit_completion_cli_entry": normalized_cli_entry',
            '"fit_review_input_fields": [dict(item) for item in FIT_REVIEW_INPUT_FIELDS]',
            '"fit_review_completion_placeholders": dict(FIT_REVIEW_COMPLETION_PLACEHOLDERS)',
            '"fit_review_completion_placeholders_zh": dict(FIT_REVIEW_COMPLETION_PLACEHOLDERS_ZH)',
            '"fit_direct_decision_completion_placeholders": dict(FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS)',
            '"fit_direct_decision_completion_placeholders_zh": dict(FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS_ZH)',
        )
    )
    assert all(
        fragment in fit_source
        for fragment in (
            "def fit_guidance_web_context(",
            "workdir: Path | str | None = None",
            'workdir_supplied = workdir is not None and str(workdir).strip() != ""',
            "_project_fit_guidance_for_workdir(",
        )
    )
    assert '"fit_review_setup_gate": dict(FIT_REVIEW_SETUP_GATE)' in fit_source
    assert all(
        fragment in fit_source
        for fragment in (
            '"fit_first_task_message_status": dict(FIT_FIRST_TASK_MESSAGE_STATUS)',
            "primary_message_state = _primary_first_task_message_state_payload(",
            '"primary_first_task_message_state": primary_message_state',
            '"first_task_message_example_state": _fit_first_task_message_example_state()',
        )
    )
    assert all(
        fragment in fit_source
        for fragment in (
            '"fit_guidance_summary": {',
            '"task_review_questions": [dict(item) for item in TASK_FIT_REVIEW_QUESTIONS]',
            "_project_fit_route_readiness_summary(payload)",
            "_project_fit_reviewed_setup_gate(payload)",
            "_project_fit_task_review_status(payload)",
            "_project_fit_summary_action_kinds(payload)",
        )
    )
    for expected in (
        'data-testid="tutorial-fit-guide"',
        'data-testid="tutorial-fit-strong-signals"',
        'data-testid="tutorial-fit-direct-signals"',
        'data-testid="tutorial-fit-task-review"',
        'data-fit-setup-ready="{{ fit_guidance.fit_review_setup_gate.ready }}"',
        'data-fit-cli-entry="{{ fit_guidance.fit_completion_cli_entry }}"',
        'data-fit-setup-blocked="{{ fit_guidance.fit_review_setup_gate.blocked }}"',
        'data-fit-setup-blocker="{{ fit_guidance.fit_review_setup_gate.blocker }}"',
        'data-fit-setup-direct="{{ fit_guidance.fit_review_setup_gate.direct }}"',
        'data-fit-setup-direct-blocker="{{ fit_guidance.fit_review_setup_gate.direct_blocker }}"',
        'data-fit-first-task-preview="{{ fit_guidance.fit_first_task_message_status.preview }}"',
        'data-fit-first-task-ready="{{ fit_guidance.fit_first_task_message_status.ready }}"',
        'data-fit-first-task-direct="{{ fit_guidance.fit_first_task_message_status.direct }}"',
        'data-current-workdir="{{ fit_guidance.workdir }}"',
        'data-fit-workdir="{{ fit_guidance.workdir }}"',
        'data-fit-workdir-state-status="{{ fit_guidance.workdir_state.status }}"',
        "data-fit-workdir-ready=\"{{ 'true' if fit_guidance.workdir_ready else 'false' }}\"",
        "data-fit-target-project-required=\"{{ 'true' if fit_guidance.target_project_required else 'false' }}\"",
        "data-fit-route-commands-placeholders=\"{{ 'true' if fit_guidance.route_commands_are_placeholders else 'false' }}\"",
        'data-fit-draft-field="{{ field.id }}"',
        'data-fit-command-option="{{ field.option }}"',
        "data-fit-required-for-first-task=\"{{ '1' if field.required_for_first_task else '0' }}\"",
        'data-fit-command-placeholder="{{ fit_guidance.fit_review_completion_placeholders[field.id] }}"',
        'data-fit-command-placeholder-en="{{ fit_guidance.fit_review_completion_placeholders[field.id] }}"',
        'data-fit-command-placeholder-zh="{{ fit_guidance.fit_review_completion_placeholders_zh[field.id] }}"',
        'data-fit-placeholder-en="{{ field.placeholder_en }}"',
        "data-fit-direct-decision-input-placeholder-en=\"{{ field.get('direct_decision_placeholder_en', field.placeholder_en) }}\"",
        "data-fit-direct-decision-placeholder-en=\"{{ fit_guidance.fit_direct_decision_completion_placeholders.get(field.id, '') }}\"",
        "data-fit-direct-decision-placeholder-zh=\"{{ fit_guidance.fit_direct_decision_completion_placeholders_zh.get(field.id, '') }}\"",
        "data-testid=\"tutorial-fit-{{ field.id | replace('_', '-') }}-input\"",
        'data-testid="tutorial-fit-task-draft"',
        "data-fit-prefer-direct",
        'data-testid="tutorial-fit-prefer-direct-input"',
        'data-fit-setup-direct-input-blocker="{{ fit_guidance.fit_review_setup_gate.direct_input_blocker }}"',
        'data-fit-first-task-direct-input="{{ fit_guidance.fit_first_task_message_status.direct_input }}"',
        'data-testid="tutorial-fit-completion-command"',
        'data-testid="tutorial-fit-completion-command-copy"',
        'data-tutorial-fit-route="choice"',
        'data-testid="tutorial-fit-task-use-tools"',
        'data-tutorial-fit-route="setup"',
        'data-tutorial-fit-route="web"',
        'data-tutorial-fit-route="expert"',
        "{% for signal in fit_guidance.strong_fit_signals %}",
        "{% for signal in fit_guidance.prefer_direct_agent_or_checks %}",
        "{% for field in fit_guidance.fit_review_input_fields if field.id == 'task' %}",
        "{% for question in fit_guidance.task_review_questions %}",
        "signal.text_zh",
        "signal.text_en",
        "question.text_zh",
        "question.text_en",
    ):
        assert expected in template
    for expected in (
        "draftForInputs(inputs, fields)",
        'completionCommandForInputs(inputs, fields, sourceWorkdir = "", preferDirect = false)',
        "localizedFitPlaceholder(field)",
        "localizedInputPlaceholder(field)",
        "localizedDirectDecisionInputPlaceholder(field)",
        "setFitFieldDecisionContext(fields, preferDirect)",
        "localizedDirectDecisionPlaceholder(field)",
        "fitPlaceholderForInput(inputId, fields)",
        "fitReviewSetupGate(reviewShell, missingInputIds, preferDirect = false, directDecisionHasInput = true)",
        "requiredFitInputIds(fields)",
        "missingFitInputIds(inputs, fields)",
        "directDecisionInputSupplied(inputs)",
        "copyButton.disabled = !isComplete",
        "function shellQuote(value)",
        "function fitCliEntry()",
        "field.dataset.fitCommandOption",
        "field?.dataset.fitCommandPlaceholder",
        "field?.dataset.fitCommandPlaceholderZh",
        'const parts = [fitCliEntry(), "fit"]',
        'parts.push("--language", "zh")',
        'parts.push("--workdir", shellQuote(workdir))',
        'document.getElementById("tutorial-fit-completion-command")',
        "function setHandoffLinksEnabled(enabled)",
        "function disabledHandoffLinkMessage()",
        "window.LooporaUI.setNavigationControlBlocked(link, !enabled",
        'markerDataset: "fitHandoffDisabled"',
        'baseHrefDataset: "handoffBaseHref"',
        'disabledHrefDataset: "disabledHref"',
        "disabledHandoffLinkMessage()",
        "setHandoffLinksEnabled(false)",
        "setHandoffLinksEnabled(true)",
        "document.querySelector(\"[data-testid='tutorial-fit-completion-command-copy']\")",
        "link.dataset.tutorialFitRoute = route",
    ):
        assert expected in script
    assert 'const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1"' in script
    for expected in ("window.sessionStorage.setItem(FIT_HANDOFF_STORAGE_KEY", "function storedFitHandoffForCurrentTarget()", "function hydrateFitReviewFromSession(fields, preferDirectInput)"):
        assert expected in script
    assert all(
        fragment in script
        for fragment in (
            'url.searchParams.get("workdir") || url.searchParams.get("alignment_workdir")',
            "function fitGuidanceWorkdirContext()",
            "dataset.currentWorkdir || reviewShell?.dataset.fitWorkdir",
            "return toolsWorkdir || urlWorkdir || fitGuidanceWorkdirContext();",
            "completionCommandForInputs(inputs, fields, tutorialWorkdirContext())",
            "const sourceWorkdir = tutorialWorkdirContext(link)",
            "source_workdir: sourceWorkdir",
            'document.addEventListener("loopora:workdirchange", renderDraft)',
        )
    )
    assert "language: currentLocale()" in script
    assert all(
        fragment in script
        for fragment in (
            "missing_first_task_input_ids: missingInputIds",
            "function primaryFirstTaskMessageState(reviewShell, setupGate)",
            "const firstTaskState = primaryFirstTaskMessageState(reviewShell, setupGate)",
            "primary_first_task_message_state: firstTaskState",
        )
    )
    assert "...setupGate" in script
    assert all(
        fragment in script
        for fragment in (
            "ready_for_loopora_plan_message: setupGate.setup_allowed",
            "function fitSetupCommandState(sourceWorkdir, setupGate)",
            '["prefer_direct_path", "missing_direct_decision_input"].includes(setupGate.setup_blocker)',
            "setup_gate_ready: false",
            "setup_gate_blockers: [setupGate.setup_blocker]",
            "setup_command_blockers: [setupGate.setup_blocker]",
            "route_preview_blockers: [setupGate.setup_blocker]",
            "target_project_required: targetProjectRequired",
            "route_commands_are_placeholders: targetProjectRequired",
            "const setupCommandsReady = blockers.length === 0",
            "setup_gate_ready: setupCommandsReady",
            "setup_gate_blockers: setupCommandsReady ? [] : blockers",
            "route_preview_executable: setupCommandsReady",
            "route_preview_blockers: setupCommandsReady ? [] : blockers",
            "const setupCommandState = fitSetupCommandState(sourceWorkdir, setupGate)",
            "...setupCommandState",
        )
    )
    assert all(
        fragment in script
        for fragment in (
            "setup_gate: ready",
            'parts.push("--prefer-direct")',
            '["task", "direct_path_check"].includes(inputId)',
            'if (inputId === "task" && !suppliedValue)',
            "return Boolean(compactText(inputs.direct_path_check));",
            "Add a direct-path reason before recording why Loopora is not needed.",
            'status: reviewShell?.dataset.fitFirstTaskDirectInput || "direct_path_needs_decision_input"',
            'status: reviewShell?.dataset.fitFirstTaskDirect || "direct_path_selected"',
            "prefer_direct_path: true",
            'fit_decision: "prefer_direct_path"',
            'primary_first_task_message: ""',
            "direct_decision_command: directDecisionCommand",
            "function directDecisionHandoffPayload(inputs, sourceWorkdir)",
            "const storedDirectDecision = preferDirect && directDecisionInputSupplied(inputs)",
            "writeFitHandoff(directDecisionHandoffPayload(inputs, tutorialWorkdirContext()))",
        )
    )
    assert 'reviewShell?.dataset.fitSetupBlocked || "blocked_until_review_inputs_complete"' in script
    assert "setCompletionCommand(inputs, true, isComplete, false)" in script
    assert "review_completion_command: missingInputIds.length > 0" in script
    assert all(
        fragment in script
        for fragment in ("primary_first_task_message: text", "primary_first_task_message_status: firstTaskState.status", "draft_first_task_message: text")
    )
    assert 'document.querySelectorAll("[data-fit-draft-field]")' in script
    assert 'document.getElementById("tutorial-fit-task-input")' in script
    assert all(
        fragment in script
        for fragment in (
            "return window.LooporaUI.writeTextToClipboard(text)",
            "function selectManualCopyField(field)",
            "the draft is selected for manual copy",
            "the completion command is selected for manual copy",
        )
    )
    assert "navigator.clipboard.writeText(text)" not in script
    assert ".tutorial-fit-guide-grid" in styles
    assert ".tutorial-fit-guide-card" in styles
    assert ".tutorial-fit-task-review" in styles
    assert ".tutorial-fit-task-draft" in styles
    assert all(
        fragment in styles
        for fragment in (
            ".tutorial-fit-completion-command",
            ".tutorial-fit-direct-decision",
            "[data-tutorial-fit-route].is-disabled",
        )
    )


def _assert_tutorial_tools_handoff_boundary(tools_template: str, tools_script: str, styles: str) -> None:
    assert 'data-testid="agent-adapter-draft-handoff"' in tools_template
    assert "data-agent-adapter-workdir-context=\"{{ workdir_context or '' }}\"" in tools_template
    assert 'const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1"' in tools_script
    assert "function renderFitHandoff()" in tools_script
    assert "agentAdapterHandoffUsesFitDraft" in tools_script
    assert "agentAdapterFirstTaskHandoffPolicies" in tools_script
    assert "first_task_handoff_policy" in tools_script
    assert "function agentAdapterFirstTaskHandoffPolicy" in tools_script
    assert 'data-testid="agent-adapter-first-task-preferred-source"' in tools_script
    assert "Generic fallback example" in tools_script
    assert "Loopora fit reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context" in tools_script
    assert 'source: "tutorial_fit_review"' in tools_script
    assert all(
        fragment in tools_script
        for fragment in (
            "const sourceWorkdir = String(payload?.source_workdir",
            "window.LooporaUI.tutorialFitSetupCommandState",
            "setupGateReady",
            "setupGateBlockers",
            "routePreviewExecutable",
            "routePreviewBlockers",
            "同一 Agent 设置命令可复制",
            "Same-Agent setup commands are copyable",
            "Choose and refresh a target in Same-Agent Setup",
            "window.LooporaUI.tutorialFitPrefersDirectPath(payload)",
            "prefer_direct_path",
            "Direct-path decision blocks Loopora setup",
            "Direct-path decision belongs to the source project",
            'data-testid="agent-draft-handoff-copy-direct-decision"',
            "fitDirectPathBlocksAgentSetup",
            "function syncAgentAdapterFitGates",
            "function fitHandoffBlocksCurrentAgentInstall",
            "function directHandoffBlocksAgentAdapterMutation",
            "same-Agent setup is disabled",
            'data-testid="agent-draft-handoff-state"',
        )
    )
    assert "function fitHandoffMatchesTarget" in tools_script
    assert "function fitHandoffReadyForAgent" in tools_script
    assert "function fitHandoffChipLabel" in tools_script
    assert "missing_first_task_input_ids" in tools_script
    assert 'setupGate !== "blocked_until_review_inputs_complete"' in tools_script
    assert "setupBlocker: String(payload?.setup_blocker" in tools_script
    assert "language: String(payload?.language" in tools_script
    assert "review_completion_command" in tools_script
    assert all(fragment in tools_script for fragment in ('["task", inputs.task]', '["direct_path_check", inputs.direct_path_check]', "Direct-path decision"))
    assert "fitHandoffChipLabel(inputId, prefersDirect)" in tools_script
    assert all(
        fragment in tools_script
        for fragment in (
            "function fitHandoffPrimaryFirstTaskState",
            "function normalizeAgentAdapterFirstTaskExampleState",
            "firstTaskExample?.state?.copyAllowed",
            "firstTaskState.copyAllowed",
            "handoff?.setupGateReady",
            "const hasWorkdirMismatch = !fitHandoffMatchesTarget(handoff, targetWorkdir)",
            "const hasSetupCommandBlockers = !prefersDirect && !handoff.setupGateReady",
            "Choose a target project first",
            "Missing target",
            "fitHandoffMatchesTarget(fitHandoff, targetWorkdir) && fitHandoffReadyForAgent(fitHandoff)",
        )
    )
    assert "allowEmptyRight: false" in tools_script
    assert "window.sessionStorage?.getItem(FIT_HANDOFF_STORAGE_KEY)" in tools_script
    assert all(
        fragment in tools_script
        for fragment in (
            'data-testid="agent-draft-handoff-source-workdir"',
            'data-testid="agent-draft-handoff-current-workdir"',
            'data-testid="agent-draft-handoff-missing-inputs"',
            'data-testid="agent-draft-handoff-use-source"',
            'data-testid="agent-draft-handoff-finish-review"',
            'data-testid="agent-draft-handoff-copy-completion"',
            "data-agent-draft-handoff-use-source",
            "data-agent-draft-handoff-finish-review",
            "data-agent-draft-handoff-copy-completion",
            "data-agent-draft-handoff-copy",
            "data-agent-draft-handoff-clear",
            'data-testid="agent-draft-handoff-manual-copy"',
            "function renderDraftHandoffManualCopy",
            "window.LooporaUI?.renderManualCopy?.(container, copyText",
            "agent-draft-handoff-manual-copy-textarea",
            "Manual completion command copy",
            "Manual direct-path command copy",
            "Manual Agent brief copy",
            "The browser blocked automatic copy; copy the command below manually.",
            "The browser blocked automatic copy; copy the Agent brief below manually.",
            "Reviewed handoff; finish setup first",
            "This Fit Guide handoff is bound to the current target.",
            "Copy the reviewed handoff for after setup is ready",
            'localeText("先设置", "Setup first")',
            "function fitHandoffReviewHref",
            "const agentBriefCopyButton = !needsAttention && handoff.draft && handoff.firstTaskState?.copyAllowed",
            "function readAgentAdapterWorkdirFromUrl()",
            "function readAgentAdapterWorkdirFromPageContext()",
            "dataset.agentAdapterWorkdirContext",
            "readAgentAdapterWorkdirFromPageContext()",
            "|| readAgentAdapterWorkdirPreference()",
            "function focusAgentAdapterTargetInput()",
            "agentAdapterWorkdirInput?.focus?.()",
            'persistAgentAdapterWorkdirPreference("")',
            "function setAgentAdapterTargetWorkdir",
            "persistAgentAdapterWorkdirPreference(value)",
            'window.LooporaUI.syncWorkdirContext(value, {syncUrl: true, urlParam: "workdir"})',
        )
    )
    assert 'data-testid="agent-adapter-clear-first-task-example"' in tools_script
    assert "agent-adapter-command-flow--with-brief" in tools_script
    assert ".agent-adapter-draft-handoff" in styles
    assert ".agent-draft-handoff-chips" in styles
    assert ".agent-draft-handoff-finish-review" in styles
    assert ".agent-adapter-first-task-example-head" in styles
    assert ".agent-adapter-first-task-source-note" in styles
    assert ".agent-adapter-command-flow--with-brief" in styles


def test_tutorial_reuses_public_fit_guidance_boundary() -> None:
    template = (REPO_ROOT / "src" / "loopora" / "templates" / "tutorial.html").read_text(encoding="utf-8")
    tools_template = (REPO_ROOT / "src" / "loopora" / "templates" / "tools.html").read_text(encoding="utf-8")
    route_source = loopora_source("web_route_context_help_pages.py")
    fit_source = loopora_source("fit_guidance.py")
    script = (REPO_ROOT / "src" / "loopora" / "static" / "pages" / "tutorial.js").read_text(encoding="utf-8")
    tools_script = (REPO_ROOT / "src" / "loopora" / "static" / "pages" / "tools.js").read_text(encoding="utf-8")
    styles = (REPO_ROOT / "src" / "loopora" / "static" / "styles" / "legacy.css").read_text(encoding="utf-8")

    _assert_tutorial_fit_guidance_boundary(template, route_source, fit_source, script, styles)
    _assert_tutorial_tools_handoff_boundary(tools_template, tools_script, styles)
