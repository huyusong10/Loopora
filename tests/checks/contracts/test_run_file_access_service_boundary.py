from __future__ import annotations

from strategy_source_architecture_test_support import design_boundary_source

from web_file_access_test_support import REPO_ROOT


def test_run_file_access_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    file_access_source = (REPO_ROOT / "src" / "loopora" / "service_run_file_access.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_run_file_access import ServiceRunFileAccessMixin" in lifecycle_source
    assert "def preview_file" not in lifecycle_source
    assert "def download_file_path" in file_access_source
    assert "requested path must be relative" in file_access_source
    assert "requested path is outside the allowed root" in file_access_source
    assert "run workdir is not available" in file_access_source
    assert "service_run_file_access.py" in design_source
