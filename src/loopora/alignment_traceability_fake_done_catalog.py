from __future__ import annotations

"""Compatibility aggregate for fake-done category catalog entries."""

from loopora.alignment_traceability_fake_done_core_catalog import (
    FAKE_DONE_CORE_CATEGORY_PATTERNS,
)
from loopora.alignment_traceability_fake_done_data_access_catalog import (
    FAKE_DONE_DATA_ACCESS_CATEGORY_PATTERNS,
)
from loopora.alignment_traceability_fake_done_delivery_catalog import (
    FAKE_DONE_DELIVERY_CATEGORY_PATTERNS,
)
from loopora.alignment_traceability_fake_done_operations_catalog import (
    FAKE_DONE_OPERATIONS_CATEGORY_PATTERNS,
)
from loopora.alignment_traceability_fake_done_surface_catalog import (
    FAKE_DONE_SURFACE_CATEGORY_PATTERNS,
)

FAKE_DONE_CATEGORY_PATTERNS = (
    *FAKE_DONE_CORE_CATEGORY_PATTERNS,
    *FAKE_DONE_DELIVERY_CATEGORY_PATTERNS,
    *FAKE_DONE_DATA_ACCESS_CATEGORY_PATTERNS,
    *FAKE_DONE_OPERATIONS_CATEGORY_PATTERNS,
    *FAKE_DONE_SURFACE_CATEGORY_PATTERNS,
)

__all__ = ("FAKE_DONE_CATEGORY_PATTERNS",)
