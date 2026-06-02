from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_residual_risk_support_uses_dedicated_marker_boundary() -> None:
    support_source = (REPO_ROOT / "src" / "loopora" / "residual_risk_support.py").read_text(encoding="utf-8")
    markers_source = (REPO_ROOT / "src" / "loopora" / "residual_risk_markers.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.residual_risk_markers import" in support_source
    for marker in (
        "NO_RESIDUAL_RISK_MARKERS",
        "VAGUE_RESIDUAL_RISK_MARKERS",
        "RESIDUAL_RISK_MANAGEMENT_MARKERS",
        "UNMANAGED_RESIDUAL_RISK_DETAIL_PATTERNS",
    ):
        assert marker in markers_source
        assert f"{marker} =" not in support_source
    for marker in (
        "def residual_risk_is_meaningful",
        "def residual_risk_is_managed",
        "def residual_risk_policy_disallows_acceptance",
    ):
        assert marker in support_source
        assert marker not in markers_source
    assert "residual_risk_markers.py" in contracts_source
    assert "residual_risk_support.py" in contracts_source
