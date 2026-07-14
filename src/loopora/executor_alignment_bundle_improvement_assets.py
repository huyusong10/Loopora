from __future__ import annotations

from functools import lru_cache
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.executor_alignment_bundle_variant_assets import (
    alignment_bundle_variant_fixture,
    alignment_bundle_variant_fixtures_from_asset,
    apply_alignment_bundle_variant_fixture,
)

IMPROVEMENT_BUNDLE_FIXTURES_ASSET_NAME = "improvement-bundle-fixtures.yml"


def apply_alignment_improvement_bundle_fixture(bundle: dict, *, fixture_key: str) -> None:
    apply_alignment_bundle_variant_fixture(
        bundle,
        fixture=alignment_improvement_bundle_fixture(fixture_key),
    )


def alignment_improvement_bundle_fixture(fixture_key: str) -> dict[str, Any]:
    return alignment_bundle_variant_fixture(
        _alignment_improvement_bundle_fixtures_asset(),
        fixture_key=fixture_key,
        asset_name=IMPROVEMENT_BUNDLE_FIXTURES_ASSET_NAME,
    )


@lru_cache
def _alignment_improvement_bundle_fixtures_asset() -> dict[str, dict[str, Any]]:
    return alignment_bundle_variant_fixtures_from_asset(
        load_alignment_guidance_assets().improvement_bundle_fixtures,
        asset_name=IMPROVEMENT_BUNDLE_FIXTURES_ASSET_NAME,
    )
