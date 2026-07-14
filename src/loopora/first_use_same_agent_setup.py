from __future__ import annotations

from collections.abc import Mapping

from loopora.agent_adapter_check_utils import adapter_label
from loopora.agent_adapter_command_prefix import rewrite_loopora_command_entry
from loopora.agent_adapter_current_host import current_agent_host_detection
from loopora.agent_native_adapter_identity import AGENT_ADAPTER_KINDS
from loopora.cli_agent_adapter_language import localized_agent_entry_command


def first_use_current_agent_host(detection: Mapping[str, object] | None = None) -> dict[str, object]:
    return dict(detection) if detection is not None else current_agent_host_detection()


def first_use_same_agent_setup_action(
    *,
    workdir_arg: str,
    language: str,
    cli_entry: str,
    current_agent_host: Mapping[str, object] | None = None,
) -> dict[str, object]:
    detection = first_use_current_agent_host(current_agent_host)
    selection_required = detection.get("selection_required") is True
    current_command = localized_agent_entry_command(
        rewrite_loopora_command_entry(f"loopora init current --workdir {workdir_arg}", cli_entry=cli_entry),
        language=language,
    )
    action: dict[str, object] = {
        "kind": "install_agent_entry",
        "selection_required": selection_required,
        "adapter_fallback_available": selection_required,
        "current_agent_host": detection,
        "note": _same_agent_setup_note(detection, language=language),
        "adapter_choices": [
            {
                "adapter": adapter,
                "command": localized_agent_entry_command(
                    rewrite_loopora_command_entry(
                        f"loopora init {adapter} --workdir {workdir_arg}",
                        cli_entry=cli_entry,
                    ),
                    language=language,
                ),
                "fallback_only": True,
                "fallback_applicable": selection_required,
                "detected_current_host": adapter == str(detection.get("adapter") or ""),
            }
            for adapter in AGENT_ADAPTER_KINDS
        ],
    }
    if detection.get("command_ready") is True:
        action["command"] = current_command
    return action


def _same_agent_setup_note(detection: Mapping[str, object], *, language: str) -> str:
    state = str(detection.get("state") or "unavailable")
    if state == "detected":
        label = adapter_label(str(detection.get("adapter") or ""))
        return (
            f"已检测到当前宿主 {label}；先用 init current 设置或验证该入口。"
            if language == "zh"
            else f"Detected {label} as the current host; set up or verify it with init current first."
        )
    if state == "ambiguous":
        labels = ", ".join(adapter_label(str(item)) for item in list(detection.get("detected_adapters") or []))
        return (
            f"检测到多个当前宿主（{labels}）；请明确选择正在使用的 adapter。"
            if language == "zh"
            else f"Multiple current hosts were detected ({labels}); choose the adapter you are using."
        )
    return (
        "未检测到当前 Agent 宿主；只有已经在该宿主会话中时，才明确选择对应 adapter。"
        if language == "zh"
        else "No current Agent host was detected; choose an explicit adapter only when already inside that host session."
    )


__all__ = ("first_use_current_agent_host", "first_use_same_agent_setup_action")
