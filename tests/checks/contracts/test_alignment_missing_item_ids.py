from __future__ import annotations

from loopora.service_alignment_decision_options import normalize_alignment_missing_items
from loopora.service_alignment_requests import ALIGNMENT_MISSING_ITEM_IDS


def test_alignment_missing_items_are_stable_ids_only() -> None:
    missing = normalize_alignment_missing_items(
        [
            "success_surface",
            "success_surface",
            "role_posture",
            "raw model prose should not become a chip",
            {"bad": "shape"},
        ],
        allowed_item_ids=ALIGNMENT_MISSING_ITEM_IDS,
    )

    assert missing == ["success_surface", "role_posture"]
