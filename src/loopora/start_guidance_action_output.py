from __future__ import annotations

from collections.abc import Mapping

from loopora.start_guidance_actions import _text


def _action_line(action: Mapping[str, object], *, language: str) -> str:
    label = _action_label(str(action.get("kind") or "").strip(), language=language)
    command = str(action.get("command") or "").strip()
    command_template = str(action.get("command_template") or "").strip()
    note = str(action.get("note") or "").strip()
    suffix = f" ({note})" if note else ""
    if command:
        line = f"- {label}: {command}{suffix}"
    elif command_template:
        line = f"- {label}: {command_template}{suffix}"
    else:
        line = f"- {label}{suffix}"
    open_url = str(action.get("open_url") or "").strip()
    if open_url:
        open_label = _text(language, "Open after Web starts", "Web 启动后打开")
        line = f"{line}\n  {open_label}: {open_url}"
    return line


def _action_label(kind: str, *, language: str) -> str:
    labels = {
        "check_fit_first": ("Check fit first", "先判断适配性"),
        "complete_review_inputs": ("Complete review inputs", "补齐判断输入"),
        "continue_fit_review_in_web": ("Continue fit review in Web", "在 Web 中继续适配审查"),
        "complete_direct_decision": ("Complete direct-path decision", "补齐直接路径决策"),
        "create_workdir": ("Create target directory", "创建目标目录"),
        "choose_workdir": ("Choose target project", "选择目标目录"),
        "confirm_readiness": ("Confirm readiness", "确认就绪"),
        "create_recovery_archive": ("Create private recovery archive", "创建私有恢复归档"),
        "preview_app_database_reset": ("Preview App database reset", "预览 App 数据库 reset"),
        "use_temporary_app_home": ("Temporary Web preview", "临时 Web 预览"),
        "use_matching_loopora_version_or_reset": (
            "Use matching Loopora version or preview reset",
            "使用匹配 Loopora 版本或预览 reset",
        ),
        "inspect_or_reset_app_state": ("Inspect or reset App state", "检查或 reset App 状态"),
        "inspect_app_state": ("Inspect App state", "检查 App 状态"),
        "fill_review_inputs": ("Complete review inputs", "补齐判断输入"),
        "continue_if_strong_fit": ("Continue if still a strong fit", "如果仍为强适配则继续"),
        "record_direct_decision": ("Record direct-path decision", "记录直接路径决策"),
        "use_direct_agent_or_hard_checks": ("Direct Agent or hard checks", "改用直接 Agent 或硬性检查"),
        "support": ("Usage/setup help", "使用/设置帮助"),
    }
    if kind in labels:
        english, chinese = labels[kind]
        return _text(language, english, chinese)
    return kind.replace("_", " ")
