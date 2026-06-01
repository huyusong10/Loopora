from __future__ import annotations

import math


def structured_non_negative_int(value: object, *, default: int = 0) -> int:
    """Return a non-negative JSON integer, rejecting bools and coerced strings."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    return default


def structured_optional_non_negative_int(value: object) -> int | None:
    """Return a non-negative JSON integer or None when the value must fail closed."""
    normalized = structured_non_negative_int(value, default=-1)
    return normalized if normalized >= 0 else None


def coerced_int(value: object, *, default: int = 0) -> int:
    """Return an integer from legacy/event payload values, rejecting bools."""
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerced_non_negative_int(
    value: object,
    *,
    default: int = 0,
    strict: bool = False,
    field_name: str = "value",
) -> int:
    """Return a non-negative legacy integer, optionally failing closed on invalid values."""
    if isinstance(value, bool):
        if strict:
            raise ValueError(f"{field_name} must be a non-negative integer")
        return default
    if value in (None, ""):
        return default
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        if strict:
            raise ValueError(f"{field_name} must be a non-negative integer") from exc
        return default
    if integer < 0:
        if strict:
            raise ValueError(f"{field_name} must be a non-negative integer")
        return default
    return integer


def coerced_optional_non_negative_int(value: object) -> int | None:
    """Return a non-negative legacy integer or None when the value must fail closed."""
    normalized = coerced_non_negative_int(value, default=-1)
    return normalized if normalized >= 0 else None


def structured_finite_number(value: object, *, default: float = 0.0) -> float:
    """Return a finite JSON number, rejecting bools and coerced strings."""
    normalized = structured_optional_finite_number(value)
    return default if normalized is None else normalized


def structured_optional_finite_number(value: object) -> float | None:
    """Return a finite JSON number or None when the value must fail closed."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None
