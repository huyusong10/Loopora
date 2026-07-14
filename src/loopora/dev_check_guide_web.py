from __future__ import annotations

from loopora.dev_check_guide_types import FocusedCheckGuide


WEB_SURFACES_GUIDE = FocusedCheckGuide(
    id="web_surfaces",
    label="Web routes, templates, and static assets",
    when="Rendered Web behavior, diagnostics APIs, browser state, templates, or static assets changed.",
    command="uv run pytest -q tests/checks/contracts/test_web_local_asset_diagnostics.py "
    "tests/checks/contracts/test_system_dialogs.py "
    "tests/checks/contracts/test_web_loop_compacted_01.py "
    "tests/checks/contracts/test_web_overview_projection.py "
    "tests/checks/contracts/test_web_run_lifecycle_api.py "
    "tests/checks/contracts/test_web_run_rerun_api.py "
    "tests/checks/journeys",
    evidence_type="journey",
    path_patterns=(
        "src/loopora/action_readiness_projection.py",
        "src/loopora/db_loop_records.py",
        "src/loopora/app_state_readiness.py",
        "src/loopora/first_use_web_guidance.py",
        "src/loopora/existing_work_status.py",
        "src/loopora/local_web_service.py",
        "src/loopora/web_service_probe.py",
        "src/loopora/loop_compose_validation.py",
        "src/loopora/web.py",
        "src/loopora/static/",
        "src/loopora/templates/",
        "src/loopora/system_dialogs.py",
        "src/loopora/token_security.py",
        "src/loopora/spec_recovery_commands.py",
        "src/loopora/workdir_inputs.py",
        "src/loopora/web_*.py",
        "src/loopora/web_route*.py",
        "src/loopora/templates/",
        "tests/checks/journeys/",
        "tests/checks/contracts/test_system_dialogs.py",
        "tests/checks/contracts/test_cli_background_worker_runtime.py",
        "tests/checks/contracts/test_web*",
        "tests/checks/contracts/web_*",
    ),
)


__all__ = ("WEB_SURFACES_GUIDE",)
