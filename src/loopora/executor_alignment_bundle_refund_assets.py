from __future__ import annotations

from functools import lru_cache
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.executor_alignment_bundle_variant_assets import (
    alignment_bundle_variant_fixture,
    alignment_bundle_variant_fixtures_from_asset,
    apply_alignment_bundle_variant_fixture,
)

REFUND_BUNDLE_FIXTURES_ASSET_NAME = "refund-bundle-fixtures.yml"


def apply_alignment_refund_bundle_fixture(
    bundle: dict,
    *,
    locale: str,
    local_governance_sentence: str,
) -> None:
    fixture_key = "refund_repair_zh" if str(locale or "") == "zh" else "refund_repair_en"
    apply_alignment_bundle_variant_fixture(
        bundle,
        fixture=alignment_refund_bundle_fixture(
            fixture_key,
            context={"local_governance_sentence": local_governance_sentence},
        ),
    )


def alignment_refund_bundle_fixture(
    fixture_key: str,
    *,
    context: dict[str, str] | None = None,
) -> dict[str, Any]:
    return alignment_bundle_variant_fixture(
        _alignment_refund_bundle_fixtures_asset(),
        fixture_key=fixture_key,
        asset_name=REFUND_BUNDLE_FIXTURES_ASSET_NAME,
        context=context,
    )


@lru_cache
def _alignment_refund_bundle_fixtures_asset() -> dict[str, dict[str, Any]]:
    return alignment_bundle_variant_fixtures_from_asset(
        load_alignment_guidance_assets().refund_bundle_fixtures,
        asset_name=REFUND_BUNDLE_FIXTURES_ASSET_NAME,
    )
