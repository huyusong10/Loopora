from __future__ import annotations

import pytest

from locale_detection_test_support import NODE, run_role_translation_case

pytestmark = pytest.mark.skipif(NODE is None, reason="node is required for locale detection tests")


def test_role_translation_accepts_current_chinese_archetype_labels() -> None:
    assert run_role_translation_case() == {
        "builder": "构建者",
        "gatekeeper": "守门者",
        "guide": "引导者",
        "custom": "自定义角色",
    }
