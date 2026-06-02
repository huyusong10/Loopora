from __future__ import annotations

from pathlib import Path


def test_provider_profile_catalog_has_dedicated_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    providers_source = (repo_root / "src" / "loopora" / "providers.py").read_text(encoding="utf-8")
    profile_source = (repo_root / "src" / "loopora" / "provider_profiles.py").read_text(encoding="utf-8")
    contracts_source = (repo_root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.provider_profiles import" in providers_source
    assert "EXECUTOR_PROFILES: dict[str, ExecutorProfile]" in profile_source
    assert "EXECUTOR_PROFILES: dict[str, ExecutorProfile]" not in providers_source
    assert "ExecutorProfile(" in profile_source
    assert "ExecutorProfile(" not in providers_source
    assert "provider_profiles.py" in contracts_source
