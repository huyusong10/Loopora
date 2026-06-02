from __future__ import annotations

import pytest

from locale_detection_test_support import NODE, LocaleCase, run_locale_case

pytestmark = pytest.mark.skipif(NODE is None, reason="node is required for locale detection tests")


def test_saved_locale_overrides_environment_detection() -> None:
    result = run_locale_case(
        LocaleCase(
            saved="en",
            languages=["zh-CN"],
            language="zh-CN",
            system_language="zh-CN",
            intl_locale="zh-CN",
        )
    )

    assert result["preferred"] == "en"
    assert result["stored"] == "en"
    assert result["htmlLang"] == "en"


def test_system_chinese_defaults_to_chinese_even_if_browser_language_is_english() -> None:
    result = run_locale_case(
        LocaleCase(
            languages=["en-US"],
            language="en-US",
            system_language="zh-CN",
            intl_locale="zh-CN",
        )
    )

    assert result["preferred"] == "zh"
    assert result["stored"] is None
    assert result["htmlLang"] == "zh-CN"


def test_primary_browser_chinese_defaults_to_chinese() -> None:
    result = run_locale_case(
        LocaleCase(
            languages=["zh-CN", "en-US"],
            language="zh-CN",
            intl_locale="en-US",
        )
    )

    assert result["preferred"] == "zh"
    assert result["stored"] is None


def test_secondary_browser_chinese_does_not_override_english_default() -> None:
    result = run_locale_case(
        LocaleCase(
            languages=["en-US", "zh-CN"],
            language="en-US",
            browser_language="en-US",
            intl_locale="en-US",
        )
    )

    assert result["preferred"] == "en"
    assert result["stored"] is None
