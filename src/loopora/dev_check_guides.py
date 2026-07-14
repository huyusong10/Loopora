from __future__ import annotations

"""Compatibility aggregate for dev-check verification catalogs."""

from loopora.dev_check_default_fast import DEFAULT_FAST_COMMANDS
from loopora.dev_check_guide_first_use import FIRST_USE_READINESS_GUIDE
from loopora.dev_check_guide_web import WEB_SURFACES_GUIDE
from loopora.dev_check_guide_agent_native import AGENT_NATIVE_GUIDE
from loopora.dev_check_guide_alignment import ALIGNMENT_BUNDLE_GUIDE
from loopora.dev_check_guide_core_execution import CORE_EXECUTION_GUIDE
from loopora.dev_check_guide_runtime import RUNTIME_STATE_GUIDE
from loopora.dev_check_guide_open_source import OPEN_SOURCE_COLLABORATION_GUIDE
from loopora.dev_check_guide_types import FocusedCheckGuide


FOCUSED_CHECK_GUIDES = (
    FIRST_USE_READINESS_GUIDE,
    WEB_SURFACES_GUIDE,
    AGENT_NATIVE_GUIDE,
    ALIGNMENT_BUNDLE_GUIDE,
    CORE_EXECUTION_GUIDE,
    RUNTIME_STATE_GUIDE,
    OPEN_SOURCE_COLLABORATION_GUIDE,
)


__all__ = (
    "AGENT_NATIVE_GUIDE",
    "ALIGNMENT_BUNDLE_GUIDE",
    "CORE_EXECUTION_GUIDE",
    "DEFAULT_FAST_COMMANDS",
    "FIRST_USE_READINESS_GUIDE",
    "FOCUSED_CHECK_GUIDES",
    "OPEN_SOURCE_COLLABORATION_GUIDE",
    "RUNTIME_STATE_GUIDE",
    "WEB_SURFACES_GUIDE",
    "FocusedCheckGuide",
)
