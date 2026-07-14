from __future__ import annotations

"""Compatibility aggregate for CJK domain traceability terms."""

from loopora.alignment_traceability_cjk_domain_terms_commerce import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_COMMERCE_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_core_trust import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_CORE_TRUST_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_data_platform import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_DATA_PLATFORM_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_governance import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_GOVERNANCE_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_operations import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_OPERATIONS_TERMS,
)
from loopora.alignment_traceability_cjk_domain_terms_workflow import (
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_WORKFLOW_TERMS,
)

ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS = (
    *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_CORE_TRUST_TERMS,
    *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_COMMERCE_TERMS,
    *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_DATA_PLATFORM_TERMS,
    *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_WORKFLOW_TERMS,
    *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_GOVERNANCE_TERMS,
    *ALIGNMENT_TRACEABILITY_CJK_DOMAIN_OPERATIONS_TERMS,
)

__all__ = ("ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS",)
