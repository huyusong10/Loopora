from __future__ import annotations

from pathlib import Path

from loopora import dev_check_default_fast
from loopora import dev_check_guide_agent_native
from loopora import dev_check_guide_alignment
from loopora import dev_check_guide_core_execution
from loopora import dev_check_guide_first_use
from loopora import dev_check_guide_open_source
from loopora import dev_check_guide_runtime
from loopora import dev_check_guide_types
from loopora import dev_check_guide_web
from loopora import dev_check_guides as dev_check_guides_catalog


ROOT = Path(__file__).resolve().parents[3]
DEV_CHECK_GUIDE_FAMILY_CATALOGS = (
    (
        "dev_check_guide_first_use.py",
        "FIRST_USE_READINESS_GUIDE",
        "first_use_readiness",
        dev_check_guide_first_use.FIRST_USE_READINESS_GUIDE,
    ),
    ("dev_check_guide_web.py", "WEB_SURFACES_GUIDE", "web_surfaces", dev_check_guide_web.WEB_SURFACES_GUIDE),
    ("dev_check_guide_agent_native.py", "AGENT_NATIVE_GUIDE", "agent_native", dev_check_guide_agent_native.AGENT_NATIVE_GUIDE),
    ("dev_check_guide_alignment.py", "ALIGNMENT_BUNDLE_GUIDE", "alignment_bundle", dev_check_guide_alignment.ALIGNMENT_BUNDLE_GUIDE),
    (
        "dev_check_guide_core_execution.py",
        "CORE_EXECUTION_GUIDE",
        "core_execution",
        dev_check_guide_core_execution.CORE_EXECUTION_GUIDE,
    ),
    ("dev_check_guide_runtime.py", "RUNTIME_STATE_GUIDE", "runtime_state", dev_check_guide_runtime.RUNTIME_STATE_GUIDE),
    (
        "dev_check_guide_open_source.py",
        "OPEN_SOURCE_COLLABORATION_GUIDE",
        "open_source_collaboration",
        dev_check_guide_open_source.OPEN_SOURCE_COLLABORATION_GUIDE,
    ),
)


def test_dev_check_guide_catalogs_have_dedicated_boundaries() -> None:
    aggregate_source = (ROOT / "src" / "loopora" / "dev_check_guides.py").read_text(encoding="utf-8")
    default_source = (ROOT / "src" / "loopora" / "dev_check_default_fast.py").read_text(encoding="utf-8")
    types_source = (ROOT / "src" / "loopora" / "dev_check_guide_types.py").read_text(encoding="utf-8")
    family_sources = {
        filename: (ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename, _constant_name, _guide_id, _guide in DEV_CHECK_GUIDE_FAMILY_CATALOGS
    }
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert dev_check_guides_catalog.DEFAULT_FAST_COMMANDS is dev_check_default_fast.DEFAULT_FAST_COMMANDS
    assert dev_check_guides_catalog.FocusedCheckGuide is dev_check_guide_types.FocusedCheckGuide
    assert tuple(guide for _filename, _constant_name, _guide_id, guide in DEV_CHECK_GUIDE_FAMILY_CATALOGS) == dev_check_guides_catalog.FOCUSED_CHECK_GUIDES
    for aggregate_guide, (_filename, _constant_name, _guide_id, family_guide) in zip(
        dev_check_guides_catalog.FOCUSED_CHECK_GUIDES,
        DEV_CHECK_GUIDE_FAMILY_CATALOGS,
        strict=True,
    ):
        assert aggregate_guide is family_guide
    assert "DEFAULT_FAST_COMMANDS = (" not in aggregate_source
    assert "FocusedCheckGuide(" not in aggregate_source
    assert "class FocusedCheckGuide" not in aggregate_source
    assert "uv sync --locked --dry-run" in default_source
    assert "class FocusedCheckGuide" in types_source
    for filename, constant_name, guide_id, _guide in DEV_CHECK_GUIDE_FAMILY_CATALOGS:
        module_name = filename.removesuffix(".py")
        assert f"from loopora.{module_name} import {constant_name}" in aggregate_source
        assert constant_name in aggregate_source
        assert guide_id in family_sources[filename]
        assert "FocusedCheckGuide(" in family_sources[filename]
        assert filename in service_boundaries
    assert "dev_check_guides.py" in service_boundaries
    assert "dev_check_default_fast.py" in service_boundaries
    assert "dev_check_guide_types.py" in service_boundaries
    assert "dev_check_guide*.py" in contracts


def test_dev_check_agent_candidate_sources_route_to_native_and_alignment_guides() -> None:
    candidate_patterns = {
        "src/loopora/service_agent_bundle_candidate*.py",
        "src/loopora/service_agent_bundle_candidates.py",
    }

    assert candidate_patterns <= set(dev_check_guide_agent_native.AGENT_NATIVE_GUIDE.path_patterns)
    assert candidate_patterns <= set(dev_check_guide_alignment.ALIGNMENT_BUNDLE_GUIDE.path_patterns)


def test_dev_check_alignment_prompt_assets_route_to_alignment_guide() -> None:
    assert "src/loopora/assets/system_prompts/alignment/" in dev_check_guide_alignment.ALIGNMENT_BUNDLE_GUIDE.path_patterns


def test_package_source_provenance_routes_to_open_source_guide() -> None:
    guide = dev_check_guide_open_source.OPEN_SOURCE_COLLABORATION_GUIDE

    assert "tests/checks/contracts/test_package_metadata.py" in guide.command
    assert {
        "setup.py",
        "src/loopora/package_source_provenance.py",
    } <= set(guide.path_patterns)


def test_provider_stop_race_evidence_routes_to_core_execution_guide() -> None:
    guide = dev_check_guide_core_execution.CORE_EXECUTION_GUIDE

    assert "tests/checks/contracts/test_executor_codex_output_contract.py" in guide.command
    assert "tests/checks/contracts/test_real_executor_architecture.py" in guide.command
    assert "tests/checks/contracts/test_real_executor_architecture.py" in guide.path_patterns


def test_private_recovery_archive_routes_to_first_use_guide() -> None:
    guide = dev_check_guide_first_use.FIRST_USE_READINESS_GUIDE

    assert "tests/checks/contracts/test_cli_dev_reset.py" in guide.command
    assert {
        "src/loopora/cli_recovery_commands.py",
        "src/loopora/recovery_archive.py",
        "src/loopora/recovery_restore.py",
    } <= set(guide.path_patterns)


def test_local_web_service_identity_routes_to_owning_focused_guides() -> None:
    shared_patterns = {"src/loopora/local_web_service.py", "src/loopora/web_service_probe.py"}

    assert shared_patterns <= set(dev_check_guide_first_use.FIRST_USE_READINESS_GUIDE.path_patterns)
    assert shared_patterns <= set(dev_check_guide_web.WEB_SURFACES_GUIDE.path_patterns)
    assert "src/loopora/agent_web.py" in dev_check_guide_agent_native.AGENT_NATIVE_GUIDE.path_patterns
    assert "tests/checks/contracts/test_cli_background_worker_runtime.py" in dev_check_guide_first_use.FIRST_USE_READINESS_GUIDE.command
    assert "tests/checks/contracts/test_agent_adapter_web_api.py" in dev_check_guide_agent_native.AGENT_NATIVE_GUIDE.command


def test_dev_check_next_action_text_has_dedicated_presenter_boundary() -> None:
    next_action_source = (ROOT / "src" / "loopora" / "cli_dev_next_action_text.py").read_text(encoding="utf-8")
    pr_evidence_source = (ROOT / "src" / "loopora" / "cli_dev_pr_evidence.py").read_text(encoding="utf-8")
    output_source = (ROOT / "src" / "loopora" / "cli_dev_check_output.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    guide_source = (ROOT / "src" / "loopora" / "dev_check_guide_open_source.py").read_text(encoding="utf-8")

    assert "from loopora.cli_dev_next_action_text import" in pr_evidence_source
    assert "from loopora.cli_dev_next_action_text import" in output_source
    assert "def dev_check_next_action_text" not in pr_evidence_source
    assert "def dev_check_file_list_summary" not in pr_evidence_source
    assert "def dev_check_next_action_text" in next_action_source
    assert "def dev_check_file_list_summary" in next_action_source
    assert "def dev_check_guide_suffix" in next_action_source
    assert "cli_dev_next_action_text.py" in service_boundaries
    assert "cli_dev_next_action_text.py" in contracts
    assert "src/loopora/cli_dev*.py" in guide_source


def test_start_and_fit_share_first_use_route_terminal_status_projection() -> None:
    root = Path(__file__).resolve().parents[3]
    shared_source = (root / "src" / "loopora" / "first_use_route_terminal.py").read_text(encoding="utf-8")
    start_source = (root / "src" / "loopora" / "start_guidance_route_output.py").read_text(encoding="utf-8")
    fit_source = (root / "src" / "loopora" / "cli_fit_route_output.py").read_text(encoding="utf-8")
    guide_source = (root / "src" / "loopora" / "dev_check_guide_first_use.py").read_text(encoding="utf-8")
    service_boundaries = (root / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    for source in (start_source, fit_source):
        assert "from loopora.first_use_route_terminal import" in source
        assert "first_use_route_action_status_lines" in source
        assert "first_use_route_preview_status_line" in source

    for marker in (
        "def _route_status_label",
        "def _route_blocker_status_label",
        "def _route_preview_blocker_label",
        "def _fit_route_status_label",
        "def _fit_route_blocker_status_label",
        "def _fit_route_preview_blocker_label",
    ):
        assert marker not in start_source
        assert marker not in fit_source

    for marker in (
        "Fit Guide/Web choices",
        "same-Agent setup choice",
        "doctor readiness check",
        "copyable /loopora-plan task message",
        "completed fit review",
        "direct-path decision",
    ):
        assert marker in shared_source

    assert "src/loopora/first_use_route_terminal.py" in guide_source
    assert "first_use_route_terminal.py` owns shared Start/Fit plain route ready/blocked" in service_boundaries
    assert "first_use_route_terminal.py" in contracts
