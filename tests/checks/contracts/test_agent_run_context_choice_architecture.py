from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_agent_run_context_choice_projection_has_dedicated_boundary() -> None:
    recovery_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_run_recovery.py").read_text(
        encoding="utf-8"
    )
    choices_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_run_context_choices.py").read_text(
        encoding="utf-8"
    )
    recovery_fields_source = (
        REPO_ROOT / "src" / "loopora" / "service_alignment_run_context_recovery_fields.py"
    ).read_text(encoding="utf-8")
    resolver_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_run_context.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_alignment_run_context_choices import" in recovery_source
    assert "from loopora.service_alignment_run_context_choices import" in resolver_source
    assert "from loopora.service_alignment_run_context_recovery_fields import" in recovery_source
    assert "from loopora.service_alignment_run_context_recovery_fields import" in resolver_source
    for marker in (
        "def agent_run_context_choice_summary",
        "def agent_run_context_next_action",
        "def agent_run_context_choice_payload",
    ):
        assert marker in choices_source
        assert marker not in recovery_source
    for marker in (
        "def agent_exact_binding_recovery_action",
        "def agent_failed_preview_choice_repair_fields",
        "def agent_redacted_context_binding",
    ):
        assert marker in recovery_fields_source
        assert marker not in choices_source
        assert marker not in recovery_source
    assert "AGENT_CONTEXT_BINDING_RECOVERY_KEYS = {" in recovery_fields_source
    assert "AGENT_CONTEXT_BINDING_RECOVERY_KEYS = {" not in choices_source
    assert "service_alignment_run_context_choices.py" in design_source
    assert "service_alignment_run_context_recovery_fields.py" in design_source
