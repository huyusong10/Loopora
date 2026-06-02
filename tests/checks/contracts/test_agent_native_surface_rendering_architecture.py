from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_agent_native_surface_plain_lines_have_dedicated_boundary() -> None:
    surface_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface.py").read_text(encoding="utf-8")
    lines_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface_lines.py").read_text(encoding="utf-8")
    helper_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface_line_helpers.py").read_text(
        encoding="utf-8"
    )
    section_source = (REPO_ROOT / "src" / "loopora" / "agent_native_surface_section_lines.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.agent_native_surface_lines import native_surface_plain_lines" in surface_source
    assert "from loopora.agent_native_surface_line_helpers import" in lines_source
    assert "from loopora.agent_native_surface_section_lines import" in lines_source
    for marker in (
        "def native_surface_plain_lines",
        "def _native_surface_capability_lines",
    ):
        assert marker in lines_source
        assert marker not in surface_source
    for marker in (
        "def _native_surface_kv_line",
        "def _native_surface_target_agents",
        "def _native_surface_role_config_refs",
    ):
        assert marker in helper_source
        assert marker not in lines_source
    for marker in (
        "def _native_surface_packaging_lines",
        "def _native_surface_permission_boundary_lines",
        "def _native_surface_ownership_lines",
    ):
        assert marker in section_source
        assert marker not in lines_source
    for marker in (
        "def attach_native_run_surface",
        "def agent_native_run_surface_for_result",
        "def _surface_adapter_from_sources",
    ):
        assert marker in surface_source
        assert marker not in lines_source
    assert "agent_native_surface_lines.py" in design_source
    assert "agent_native_surface_line_helpers.py" in design_source
    assert "agent_native_surface_section_lines.py" in design_source
