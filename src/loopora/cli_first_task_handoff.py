from __future__ import annotations

from collections.abc import Callable

import typer

CopyRuleTransform = Callable[[dict[str, object], str], str]
FIRST_TASK_ORIENTATION_EXAMPLE_ZH = (
    "/loopora-plan\n\n"
    "Loopora 适配理由：权限、重放、异常与回滚证明需要多轮证据审查；"
    "任务目标：交付保留审计轨迹的支持运营事件面板；"
    "伪完成风险：只有正常路径 UI，没有重放/异常证明，缺少权限检查，或回滚含糊；"
    "必需证据：项目测试、一次浏览器旅程，以及 GateKeeper 可审查的证据摘要；"
    "判断取舍：保持范围收敛，数据安全未被证明时必须失败关闭。"
)


def first_task_handoff_lines(
    payload: dict[str, object],
    *,
    example: str | None = None,
    copy_rule_transform: CopyRuleTransform | None = None,
    language: str = "en",
) -> list[str]:
    example_text = str(example if example is not None else payload.get("first_task_message_example") or "").strip()
    if not example_text:
        return []
    policy = payload.get("first_task_handoff_policy") if isinstance(payload.get("first_task_handoff_policy"), dict) else {}
    copy_rule = str(policy.get("copy_rule") or "").strip()
    if copy_rule and copy_rule_transform is not None:
        copy_rule = copy_rule_transform(policy, copy_rule)
    lines = ["首次任务消息交接：" if language == "zh" else "first task message handoff:"]
    status_line = _first_task_handoff_status_line(payload, language=language)
    if status_line:
        lines.append(status_line)
    if language == "zh":
        lines.append("- 已完成 fit 审查：把 fit 输出的完整可复制 /loopora-plan 交接作为一条 Agent 消息粘贴。")
    elif copy_rule:
        lines.append(f"- completed fit review: {copy_rule}")
    else:
        lines.append("- completed fit review: paste its copyable /loopora-plan handoff as one Agent message.")
    lines.append("- 通用方向示例（不是已完成审查）：" if language == "zh" else "- generic orientation example (not a completed review):")
    lines.append(example_text)
    return lines


def _first_task_handoff_status_line(payload: dict[str, object], *, language: str = "en") -> str:
    blockers = [
        _first_task_handoff_blocker_label(str(blocker or "").strip(), language=language)
        for blocker in list(payload.get("first_task_handoff_blockers") or [])
    ]
    labels = [label for label in blockers if label]
    if not labels:
        return ""
    joined = "；".join(labels) if language == "zh" else "; ".join(labels)
    if language == "zh":
        return f"- 仅预览：/loopora-plan 交接尚未就绪；请先解决：{joined}。"
    return f"- preview only: /loopora-plan handoff is not ready yet; first resolve: {joined}."


def _first_task_handoff_blocker_label(blocker: str, *, language: str = "en") -> str:
    labels = {
        "target_project_required": "usable target project",
        "target_project_unready": "usable target project",
        "same_agent_entry_required": "same-Agent project entry",
        "app_state_not_ready": "local App state",
    }
    zh_labels = {
        "target_project_required": "可用目标项目",
        "target_project_unready": "可用目标项目",
        "same_agent_entry_required": "同一 Agent 项目入口",
        "app_state_not_ready": "本地 App 状态",
    }
    source = zh_labels if language == "zh" else labels
    return source.get(blocker, blocker.replace("_", " "))


def echo_first_task_handoff(
    payload: dict[str, object],
    *,
    example: str | None = None,
    copy_rule_transform: CopyRuleTransform | None = None,
    language: str = "en",
) -> None:
    for line in first_task_handoff_lines(
        payload,
        example=example,
        copy_rule_transform=copy_rule_transform,
        language=language,
    ):
        typer.echo(line)
