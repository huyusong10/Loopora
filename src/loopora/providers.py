from __future__ import annotations

from loopora.provider_profiles import (
    CLAUDE_DEFAULT_MODEL as CLAUDE_DEFAULT_MODEL,
    EXECUTOR_KIND_ALIASES as EXECUTOR_KIND_ALIASES,
    EXECUTOR_KINDS as EXECUTOR_KINDS,
    EXECUTOR_MODES as EXECUTOR_MODES,
    EXECUTOR_PROFILES as EXECUTOR_PROFILES,
    OPENCODE_DEFAULT_MODEL as OPENCODE_DEFAULT_MODEL,
    ExecutorProfile as ExecutorProfile,
)

_CODEX_ALIASES = {"minimal": "low"}
_CLAUDE_ALIASES = {"minimal": "low", "xhigh": "max"}
_OPENCODE_BLANK_ALIASES = {"auto", "default"}


def _normalize_bounded_reasoning_setting(raw: str, *, profile: ExecutorProfile, aliases: dict[str, str], label: str) -> str:
    if not raw or raw in _OPENCODE_BLANK_ALIASES:
        return profile.effort_default
    normalized = aliases.get(raw, raw)
    if normalized not in profile.effort_options:
        supported = ", ".join(profile.effort_options)
        raise ValueError(f"unsupported reasoning effort for {label}: {raw!r}. Expected one of: {supported}")
    return normalized


def normalize_executor_kind(value: str | None) -> str:
    normalized = (value or "codex").strip().lower()
    if normalized in EXECUTOR_KIND_ALIASES:
        return EXECUTOR_KIND_ALIASES[normalized]
    supported = ", ".join(EXECUTOR_KINDS)
    raise ValueError(f"unsupported executor kind: {value!r}. Expected one of: {supported}")


def executor_profile(kind: str | None) -> ExecutorProfile:
    normalized = normalize_executor_kind(kind)
    return EXECUTOR_PROFILES[normalized]


def list_executor_profiles() -> list[dict[str, object]]:
    return [EXECUTOR_PROFILES[key].to_dict() for key in EXECUTOR_KINDS]


def normalize_executor_mode(value: str | None) -> str:
    normalized = (value or "preset").strip().lower()
    if normalized in EXECUTOR_MODES:
        return normalized
    supported = ", ".join(EXECUTOR_MODES)
    raise ValueError(f"unsupported executor mode: {value!r}. Expected one of: {supported}")


def normalize_reasoning_setting(value: str | None, *, executor_kind: str) -> str:
    profile = executor_profile(executor_kind)
    raw = (value or "").strip().lower()
    if profile.key == "codex":
        return _normalize_bounded_reasoning_setting(raw, profile=profile, aliases=_CODEX_ALIASES, label="Codex")
    if profile.key == "claude":
        return _normalize_bounded_reasoning_setting(raw, profile=profile, aliases=_CLAUDE_ALIASES, label="Claude Code")
    if profile.key == "custom":
        if not raw or raw in _OPENCODE_BLANK_ALIASES:
            return ""
        return raw
    if not raw or raw in _OPENCODE_BLANK_ALIASES:
        return ""
    return raw


def coerce_reasoning_setting(value: str | None, *, executor_kind: str) -> str:
    profile = executor_profile(executor_kind)
    try:
        return normalize_reasoning_setting(value, executor_kind=executor_kind)
    except ValueError:
        return profile.effort_default
