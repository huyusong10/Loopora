from __future__ import annotations

from loopora.run_takeaways import normalize_run_takeaway_projection_shape


def test_takeaway_judgment_contract_preserves_inherited_run_id_after_normalization() -> None:
    projection = normalize_run_takeaway_projection_shape(
        {"id": "run_next", "status": "awaiting_agent"},
        {
            "judgment_contract": {
                "goal": "Continue from the prior evidence gap.",
                "inherited_from_run_id": "run_previous",
            },
        },
    )

    assert projection["judgment_contract"]["inherited_from_run_id"] == "run_previous"
