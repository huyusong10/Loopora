from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_context_factory_delegates_executor_context_wiring() -> None:
    factory_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_context_factory.py").read_text(
        encoding="utf-8"
    )
    executor_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_executor_context.py").read_text(
        encoding="utf-8"
    )
    protocols_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_context_protocols.py").read_text(
        encoding="utf-8"
    )
    resolution_factory_source = (
        REPO_ROOT / "src" / "loopora" / "service_alignment_context_resolution_factory.py"
    ).read_text(encoding="utf-8")
    session_layout_context_source = (
        REPO_ROOT / "src" / "loopora" / "service_alignment_session_layout_context.py"
    ).read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_alignment_context_protocols import AlignmentFactoryService" in factory_source
    assert "from loopora.service_alignment_context_resolution_factory import" in factory_source
    assert "from loopora.service_alignment_executor_context import alignment_executor_run_context" in factory_source
    assert "from loopora.service_alignment_orchestration_context import alignment_session_orchestration_context" in factory_source
    assert "from loopora.service_alignment_session_layout_context import" in factory_source
    assert "return build_alignment_run_context_resolver_context(self.service)" in factory_source
    assert "return build_alignment_workdir_context_resolver_context(self.service)" in factory_source
    assert "return build_alignment_loopora_context_resolver_context(self.service)" in factory_source
    assert "return alignment_executor_run_context(self.service)" in factory_source
    assert "return alignment_session_orchestration_context(self.service, self)" in factory_source
    assert "return ensure_alignment_session_layout_from_service(self.service, self.logger, session)" in factory_source
    assert "class AlignmentFactoryService" in protocols_source
    assert "def ensure_alignment_session_layout_from_service" in session_layout_context_source
    for marker in (
        "AlignmentLegacyLayoutContext",
        "append_alignment_diagnostic_event",
        "append_alignment_local_diagnostic_event",
        "ensure_alignment_artifact_dirs",
    ):
        assert marker in session_layout_context_source
    for marker in (
        "from loopora.service_alignment_diagnostics import",
        "AlignmentLegacyLayoutContext",
    ):
        assert marker not in factory_source
    for marker in ("AlignmentExecutorInvocationConfig", "def build_prompt", "ALIGNMENT_RESPONSE_SCHEMA"):
        assert marker in executor_source
        assert marker not in factory_source
    for marker in ("run_alignment_executor_command", "AlignmentOutputStageRequest", "AlignmentAssistantMessageEffect"):
        assert marker not in factory_source
    for marker in (
        "def alignment_run_context_resolver_context",
        "def alignment_workdir_context_resolver_context",
        "def alignment_loopora_context_resolver_context",
        "resolve_alignment_run_context",
    ):
        assert marker in resolution_factory_source
    for marker in ("def workdir_context_payload", "resolve_plan_context_from_workdir_context"):
        assert marker in resolution_factory_source
        assert marker not in factory_source
    assert "service_alignment_context_protocols.py" in design_source
    assert "service_alignment_context_resolution_factory.py" in design_source
    assert "service_alignment_executor_context.py" in design_source
    assert "service_alignment_orchestration_context.py" in design_source
    assert "service_alignment_session_layout_context.py" in design_source


def test_alignment_orphan_recovery_has_dedicated_boundary() -> None:
    alignment_source = (REPO_ROOT / "src" / "loopora" / "service_alignment.py").read_text(encoding="utf-8")
    recovery_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_recovery.py").read_text(encoding="utf-8")
    app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_alignment_recovery import" in alignment_source
    assert "def reconcile_orphaned_alignment_sessions" in recovery_source
    assert "def _alignment_session_is_orphaned" in recovery_source
    assert "self.reconcile_orphaned_alignment_sessions()" in app_source
    assert "service_alignment_recovery.py" in design_source
