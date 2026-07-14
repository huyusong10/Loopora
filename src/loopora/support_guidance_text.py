from __future__ import annotations

from collections.abc import Mapping

from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.support_guidance_constants import (
    SUPPORT_LOCAL_ONLY_ITEMS_EN,
    SUPPORT_LOCAL_ONLY_ITEMS_ZH,
    SUPPORT_PUBLIC_PASTE_ITEMS_EN,
    SUPPORT_PUBLIC_PASTE_ITEMS_ZH,
    SUPPORT_REDACTION_ITEMS,
    SUPPORT_REDACTION_ITEMS_ZH,
)


def support_payload_language(payload: Mapping[str, object]) -> str:
    try:
        return normalize_fit_guidance_language(str(payload.get("language") or "en"))
    except ValueError:
        return "en"


def support_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english


def support_redaction_items(language: str) -> list[str]:
    return SUPPORT_REDACTION_ITEMS_ZH if language == "zh" else SUPPORT_REDACTION_ITEMS


def support_public_paste_items(language: str) -> list[str]:
    return SUPPORT_PUBLIC_PASTE_ITEMS_ZH if language == "zh" else SUPPORT_PUBLIC_PASTE_ITEMS_EN


def support_local_only_items(language: str) -> list[str]:
    return SUPPORT_LOCAL_ONLY_ITEMS_ZH if language == "zh" else SUPPORT_LOCAL_ONLY_ITEMS_EN


def support_posting_guidance_text(payload: Mapping[str, object], *, language: str) -> str:
    if bool(payload.get("target_project_report_only")):
        return support_text(
            language,
            "Run ready preferred-bundle/fallback-report/identity commands locally; this can produce redacted evidence, but setup still needs a usable target project. "
            "Support JSON is route metadata, and command fields are local-only. In public issues, paste the public issue support bundle first; use redacted report/version output only when requested, "
            "not command lines that contain local paths.",
            "请在本地运行已就绪的优先支持包/兜底报告/身份命令；这可以生成脱敏证据，但设置仍需要可用的目标项目。support JSON 是路由元数据，"
            "其中命令字段仅供本地使用。公开 issue 中优先粘贴公开 issue 支持包；仅在被要求时再提供脱敏报告/版本输出，不要粘贴包含本地路径的命令行。",
        )
    if bool(payload.get("command_fields_executable")):
        return support_text(
            language,
            "Run these commands locally; support JSON is route metadata, and command fields are local-only. "
            "In public issues, paste the public issue support bundle first; use redacted report/version output only when requested, not command lines that contain local paths.",
            "请在本地运行这些命令；support JSON 是路由元数据，其中命令字段仅供本地使用。"
            "公开 issue 中优先粘贴公开 issue 支持包；仅在被要求时再提供脱敏报告/版本输出，不要粘贴包含本地路径的命令行。",
        )
    return support_text(
        language,
        "Run only ready commands locally; preferred-bundle/fallback-report commands are preview-only until a target project is supplied. "
        "Support JSON is route metadata, and command fields are local-only. In public issues, paste the public issue support bundle first; use redacted report/version output only when requested, "
        "not command lines that contain local paths.",
        "只在本地运行已就绪的命令；优先支持包/兜底报告命令在提供目标项目之前只是预览。support JSON 是路由元数据，"
        "其中命令字段仅供本地使用。公开 issue 中优先粘贴公开 issue 支持包；仅在被要求时再提供脱敏报告/版本输出，不要粘贴包含本地路径的命令行。",
    )


def support_local_command_lines(
    payload: Mapping[str, object],
    *,
    commands: Mapping[str, object],
    language: str,
) -> list[str]:
    public_issue_bundle_command = str(commands.get("public_issue_bundle") or "")
    version_command = str(commands.get("version") or "")
    version_json_command = str(commands.get("version_json") or "")
    public_doctor_command = str(commands.get("public_doctor") or "")
    lines = [
        support_text(
            language,
            "Run locally; paste generated outputs only:",
            "在本地运行；只粘贴生成的输出:",
        ),
        support_text(
            language,
            f"- compact version/source identity command: {version_command}",
            f"- 紧凑版本/源码身份命令: {version_command}",
        ),
        support_text(
            language,
            f"- structured version/source identity command: {version_json_command}",
            f"- 结构化版本/源码身份命令: {version_json_command}",
        ),
    ]
    if bool(payload.get("command_fields_executable")):
        lines.insert(
            1,
            support_text(
                language,
                f"- preferred public issue support bundle command: {public_issue_bundle_command}",
                f"- 优先公开 issue 支持包命令: {public_issue_bundle_command}",
            ),
        )
        lines.insert(
            2,
            support_text(
                language,
                f"- fallback redacted readiness report command (when requested): {public_doctor_command}",
                f"- 兜底脱敏就绪报告命令（被要求时）: {public_doctor_command}",
            ),
        )
        return lines
    lines.extend(
        [
            support_text(
                language,
                "Preview command shape; do not run support-bundle/fallback-report commands until the target project is supplied:",
                "命令形状预览；提供目标项目之前不要运行支持包/兜底报告命令:",
            ),
            support_text(
                language,
                f"- preferred public issue support bundle command shape: {public_issue_bundle_command}",
                f"- 优先公开 issue 支持包命令形状: {public_issue_bundle_command}",
            ),
            support_text(
                language,
                f"- fallback redacted readiness report command shape (when requested): {public_doctor_command}",
                f"- 兜底脱敏就绪报告命令形状（被要求时）: {public_doctor_command}",
            ),
        ]
    )
    return lines


def support_web_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    links = payload.get("local_links") if isinstance(payload.get("local_links"), Mapping) else {}
    web_support_url = str(links.get("web_support") or "").strip()
    if not web_support_url:
        return []
    return [
        support_text(
            language,
            f"Local Web Support page for this Web target: {web_support_url}",
            f"当前 Web 目标的本地支持页: {web_support_url}",
        )
    ]


def support_target_project_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    if not bool(payload.get("target_project_required")):
        return support_target_project_state_lines(payload, language=language)
    rerun_command = _support_action_command(payload, "choose_workdir_for_public_report")
    return [
        support_text(
            language,
            "Target project: not supplied; rerun support from the target project before copying preferred bundle or fallback report commands.",
            "目标项目：尚未提供；请先从目标项目重跑 support，再复制优先支持包或兜底报告命令。",
        ),
        support_text(
            language,
            f"Target-project support command: {rerun_command}",
            f"目标项目 support 命令: {rerun_command}",
        ),
    ]


def support_target_project_state_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    if not bool(payload.get("target_project_report_only")):
        return []
    status = str(payload.get("target_project_status") or "unknown").strip() or "unknown"
    status_label = support_target_project_status_label(status, language=language)
    return [
        support_text(
            language,
            f"Target project state: {status_label}; preferred bundle/fallback report commands are ready, but setup still needs a usable target project.",
            f"目标项目状态：{status_label}；优先支持包/兜底报告命令已就绪，但设置仍需要可用的目标项目。",
        )
    ]


def support_target_project_status_label(status: str, *, language: str) -> str:
    labels = {
        "required": ("not supplied", "尚未提供"),
        "missing": ("missing", "不存在"),
        "not_directory": ("not a directory", "不是目录"),
        "unavailable": ("unavailable", "无法检查"),
        "ready": ("ready", "已就绪"),
    }
    english, chinese = labels.get(status, (status.replace("_", " "), status.replace("_", " ")))
    return chinese if language == "zh" else english


def support_command_status_lines(payload: Mapping[str, object], *, language: str) -> list[str]:
    if bool(payload.get("command_fields_executable")):
        return []
    raw_blockers = payload.get("command_field_blockers")
    blockers = raw_blockers if isinstance(raw_blockers, list) else []
    labels = [label for label in (support_command_blocker_label(str(blocker or "").strip(), language=language) for blocker in blockers) if label]
    if not labels:
        return []
    return [
        support_text(
            language,
            f"- preview only: preferred bundle/fallback report commands are not ready yet; first resolve: {'; '.join(labels)}.",
            f"- 仅预览：优先支持包/兜底报告命令尚未就绪；请先处理：{'; '.join(labels)}。",
        )
    ]


def support_command_blocker_label(blocker: str, *, language: str) -> str:
    if blocker == "target_project_required":
        return support_text(language, "target project", "目标项目")
    return blocker.replace("_", " ")


def _support_action_command(payload: Mapping[str, object], kind: str) -> str:
    actions = payload.get("next_actions") if isinstance(payload.get("next_actions"), list) else []
    for action in actions:
        if isinstance(action, Mapping) and str(action.get("kind") or "") == kind:
            return str(action.get("command") or "").strip()
    return ""
