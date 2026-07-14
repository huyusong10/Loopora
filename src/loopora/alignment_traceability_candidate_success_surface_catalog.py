from __future__ import annotations

"""Compatibility aggregate for Agent-candidate success-surface category catalogs."""

from loopora.alignment_traceability_candidate_success_surface_core_catalog import (
    SUCCESS_SURFACE_BASE_CATEGORY,
    SUCCESS_SURFACE_CORE_CATEGORY_PATTERNS,
    SUCCESS_SURFACE_MARKER_PATTERNS,
)

from loopora.alignment_traceability_candidate_success_surface_data_access_catalog import (
    SUCCESS_SURFACE_DATA_ACCESS_CATEGORY_PATTERNS,
)

from loopora.alignment_traceability_candidate_success_surface_delivery_catalog import (
    SUCCESS_SURFACE_DELIVERY_CATEGORY_PATTERNS,
)

from loopora.alignment_traceability_candidate_success_surface_operations_catalog import (
    SUCCESS_SURFACE_OPERATIONS_CATEGORY_PATTERNS,
)

from loopora.alignment_traceability_candidate_success_surface_trust_locale_catalog import (
    SUCCESS_SURFACE_TRUST_LOCALE_CATEGORY_PATTERNS,
)

SUCCESS_SURFACE_CATEGORY_PATTERNS = (
    *SUCCESS_SURFACE_CORE_CATEGORY_PATTERNS,
    *SUCCESS_SURFACE_DELIVERY_CATEGORY_PATTERNS,
    *SUCCESS_SURFACE_DATA_ACCESS_CATEGORY_PATTERNS,
    *SUCCESS_SURFACE_OPERATIONS_CATEGORY_PATTERNS,
    *SUCCESS_SURFACE_TRUST_LOCALE_CATEGORY_PATTERNS,
)

__all__ = (
    "SUCCESS_SURFACE_BASE_CATEGORY",
    "SUCCESS_SURFACE_CATEGORY_PATTERNS",
    "SUCCESS_SURFACE_MARKER_PATTERNS",
)
