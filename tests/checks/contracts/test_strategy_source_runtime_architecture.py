from __future__ import annotations

from strategy_source_architecture_test_support import (
    assert_contains,
    assert_contains_all,
    assert_excludes,
    assert_excludes_all,
    loopora_path,
    loopora_source,
    loopora_sources,
)


def test_runtime_uses_strategy_source_boundary_for_workflow_source_helpers() -> None:
    strategy_source_path = loopora_path("strategy_source.py")
    strategy_source_boundary_sources = (
        "service.py",
        "service_app.py",
        "service_asset_common.py",
        "service_bundle_export.py",
        "agent_native_runtime_context.py",
        "service_run_registration.py",
        "service_loop_records.py",
        "service_runner_step_runtime.py",
        "service_runner_support.py",
    )
    sources = loopora_sources("strategy_source.py", "service_bundle_assets.py", *strategy_source_boundary_sources)
    runner_execution_source = loopora_source("service_runner_execution.py") + loopora_source("service_runner_context_preparation.py")
    strategy_import_sources = [sources[source_name] for source_name in strategy_source_boundary_sources]

    assert strategy_source_path.exists()
    assert_contains(
        sources["strategy_source.py"],
        "StrategySourceError",
        "def normalize_strategy_source",
        "def strategy_source_has_finish_gatekeeper_step",
        "def build_preset_strategy_source",
        "def resolve_strategy_prompt_files",
        "def normalize_strategy_role_models",
        "LEGACY_STRATEGY_ROLE_BY_ARCHETYPE",
        "STRATEGY_SOURCE_ARCHETYPES",
        "STRATEGY_ROLE_EXECUTION_FIELDS",
        "STRATEGY_ROLE_POSTURE_FIELDS",
    )
    assert_contains_all([*strategy_import_sources, runner_execution_source], "from loopora.strategy_source import")
    assert_excludes_all(
        [*strategy_import_sources, sources["service_bundle_assets.py"], runner_execution_source],
        "from loopora.workflows import",
    )
    loop_records_source = sources["service_loop_records.py"]
    assert_contains(loop_records_source, "_normalized_strategy_source_from_record", "_strategy_source_snapshot_from_record")
    assert "def _read_prompt_files" in loopora_source("service_loop_prompt_files.py")
    assert "def _read_prompt_files" not in loop_records_source
    assert "strategy_source_from_record(run)" in sources["agent_native_runtime_context.py"]
    assert "from loopora.strategy_source import" in runner_execution_source
    assert "strategy_source = self._strategy_source_snapshot_from_record(run)" in runner_execution_source
    assert "_normalized_workflow_from_record" not in loop_records_source


def test_compiler_sources_use_strategy_source_boundary_for_strategy_inputs() -> None:
    sources = loopora_sources(
        "strategy_source.py",
        "compiler/loop_compiler.py",
        "specs.py",
        "spec_markdown.py",
        "cli_spec_commands.py",
        "cli_spec_recovery.py",
        "web_spec_template_api_routes.py",
        "web_route_context_orchestration_pages.py",
    )
    loop_compiler_source = sources["compiler/loop_compiler.py"]
    specs_source = sources["specs.py"]

    assert "def normalize_strategy_role_display_name" in sources["strategy_source.py"]
    assert_contains(loop_compiler_source, "from loopora.strategy_source import", "strategy_source_from_record(record)")
    assert 'record.get("workflow_json")' not in loop_compiler_source
    assert "from loopora.spec_markdown import" in specs_source
    assert "from loopora.strategy_source import" in sources["spec_markdown.py"]
    assert_excludes(loop_compiler_source, "from loopora.workflows import", "_loopfile_strategy_workflow")
    assert "from loopora.workflows import" not in specs_source
    assert_contains(
        specs_source,
        "def render_spec_template_for_strategy_source",
        "def init_spec_file_for_strategy_source",
        "strategy_source: dict[str, Any] | None = None",
    )
    for command_source in [sources["cli_spec_commands.py"], sources["web_spec_template_api_routes.py"]]:
        assert_contains(command_source, "render_spec_template_for_strategy_source", "init_spec_file_for_strategy_source")
        assert "render_spec_template(locale=locale, workflow=" not in command_source
    assert_contains(sources["cli_spec_commands.py"], "from loopora.cli_spec_recovery import")
    assert_excludes(
        sources["cli_spec_commands.py"],
        "def exit_with_missing_spec_file_recovery",
        '"resource_recovery": "invalid_spec_file_input"',
    )
    assert_contains(
        sources["cli_spec_recovery.py"],
        "def exit_with_missing_spec_file_recovery",
        '"resource_recovery": "invalid_spec_file_input"',
        "copyable_loopora_command",
    )
    assert "render_spec_template_for_strategy_source" in sources["web_route_context_orchestration_pages.py"]
    assert_contains(loop_compiler_source, "_loopfile_strategy_source", 'strategy_source_payload = mapping(bundle.get("workflow"))')
    assert 'workflow = mapping(bundle.get("workflow"))' not in loop_compiler_source


def test_run_takeaway_projection_uses_strategy_snapshot_for_contract_trace_inputs() -> None:
    sources = loopora_sources(
        "service_bundle_control_trace_mining.py",
        "run_takeaways.py",
        "run_takeaway_common.py",
        "run_takeaway_evidence.py",
        "run_takeaway_iterations.py",
        "run_takeaway_judgment.py",
        "run_takeaway_legacy.py",
    )
    run_takeaways_source = sources["run_takeaways.py"]
    judgment_source = sources["run_takeaway_judgment.py"]

    assert "strategy_source: object = None" in sources["service_bundle_control_trace_mining.py"]
    assert "from loopora.service_bundle_control_trace_mining import" in judgment_source
    assert "service_bundle_control_summary" not in judgment_source
    assert 'strategy_snapshot = raw.get("workflow")' in judgment_source
    assert 'workflow = raw.get("workflow")' not in judgment_source
    assert "strategy_source=strategy_snapshot" in judgment_source
    assert "workflow=strategy_snapshot" not in judgment_source
    assert "from loopora.run_takeaway_common import" in run_takeaways_source
    assert "from loopora.run_takeaway_evidence import" in run_takeaways_source
    assert "from loopora.run_takeaway_iterations import" in run_takeaways_source
    assert "from loopora.run_takeaway_judgment import" in run_takeaways_source
    assert "from loopora.run_takeaway_legacy import build_legacy_iteration_takeaway" in run_takeaways_source
    assert_contains(sources["run_takeaway_common.py"], "def display_iter", "def clean_takeaway_text")
    assert_contains(sources["run_takeaway_evidence.py"], "def build_evidence_coverage", "def normalize_evidence_coverage_payload")
    assert_contains(
        sources["run_takeaway_iterations.py"],
        "def build_structured_iteration_takeaways",
        "def build_role_takeaway_from_handoff",
    )
    assert_contains(judgment_source, "def build_judgment_contract", "def normalize_judgment_contract_payload")
    assert "def build_legacy_iteration_takeaway" in sources["run_takeaway_legacy.py"]
    assert_excludes(
        run_takeaways_source,
        "def display_iter",
        "def build_evidence_coverage",
        "def build_structured_iteration_takeaways",
        "def build_judgment_contract",
        "def build_legacy_iteration_takeaway",
    )
    for source_name in [
        "agent_entry_run_projection.py",
        "agent_native_judgment_contract.py",
        "agent_native_task_proof.py",
        "cli_run_contract_output.py",
        "service_alignment_run_source_projection.py",
    ]:
        source = loopora_source(source_name)
        assert "from loopora.run_takeaway_judgment import build_judgment_contract" in source
        assert "from loopora.run_takeaways import build_judgment_contract" not in source
    web_overviews_source = loopora_source("web_overviews.py")
    assert "from loopora.run_takeaway_common import" in web_overviews_source
    assert "from loopora.run_takeaway_evidence import build_evidence_coverage" in web_overviews_source
