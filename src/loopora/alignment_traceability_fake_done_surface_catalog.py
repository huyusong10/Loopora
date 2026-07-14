from __future__ import annotations

"""Fake-done catalog entries for surface-only and locale/accessibility proof gaps."""

from loopora.alignment_traceability_domain_patterns import (
    ACCESSIBILITY_A11Y_PATTERN,
    LOCALE_I18N_PATTERN,
)

FAKE_DONE_SURFACE_CATEGORY_PATTERNS = (
    (
        "visual/polish/screenshot-only",
        r"\b(?:screenshot|visual|polish|pretty|polished-looking)\b|截图|视觉|美化|漂亮",
        r"\b(?:screenshot|visual|polish|pretty|polished-looking)\b|截图|视觉|美化|漂亮",
    ),
    (
        "claim/narrative-only",
        r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
        r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
    ),
    (
        "happy-path-only",
        r"\bhappy[- ]?path\b|主路径|快乐路径",
        r"\bhappy[- ]?path\b|主路径|快乐路径",
    ),
    (
        "mock/static/stub-only",
        r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
        r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
    ),
    (
        "accessibility/a11y",
        ACCESSIBILITY_A11Y_PATTERN,
        ACCESSIBILITY_A11Y_PATTERN,
    ),
    (
        "locale/i18n",
        LOCALE_I18N_PATTERN,
        LOCALE_I18N_PATTERN,
    ),
)

__all__ = ("FAKE_DONE_SURFACE_CATEGORY_PATTERNS",)
