from __future__ import annotations

from loopora.providers import normalize_executor_kind, normalize_executor_mode, normalize_reasoning_setting
from loopora.providers import executor_profile


def test_executor_kind_aliases_normalize() -> None:
    assert normalize_executor_kind("codex") == "codex"
    assert normalize_executor_kind("claudecode") == "claude"
    assert normalize_executor_kind("open-code") == "opencode"
    assert normalize_executor_kind("custom") == "custom"


def test_executor_mode_normalizes() -> None:
    assert normalize_executor_mode("preset") == "preset"
    assert normalize_executor_mode("command") == "command"


def test_reasoning_setting_is_provider_specific() -> None:
    assert normalize_reasoning_setting("", executor_kind="codex") == ""
    assert normalize_reasoning_setting("default", executor_kind="codex") == ""
    assert normalize_reasoning_setting("minimal", executor_kind="codex") == "low"
    assert normalize_reasoning_setting("", executor_kind="claude") == ""
    assert normalize_reasoning_setting("default", executor_kind="claude") == ""
    assert normalize_reasoning_setting("xhigh", executor_kind="claude") == "max"
    assert normalize_reasoning_setting("", executor_kind="opencode") == ""
    assert normalize_reasoning_setting("default", executor_kind="opencode") == ""
    assert normalize_reasoning_setting("default", executor_kind="custom") == ""
    assert executor_profile("opencode").preset_effort_visible is True
    assert executor_profile("custom").command_only is True
