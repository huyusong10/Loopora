from __future__ import annotations

from loopora.utils import structured_optional_finite_number


def structured_score_value(value: object) -> float | None:
    return structured_optional_finite_number(value)


def structured_score_values(value: object) -> list[float]:
    if not isinstance(value, list):
        return []
    return [score for item in value if (score := structured_score_value(item)) is not None]
